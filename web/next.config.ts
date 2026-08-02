import type { NextConfig } from "next";

// FastAPI が同一オリジンで静的ファイルを配信するため、basePath は不要
// （GitHub Pages 配信はやめて Fly.io 単体構成に統合した）
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
