import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/contexts/AuthContext';

const inter   = Inter({ subsets: ['latin'], variable: '--font-sans' });
const jbMono  = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' });

export const metadata: Metadata = {
  title: 'LogoForge AI - Next Generation',
  description: 'Premium AI-driven logo generation using Next.js and WebSockets.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jbMono.variable}`}>
        {/*
          AuthProvider (P1.1): wraps the entire app so any component can call
          useAuth() to obtain the in-memory token without touching localStorage.
        */}
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
