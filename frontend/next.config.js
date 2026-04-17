/** @type {import('next').NextConfig} */
const isTauri = process.env.TAURI_BUILD === "1";

const nextConfig = {
  reactStrictMode: true,
  ...(isTauri
    ? {
        output: "export",
        images: { unoptimized: true },
        trailingSlash: true,
      }
    : {}),
};

module.exports = nextConfig;
