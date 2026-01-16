/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  // PERFORMANCE: Enable image optimization
  images: {
    // Enable Next.js image optimization
    unoptimized: false,
    // Define allowed image domains
    remotePatterns: [],
    // Optimize for common device sizes
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    // Use modern formats
    formats: ['image/avif', 'image/webp'],
  },
  // PERFORMANCE: Enable compression
  compress: true,
  // PERFORMANCE: Enable production source maps for debugging
  productionBrowserSourceMaps: false,
  // PERFORMANCE: Optimize package imports
  experimental: {
    optimizePackageImports: ['lucide-react', 'recharts', 'date-fns'],
  },
  // PERFORMANCE: Configure headers for caching
  async headers() {
    return [
      {
        source: '/:all*(svg|jpg|jpeg|png|gif|ico|webp|avif)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/:all*(js|css)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ]
  },
}

export default nextConfig
