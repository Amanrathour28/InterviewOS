import https from 'https';

function fetch(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    }).on('error', reject);
  });
}

async function main() {
  const page = await fetch('https://interviewos-nine.vercel.app/join/test-token/room');
  console.log('Page status:', page.status);
  const re = /\/_next\/static\/chunks\/[a-zA-Z0-9_\-./]+\.js/g;
  const matches = [...new Set(page.body.match(re) || [])];
  console.log('Found chunk scripts:', matches.length);

  let foundRollback = false;
  for (const chunk of matches) {
    const chunkRes = await fetch('https://interviewos-nine.vercel.app' + chunk);
    if (chunkRes.body.includes('Polite peer rolling back') || chunkRes.body.includes('mergeRemoteChanges')) {
      console.log('FOUND NEW CODE in chunk:', chunk);
      foundRollback = true;
      break;
    }
  }

  if (foundRollback) {
    console.log('DEPLOYMENT STATUS: NEW CODE IS ACTIVE ON VERCEL PRODUCTION!');
  } else {
    console.log('DEPLOYMENT STATUS: Not found in room scripts yet. Might still be building on Vercel.');
  }
}

main().catch(console.error);
