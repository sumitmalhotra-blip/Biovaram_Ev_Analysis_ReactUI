import type React from "react"
import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import { SessionProvider } from "@/components/session-provider"
import { StoreProvider } from "@/components/store-provider"
import "./globals.css"

// PERFORMANCE: Optimize font loading with display swap and subset
const inter = Inter({ 
  subsets: ["latin"],
  display: "swap",
  preload: true,
  variable: "--font-inter",
})

export const metadata: Metadata = {
  title: "BioVaram EV Analysis Platform",
  description: "Advanced Extracellular Vesicle Analysis for Flow Cytometry and NTA",
  generator: 'v0.app',
  manifest: '/manifest.json',
  icons: {
    icon: [
      { url: '/icon-dark-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: '/apple-icon.png',
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'BioVaram EV',
  },
}

export const viewport: Viewport = {
  themeColor: "#0f172a",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable}`}>
      <head>
        {/* PERFORMANCE: Preconnect to external origins */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* PERFORMANCE: DNS prefetch for API */}
        <link rel="dns-prefetch" href="//localhost:8000" />
      </head>
      <body className={`${inter.className} antialiased`}>
        <SessionProvider>
          <StoreProvider>
            {children}
          </StoreProvider>
        </SessionProvider>
        <Analytics />
      </body>
    </html>
  )
}
