import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import (
    ChatChannel,
    ChatChannelType,
    ChatMessage,
    ChatMessageType,
    ChatReaction,
    ChatReadState,
)
from app.models.session import InterviewSession, SessionStatus
from app.schemas.chat import (
    ChatMessageResponse,
    ChatReactionResponse,
    MessageCreateRequest,
    MessageEditRequest,
)
from app.services.session_service import session_service


class ChatService:
    @staticmethod
    def sanitize_content(content: str) -> str:
        """Sanitizes plain-text / markdown content to protect against XSS and unsafe script injection."""
        if not content:
            return ""
        # Disallow raw <script> and dangerous attributes
        sanitized = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", content, flags=re.DOTALL | re.IGNORECASE)
        sanitized = re.sub(r"javascript\s*:", "blocked-scheme:", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"onerror\s*=", "blocked-attr=", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"onload\s*=", "blocked-attr=", sanitized, flags=re.IGNORECASE)
        return sanitized.strip()

    async def ensure_session_channels(
        self, session: InterviewSession, db: AsyncSession
    ) -> List[ChatChannel]:
        """Idempotently ensures that standard Public and Interviewer-Private channels exist for the session."""
        result = await db.execute(
            select(ChatChannel).where(ChatChannel.session_id == session.id)
        )
        existing_channels = list(result.scalars().all())
        existing_types = {c.channel_type for c in existing_channels}

        created = []
        if ChatChannelType.PUBLIC not in existing_types:
            pub = ChatChannel(
                id=uuid.uuid4(),
                session_id=session.id,
                workspace_id=session.workspace_id,
                channel_type=ChatChannelType.PUBLIC,
                name="Public Chat",
            )
            db.add(pub)
            created.append(pub)

        if ChatChannelType.INTERVIEWER_PRIVATE not in existing_types:
            priv = ChatChannel(
                id=uuid.uuid4(),
                session_id=session.id,
                workspace_id=session.workspace_id,
                channel_type=ChatChannelType.INTERVIEWER_PRIVATE,
                name="Private Interviewer Chat",
            )
            db.add(priv)
            created.append(priv)

        if created:
            await db.commit()
            for c in created:
                await db.refresh(c)

        # Re-fetch all
        result = await db.execute(
            select(ChatChannel).where(ChatChannel.session_id == session.id)
        )
        return list(result.scalars().all())

    async def get_accessible_channels(
        self, session: InterviewSession, is_interviewer: bool, db: AsyncSession
    ) -> List[ChatChannel]:
        """Returns channels accessible to the user based on role."""
        all_channels = await self.ensure_session_channels(session, db)
        if is_interviewer:
            return all_channels
        # Candidates can only access public channels
        return [c for c in all_channels if c.channel_type == ChatChannelType.PUBLIC]

    async def get_channel_or_404(
        self, channel_id: uuid.UUID, is_interviewer: bool, db: AsyncSession
    ) -> ChatChannel:
        """Fetches channel and enforces role-based access isolation."""
        result = await db.execute(
            select(ChatChannel).where(ChatChannel.id == channel_id)
        )
        channel = result.scalar_one_or_none()
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat channel not found",
            )

        if channel.channel_type == ChatChannelType.INTERVIEWER_PRIVATE and not is_interviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidates are forbidden from accessing the private interviewer channel",
            )
        return channel

    async def send_message(
        self,
        channel_id: uuid.UUID,
        session: InterviewSession,
        sender_id: Optional[uuid.UUID],
        sender_name: str,
        sender_role: str,
        is_interviewer: bool,
        request: MessageCreateRequest,
        db: AsyncSession,
    ) -> ChatMessage:
        """Sends a persistent chat message or structured code snippet."""
        # 1. Enforce channel permission
        channel = await self.get_channel_or_404(channel_id, is_interviewer, db)

        # 2. Check session state (read-only if completed or cancelled)
        if session.status in (SessionStatus.COMPLETED, SessionStatus.CANCELLED, SessionStatus.EXPIRED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chat is read-only because session is {session.status.value}",
            )

        # 3. Handle client_message_id idempotency
        if request.client_message_id:
            existing_res = await db.execute(
                select(ChatMessage)
                .options(selectinload(ChatMessage.reactions))
                .where(
                    and_(
                        ChatMessage.channel_id == channel.id,
                        ChatMessage.client_message_id == request.client_message_id,
                        ChatMessage.is_deleted == False,
                    )
                )
            )
            existing_msg = existing_res.scalar_one_or_none()
            if existing_msg:
                return existing_msg

        # 4. Handle threaded reply validation
        if request.parent_message_id:
            parent_res = await db.execute(
                select(ChatMessage).where(ChatMessage.id == request.parent_message_id)
            )
            parent_msg = parent_res.scalar_one_or_none()
            if not parent_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent message for thread reply not found",
                )
            if parent_msg.channel_id != channel.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Thread reply must belong to the exact same channel as parent message",
                )

        # 5. Sanitize content
        sanitized_content = self.sanitize_content(request.content)
        if not sanitized_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content cannot be empty",
            )

        # 6. Create message
        message = ChatMessage(
            id=uuid.uuid4(),
            channel_id=channel.id,
            session_id=session.id,
            workspace_id=session.workspace_id,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_role=sender_role,
            parent_message_id=request.parent_message_id,
            message_type=ChatMessageType(request.message_type),
            content=sanitized_content,
            metadata_json=request.metadata or {},
            client_message_id=request.client_message_id,
            is_edited=False,
            is_deleted=False,
        )
        db.add(message)

        # 7. Log monotonic session event
        event_type = "CHAT_THREAD_REPLY_CREATED" if request.parent_message_id else "CHAT_MESSAGE_CREATED"
        event_payload = {
            "message_id": str(message.id),
            "channel_id": str(channel.id),
            "channel_type": channel.channel_type.value,
            "sender_id": str(sender_id) if sender_id else None,
            "sender_name": sender_name,
            "sender_role": sender_role,
            "message_type": message.message_type.value,
            "content": sanitized_content[:200],  # truncated summary for event log
            "parent_message_id": str(request.parent_message_id) if request.parent_message_id else None,
        }
        await session_service.log_event(
            session=session,
            event_type=event_type,
            actor_id=sender_id,
            actor_role=sender_role,
            payload=event_payload,
            db=db,
        )

        await db.commit()
        await db.refresh(message)
        return message

    async def edit_message(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        is_interviewer: bool,
        request: MessageEditRequest,
        db: AsyncSession,
    ) -> ChatMessage:
        """Edits an existing message (author only)."""
        result = await db.execute(
            select(ChatMessage)
            .options(selectinload(ChatMessage.reactions))
            .where(ChatMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message or message.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        # Only sender can edit message
        if message.sender_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot edit a message sent by another user",
            )

        sanitized_content = self.sanitize_content(request.content)
        if not sanitized_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Edited content cannot be empty",
            )

        message.content = sanitized_content
        if request.metadata is not None:
            message.metadata_json = request.metadata
        message.is_edited = True
        message.updated_at = datetime.now(timezone.utc)

        sess = await session_service.get_session(message.session_id, db)
        await session_service.log_event(
            session=sess,
            event_type="CHAT_MESSAGE_UPDATED",
            actor_id=user_id,
            actor_role=message.sender_role,
            payload={"message_id": str(message.id), "channel_id": str(message.channel_id)},
            db=db,
        )

        await db.commit()
        await db.refresh(message)
        return message

    async def delete_message(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        is_interviewer: bool,
        db: AsyncSession,
    ) -> ChatMessage:
        """Soft-deletes a message (author or interviewer)."""
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message or message.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        # Author or interviewer can delete
        if message.sender_id != user_id and not is_interviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot delete another participant's message",
            )

        message.is_deleted = True
        message.deleted_at = datetime.now(timezone.utc)

        sess = await session_service.get_session(message.session_id, db)
        await session_service.log_event(
            session=sess,
            event_type="CHAT_MESSAGE_DELETED",
            actor_id=user_id,
            actor_role=message.sender_role,
            payload={"message_id": str(message.id), "channel_id": str(message.channel_id)},
            db=db,
        )

        await db.commit()
        await db.refresh(message)
        return message

    async def toggle_reaction(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        user_name: str,
        emoji: str,
        is_interviewer: bool,
        db: AsyncSession,
    ) -> Tuple[bool, List[ChatReaction]]:
        """Toggles an emoji reaction on a message."""
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message or message.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        # Check channel access
        await self.get_channel_or_404(message.channel_id, is_interviewer, db)

        # Check existing reaction
        react_res = await db.execute(
            select(ChatReaction).where(
                and_(
                    ChatReaction.message_id == message_id,
                    ChatReaction.user_id == user_id,
                    ChatReaction.emoji == emoji,
                )
            )
        )
        existing_reaction = react_res.scalar_one_or_none()

        if existing_reaction:
            await db.delete(existing_reaction)
            is_added = False
            event_type = "CHAT_REACTION_REMOVED"
        else:
            new_reaction = ChatReaction(
                id=uuid.uuid4(),
                message_id=message_id,
                user_id=user_id,
                user_name=user_name,
                emoji=emoji,
            )
            db.add(new_reaction)
            is_added = True
            event_type = "CHAT_REACTION_ADDED"

        sess = await session_service.get_session(message.session_id, db)
        await session_service.log_event(
            session=sess,
            event_type=event_type,
            actor_id=user_id,
            actor_role="participant",
            payload={
                "message_id": str(message_id),
                "channel_id": str(message.channel_id),
                "emoji": emoji,
                "user_id": str(user_id),
                "user_name": user_name,
                "is_added": is_added,
            },
            db=db,
        )

        await db.commit()

        # Fetch updated reactions
        updated_res = await db.execute(
            select(ChatReaction).where(ChatReaction.message_id == message_id)
        )
        return is_added, list(updated_res.scalars().all())

    async def get_messages(
        self,
        channel_id: uuid.UUID,
        is_interviewer: bool,
        limit: int = 50,
        before_id: Optional[uuid.UUID] = None,
        db: AsyncSession = None,
    ) -> List[ChatMessageResponse]:
        """Fetches top-level messages in chronological order with cursor pagination."""
        await self.get_channel_or_404(channel_id, is_interviewer, db)

        query = (
            select(ChatMessage)
            .options(
                selectinload(ChatMessage.reactions),
                selectinload(ChatMessage.replies),
            )
            .where(
                and_(
                    ChatMessage.channel_id == channel_id,
                    ChatMessage.parent_message_id == None,
                    ChatMessage.is_deleted == False,
                )
            )
        )

        if before_id:
            before_res = await db.execute(
                select(ChatMessage.created_at).where(ChatMessage.id == before_id)
            )
            before_ts = before_res.scalar_one_or_none()
            if before_ts:
                query = query.where(ChatMessage.created_at < before_ts)

        query = query.order_by(ChatMessage.created_at.desc()).limit(min(limit, 100))
        result = await db.execute(query)
        messages = list(result.scalars().all())
        messages.reverse()  # Return in chronological order

        return [
            ChatMessageResponse(
                id=m.id,
                channel_id=m.channel_id,
                session_id=m.session_id,
                workspace_id=m.workspace_id,
                sender_id=m.sender_id,
                sender_name=m.sender_name,
                sender_role=m.sender_role,
                parent_message_id=m.parent_message_id,
                message_type=m.message_type.value,
                content=m.content,
                metadata=m.metadata_json or {},
                client_message_id=m.client_message_id,
                is_edited=m.is_edited,
                is_deleted=m.is_deleted,
                reply_count=len([r for r in m.replies if not r.is_deleted]),
                reactions=[
                    ChatReactionResponse(
                        id=r.id,
                        message_id=r.message_id,
                        user_id=r.user_id,
                        user_name=r.user_name,
                        emoji=r.emoji,
                        created_at=r.created_at,
                    )
                    for r in m.reactions
                ],
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in messages
        ]

    async def get_thread_detail(
        self,
        parent_message_id: uuid.UUID,
        is_interviewer: bool,
        db: AsyncSession,
    ) -> Tuple[ChatMessage, List[ChatMessage]]:
        """Fetches parent message and all replies in chronological order."""
        result = await db.execute(
            select(ChatMessage)
            .options(selectinload(ChatMessage.reactions))
            .where(ChatMessage.id == parent_message_id)
        )
        parent = result.scalar_one_or_none()
        if not parent or parent.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent message not found",
            )

        # Enforce channel permission
        await self.get_channel_or_404(parent.channel_id, is_interviewer, db)

        replies_res = await db.execute(
            select(ChatMessage)
            .options(selectinload(ChatMessage.reactions))
            .where(
                and_(
                    ChatMessage.parent_message_id == parent_message_id,
                    ChatMessage.is_deleted == False,
                )
            )
            .order_by(ChatMessage.created_at.asc())
        )
        replies = list(replies_res.scalars().all())
        return parent, replies

    async def update_read_state(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
        last_read_message_id: uuid.UUID,
        is_interviewer: bool,
        db: AsyncSession,
    ) -> ChatReadState:
        """Updates last read cursor for user in channel."""
        await self.get_channel_or_404(channel_id, is_interviewer, db)

        result = await db.execute(
            select(ChatReadState).where(
                and_(
                    ChatReadState.channel_id == channel_id,
                    ChatReadState.user_id == user_id,
                )
            )
        )
        read_state = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if read_state:
            read_state.last_read_message_id = last_read_message_id
            read_state.last_read_at = now
        else:
            read_state = ChatReadState(
                id=uuid.uuid4(),
                channel_id=channel_id,
                user_id=user_id,
                last_read_message_id=last_read_message_id,
                last_read_at=now,
            )
            db.add(read_state)

        await db.commit()
        await db.refresh(read_state)
        return read_state

    async def get_unread_count(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
        is_interviewer: bool,
        db: AsyncSession,
    ) -> int:
        """Returns unread message count for user in a channel."""
        await self.get_channel_or_404(channel_id, is_interviewer, db)

        read_res = await db.execute(
            select(ChatReadState.last_read_at).where(
                and_(
                    ChatReadState.channel_id == channel_id,
                    ChatReadState.user_id == user_id,
                )
            )
        )
        last_read_at = read_res.scalar_one_or_none()

        query = select(func.count(ChatMessage.id)).where(
            and_(
                ChatMessage.channel_id == channel_id,
                ChatMessage.is_deleted == False,
                ChatMessage.sender_id != user_id,
            )
        )
        if last_read_at:
            query = query.where(ChatMessage.created_at > last_read_at)

        count_res = await db.execute(query)
        return count_res.scalar() or 0


chat_service = ChatService()
