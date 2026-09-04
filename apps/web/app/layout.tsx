import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'InterviewOS — Production-Level AI Interview & Collaborative Coding Platform',
  description:
    'AI-powered technical interviews, collaborative coding in Monaco, real-time video, interactive system design whiteboards, and evidence-based candidate evaluations.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#09090b] text-[#f4f4f5] bg-grid-pattern antialiased">
        {children}
      </body>
    </html>
  );
}
