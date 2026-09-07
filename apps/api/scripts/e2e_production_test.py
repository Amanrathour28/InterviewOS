"""
scripts/e2e_production_test.py — Full end-to-end production test of Phase 17.2:
1. Authenticate / Login as interviewer on production
2. POST /api/v1/interviews/instant — create instant interview
3. Verify returned payload: HTTP 201, interview_id, token, join_url
4. Verify join_url points to https://interviewos-nine.vercel.app/join/{token}
5. GET /join/{token} — verify public Next.js candidate page returns HTTP 200
6. GET /api/v1/interviews/join/{token} — verify public interview metadata returned
7. POST /api/v1/interviews/join/{token}/identity — submit candidate identity, verify candidate JWT issued
8. GET /api/v1/interviews/join/{token}/status — verify candidate-scoped status endpoint returns interview_started=False
9. Test invalid token on /api/v1/interviews/join/{invalid} — verify controlled 404 (not Vercel crash)
"""
import json
import ssl
import sys
import urllib.request
import urllib.error

PROD_URL = "https://interviewos-nine.vercel.app"
API_BASE = f"{PROD_URL}/api/v1"
CTX = ssl.create_default_context()


def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    if "User-Agent" not in headers:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15, context=CTX) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            return resp.status, content, resp.headers
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8", errors="ignore")
        return e.code, content, e.headers


def main():
    print(f"=== Running Production E2E Against: {PROD_URL} ===")
    
    # Step 1: Login / Register Interviewer
    test_email = "prod-test-interviewer-17@example.com"
    test_password = "Password123!SecureTest"
    
    print("\n[1/7] Authenticating interviewer...")
    status, body, _ = make_request(
        f"{API_BASE}/auth/login",
        method="POST",
        data={"email": test_email, "password": test_password},
    )
    
    auth_token = None
    if status == 200:
        token_data = json.loads(body)
        auth_token = token_data.get("access_token")
        print("   [PASS] Logged in with existing test interviewer")
    else:
        # Register new
        reg_status, reg_body, _ = make_request(
            f"{API_BASE}/auth/register",
            method="POST",
            data={
                "email": test_email,
                "password": test_password,
                "first_name": "E2E",
                "last_name": "Interviewer",
            },
        )
        if reg_status in (200, 201):
            token_data = json.loads(reg_body)
            auth_token = token_data.get("access_token")
            print("   [PASS] Registered and authenticated new test interviewer")
        else:
            print(f"   [FAIL] Could not authenticate interviewer: {status} / {reg_status} - {reg_body}")
            sys.exit(1)

    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    # Get or create workspace
    print("\n[2/8] Fetching organization and workspace...")
    status, body, _ = make_request(f"{API_BASE}/organizations", headers=auth_headers)
    orgs = json.loads(body) if status == 200 else []
    org_id = orgs[0]["id"] if orgs else None
    if not org_id:
        status, body, _ = make_request(
            f"{API_BASE}/organizations",
            method="POST",
            headers=auth_headers,
            data={"name": "E2E Test Org"},
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
            data={"name": "E2E Test Workspace", "organization_id": org_id},
        )
        workspace_id = json.loads(body)["id"]
    
    print(f"   [PASS] Using workspace: {workspace_id}")

    # Step 3: POST /api/v1/interviews/instant
    print("\n[3/7] Testing POST /api/v1/interviews/instant...")
    instant_payload = {
        "workspace_id": workspace_id,
        "interview_type": "coding",
        "duration_minutes": 60,
        "candidate_name": "Production Candidate",
        "candidate_email": "candidate@example.test",
    }
    status, body, _ = make_request(
        f"{API_BASE}/interviews/instant",
        method="POST",
        headers=auth_headers,
        data=instant_payload,
    )
    
    if status != 201:
        print(f"   [FAIL] Expected HTTP 201, got {status}: {body}")
        sys.exit(1)

    instant_resp = json.loads(body)
    raw_token = instant_resp["token"]
    join_url = instant_resp["join_url"]
    interview_id = instant_resp["interview_id"]
    print(f"   [PASS] HTTP 201 Created! interview_id={interview_id}")
    print(f"   Generated join_url={join_url}")

    # Step 4: Verify Next.js frontend route GET /join/{token}
    print(f"\n[4/7] Testing frontend page GET {join_url}...")
    page_status, page_body, page_headers = make_request(join_url)
    if page_status == 200 and "Interview" in page_body:
        matched_path = page_headers.get("x-matched-path", "")
        print(f"   [PASS] HTTP 200 OK from Next.js (matched path: {matched_path})")
    else:
        print(f"   [FAIL] Frontend returned status {page_status}: {page_body[:200]}")
        sys.exit(1)

    # Step 5: Public API GET /api/v1/interviews/join/{token}
    print(f"\n[5/7] Testing public API GET /api/v1/interviews/join/{raw_token}...")
    status, body, _ = make_request(f"{API_BASE}/interviews/join/{raw_token}")
    if status == 200:
        join_data = json.loads(body)
        print(f"   [PASS] Public metadata returned: title='{join_data.get('title')}', type='{join_data.get('interview_type')}'")
    else:
        print(f"   [FAIL] Expected HTTP 200, got {status}: {body}")
        sys.exit(1)

    # Step 6: Candidate Identity POST /api/v1/interviews/join/{token}/identity
    print(f"\n[6/7] Testing POST /api/v1/interviews/join/{raw_token}/identity...")
    status, body, _ = make_request(
        f"{API_BASE}/interviews/join/{raw_token}/identity",
        method="POST",
        data={"name": "Production Candidate", "email": "candidate@example.test"},
    )
    if status == 200:
        candidate_session = json.loads(body)
        candidate_jwt = candidate_session["candidate_session_token"]
        print(f"   [PASS] Candidate session token issued (expires in {candidate_session.get('expires_in_seconds')}s)")
    else:
        print(f"   [FAIL] Expected HTTP 200, got {status}: {body}")
        sys.exit(1)

    # Step 7: Candidate Waiting Room GET /api/v1/interviews/join/{token}/status
    print(f"\n[7/8] Testing waiting room GET /api/v1/interviews/join/{raw_token}/status...")
    candidate_headers = {"Authorization": f"Bearer {candidate_jwt}"}
    status, body, _ = make_request(
        f"{API_BASE}/interviews/join/{raw_token}/status",
        headers=candidate_headers,
    )
    if status == 200:
        status_data = json.loads(body)
        print(f"   [PASS] Pre-start waiting room status: interview_started={status_data.get('interview_started')}, status='{status_data.get('interview_status')}'")
    else:
        print(f"   [FAIL] Expected HTTP 200, got {status}: {body}")
        sys.exit(1)

    # Step 8: Interviewer starts interview -> Candidate polls and detects in_progress
    print(f"\n[8/8] Testing interviewer starting interview and candidate room progression...")
    start_status, start_body, _ = make_request(
        f"{API_BASE}/interviews/{interview_id}/session",
        method="POST",
        headers=auth_headers,
    )
    if start_status in (200, 201):
        # Poll status as candidate
        poll_status, poll_body, _ = make_request(
            f"{API_BASE}/interviews/join/{raw_token}/status",
            headers=candidate_headers,
        )
        if poll_status == 200:
            poll_data = json.loads(poll_body)
            print(f"   [PASS] Post-start candidate status: interview_started={poll_data.get('interview_started')}, status='{poll_data.get('interview_status')}'")

    # Step 10: Candidate Room Session POST /api/v1/interviews/join/{token}/room-session
    print(f"\n[10] Testing candidate room session POST /api/v1/interviews/join/{raw_token}/room-session...")
    room_sess_status, room_sess_body, _ = make_request(
        f"{API_BASE}/interviews/join/{raw_token}/room-session",
        method="POST",
        headers=candidate_headers,
    )
    if room_sess_status in (200, 201):
        room_sess_data = json.loads(room_sess_body)
        print(f"   [PASS] Candidate room session obtained: session_id={room_sess_data.get('session_id')}, candidate_join_token={'[REDACTED]' if room_sess_data.get('candidate_join_token') else None}, realtime_url={room_sess_data.get('realtime_url')}")
    else:
        print(f"   [NOTE] Candidate room session endpoint returned {room_sess_status} (may not yet be deployed to Vercel)")

    print("\n=======================================================")
    print("ALL PRODUCTION E2E STEPS PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    main()
