import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    get_session_participant,
    check_session_participant_access,
    SessionParticipantCaller,
)
from app.api.v1.endpoints.sessions import check_session_permission
from app.models.user import User
from app.models.chat import ChatChannelType
from app.schemas.chat import (
    ChatChannelResponse,
    ChatMessageResponse,
    ChatReactionResponse,
    MessageCreateRequest,
    MessageEditRequest,
    ReactionRequest,
    ReadCursorRequest,
    ThreadDetailResponse,
    UnreadCountResponse,
)
from app.services.chat_service import chat_service
from app.services.session_service import session_service

router = APIRouter()


@router.get("/sessions/{session_id}/chat/channels", response_model=List[ChatChannelResponse])
async def list_session_channels(
    session_id: uuid.UUID,
    caller: SessionParticipantCaller = Depends(get_session_participant),
    db: AsyncSession = Depends(get_db),
):
    """Lists all accessible chat channels for the caller in the specified session."""
    session = await session_service.get_session(session_id, db)
    is_interviewer, _ = await check_session_participant_access(
        session, caller, db, require_interviewer=False
    )

    channels = await chat_service.get_accessible_channels(session, is_interviewer, db)
    response = []
    for c in channels:
        unread = 0
        if caller.user:
            unread = await chat_service.get_unread_count(c.id, caller.user.id, is_interviewer, db)
        response.append(
            ChatChannelResponse(
                id=c.id,
                session_id=c.session_id,
                workspace_id=c.workspace_id,
                channel_type=c.channel_type.value,
                name=c.name,
                unread_count=unread,
                created_at=c.created_at,
            )
        )
    return response


@router.get("/chat/channels/{channel_id}/messages", response_model=List[ChatMessageResponse])
async def get_channel_messages(
    channel_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[uuid.UUID] = Query(None),
    caller: SessionParticipantCaller = Depends(get_session_participant),
    db: AsyncSession = Depends(get_db),
):
    """Fetches paginated top-level chat messages in chronological order."""
    # First fetch channel to resolve session
    channel = await chat_service.get_channel_or_404(channel_id, is_interviewer=True, db=db)
    session = await session_service.get_session(channel.session_id, db)
    is_interviewer, _ = await check_session_participant_access(
        session, caller, db, require_interviewer=False
    )

    if channel.channel_type == ChatChannelType.INTERVIEWER_PRIVATE and not is_interviewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates are forbidden from accessing the private interviewer channel",
        )

    return await chat_service.get_messages(
        channel_id=channel_id,
        is_interviewer=is_interviewer,
        limit=limit,
        before_id=before_id,
        db=db,
    )


@router.post("/chat/channels/{channel_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    channel_id: uuid.UUID,
    request: MessageCreateRequest,
    caller: SessionParticipantCaller = Depends(get_session_participant),
    db: AsyncSession = Depends(get_db),
):
    """Sends a new text message or structured code snippet."""
    channel = await chat_service.get_channel_or_404(channel_id, is_interviewer=True, db=db)
    session = await session_service.get_session(channel.session_id, db)
    is_interviewer, resolved_role = await check_session_participant_access(
        session, caller, db, require_interviewer=False
    )

    if channel.channel_type == ChatChannelType.INTERVIEWER_PRIVATE and not is_interviewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates are forbidden from posting to the private interviewer channel",
        )

    sender_id = caller.user.id if caller.user else None
    sender_name = caller.name

    msg = await chat_service.send_message(
        channel_id=channel_id,
        session=session,
        sender_id=sender_id,
        sender_name=sender_name,
        sender_role=resolved_role,
        is_interviewer=is_interviewer,
        request=request,
        db=db,
    )

    return ChatMessageResponse(
        id=msg.id,
        channel_id=msg.channel_id,
        session_id=msg.session_id,
        workspace_id=msg.workspace_id,
        sender_id=msg.sender_id,
        sender_name=msg.sender_name,
        sender_role=msg.sender_role,
        parent_message_id=msg.parent_message_id,
        message_type=msg.message_type.value,
        content=msg.content,
        metadata=msg.metadata_json or {},
        client_message_id=msg.client_message_id,
        is_edited=msg.is_edited,
        is_deleted=msg.is_deleted,
        reply_count=0,
        reactions=[],
        created_at=msg.created_at,
        updated_at=msg.updated_at,
    )


@router.patch("/chat/messages/{message_id}", response_model=ChatMessageResponse)
async def edit_message(
    message_id: uuid.UUID,
    request: MessageEditRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edits an existing message (author only)."""
    # Fetch message to resolve session
    from sqlalchemy import select
    from app.models.chat import ChatMessage
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    message = result.scalar_one_or_none()
    if not message or message.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    session = await session_service.get_session(message.session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    updated = await chat_service.edit_message(
        message_id=message_id,
        user_id=current_user.id,
        is_interviewer=is_interviewer,
        request=request,
        db=db,
    )

    return ChatMessageResponse(
        id=updated.id,
        channel_id=updated.channel_id,
        session_id=updated.session_id,
        workspace_id=updated.workspace_id,
        sender_id=updated.sender_id,
        sender_name=updated.sender_name,
        sender_role=updated.sender_role,
        parent_message_id=updated.parent_message_id,
        message_type=updated.message_type.value,
        content=updated.content,
        metadata=updated.metadata_json or {},
        client_message_id=updated.client_message_id,
        is_edited=updated.is_edited,
        is_deleted=updated.is_deleted,
        reply_count=0,
        reactions=[
            ChatReactionResponse(
                id=r.id,
                message_id=r.message_id,
                user_id=r.user_id,
                user_name=r.user_name,
                emoji=r.emoji,
                created_at=r.created_at,
            )
            for r in updated.reactions
        ],
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/chat/messages/{message_id}", response_model=ChatMessageResponse)
async def delete_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-deletes a message (author or interviewer)."""
    from sqlalchemy import select
    from app.models.chat import ChatMessage
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    message = result.scalar_one_or_none()
    if not message or message.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    session = await session_service.get_session(message.session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    deleted = await chat_service.delete_message(
        message_id=message_id,
        user_id=current_user.id,
        is_interviewer=is_interviewer,
        db=db,
    )

    return ChatMessageResponse(
        id=deleted.id,
        channel_id=deleted.channel_id,
        session_id=deleted.session_id,
        workspace_id=deleted.workspace_id,
        sender_id=deleted.sender_id,
        sender_name=deleted.sender_name,
        sender_role=deleted.sender_role,
        parent_message_id=deleted.parent_message_id,
        message_type=deleted.message_type.value,
        content="This message was deleted.",
        metadata={},
        client_message_id=deleted.client_message_id,
        is_edited=deleted.is_edited,
        is_deleted=deleted.is_deleted,
        reply_count=0,
        reactions=[],
        created_at=deleted.created_at,
        updated_at=deleted.updated_at,
    )


@router.get("/chat/messages/{message_id}/thread", response_model=ThreadDetailResponse)
async def get_message_thread(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetches parent message and all thread replies."""
    from sqlalchemy import select
    from app.models.chat import ChatMessage
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    message = result.scalar_one_or_none()
    if not message or message.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent message not found")

    session = await session_service.get_session(message.session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    parent, replies = await chat_service.get_thread_detail(message_id, is_interviewer, db)

    def to_schema(m: ChatMessage) -> ChatMessageResponse:
        return ChatMessageResponse(
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
            reply_count=0,
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

    return ThreadDetailResponse(
        parent_message=to_schema(parent),
        replies=[to_schema(r) for r in replies],
    )


@router.post("/chat/messages/{message_id}/reactions", response_model=List[ChatReactionResponse])
async def toggle_reaction(
    message_id: uuid.UUID,
    request: ReactionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Adds or removes an emoji reaction on a message."""
    from sqlalchemy import select
    from app.models.chat import ChatMessage
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    message = result.scalar_one_or_none()
    if not message or message.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    session = await session_service.get_session(message.session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    user_name = f"{current_user.first_name} {current_user.last_name}".strip()
    _, reactions = await chat_service.toggle_reaction(
        message_id=message_id,
        user_id=current_user.id,
        user_name=user_name,
        emoji=request.emoji,
        is_interviewer=is_interviewer,
        db=db,
    )

    return [
        ChatReactionResponse(
            id=r.id,
            message_id=r.message_id,
            user_id=r.user_id,
            user_name=r.user_name,
            emoji=r.emoji,
            created_at=r.created_at,
        )
        for r in reactions
    ]


@router.post("/chat/channels/{channel_id}/read", response_model=UnreadCountResponse)
async def mark_channel_read(
    channel_id: uuid.UUID,
    request: ReadCursorRequest,
    caller: SessionParticipantCaller = Depends(get_session_participant),
    db: AsyncSession = Depends(get_db),
):
    """Updates user last read cursor for channel."""
    channel = await chat_service.get_channel_or_404(channel_id, is_interviewer=True, db=db)
    session = await session_service.get_session(channel.session_id, db)
    is_interviewer, _ = await check_session_participant_access(session, caller, db, require_interviewer=False)

    if caller.user:
        await chat_service.update_read_state(
            channel_id=channel_id,
            user_id=caller.user.id,
            last_read_message_id=request.last_read_message_id,
            is_interviewer=is_interviewer,
            db=db,
        )
        unread = await chat_service.get_unread_count(channel_id, caller.user.id, is_interviewer, db)
    else:
        unread = 0

    return UnreadCountResponse(
        channel_id=channel_id,
        channel_type=channel.channel_type.value,
        unread_count=unread,
    )


@router.get("/chat/channels/{channel_id}/unread", response_model=UnreadCountResponse)
async def get_channel_unread(
    channel_id: uuid.UUID,
    caller: SessionParticipantCaller = Depends(get_session_participant),
    db: AsyncSession = Depends(get_db),
):
    """Returns unread message count for user in channel."""
    channel = await chat_service.get_channel_or_404(channel_id, is_interviewer=True, db=db)
    session = await session_service.get_session(channel.session_id, db)
    is_interviewer, _ = await check_session_participant_access(session, caller, db, require_interviewer=False)

    if caller.user:
        unread = await chat_service.get_unread_count(channel_id, caller.user.id, is_interviewer, db)
    else:
        unread = 0

    return UnreadCountResponse(
        channel_id=channel_id,
        channel_type=channel.channel_type.value,
        unread_count=unread,
    )
