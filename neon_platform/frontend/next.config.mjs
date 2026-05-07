/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/media/**',
      },
      {
        protocol: 'https',
        hostname: '**.ngrok-free.dev',
        pathname: '/media/**',
      },
      {
        protocol: 'https',
        hostname: '**.ngrok.io',
        pathname: '/media/**',
      },
    ],
  },
};

export default nextConfig;
