import type { Metadata } from 'next'
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
// import { Analytics } from '@vercel/analytics/next' // Deshabilitado - no usamos Vercel
import './globals.css'

export const metadata: Metadata = {
  title: 'Diaresis - Separación de Voces',
  description: 'Separa el audio por hablante automáticamente con IA',
  generator: 'Diaresis',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`font-sans ${GeistSans.variable} ${GeistMono.variable}`}>
        {children}
        {/* <Analytics /> */}
      </body>
    </html>
  )
}
