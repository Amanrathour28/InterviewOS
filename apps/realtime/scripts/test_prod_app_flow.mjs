import http from 'http';
import https from 'https';
import { io } from '../../web/node_modules/socket.io-client/build/esm/index.js';

const PROD_API = 'https://interviewos-nine.vercel.app/api/v1';

async function apiRequest(endpoint, method = 'GET', body = null, token = null) {
  const url = endpoint.startsWith('http') ? endpoint : `${PROD_API}${endpoint}`;
  const parsed = new URL(url);
  const isHttps = parsed.protocol === 'https:';
  const transport = isHttps ? https : http;

  const headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 App-Flow-Debugger',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return new Promise((resolve, reject) => {
    const req = transport.request(
      url,
      {
        method,
        headers,
        timeout: 15000,
      },
      (res) => {
        let raw = '';
        res.on('data', (chunk) => (raw += chunk));
        res.on('end', () => {
          let data = null;
          try {
            data = JSON.parse(raw);
          } catch (e) {
            data = raw;
          }
          resolve({ status: res.statusCode, data, headers: res.headers });
        });
      }
    );

    req.on('error', reject);
    if (body) {
      req.write(JSON.stringify(body));
    }
    req.end();
  });
}

async function run() {
  console.log('--- 1. Login Interviewer ---');
  const testEmail = 'prod-test-interviewer-17@example.com';
  const testPassword = 'Password123!SecureTest';

  let loginRes = await apiRequest('/auth/login', 'POST', {
    email: testEmail,
    password: testPassword,
  });
  let interviewerAuthToken = loginRes.data?.access_token;
  const orgsRes = await apiRequest('/organizations', 'GET', null, interviewerAuthToken);
  let orgId = orgsRes.data?.[0]?.id;
  const wsRes = await apiRequest(`/workspaces?organization_id=${orgId}`, 'GET', null, interviewerAuthToken);
  let workspaceId = wsRes.data?.[0]?.id;

  console.log('--- 2. Create Instant Interview ---');
  const instantRes = await apiRequest(
    '/interviews/instant',
    'POST',
    {
      workspace_id: workspaceId,
      title: 'Debug Functional Flow Interview',
      candidate_name: 'Flow Candidate',
      candidate_email: 'flow-cand@example.com',
      interview_type: 'coding',
      difficulty: 'medium',
    },
    interviewerAuthToken
  );
  const interviewId = instantRes.data?.interview_id;
  const token = instantRes.data?.token;
  console.log('Interview ID:', interviewId, 'Token:', token);

  console.log('--- 3. Create Session ---');
  const sessRes = await apiRequest(`/interviews/${interviewId}/session`, 'POST', {}, interviewerAuthToken);
  const sessionId = sessRes.data?.id;
  console.log('Session ID:', sessionId);

  console.log('--- 4. Interviewer Join Token ---');
  const interviewerJoinRes = await apiRequest(`/sessions/${sessionId}/join-token`, 'POST', {}, interviewerAuthToken);
  const interviewerWsToken = interviewerJoinRes.data?.token;

  console.log('--- 5. Candidate Join Flow ---');
  const verifyRes = await apiRequest(`/interviews/join/${token}`, 'GET');
  const invitationToken = verifyRes.data?.invitation_token || token;

  const candIdentRes = await apiRequest(`/interviews/join/${token}/identity`, 'POST', {
    name: 'Flow Candidate',
    email: 'flow-cand@example.com',
  });
  console.log('candIdentRes:', candIdentRes.status, candIdentRes.data);
  const candidateSessionToken = candIdentRes.data?.candidate_session_token;

  const candRoomRes = await apiRequest(
    `/interviews/join/${token}/room-session`,
    'POST',
    {},
    candidateSessionToken
  );
  console.log('candRoomRes:', candRoomRes.status, candRoomRes.data);
  const candidateWsToken = candRoomRes.data?.candidate_join_token;
  console.log('Candidate ws_token obtained:', candidateWsToken ? 'YES' : 'NO');

  console.log('\n==================================================');
  console.log('TESTING CHAT API ACCESS FOR INTERVIEWER & CANDIDATE');
  console.log('==================================================');

  // Interviewer lists channels
  const intChannels = await apiRequest(`/sessions/${sessionId}/chat/channels`, 'GET', null, interviewerAuthToken);
  console.log('Interviewer list channels status:', intChannels.status, 'Count:', intChannels.data?.length);

  // Candidate lists channels with candidateWsToken (the token setApiAuthToken sets!)
  const candChannels = await apiRequest(`/sessions/${sessionId}/chat/channels`, 'GET', null, candidateWsToken);
  console.log('Candidate list channels (with candidateWsToken) status:', candChannels.status, 'Data:', candChannels.data);

  // Also test with candidateSessionToken
  const candChannelsWithSess = await apiRequest(`/sessions/${sessionId}/chat/channels`, 'GET', null, candidateSessionToken);
  console.log('Candidate list channels (with candidateSessionToken) status:', candChannelsWithSess.status);

  if (candChannels.data && candChannels.data.length > 0) {
    const pubChannel = candChannels.data.find(c => c.channel_type === 'public') || candChannels.data[0];
    console.log('Found public channel:', pubChannel.id);

    // Candidate posts message with candidateWsToken
    const candMsgRes = await apiRequest(`/chat/channels/${pubChannel.id}/messages`, 'POST', {
      message_type: 'text',
      content: 'Hello from Candidate via candidateWsToken!',
      client_message_id: `test-${Date.now()}`,
    }, candidateWsToken);
    console.log('Candidate send message status:', candMsgRes.status, 'Response:', candMsgRes.data);

    // Interviewer posts message with interviewerAuthToken
    const intMsgRes = await apiRequest(`/chat/channels/${pubChannel.id}/messages`, 'POST', {
      message_type: 'text',
      content: 'Hello from Interviewer!',
      client_message_id: `test-int-${Date.now()}`,
    }, interviewerAuthToken);
    console.log('Interviewer send message status:', intMsgRes.status, 'Response:', intMsgRes.data);
  }

  console.log('\n==================================================');
  console.log('TESTING WHITEBOARD API ACCESS FOR CANDIDATE');
  console.log('==================================================');

  const intWb = await apiRequest(`/sessions/${sessionId}/whiteboard`, 'GET', null, interviewerAuthToken);
  console.log('Interviewer GET whiteboard status:', intWb.status, 'Whiteboard ID:', intWb.data?.id);

  const candWb = await apiRequest(`/sessions/${sessionId}/whiteboard`, 'GET', null, candidateWsToken);
  console.log('Candidate GET whiteboard (with candidateWsToken) status:', candWb.status, 'Whiteboard ID:', candWb.data?.id);

  if (intWb.data?.id) {
    const wbId = intWb.data.id;
    const candPatch = await apiRequest(`/whiteboards/${wbId}`, 'PATCH', {
      document: { test: 'cand_edit' },
    }, candidateWsToken);
    console.log('Candidate PATCH whiteboard status:', candPatch.status, candPatch.data);
  }

  process.exit(0);
}

run().catch((err) => {
  console.error('Fatal Error:', err);
  process.exit(1);
});
