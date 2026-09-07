import { spawn } from 'child_process';
import http from 'http';
import jwt from 'jsonwebtoken';
import { io } from '../../web/node_modules/socket.io-client/build/esm/index.js';

const JWT_SECRET = 'dev-secret-key-32-chars-interviewos-platform-security';
const PORT = 4005;
const REALTIME_URL = `http://localhost:${PORT}`;

const SESSION_ID = 'test-session-' + Date.now();
const INTERVIEW_ID = 'test-interview-' + Date.now();

// 1. Generate Interviewer & Candidate JWTs
const interviewerToken = jwt.sign(
  {
    sub: 'interviewer-1',
    user_id: 'interviewer-1',
    user_name: 'Sarah Interviewer',
    user_email: 'sarah@example.com',
    session_id: SESSION_ID,
    interview_id: INTERVIEW_ID,
    workspace_id: 'ws-1',
    role: 'interviewer',
    is_interviewer: true,
  },
  JWT_SECRET,
  { expiresIn: '1h' }
);

const candidateToken = jwt.sign(
  {
    sub: 'candidate-1',
    user_id: 'candidate-1',
    user_name: 'Alex Candidate',
    user_email: 'alex@example.com',
    session_id: SESSION_ID,
    interview_id: INTERVIEW_ID,
    workspace_id: 'ws-1',
    role: 'candidate',
    is_interviewer: false,
    type: 'candidate_session',
    scope: 'candidate',
  },
  JWT_SECRET,
  { expiresIn: '1h' }
);

async function runTest() {
  console.log('--- Starting Realtime Gateway Process on port ' + PORT + ' ---');
  const serverProc = spawn('node', ['dist/index.js'], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PORT: String(PORT),
      JWT_SECRET_KEY: JWT_SECRET,
      NODE_ENV: 'test',
    },
    stdio: 'pipe',
  });

  serverProc.stdout.on('data', (d) => process.stdout.write('[Server STDOUT] ' + d));
  serverProc.stderr.on('data', (d) => process.stderr.write('[Server STDERR] ' + d));

  // Wait for server to listen
  await new Promise((r) => setTimeout(r, 2000));

  try {
    // Check /health
    console.log('--- 1. Testing GET /health ---');
    const healthData = await new Promise((resolve, reject) => {
      http.get(`${REALTIME_URL}/health`, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          if (res.statusCode === 200) {
            resolve(JSON.parse(data));
          } else {
            reject(new Error(`Health check returned ${res.statusCode}`));
          }
        });
      }).on('error', reject);
    });

    console.log('[PASS] /health returned:', healthData);
    if (healthData.status !== 'ok' || healthData.service !== 'interviewos-realtime') {
      throw new Error('Health check payload mismatch');
    }

    // 2. Connect Interviewer Socket
    console.log('--- 2. Connecting Interviewer Socket ---');
    const interviewerSocket = io(REALTIME_URL, {
      auth: { token: interviewerToken },
      transports: ['websocket'],
    });

    await new Promise((resolve, reject) => {
      interviewerSocket.on('connect', resolve);
      interviewerSocket.on('connect_error', reject);
    });
    console.log('[PASS] Interviewer Socket connected with ID:', interviewerSocket.id);

    // Receive room_sync on interviewer
    const interviewerSync = await new Promise((resolve) => {
      interviewerSocket.once('room_sync', resolve);
    });
    console.log('[PASS] Interviewer received room_sync. Participant count:', interviewerSync.participants.length);

    // 3. Connect Candidate Socket
    console.log('--- 3. Connecting Candidate Socket ---');
    const candidateSocket = io(REALTIME_URL, {
      auth: { token: candidateToken },
      transports: ['websocket'],
    });

    await new Promise((resolve, reject) => {
      candidateSocket.on('connect', resolve);
      candidateSocket.on('connect_error', reject);
    });
    console.log('[PASS] Candidate Socket connected with ID:', candidateSocket.id);

    // 4. Test Presence Synchronization
    console.log('--- 4. Testing Presence Synchronization ---');
    // Interviewer should receive PARTICIPANT_JOINED event
    const joinEventPromise = new Promise((resolve) => {
      interviewerSocket.on('interview_event', (event) => {
        if (event.event_type === 'PARTICIPANT_JOINED') {
          resolve(event);
        }
      });
    });

    const joinEvent = await joinEventPromise;
    console.log('[PASS] Interviewer received PARTICIPANT_JOINED:', joinEvent.payload.user_name);

    // Candidate should receive room_sync with 2 participants
    const candidateSync = await new Promise((resolve) => {
      candidateSocket.emit('request_room_state');
      candidateSocket.once('room_sync', resolve);
    });
    console.log('[PASS] Candidate requested room state. Participant count:', candidateSync.participants.length);
    if (candidateSync.participants.length < 2) {
      throw new Error('Expected 2 participants in room_sync');
    }

    // 5. Test Live Chat Event Relay
    console.log('--- 5. Testing Chat Event Relay ---');
    const chatReceivedPromise = new Promise((resolve) => {
      candidateSocket.on('interview_event', (event) => {
        if (event.event_type === 'CHAT_MESSAGE_CREATED') {
          resolve(event);
        }
      });
    });

    interviewerSocket.emit('dispatch_event', {
      event_type: 'CHAT_MESSAGE_CREATED',
      payload: {
        channel_id: 'chan-1',
        message: { content: 'Hello Candidate', sender_name: 'Sarah' },
      },
    });

    const chatEvent = await chatReceivedPromise;
    console.log('[PASS] Candidate received chat message:', chatEvent.payload.message.content);

    // 6. Test Whiteboard Synchronization
    console.log('--- 6. Testing Whiteboard Patch Relay ---');
    const whiteboardReceivedPromise = new Promise((resolve) => {
      candidateSocket.on('whiteboard_patch', (data) => {
        resolve(data);
      });
    });

    interviewerSocket.emit('whiteboard_patch', {
      changes: { added: { shape_1: { id: 'shape_1', type: 'geo' } } },
      isLocked: false,
    });

    const wbPatch = await whiteboardReceivedPromise;
    console.log('[PASS] Candidate received whiteboard patch:', wbPatch.changes);

    // 7. Test Collaborative Coding (Yjs / Text update)
    console.log('--- 7. Testing Collaborative Code Relay ---');
    const codeReceivedPromise = new Promise((resolve) => {
      candidateSocket.on('coding_yjs_update', (data) => {
        resolve(data);
      });
    });

    interviewerSocket.emit('coding_yjs_update', {
      fileId: 'file-1',
      update: 'console.log("interviewer")',
      isLocked: false,
    });

    const codeData = await codeReceivedPromise;
    console.log('[PASS] Candidate received code update:', codeData.update);

    // 8. Test WebRTC Signaling Relay
    console.log('--- 8. Testing WebRTC Signaling Relay ---');
    const signalReceivedPromise = new Promise((resolve) => {
      interviewerSocket.on('webrtc_signal', (data) => {
        resolve(data);
      });
    });

    candidateSocket.emit('webrtc_signal', {
      signalType: 'offer',
      targetUserId: 'interviewer-1',
      sdp: { type: 'offer', sdp: 'v=0...' },
    });

    const signalData = await signalReceivedPromise;
    console.log('[PASS] Interviewer received WebRTC signal:', signalData.signalType, 'from:', signalData.senderUserId);

    // 9. Test Participant Disconnect & Reconnect
    console.log('--- 9. Testing Disconnect & Presence Cleanup ---');
    const leaveEventPromise = new Promise((resolve) => {
      interviewerSocket.on('interview_event', (event) => {
        if (event.event_type === 'PARTICIPANT_LEFT') {
          resolve(event);
        }
      });
    });

    candidateSocket.disconnect();
    const leaveEvent = await leaveEventPromise;
    console.log('[PASS] Interviewer received PARTICIPANT_LEFT for:', leaveEvent.payload.user_id);

    // Clean up
    interviewerSocket.disconnect();
    console.log('=== ALL REALTIME INTEGRATION TESTS PASSED ===');
  } finally {
    serverProc.kill('SIGTERM');
  }
}

runTest().catch((err) => {
  console.error('[FAIL] Test failed:', err);
  process.exit(1);
});
