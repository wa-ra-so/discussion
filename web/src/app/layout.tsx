import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "商談解析システム | 食べログ営業支援",
  description: "商談音声を自動解析し、法人カルテとして蓄積する営業支援システム",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" className="h-full antialiased">
      <body className="min-h-full bg-gradient-to-br from-[var(--app-bg-from)] to-[var(--app-bg-to)]">
        {children}
      </body>
    </html>
  );
}
