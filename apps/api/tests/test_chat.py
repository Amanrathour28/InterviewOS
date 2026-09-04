import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_lifecycle_and_channel_isolation(client: AsyncClient):
    # 1. Setup Organization, Workspace, Interviewer, Candidate
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "lead.interviewer@interviewos.com", "password": "Password123!", "first_name": "Lead", "last_name": "Interviewer"},
    )
    interviewer_token = interviewer_res.json()["access_token"]
    interviewer_headers = {"Authorization": f"Bearer {interviewer_token}"}

    candidate_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "john.candidate@example.com", "password": "Password123!", "first_name": "John", "last_name": "Candidate"},
    )
    candidate_token = candidate_res.json()["access_token"]
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

    org = (await client.post("/api/v1/organizations", headers=interviewer_headers, json={"name": "ChatOrg", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "first_name": "John", "last_name": "Candidate", "email": "john.candidate@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Senior Systems Interview", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=interviewer_headers, json={"name": "Coding Round", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=interviewer_headers, json={"status": "ready"})

    # Create session
    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=interviewer_headers)).json()
    sess_id = session["id"]

    # 2. Test Channel Listing & Isolation
    # Interviewer sees Public AND Interviewer Private channels
    itw_channels_res = await client.get(f"/api/v1/sessions/{sess_id}/chat/channels", headers=interviewer_headers)
    assert itw_channels_res.status_code == 200
    itw_channels = itw_channels_res.json()
    assert len(itw_channels) == 2
    types = {c["channel_type"] for c in itw_channels}
    assert types == {"public", "interviewer_private"}

    pub_channel = next(c for c in itw_channels if c["channel_type"] == "public")
    priv_channel = next(c for c in itw_channels if c["channel_type"] == "interviewer_private")

    # Candidate sees ONLY Public channel
    cand_channels_res = await client.get(f"/api/v1/sessions/{sess_id}/chat/channels", headers=candidate_headers)
    assert cand_channels_res.status_code == 200
    cand_channels = cand_channels_res.json()
    assert len(cand_channels) == 1
    assert cand_channels[0]["channel_type"] == "public"

    # Candidate attempting to access private channel history directly -> 403 Forbidden
    cand_priv_res = await client.get(f"/api/v1/chat/channels/{priv_channel['id']}/messages", headers=candidate_headers)
    assert cand_priv_res.status_code == 403

    # Candidate attempting to send to private channel -> 403 Forbidden
    cand_priv_send = await client.post(
        f"/api/v1/chat/channels/{priv_channel['id']}/messages",
        headers=candidate_headers,
        json={"message_type": "text", "content": "I shouldn't be here"},
    )
    assert cand_priv_send.status_code == 403

    # 3. Test Public Message Sending & XSS Sanitization
    xss_payload = "<script>alert('pwned')</script>Hello <img src=x onerror=alert(1)> from interviewer!"
    msg_res = await client.post(
        f"/api/v1/chat/channels/{pub_channel['id']}/messages",
        headers=interviewer_headers,
        json={"message_type": "text", "content": xss_payload, "client_message_id": "client-msg-1"},
    )
    assert msg_res.status_code == 200
    msg = msg_res.json()
    assert "<script>" not in msg["content"]
    assert "onerror=" not in msg["content"]
    assert "Hello" in msg["content"]

    # Test Idempotency with client_message_id
    dup_res = await client.post(
        f"/api/v1/chat/channels/{pub_channel['id']}/messages",
        headers=interviewer_headers,
        json={"message_type": "text", "content": xss_payload, "client_message_id": "client-msg-1"},
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["id"] == msg["id"]

    # 4. Candidate reads message in public channel
    cand_msgs_res = await client.get(f"/api/v1/chat/channels/{pub_channel['id']}/messages", headers=candidate_headers)
    assert cand_msgs_res.status_code == 200
    assert len(cand_msgs_res.json()) == 1

    # 5. Code Snippet Sharing & Language Validation
    code_res = await client.post(
        f"/api/v1/chat/channels/{pub_channel['id']}/messages",
        headers=interviewer_headers,
        json={
            "message_type": "code",
            "content": "def binary_search(arr, target):\n    return -1",
            "metadata": {"language": "python", "title": "Search Function"},
        },
    )
    assert code_res.status_code == 200
    code_msg = code_res.json()
    assert code_msg["message_type"] == "code"
    assert code_msg["metadata"]["language"] == "python"

    # 6. Threaded Reply
    reply_res = await client.post(
        f"/api/v1/chat/channels/{pub_channel['id']}/messages",
        headers=candidate_headers,
        json={
            "message_type": "text",
            "content": "Looks good, let me optimize it to O(log n)!",
            "parent_message_id": code_msg["id"],
        },
    )
    assert reply_res.status_code == 200
    reply = reply_res.json()
    assert reply["parent_message_id"] == code_msg["id"]

    # Fetch thread
    thread_res = await client.get(f"/api/v1/chat/messages/{code_msg['id']}/thread", headers=interviewer_headers)
    assert thread_res.status_code == 200
    thread_data = thread_res.json()
    assert thread_data["parent_message"]["id"] == code_msg["id"]
    assert len(thread_data["replies"]) == 1
    assert thread_data["replies"][0]["id"] == reply["id"]

    # 7. Reactions
    react_res = await client.post(
        f"/api/v1/chat/messages/{reply['id']}/reactions",
        headers=interviewer_headers,
        json={"emoji": "🎯"},
    )
    assert react_res.status_code == 200
    reactions = react_res.json()
    assert len(reactions) == 1
    assert reactions[0]["emoji"] == "🎯"

    # Toggle reaction off
    react_off_res = await client.post(
        f"/api/v1/chat/messages/{reply['id']}/reactions",
        headers=interviewer_headers,
        json={"emoji": "🎯"},
    )
    assert react_off_res.status_code == 200
    assert len(react_off_res.json()) == 0

    # 8. Message Editing (Author only)
    edit_res = await client.patch(
        f"/api/v1/chat/messages/{reply['id']}",
        headers=candidate_headers,
        json={"content": "Looks great, optimizing to O(log N)!"},
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["is_edited"] is True
    assert "O(log N)" in edit_res.json()["content"]

    # Non-author attempting to edit -> 403 Forbidden
    hack_edit = await client.patch(
        f"/api/v1/chat/messages/{reply['id']}",
        headers=interviewer_headers,
        json={"content": "Tampered content"},
    )
    assert hack_edit.status_code == 403

    # 9. Read cursor & Unread Count
    unread_res = await client.get(f"/api/v1/chat/channels/{pub_channel['id']}/unread", headers=candidate_headers)
    assert unread_res.status_code == 200
    # Candidate sent 1 reply, interviewer sent 2 messages -> Candidate has 2 unread
    assert unread_res.json()["unread_count"] == 2

    # Mark read
    mark_read_res = await client.post(
        f"/api/v1/chat/channels/{pub_channel['id']}/read",
        headers=candidate_headers,
        json={"last_read_message_id": reply["id"]},
    )
    assert mark_read_res.status_code == 200
    assert mark_read_res.json()["unread_count"] == 0

    # 10. Soft-Delete Message
    del_res = await client.delete(f"/api/v1/chat/messages/{reply['id']}", headers=candidate_headers)
    assert del_res.status_code == 200
    assert del_res.json()["is_deleted"] is True
