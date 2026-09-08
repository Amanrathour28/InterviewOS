/**
 * WebRTC ICE Configuration & TURN server resolution helper.
 *
 * Merges backend API ice_servers with client-side environment fallback
 * (NEXT_PUBLIC_TURN_URL, NEXT_PUBLIC_TURN_USERNAME, NEXT_PUBLIC_TURN_CREDENTIAL)
 * ensuring robust STUN + TURN discovery across all enterprise network environments.
 */

export function buildEffectiveIceServers(backendIceServers?: any[]): RTCIceServer[] {
  const servers: RTCIceServer[] = Array.isArray(backendIceServers) && backendIceServers.length > 0
    ? [...backendIceServers]
    : [{ urls: 'stun:stun.l.google.com:19302' }];

  const hasTurn = servers.some((s) => {
    const urls = Array.isArray(s.urls) ? s.urls : [s.urls];
    return urls.some((u) => u && (u.startsWith('turn:') || u.startsWith('turns:')));
  });

  if (!hasTurn && process.env.NEXT_PUBLIC_TURN_URL) {
    const rawUrls = process.env.NEXT_PUBLIC_TURN_URL
      .split(',')
      .map((u) => u.trim())
      .filter(Boolean);

    if (rawUrls.length > 0) {
      const turnEntry: RTCIceServer = {
        urls: rawUrls.length > 1 ? rawUrls : rawUrls[0],
      };
      if (process.env.NEXT_PUBLIC_TURN_USERNAME) {
        turnEntry.username = process.env.NEXT_PUBLIC_TURN_USERNAME;
      }
      if (process.env.NEXT_PUBLIC_TURN_CREDENTIAL) {
        turnEntry.credential = process.env.NEXT_PUBLIC_TURN_CREDENTIAL;
      }
      servers.push(turnEntry);
    }
  }

  return servers;
}

export function resolveIceTransportPolicy(): RTCIceTransportPolicy {
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    if (params.get('forceRelay') === 'true') {
      console.log('[WebRTC] Forced relay policy active via query parameter (?forceRelay=true)');
      return 'relay';
    }
  }
  return 'all';
}
