/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 'standalone' output is for containerized Docker deployments.
  // For Vercel, we let Vercel handle the output automatically.
  // output: 'standalone',  // uncomment only for Docker deployments
  images: {
    remotePatterns: [],
  },
  env: {
    // Runtime-accessible (but not NEXT_PUBLIC_) server-side env vars go here if needed
  },
};

export default nextConfig;
