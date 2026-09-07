import dotenv from 'dotenv';

dotenv.config();

export const config = {
  port: parseInt(process.env.PORT || '4000', 10),
  jwtSecretKey: process.env.JWT_SECRET_KEY || process.env.SECRET_KEY || 'dev-secret-key-32-chars-interviewos-platform-security',
  redisUrl: process.env.REDIS_URL || '',
  apiUrl: process.env.API_URL || 'http://localhost:8000/api/v1',
  corsOrigins: process.env.CORS_ORIGINS
    ? process.env.CORS_ORIGINS.split(',').map((o) => o.trim())
    : [
        'https://interviewos-nine.vercel.app',
        ...(process.env.NODE_ENV !== 'production'
          ? ['http://localhost:3000', 'http://127.0.0.1:3000']
          : []),
      ],
  heartbeatIntervalMs: 30000,
  heartbeatTimeoutMs: 60000,
};

export function isAllowedOrigin(origin: string | undefined): boolean {
  if (!origin) return true; // allow curl, health checks, server-to-server requests
  if (config.corsOrigins.includes('*')) return true;
  if (config.corsOrigins.includes(origin)) return true;
  // Match InterviewOS Vercel deployments (e.g. preview and production domains)
  if (/^https:\/\/interviewos(-[a-z0-9-]+)?\.vercel\.app$/.test(origin)) {
    return true;
  }
  return false;
}
