/** @type {import('next').NextConfig} */
const nextConfig = {
  // DESKTOP: Static export for PyInstaller bundling
  // Produces pure HTML/CSS/JS in 'out/' directory — served by FastAPI
  output: 'export',
  
  typescript: {
    ignoreBuildErrors: true,
  },
  // DESKTOP: Images must be unoptimized for static export
  images: {
    unoptimized: true,
  },
  // PERFORMANCE: Enable compression
  compress: true,
  // PERFORMANCE: Enable production source maps for debugging
  productionBrowserSourceMaps: false,
  // PERFORMANCE: Optimize package imports
  experimental: {
    optimizePackageImports: ['lucide-react', 'recharts', 'date-fns'],
  },
}

export default nextConfig
