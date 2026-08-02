import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Noto_Sans_JP } from "next/font/google";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jakarta",
  display: "swap",
});

const notoSansJP = Noto_Sans_JP({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-noto-jp",
  display: "swap",
});

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
    <html
      lang="ja"
      className={`h-full antialiased ${plusJakartaSans.variable} ${notoSansJP.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script
          // テーマ切替時のちらつき（FOUC）を防ぐため、React水和前に同期実行する
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.setAttribute('data-theme','dark');document.documentElement.classList.add('dark')}else{document.documentElement.setAttribute('data-theme','light')}}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-full bg-[var(--background)] text-[var(--foreground)]">
        <div className="pointer-events-none fixed inset-0 -z-10 bg-gradient-to-br from-[var(--app-bg-from)] to-[var(--app-bg-to)]" />
        {children}
      </body>
    </html>
  );
}
