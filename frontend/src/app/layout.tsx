import './globals.css'

export const metadata = {
  title: 'Sentient Audit',
  description: 'AI Financial Audit System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
