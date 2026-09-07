import dotenv from 'dotenv';

dotenv.config();

export const config = {
  port: parseInt(process.env.PORT || '4000', 10),
  jwtSecretKey: process.env.JWT_SECRET_KEY || 'dev-secret-key-32-chars-interviewos-platform-security',
  redisUrl: process.env.REDIS_URL || 'redis://localhost:6379/0',
  apiUrl: process.env.API_URL || 'http://localhost:8000/api/v1',
  corsOrigins: process.env.CORS_ORIGINS
    ? process.env.CORS_ORIGINS.split(',')
    : ['http://localhost:3000', 'http://127.0.0.1:3000', 'https://interviewos-nine.vercel.app'],
  heartbeatIntervalMs: 30000,
  heartbeatTimeoutMs: 60000,
};
