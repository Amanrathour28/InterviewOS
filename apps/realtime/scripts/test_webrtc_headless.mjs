import puppeteer from 'puppeteer-core';

async function testWebRtcHeadless() {
  console.log('Testing WebRTC in headless Chrome...');
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      '--no-sandbox'
    ]
  });

  const page = await browser.newPage();
  await page.goto('https://interviewos-nine.vercel.app');
  
  const result = await page.evaluate(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      return {
        success: true,
        videoTracks: stream.getVideoTracks().map(t => ({ kind: t.kind, readyState: t.readyState, label: t.label })),
        audioTracks: stream.getAudioTracks().map(t => ({ kind: t.kind, readyState: t.readyState, label: t.label })),
      };
    } catch(e) {
      return { success: false, error: e.message };
    }
  });

  console.log('Result:', JSON.stringify(result, null, 2));
  await browser.close();
}

testWebRtcHeadless().catch(console.error);
