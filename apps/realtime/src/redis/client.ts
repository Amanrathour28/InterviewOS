import { Redis } from 'ioredis';
import { createAdapter } from '@socket.io/redis-adapter';
import { config } from '../config/index.js';

let pubClient: Redis | null = null;
let subClient: Redis | null = null;
let isRedisConnected = false;

export function getRedisClients() {
  if (!pubClient || !subClient) {
    pubClient = new Redis(config.redisUrl, {
      lazyConnect: true,
      maxRetriesPerRequest: 1,
      retryStrategy: (times: number) => {
        if (times > 3) return null;
        return Math.min(times * 100, 1000);
      },
    });

    subClient = pubClient.duplicate();

    pubClient.on('connect', () => {
      isRedisConnected = true;
      console.log('[Redis] Publisher connected successfully');
    });

    pubClient.on('error', (err: any) => {
      isRedisConnected = false;
      console.warn('[Redis] Connection warning (running in standalone mode if offline):', err.message);
    });

    subClient.on('error', (err: any) => {
      console.warn('[Redis Sub] Connection warning:', err.message);
    });
  }

  return { pubClient, subClient };
}

export async function createRedisAdapter() {
  if (!config.redisUrl || config.redisUrl.trim() === '') {
    console.log('[Redis Adapter] No REDIS_URL configured, running with local in-memory adapter');
    return null;
  }
  try {
    const { pubClient, subClient } = getRedisClients();
    await Promise.all([pubClient.connect(), subClient.connect()]);
    return createAdapter(pubClient, subClient);
  } catch (err: any) {
    console.warn('[Redis Adapter] Could not connect to Redis, falling back to in-memory adapter:', err.message);
    try {
      pubClient?.disconnect();
      subClient?.disconnect();
    } catch {}
    return null;
  }
}

export function checkRedisHealth(): Promise<boolean> {
  if (!pubClient || !isRedisConnected) return Promise.resolve(false);
  return pubClient
    .ping()
    .then((res: string) => res === 'PONG')
    .catch(() => false);
}
