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
    'User-Agent': 'Mozilla/5.0 Realtime-Debugger',
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
  console.log('==================================================');
  console.log('1. AUTHENTICATING INTERVIEWER ON PRODUCTION');
  console.log('==================================================');

  const testEmail = 'prod-test-interviewer-17@example.com';
  const testPassword = 'Password123!SecureTest';

  let loginRes = await apiRequest('/auth/login', 'POST', {
    email: testEmail,
    password: testPassword,
  });

  let interviewerAuthToken = loginRes.data?.access_token;
  if (!interviewerAuthToken) {
    console.log('Registering test interviewer...');
    const regRes = await apiRequest('/auth/register', 'POST', {
      email: testEmail,
      password: testPassword,
      first_name: 'Debug',
      last_name: 'Interviewer',
    });
    interviewerAuthToken = regRes.data?.access_token;
  }
  console.log('[PASS] Interviewer logged in');

  // Get organization and workspace
  const orgsRes = await apiRequest('/organizations', 'GET', null, interviewerAuthToken);
  let orgId = orgsRes.data?.[0]?.id;
  if (!orgId) {
    const newOrg = await apiRequest('/organizations', 'POST', { name: 'Debug Org' }, interviewerAuthToken);
    orgId = newOrg.data?.id;
  }
  const wsRes = await apiRequest(`/workspaces?organization_id=${orgId}`, 'GET', null, interviewerAuthToken);
  let workspaceId = wsRes.data?.[0]?.id;
  if (!workspaceId) {
    const newWs = await apiRequest('/workspaces', 'POST', { name: 'Debug WS', organization_id: orgId }, interviewerAuthToken);
    workspaceId = newWs.data?.id;
  }
  console.log('[PASS] Workspace ID:', workspaceId);

  console.log('\n==================================================');
  console.log('2. CREATING INSTANT INTERVIEW');
  console.log('==================================================');

  const instantRes = await apiRequest('/interviews/instant', 'POST', {
    workspace_id: workspaceId,
    candidate_name: 'Debug Candidate',
    candidate_email: 'candidate@test.local',
    title: 'Live Debug Session',
    interview_type: 'coding',
    difficulty: 'medium',
  }, interviewerAuthToken);

  console.log('[PASS] Created instant interview:', instantRes.data);
  const interviewId = instantRes.data.interview_id;
  const candidateToken = instantRes.data.token;

  console.log('\n==================================================');
  console.log('3. RETRIEVING INTERVIEWER SESSION & JOIN TOKEN');
  console.log('==================================================');

  const itwSessionRes = await apiRequest(`/interviews/${interviewId}/session`, 'POST', {}, interviewerAuthToken);
  console.log('Interviewer /interviews/{id}/session response:', itwSessionRes.status, itwSessionRes.data);
  const sessionId = itwSessionRes.data?.id;

  const interviewerJoinRes = await apiRequest(`/sessions/${sessionId}/join-token`, 'POST', {}, interviewerAuthToken);
  console.log('Interviewer /sessions/{id}/join-token response:', interviewerJoinRes.status, {
    user_id: interviewerJoinRes.data?.user_id,
    user_name: interviewerJoinRes.data?.user_name,
    session_id: interviewerJoinRes.data?.session_id,
    realtime_url: interviewerJoinRes.data?.realtime_url,
    ice_servers_count: interviewerJoinRes.data?.ice_servers?.length,
  });

  const interviewerUserId = interviewerJoinRes.data?.user_id;
  const interviewerWsToken = interviewerJoinRes.data?.token;
  const realtimeUrl = interviewerJoinRes.data?.realtime_url;

  console.log('\n==================================================');
  console.log('4. RETRIEVING CANDIDATE SESSION & JOIN TOKEN');
  console.log('==================================================');

  // Submit candidate identity
  const candIdentRes = await apiRequest(`/interviews/join/${candidateToken}/identity`, 'POST', {
    name: 'Debug Candidate',
    email: 'candidate@test.local',
  });
  console.log('Candidate identity status:', candIdentRes.status);
  const candidateSessionToken = candIdentRes.data?.candidate_session_token;

  // Candidate room-session
  const candRoomRes = await apiRequest(`/interviews/join/${candidateToken}/room-session`, 'POST', {}, candidateSessionToken);
  console.log('Candidate room-session response:', candRoomRes.status, {
    user_id: candRoomRes.data?.user_id,
    user_name: candRoomRes.data?.user_name,
    session_id: candRoomRes.data?.session_id,
    realtime_url: candRoomRes.data?.realtime_url,
    ice_servers_count: candRoomRes.data?.ice_servers?.length,
  });

  const candidateUserId = candRoomRes.data?.user_id;
  const candidateWsToken = candRoomRes.data?.candidate_join_token;

  console.log('\n==================================================');
  console.log('SESSION ID COMPARISON:');
  console.log('Interviewer session_id:', interviewerJoinRes.data?.session_id);
  console.log('Candidate   session_id:', candRoomRes.data?.session_id);
  console.log('Match?', interviewerJoinRes.data?.session_id === candRoomRes.data?.session_id);
  console.log('Interviewer user_id:', interviewerUserId);
  console.log('Candidate   user_id:', candidateUserId);
  console.log('Realtime Gateway URL:', realtimeUrl);
  console.log('==================================================');

  console.log('\n==================================================');
  console.log('5. CONNECTING INTERVIEWER SOCKET');
  console.log('==================================================');

  const interviewerSocket = io(realtimeUrl, {
    auth: { token: interviewerWsToken },
    transports: ['websocket'],
    timeout: 10000,
  });

  const intSync = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Interviewer socket connection timed out')), 10000);
    interviewerSocket.on('connect', () => {
      console.log('[PASS] Interviewer Socket connected! Socket ID:', interviewerSocket.id);
    });
    interviewerSocket.on('connect_error', (err) => {
      console.error('[FAIL] Interviewer connect_error:', err.message);
      clearTimeout(timer);
      reject(err);
    });
    interviewerSocket.on('room_sync', (sync) => {
      console.log('[PASS] Interviewer received room_sync:', sync);
      clearTimeout(timer);
      resolve(sync);
    });
  });

  console.log('\n==================================================');
  console.log('6. CONNECTING CANDIDATE SOCKET');
  console.log('==================================================');

  // Listen on interviewer for candidate join
  const interviewerJoinPromise = new Promise((resolve) => {
    interviewerSocket.on('interview_event', (event) => {
      console.log('Interviewer received interview_event:', event.event_type, event.payload);
      if (event.event_type === 'PARTICIPANT_JOINED') {
        resolve(event);
      }
    });
  });

  const candidateSocket = io(realtimeUrl, {
    auth: { token: candidateWsToken },
    transports: ['websocket'],
    timeout: 10000,
  });

  const candSync = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Candidate socket connection timed out')), 10000);
    candidateSocket.on('connect', () => {
      console.log('[PASS] Candidate Socket connected! Socket ID:', candidateSocket.id);
    });
    candidateSocket.on('connect_error', (err) => {
      console.error('[FAIL] Candidate connect_error:', err.message);
      clearTimeout(timer);
      reject(err);
    });
    candidateSocket.on('room_sync', (sync) => {
      console.log('[PASS] Candidate received room_sync:', sync);
      clearTimeout(timer);
      resolve(sync);
    });
  });

  console.log('Waiting for Interviewer to receive PARTICIPANT_JOINED...');
  const joinEvent = await Promise.race([
    interviewerJoinPromise,
    new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout waiting for PARTICIPANT_JOINED')), 5000)),
  ]);
  console.log('[PASS] Interviewer received PARTICIPANT_JOINED successfully:', joinEvent);

  console.log('\n==================================================');
  console.log('7. TESTING CHAT EVENT BIDIRECTIONAL FLOW');
  console.log('==================================================');

  // 7a. Interviewer -> Candidate chat
  const candChatPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Candidate timed out waiting for chat')), 5000);
    candidateSocket.on('interview_event', (event) => {
      if (event.event_type === 'CHAT_MESSAGE_CREATED') {
        clearTimeout(timer);
        resolve(event);
      }
    });
  });

  console.log('Interviewer sending CHAT_MESSAGE_CREATED...');
  interviewerSocket.emit('dispatch_event', {
    event_type: 'CHAT_MESSAGE_CREATED',
    payload: {
      channel_id: 'chan-debug',
      message: { id: 'msg-1', content: 'Hello Candidate from Interviewer' },
    },
  });

  const candChatEvent = await candChatPromise;
  console.log('[PASS] Candidate received chat:', candChatEvent.payload.message.content);

  // 7b. Candidate -> Interviewer chat
  const intChatPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Interviewer timed out waiting for chat')), 5000);
    interviewerSocket.on('interview_event', (event) => {
      if (event.event_type === 'CHAT_MESSAGE_CREATED') {
        clearTimeout(timer);
        resolve(event);
      }
    });
  });

  console.log('Candidate sending CHAT_MESSAGE_CREATED...');
  candidateSocket.emit('dispatch_event', {
    event_type: 'CHAT_MESSAGE_CREATED',
    payload: {
      channel_id: 'chan-debug',
      message: { id: 'msg-2', content: 'Hello Interviewer from Candidate' },
    },
  });

  const intChatEvent = await intChatPromise;
  console.log('[PASS] Interviewer received chat:', intChatEvent.payload.message.content);

  console.log('\n==================================================');
  console.log('8. TESTING WHITEBOARD MUTATION BIDIRECTIONAL FLOW');
  console.log('==================================================');

  const candWbPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Candidate timed out waiting for whiteboard_patch')), 5000);
    candidateSocket.on('whiteboard_patch', (data) => {
      clearTimeout(timer);
      resolve(data);
    });
  });

  console.log('Interviewer emitting whiteboard_patch...');
  interviewerSocket.emit('whiteboard_patch', {
    changes: { added: { shape1: { id: 'shape1', type: 'draw' } } },
    isLocked: false,
  });

  const candWbData = await candWbPromise;
  console.log('[PASS] Candidate received whiteboard_patch:', candWbData);

  const intWbPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Interviewer timed out waiting for whiteboard_patch')), 5000);
    interviewerSocket.on('whiteboard_patch', (data) => {
      clearTimeout(timer);
      resolve(data);
    });
  });

  console.log('Candidate emitting whiteboard_patch...');
  candidateSocket.emit('whiteboard_patch', {
    changes: { added: { shape2: { id: 'shape2', type: 'draw' } } },
    isLocked: false,
  });

  const intWbData = await intWbPromise;
  console.log('[PASS] Interviewer received whiteboard_patch:', intWbData);

  console.log('\n==================================================');
  console.log('9. TESTING WEBRTC SIGNALING RELAY');
  console.log('==================================================');

  // Candidate -> Interviewer offer
  const intSignalPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Interviewer timed out waiting for webrtc_signal')), 5000);
    interviewerSocket.on('webrtc_signal', (data) => {
      clearTimeout(timer);
      resolve(data);
    });
  });

  console.log(`Candidate sending offer to targetUserId: ${interviewerUserId}...`);
  candidateSocket.emit('webrtc_signal', {
    signalType: 'offer',
    targetUserId: interviewerUserId,
    sdp: { type: 'offer', sdp: 'v=0 candidate offer sdp' },
  });

  const intSignal = await intSignalPromise;
  console.log('[PASS] Interviewer received signal:', intSignal.signalType, 'from:', intSignal.senderUserId);

  // Interviewer -> Candidate answer
  const candSignalPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Candidate timed out waiting for webrtc_signal')), 5000);
    candidateSocket.on('webrtc_signal', (data) => {
      clearTimeout(timer);
      resolve(data);
    });
  });

  console.log(`Interviewer sending answer to targetUserId: ${candidateUserId}...`);
  interviewerSocket.emit('webrtc_signal', {
    signalType: 'answer',
    targetUserId: candidateUserId,
    sdp: { type: 'answer', sdp: 'v=0 interviewer answer sdp' },
  });

  const candSignal = await candSignalPromise;
  console.log('[PASS] Candidate received signal:', candSignal.signalType, 'from:', candSignal.senderUserId);

  console.log('\n==================================================');
  console.log('ALL PROD REALTIME SERVER TESTS COMPLETED!');
  console.log('==================================================');

  candidateSocket.disconnect();
  interviewerSocket.disconnect();
  process.exit(0);
}

run().catch((err) => {
  console.error('[FATAL ERROR IN TEST]', err);
  process.exit(1);
});
