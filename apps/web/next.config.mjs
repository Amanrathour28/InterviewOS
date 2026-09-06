/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 'standalone' output is for containerized Docker deployments.
  // For Vercel, we let Vercel handle the output automatically.
  // output: 'standalone',  // uncomment only for Docker deployments
  images: {
    remotePatterns: [],
  },
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/v1/:path*',
          destination: 'http://127.0.0.1:8000/api/v1/:path*',
        },
      ];
    }
    return [
      {
        source: '/api/v1/:path*',
        destination: '/api',
      },
    ];
  },
};

export default nextConfig;
