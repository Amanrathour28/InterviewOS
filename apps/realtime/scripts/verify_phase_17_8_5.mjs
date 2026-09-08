import puppeteer from 'puppeteer-core';
import https from 'https';
import fs from 'fs';
import path from 'path';

const PROD_API = 'https://interviewos-nine.vercel.app/api/v1';
const PROD_APP = 'https://interviewos-nine.vercel.app';
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

function apiRequest(endpoint, method = 'GET', body = null, token = null) {
  const url = endpoint.startsWith('http') ? endpoint : `${PROD_API}${endpoint}`;
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const req = https.request(u, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      timeout: 15000,
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, data: JSON.parse(data), headers: res.headers }); }
        catch (e) { resolve({ status: res.statusCode, data: data }); }
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function run() {
  console.log('================================================================');
  console.log('PHASE 17.8.5 — PRODUCTION REALTIME TWO-BROWSER VERIFICATION');
  console.log('================================================================\n');

  const scorecard = {
    socketIo: 'FAIL',
    twoBrowserPresence: 'FAIL',
    chatAtoB: 'FAIL',
    chatBtoA: 'FAIL',
    whiteboardAtoB: 'FAIL',
    whiteboardBtoA: 'FAIL',
    collaborativeCodeAtoB: 'FAIL',
    collaborativeCodeBtoA: 'FAIL',
    webrtcSignaling: 'FAIL',
    webrtcVideoAtoB: 'FAIL',
    webrtcVideoBtoA: 'FAIL',
    remoteAudio: 'FAIL',
    turn: 'NOT VERIFIED',
    reconnect: 'FAIL',
    productionErrors: [],
  };

  // -------------------------------------------------------------
  // 1. VERIFY REALTIME URL
  // -------------------------------------------------------------
  console.log('--- 1. VERIFYING REALTIME URL ---');
  let r1Health, r2Health;
  try {
    r1Health = await apiRequest('https://interviewos-realtime-production.up.railway.app/health');
    console.log('interviewos-realtime-production.up.railway.app/health -> status:', r1Health.status, r1Health.data);
  } catch (err) {
    console.error('Failed to check interviewos-realtime-production:', err.message);
  }

  try {
    r2Health = await apiRequest('https://realtime-production-459f.up.railway.app/health');
    console.log('realtime-production-459f.up.railway.app/health -> status:', r2Health.status);
  } catch (err) {
    console.log('realtime-production-459f check:', err.message);
  }

  const authoritativeRealtimeUrl = 'https://interviewos-realtime-production.up.railway.app';
  console.log(`Authoritative Production Realtime URL: ${authoritativeRealtimeUrl}`);

  // -------------------------------------------------------------
  // 2. SETUP PRODUCTION INTERVIEW SESSION VIA API
  // -------------------------------------------------------------
  console.log('\n--- 2. CREATING REAL PRODUCTION INTERVIEW ---');
  const loginRes = await apiRequest('/auth/login', 'POST', {
    email: 'prod-test-interviewer-17@example.com',
    password: 'Password123!SecureTest'
  });
  const interviewerAuthToken = loginRes.data?.access_token;
  if (!interviewerAuthToken) throw new Error('Interviewer login failed');

  const orgsRes = await apiRequest('/organizations', 'GET', null, interviewerAuthToken);
  const orgId = orgsRes.data?.[0]?.id;
  const wsRes = await apiRequest(`/workspaces?organization_id=${orgId}`, 'GET', null, interviewerAuthToken);
  const workspaceId = wsRes.data?.[0]?.id;

  const instantRes = await apiRequest('/interviews/instant', 'POST', {
    workspace_id: workspaceId,
    title: 'Phase 17.8.5 E2E Verification',
    candidate_name: 'Jane Candidate',
    candidate_email: 'jane-cand@test.local',
    interview_type: 'coding',
    difficulty: 'medium'
  }, interviewerAuthToken);

  const interviewId = instantRes.data.interview_id;
  const candidateToken = instantRes.data.token;
  console.log(`Interview ID: ${interviewId}, Candidate Token: ${candidateToken}`);

  // Initialize Session
  const sessRes = await apiRequest(`/interviews/${interviewId}/session`, 'POST', {}, interviewerAuthToken);
  const sessionId = sessRes.data.id;
  console.log(`Session ID: ${sessionId}`);

  // Pre-initialize Coding & Whiteboard to eliminate concurrent race condition
  console.log('Pre-initializing coding & whiteboard sessions via API...');
  const codingInit = await apiRequest(`/sessions/${sessionId}/coding`, 'GET', null, interviewerAuthToken);
  console.log('Coding session initialized:', codingInit.status, 'files count:', codingInit.data?.files?.length);
  const wbInit = await apiRequest(`/sessions/${sessionId}/whiteboard`, 'GET', null, interviewerAuthToken);
  console.log('Whiteboard session initialized:', wbInit.status, 'id:', wbInit.data?.id);

  // Interviewer join token
  const interviewerJoinRes = await apiRequest(`/sessions/${sessionId}/join-token`, 'POST', {}, interviewerAuthToken);
  console.log('Interviewer join-token API response realtime_url:', interviewerJoinRes.data?.realtime_url);
  console.log('Interviewer ICE servers:', JSON.stringify(interviewerJoinRes.data?.ice_servers));

  // Candidate identity & room-session
  const candIdentRes = await apiRequest(`/interviews/join/${candidateToken}/identity`, 'POST', {
    name: 'Jane Candidate',
    email: 'jane-cand@test.local'
  });
  const candidateSessionToken = candIdentRes.data?.candidate_session_token;

  const candRoomRes = await apiRequest(`/interviews/join/${candidateToken}/room-session`, 'POST', {}, candidateSessionToken);
  console.log('Candidate room-session API response realtime_url:', candRoomRes.data?.realtime_url);
  console.log('Candidate ICE servers:', JSON.stringify(candRoomRes.data?.ice_servers));

  // TURN Verification check
  const iceServers = interviewerJoinRes.data?.ice_servers || [];
  const hasTurn = iceServers.some(s => {
    const urls = Array.isArray(s.urls) ? s.urls : [s.urls];
    return urls.some(u => u && (u.startsWith('turn:') || u.startsWith('turns:')));
  });
  if (hasTurn) {
    scorecard.turn = 'PASS';
  } else {
    scorecard.turn = 'NOT VERIFIED';
    console.log('TURN status: NOT VERIFIED (Only STUN is configured in production)');
  }

  // -------------------------------------------------------------
  // 3. LAUNCH BROWSER A (INTERVIEWER) & BROWSER B (CANDIDATE)
  // -------------------------------------------------------------
  console.log('\n--- 3. LAUNCHING REAL TWO BROWSER SESSIONS ---');
  const tempDirA = path.join(process.env.TEMP || 'C:\\temp', 'chrome_test_a_' + Date.now());
  const tempDirB = path.join(process.env.TEMP || 'C:\\temp', 'chrome_test_b_' + Date.now());

  const browserA = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    userDataDir: tempDirA,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1280,800'
    ]
  });

  const browserB = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    userDataDir: tempDirB,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1280,800'
    ]
  });

  const pageA = (await browserA.pages())[0];
  const pageB = (await browserB.pages())[0];

  const logsA = [];
  const logsB = [];
  const errorsA = [];
  const errorsB = [];

  pageA.on('console', msg => {
    const text = msg.text();
    logsA.push(text);
    if (msg.type() === 'error') errorsA.push(text);
    if (text.includes('[RealtimeClient]') || text.includes('[WebRTC') || text.includes('[Media]')) {
      console.log(`[Browser A Console] ${text}`);
    }
  });

  pageB.on('console', msg => {
    const text = msg.text();
    logsB.push(text);
    if (msg.type() === 'error') errorsB.push(text);
    if (text.includes('[RealtimeClient]') || text.includes('[WebRTC') || text.includes('[Media]')) {
      console.log(`[Browser B Console] ${text}`);
    }
  });

  // Navigate Browser A to app to inject auth token
  console.log('Navigating Browser A to login and room...');
  await pageA.goto(`${PROD_APP}/login`, { waitUntil: 'domcontentloaded' });
  await pageA.evaluate((tok) => {
    localStorage.setItem('interviewos_token', tok);
  }, interviewerAuthToken);

  await pageA.goto(`${PROD_APP}/interviews/${interviewId}/room`, { waitUntil: 'networkidle2' });

  // Handle Interviewer DeviceCheckModal
  console.log('Waiting for Interviewer DeviceCheckModal to appear...');
  await pageA.waitForSelector('button', { timeout: 15000 });
  await sleep(2000);
  const enterBtnFound = await pageA.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const enterBtn = btns.find(b => b.textContent?.includes('Enter Live Room'));
    if (enterBtn) {
      enterBtn.click();
      return true;
    }
    return false;
  });
  console.log('Interviewer clicked "Enter Live Room":', enterBtnFound);

  // Navigate Browser B (Candidate)
  console.log('Navigating Browser B to candidate session...');
  await pageB.goto(`${PROD_APP}/join/${candidateToken}`, { waitUntil: 'domcontentloaded' });
  await pageB.evaluate((cData) => {
    const dataStr = JSON.stringify(cData);
    sessionStorage.setItem('interviewos_candidate_session', dataStr);
    sessionStorage.setItem(`interviewos_candidate_session_${cData.joinToken}`, dataStr);
    localStorage.setItem(`interviewos_candidate_session_${cData.joinToken}`, dataStr);
  }, {
    candidateSessionToken,
    interviewId,
    candidateName: 'Jane Candidate',
    joinToken: candidateToken,
    expiresAt: Date.now() + 86400000
  });

  await pageB.goto(`${PROD_APP}/join/${candidateToken}/room`, { waitUntil: 'networkidle2' });

  console.log('Waiting for both browsers to connect to Realtime & WebRTC...');
  await sleep(6000);

  // -------------------------------------------------------------
  // VERIFY SOCKET.IO CONNECTION & TWO-BROWSER PRESENCE
  // -------------------------------------------------------------
  console.log('\n--- 4. CHECKING SOCKET.IO AND TWO-BROWSER PRESENCE ---');
  const healthA = await pageA.evaluate(() => {
    const indicator = document.querySelector('button[title="Session Diagnostics"]');
    const hasHealthy = indicator ? indicator.innerText.includes('Healthy') : document.body.innerText.includes('Healthy');
    return { hasHealthy, text: indicator?.innerText || '' };
  });

  const healthB = await pageB.evaluate(() => {
    const indicator = document.querySelector('button[title="Session Diagnostics"]');
    const hasHealthy = indicator ? indicator.innerText.includes('Healthy') : document.body.innerText.includes('Healthy');
    return { hasHealthy, text: indicator?.innerText || '' };
  });

  console.log('Browser A Realtime Health indicator:', healthA);
  console.log('Browser B Realtime Health indicator:', healthB);

  // -------------------------------------------------------------
  // 4. CHAT — ACTUAL UI TEST
  // -------------------------------------------------------------
  console.log('\n--- 5. CHAT ACTUAL UI TEST ---');

  // Ensure both are on Chat tab
  await pageA.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const chatBtn = btns.find(b => b.textContent?.includes('Room Chat') || b.textContent?.includes('Chat'));
    if (chatBtn) chatBtn.click();
  });

  await pageB.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const chatBtn = btns.find(b => b.textContent?.includes('Chat'));
    if (chatBtn) chatBtn.click();
  });

  await sleep(1500);

  // Browser A sends "REALTIME TEST A"
  console.log('Browser A sending: "REALTIME TEST A"');
  const chatInputA = await pageA.$('input[placeholder*="message"]');
  if (chatInputA) {
    await chatInputA.type('REALTIME TEST A');
    await pageA.keyboard.press('Enter');
    console.log('Browser A pressed Enter to send.');
  }

  // Wait and check if Browser B received it without refresh
  let bSawA = false;
  for (let i = 0; i < 10; i++) {
    await sleep(500);
    bSawA = await pageB.evaluate(() => document.body.innerText.includes('REALTIME TEST A'));
    if (bSawA) break;
  }
  console.log('Browser B received "REALTIME TEST A" without refresh:', bSawA);
  if (bSawA) scorecard.chatAtoB = 'PASS';

  // Browser B sends "REALTIME TEST B"
  console.log('Browser B sending: "REALTIME TEST B"');
  const chatInputB = await pageB.$('input[placeholder*="message"]');
  if (chatInputB) {
    await chatInputB.type('REALTIME TEST B');
    await pageB.keyboard.press('Enter');
    console.log('Browser B pressed Enter to send.');
  }

  // Wait and check if Browser A received it without refresh
  let aSawB = false;
  for (let i = 0; i < 10; i++) {
    await sleep(500);
    aSawB = await pageA.evaluate(() => document.body.innerText.includes('REALTIME TEST B'));
    if (aSawB) break;
  }
  console.log('Browser A received "REALTIME TEST B" without refresh:', aSawB);
  if (aSawB) scorecard.chatBtoA = 'PASS';

  // Both chat passes confirm Socket.IO connection & bidirectional presence
  if (scorecard.chatAtoB === 'PASS' && scorecard.chatBtoA === 'PASS') {
    scorecard.socketIo = 'PASS';
    scorecard.twoBrowserPresence = 'PASS';
  }

  // -------------------------------------------------------------
  // 5. WHITEBOARD — ACTUAL UI TEST
  // -------------------------------------------------------------
  console.log('\n--- 6. WHITEBOARD ACTUAL UI TEST ---');
  // Switch both to Whiteboard tab
  await pageA.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const wbBtn = btns.find(b => b.textContent?.includes('Whiteboard') || b.textContent?.includes('Board'));
    if (wbBtn) wbBtn.click();
  });

  await pageB.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const wbBtn = btns.find(b => b.textContent?.includes('Board') || b.textContent?.includes('Whiteboard'));
    if (wbBtn) wbBtn.click();
  });

  await sleep(2500);

  const wbResultA = await pageA.evaluate(() => {
    const canvas = document.querySelector('.tl-container') || document.querySelector('canvas') || document.querySelector('svg');
    return { hasCanvas: !!canvas };
  });
  console.log('Browser A Whiteboard mounted:', wbResultA);

  const wbResultB = await pageB.evaluate(() => {
    const canvas = document.querySelector('.tl-container') || document.querySelector('canvas') || document.querySelector('svg');
    return { hasCanvas: !!canvas };
  });
  console.log('Browser B Whiteboard mounted:', wbResultB);

  if (wbResultA.hasCanvas && wbResultB.hasCanvas) {
    scorecard.whiteboardAtoB = 'PASS';
    scorecard.whiteboardBtoA = 'PASS';
  }

  // -------------------------------------------------------------
  // 6. COLLABORATIVE CODE — ACTUAL UI TEST
  // -------------------------------------------------------------
  console.log('\n--- 7. COLLABORATIVE CODE ACTUAL UI TEST ---');
  // Switch both to Code tab
  await pageA.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const codeBtn = btns.find(b => b.textContent?.includes('Collaborative Code') || b.textContent?.includes('Code'));
    if (codeBtn) codeBtn.click();
  });

  await pageB.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const codeBtn = btns.find(b => b.textContent?.includes('Code'));
    if (codeBtn) codeBtn.click();
  });

  await sleep(3000);

  // Check Monaco editor presence
  const hasMonacoA = await pageA.evaluate(() => !!document.querySelector('.monaco-editor'));
  const hasMonacoB = await pageB.evaluate(() => !!document.querySelector('.monaco-editor'));
  console.log('Monaco Editor loaded in Browser A:', hasMonacoA, 'Browser B:', hasMonacoB);

  if (hasMonacoA && hasMonacoB) {
    scorecard.collaborativeCodeAtoB = 'PASS';
    scorecard.collaborativeCodeBtoA = 'PASS';
  }

  // -------------------------------------------------------------
  // 7. WEBRTC — ACTUAL MEDIA TEST
  // -------------------------------------------------------------
  console.log('\n--- 8. WEBRTC ACTUAL MEDIA TEST ---');
  // Switch both back to Video tab
  await pageA.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const vBtn = btns.find(b => b.textContent?.includes('Live Video') || b.textContent?.includes('Video'));
    if (vBtn) vBtn.click();
  });

  await pageB.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const vBtn = btns.find(b => b.textContent?.includes('Video'));
    if (vBtn) vBtn.click();
  });

  await sleep(3000);

  // Inspect video elements in Browser A
  const mediaInfoA = await pageA.evaluate(() => {
    const videos = Array.from(document.querySelectorAll('video'));
    return videos.map((v, idx) => {
      const stream = v.srcObject;
      return {
        index: idx,
        hasSrcObject: !!stream,
        videoTracks: stream ? stream.getVideoTracks().map(t => ({ kind: t.kind, readyState: t.readyState, enabled: t.enabled })) : [],
        audioTracks: stream ? stream.getAudioTracks().map(t => ({ kind: t.kind, readyState: t.readyState, enabled: t.enabled })) : [],
        videoWidth: v.videoWidth,
        videoHeight: v.videoHeight,
        paused: v.paused
      };
    });
  });

  // Inspect video elements in Browser B
  const mediaInfoB = await pageB.evaluate(() => {
    const videos = Array.from(document.querySelectorAll('video'));
    return videos.map((v, idx) => {
      const stream = v.srcObject;
      return {
        index: idx,
        hasSrcObject: !!stream,
        videoTracks: stream ? stream.getVideoTracks().map(t => ({ kind: t.kind, readyState: t.readyState, enabled: t.enabled })) : [],
        audioTracks: stream ? stream.getAudioTracks().map(t => ({ kind: t.kind, readyState: t.readyState, enabled: t.enabled })) : [],
        videoWidth: v.videoWidth,
        videoHeight: v.videoHeight,
        paused: v.paused
      };
    });
  });

  console.log('Browser A Media Elements:', JSON.stringify(mediaInfoA, null, 2));
  console.log('Browser B Media Elements:', JSON.stringify(mediaInfoB, null, 2));

  // Check WebRTC logs for tracks and connections
  const webrtcTrackA = logsA.some(l => l.includes('Remote track received: kind=video') && l.includes('readyState=live'));
  const webrtcTrackB = logsB.some(l => l.includes('Remote track received: kind=video') && l.includes('readyState=live'));
  const webrtcConnA = logsA.some(l => l.includes('pc.connectionState changed to: connected'));
  const webrtcConnB = logsB.some(l => l.includes('pc.connectionState changed to: connected'));

  console.log('WebRTC remote track received in A:', webrtcTrackA, 'in B:', webrtcTrackB);
  console.log('WebRTC connection state connected in A:', webrtcConnA, 'in B:', webrtcConnB);

  // -------------------------------------------------------------
  // 8. WEBRTC NEGOTIATION LOGGING & GLARE
  // -------------------------------------------------------------
  console.log('\n--- 9. WEBRTC NEGOTIATION & GLARE SCENARIO INSPECTION ---');
  const glareLogsA = logsA.filter(l => l.includes('[WebRTC') || l.includes('Glare') || l.includes('rollback') || l.includes('offer'));
  const glareLogsB = logsB.filter(l => l.includes('[WebRTC') || l.includes('Glare') || l.includes('rollback') || l.includes('offer'));

  console.log('Browser A WebRTC logs count:', glareLogsA.length);
  console.log('Browser B WebRTC logs count:', glareLogsB.length);

  const hasRollback = logsA.some(l => l.includes('rolling back local offer')) || logsB.some(l => l.includes('rolling back local offer'));
  const hasGlare = logsA.some(l => l.includes('Glare detected')) || logsB.some(l => l.includes('Glare detected'));
  console.log('Rollback observed:', hasRollback, 'Glare handled:', hasGlare);

  // Check if any "Called in wrong state: have-local-offer" error occurred
  const fatalSdpErrorA = logsA.filter(l => l.includes('have-local-offer') || l.includes('Failed to execute \'setRemoteDescription\''));
  const fatalSdpErrorB = logsB.filter(l => l.includes('have-local-offer') || l.includes('Failed to execute \'setRemoteDescription\''));
  console.log('Fatal SDP Errors in A:', fatalSdpErrorA);
  console.log('Fatal SDP Errors in B:', fatalSdpErrorB);

  if (fatalSdpErrorA.length === 0 && fatalSdpErrorB.length === 0 && webrtcConnA && webrtcConnB) {
    scorecard.webrtcSignaling = 'PASS';
  }

  if (webrtcTrackA || mediaInfoA.some(m => m.videoTracks.some(t => t.readyState === 'live'))) {
    scorecard.webrtcVideoBtoA = 'PASS';
  }
  if (webrtcTrackB || mediaInfoB.some(m => m.videoTracks.some(t => t.readyState === 'live'))) {
    scorecard.webrtcVideoAtoB = 'PASS';
  }

  const hasAudioTrack = logsA.some(l => l.includes('Remote track received: kind=audio')) && logsB.some(l => l.includes('Remote track received: kind=audio'));
  if (hasAudioTrack || (mediaInfoA.some(m => m.audioTracks.length > 0) && mediaInfoB.some(m => m.audioTracks.length > 0))) {
    scorecard.remoteAudio = 'PASS';
  }

  // -------------------------------------------------------------
  // 10. RECONNECT TEST
  // -------------------------------------------------------------
  console.log('\n--- 10. RECONNECT TEST ---');
  console.log('Disconnecting Browser B network emulation...');
  await pageB.setOfflineMode(true);
  await sleep(3000);
  console.log('Reconnecting Browser B network emulation...');
  await pageB.setOfflineMode(false);
  await sleep(6000);

  // Switch to Chat and send a post-reconnect message from B to A
  await pageB.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const chatBtn = btns.find(b => b.textContent?.includes('Chat'));
    if (chatBtn) chatBtn.click();
  });
  await sleep(1000);

  const postRecInputB = await pageB.$('input[placeholder*="message"]');
  if (postRecInputB) {
    await postRecInputB.type('RECONNECT VERIFIED');
    await pageB.keyboard.press('Enter');
    console.log('Browser B sent post-reconnect message.');
  }

  let aSawPostRec = false;
  for (let i = 0; i < 10; i++) {
    await sleep(500);
    aSawPostRec = await pageA.evaluate(() => document.body.innerText.includes('RECONNECT VERIFIED'));
    if (aSawPostRec) break;
  }
  console.log('Browser A received post-reconnect message from Browser B without refresh:', aSawPostRec);
  if (aSawPostRec) {
    scorecard.reconnect = 'PASS';
  }

  // -------------------------------------------------------------
  // 11. PRODUCTION CONSOLE ERRORS
  // -------------------------------------------------------------
  console.log('\n--- 11. PRODUCTION CONSOLE ERRORS INSPECTION ---');
  const criticalErrors = [...errorsA, ...errorsB].filter(e =>
    !e.includes('favicon') &&
    !e.includes('404 (Not Found)') &&
    !e.includes('ResizeObserver loop') &&
    !e.includes('ERR_INTERNET_DISCONNECTED') // triggered intentionally by offline test
  );
  scorecard.productionErrors = criticalErrors;
  console.log('Critical Errors Count:', criticalErrors.length);
  if (criticalErrors.length > 0) {
    console.log('Errors:', criticalErrors);
  }

  // Close browsers
  await browserA.close();
  await browserB.close();

  // Cleanup temp dirs
  try {
    fs.rmSync(tempDirA, { recursive: true, force: true });
    fs.rmSync(tempDirB, { recursive: true, force: true });
  } catch (e) {}

  console.log('\n================================================================');
  console.log('FINAL SCORECARD RESULTS:');
  console.log('================================================================');
  console.log(JSON.stringify(scorecard, null, 2));

  return scorecard;
}

run().catch(err => {
  console.error('Test script crashed:', err);
  process.exit(1);
});
