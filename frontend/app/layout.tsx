import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import 'maplibre-gl/dist/maplibre-gl.css';
import './globals.css';

import { MantineProvider, ColorSchemeScript } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import Navbar from '@/components/Navbar';

export const metadata = {
  title: 'COMMUTE-COOL',
  description: 'Sistem Navigasi Pejalan Kaki Berbasis Kenyamanan Termal',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <ColorSchemeScript />
      </head>
      <body>
        <MantineProvider defaultColorScheme="light">
          <Notifications position="top-right" />
          <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
            <Navbar />
            <main style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
              {children}
            </main>
          </div>
        </MantineProvider>
      </body>
    </html>
  );
}
