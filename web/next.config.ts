import type { NextConfig } from "next";

// GitHub Pages はプロジェクトページとして https://<owner>.github.io/<repo>/ に配信されるため、
// GITHUB_PAGES=true でビルドするときだけ basePath を付与する（Vercel やローカルでは不要）。
const isGithubPages = process.env.GITHUB_PAGES === "true";
const repoName = process.env.NEXT_PUBLIC_BASE_PATH ?? "/discussion";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  ...(isGithubPages
    ? {
        basePath: repoName,
        assetPrefix: repoName,
      }
    : {}),
};

export default nextConfig;
