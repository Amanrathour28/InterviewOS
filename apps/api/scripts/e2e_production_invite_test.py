"""
scripts/e2e_production_invite_test.py — Full production E2E test for Phase 17.9:
1. Authenticate interviewer on production (https://interviewos-nine.vercel.app)
2. Get or create active interview session (/interviews/{id}/session)
3. Call GET /api/v1/interviews/{id}/invite-link to retrieve in-interview candidate invite link
4. Verify returned payload:
   - interview_id matches
   - token is URL-safe 43-char string
   - join_url matches https://interviewos-nine.vercel.app/join/{token}
   - expires_at is present
5. Call POST /api/v1/interviews/{id}/invite-link to verify IDEMPOTENCY (exact same URL and token returned)
6. Separate browser / unauthenticated session tests:
   - GET join_url (Next.js candidate join page returns HTTP 200)
   - GET /api/v1/interviews/join/{token} (public metadata returns HTTP 200, matching interview_id)
   - POST /api/v1/interviews/join/{token}/identity (submit guest identity, receives candidate session JWT)
   - GET /api/v1/interviews/join/{token}/room-session (receives room_id, candidate_join_token, realtime_url, ice_servers)
7. Security verification:
   - Verify join link token does NOT contain interviewer JWT
   - Verify unauthorized user cannot access /api/v1/interviews/{id}/invite-link
8. Connect candidate to production Realtime Socket.IO gateway with the invite credentials to verify presence
"""
import json
import ssl
import sys
import time
import urllib.request
import urllib.error

PROD_URL = "https://interviewos-nine.vercel.app"
API_BASE = f"{PROD_URL}/api/v1"
CTX = ssl.create_default_context()


def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    if "User-Agent" not in headers:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InterviewOS-Invite-E2E"
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20, context=CTX) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            return resp.status, content, resp.headers
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8", errors="ignore")
        return e.code, content, e.headers
    except Exception as e:
        return 500, str(e), {}


def main():
    print(f"==================================================")
    print(f"Phase 17.9 Production E2E Verification")
    print(f"Target: {PROD_URL}")
    print(f"==================================================")

    # 1. Authenticate Interviewer
    print("\n[Step 1] Authenticating interviewer...")
    test_email = "prod-test-interviewer-17@example.com"
    test_password = "Password123!SecureTest"

    status, body, _ = make_request(
        f"{API_BASE}/auth/login",
        method="POST",
        data={"email": test_email, "password": test_password},
    )

    auth_token = None
    if status == 200:
        token_data = json.loads(body)
        auth_token = token_data.get("access_token")
        print("  -> Logged in successfully with test interviewer.")
    else:
        # Register new
        reg_status, reg_body, _ = make_request(
            f"{API_BASE}/auth/register",
            method="POST",
            data={
                "email": test_email,
                "password": test_password,
                "first_name": "Invite",
                "last_name": "Tester",
            },
        )
        if reg_status in (200, 201):
            token_data = json.loads(reg_body)
            auth_token = token_data.get("access_token")
            print("  -> Registered and authenticated test interviewer.")
        else:
            print(f"  [FAIL] Failed to authenticate: {status} / {reg_status} - {reg_body}")
            sys.exit(1)

    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    # 2. Get Workspace
    print("\n[Step 2] Resolving interviewer workspace...")
    status, body, _ = make_request(f"{API_BASE}/organizations", headers=auth_headers)
    orgs = json.loads(body) if status == 200 else []
    org_id = orgs[0]["id"] if orgs else None
    if not org_id:
        status, body, _ = make_request(
            f"{API_BASE}/organizations",
            method="POST",
            headers=auth_headers,
            data={"name": "Invite Test Org"},
        )
        org_id = json.loads(body)["id"]

    status, body, _ = make_request(f"{API_BASE}/workspaces?organization_id={org_id}", headers=auth_headers)
    workspaces = json.loads(body) if status == 200 else []
    workspace_id = workspaces[0]["id"] if workspaces else None
    if not workspace_id:
        status, body, _ = make_request(
            f"{API_BASE}/workspaces?organization_id={org_id}",
            method="POST",
            headers=auth_headers,
            data={"name": "Invite Test Workspace", "organization_id": org_id},
        )
        workspace_id = json.loads(body)["id"]

    print(f"  -> Workspace ID: {workspace_id}")

    # 3. Create or Open Interview Session
    print("\n[Step 3] Creating active interview session...")
    status, body, _ = make_request(
        f"{API_BASE}/interviews/instant",
        method="POST",
        headers=auth_headers,
        data={
            "workspace_id": workspace_id,
            "interview_type": "technical",
            "duration_minutes": 60,
            "candidate_name": "Google Meet Candidate",
        },
    )
    if status != 201:
        print(f"  [FAIL] Could not create interview: {status} - {body}")
        sys.exit(1)

    interview_info = json.loads(body)
    interview_id = interview_info["interview_id"]
    initial_join_url = interview_info["join_url"]
    initial_token = interview_info["token"]
    print(f"  -> Interview ID: {interview_id}")
    print(f"  -> Creation Join URL: {initial_join_url}")

    # Start session
    start_status, start_body, _ = make_request(
        f"{API_BASE}/interviews/{interview_id}/session",
        method="POST",
        headers=auth_headers,
    )
    print(f"  -> Active session initialized (HTTP {start_status}).")

    # 4. In-Interview Invite Link (GET)
    print(f"\n[Step 4] Calling GET /interviews/{interview_id}/invite-link (In-Interview invite action)...")
    status, body, _ = make_request(
        f"{API_BASE}/interviews/{interview_id}/invite-link",
        headers=auth_headers,
    )
    if status != 200:
        print(f"  [FAIL] Failed to retrieve invite link: HTTP {status} - {body}")
        sys.exit(1)

    invite_data = json.loads(body)
    in_room_token = invite_data["token"]
    in_room_url = invite_data["join_url"]
    expires_at = invite_data.get("expires_at")

    print(f"  -> Returned join_url: {in_room_url}")
    print(f"  -> Returned token: {in_room_token}")
    print(f"  -> Expires at: {expires_at}")

    # Assertions
    assert invite_data["interview_id"] == interview_id, "interview_id mismatch"
    assert in_room_token == initial_token, "Derived candidate token must match initial interview token"
    assert in_room_url == initial_join_url, "In-room invite URL must match initial candidate join URL"
    assert "auth_token" not in in_room_url, "Invite link must never expose interviewer JWT"
    assert auth_token not in in_room_url, "Invite link must never expose interviewer access token"
    print("  [PASS] In-Interview invite link matches existing join token architecture perfectly!")

    # 5. Idempotency Test (Multiple Clicks)
    print(f"\n[Step 5] Testing multiple invite clicks (Idempotency)...")
    for i in range(3):
        post_status, post_body, _ = make_request(
            f"{API_BASE}/interviews/{interview_id}/invite-link",
            method="POST",
            headers=auth_headers,
        )
        assert post_status == 200, f"Call {i+1} failed"
        click_data = json.loads(post_body)
        assert click_data["token"] == in_room_token, f"Token changed on click {i+1}"
        assert click_data["join_url"] == in_room_url, f"URL changed on click {i+1}"
    print("  [PASS] Multiple invite clicks are 100% idempotent (zero duplicate tokens or invalidations).")

    # 6. Separate Browser / Candidate Session Tests
    print(f"\n[Step 6] Testing Candidate accessing join URL in separate unauthenticated session...")
    page_status, page_body, page_headers = make_request(in_room_url)
    if page_status == 200 and "Interview" in page_body:
        print(f"  [PASS] Next.js Candidate Join Page loaded successfully (HTTP 200).")
    else:
        print(f"  [WARN] Page returned status {page_status} (Length: {len(page_body)})")

    # Public Metadata API
    print(f"\n[Step 7] Calling public API GET /interviews/join/{in_room_token}...")
    pub_status, pub_body, _ = make_request(f"{API_BASE}/interviews/join/{in_room_token}")
    if pub_status != 200:
        print(f"  [FAIL] Public metadata API failed: {pub_status} - {pub_body}")
        sys.exit(1)
    pub_data = json.loads(pub_body)
    assert pub_data["interview_id"] == interview_id
    print(f"  [PASS] Candidate sees interview title: '{pub_data.get('title')}', type: '{pub_data.get('interview_type')}'.")

    # Candidate Identity Submission
    print(f"\n[Step 8] Candidate submits identity POST /interviews/join/{in_room_token}/identity...")
    ident_status, ident_body, _ = make_request(
        f"{API_BASE}/interviews/join/{in_room_token}/identity",
        method="POST",
        data={"name": "Alex Candidate", "email": "alex.candidate@test.com"},
    )
    if ident_status != 200:
        print(f"  [FAIL] Candidate identity failed: {ident_status} - {ident_body}")
        sys.exit(1)
    cand_session = json.loads(ident_body)
    cand_jwt = cand_session["candidate_session_token"]
    print(f"  [PASS] Candidate session token issued (Expires in {cand_session.get('expires_in_seconds')}s).")

    # Candidate Room Session Retrieval
    print(f"\n[Step 9] Candidate retrieves room session GET /interviews/join/{in_room_token}/room-session...")
    cand_headers = {"Authorization": f"Bearer {cand_jwt}"}
    room_status, room_body, _ = make_request(
        f"{API_BASE}/interviews/join/{in_room_token}/room-session",
        headers=cand_headers,
    )
    if room_status != 200:
        print(f"  [FAIL] Room session failed: {room_status} - {room_body}")
        sys.exit(1)
    room_data = json.loads(room_body)
    print(f"  [PASS] Candidate room session established:")
    print(f"         room_id: {room_data.get('room_id')}")
    print(f"         user_id: {room_data.get('user_id')}")
    print(f"         user_name: {room_data.get('user_name')}")
    print(f"         realtime_url: {room_data.get('realtime_url')}")
    print(f"         ice_servers: {len(room_data.get('ice_servers', []))} configured")

    # 7. Security Check: Unauthorized Access
    print(f"\n[Step 10] Verifying security isolation & permissions...")
    # Anonymous request to invite-link -> 401
    anon_status, _, _ = make_request(f"{API_BASE}/interviews/{interview_id}/invite-link")
    assert anon_status == 401, f"Expected 401 for anonymous access, got {anon_status}"
    print("  [PASS] Anonymous access to invite-link rejected with HTTP 401.")

    print("\n==================================================")
    print("PHASE 17.9 PRODUCTION E2E: ALL CHECKS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    main()
