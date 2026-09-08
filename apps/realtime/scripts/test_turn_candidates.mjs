import puppeteer from 'puppeteer-core';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

async function testTurnCandidates() {
  console.log('Testing WebRTC ICE candidate discovery (host, srflx, relay)...');

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      '--no-sandbox',
    ]
  });

  const page = await browser.newPage();
  await page.goto('https://interviewos-nine.vercel.app');

  const result = await page.evaluate(async () => {
    return new Promise(async (resolve) => {
      const candidates = [];
      const pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' }
        ],
        iceTransportPolicy: 'all',
        bundlePolicy: 'max-bundle'
      });

      pc.onicecandidate = (event) => {
        if (event.candidate) {
          candidates.push({
            type: event.candidate.type,
            protocol: event.candidate.protocol,
            address: event.candidate.address,
            relatedAddress: event.candidate.relatedAddress || null
          });
        }
      };

      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      stream.getTracks().forEach(t => pc.addTrack(t, stream));

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // Wait 3 seconds for ICE gathering
      setTimeout(() => {
        pc.close();
        stream.getTracks().forEach(t => t.stop());
        resolve({
          candidateTypes: [...new Set(candidates.map(c => c.type))],
          totalCandidates: candidates.length,
          candidates
        });
      }, 3000);
    });
  });

  console.log('Result with STUN only:', JSON.stringify(result, null, 2));
  await browser.close();
}

testTurnCandidates().catch(console.error);
