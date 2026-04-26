/** @type {import('next').NextConfig} */
const isTauri = process.env.TAURI_BUILD === "1";
const isWebExport = process.env.WEB_EXPORT === "1";

const nextConfig = {
  reactStrictMode: true,
  ...((isTauri || isWebExport)
    ? {
        output: "export",
        images: { unoptimized: true },
        trailingSlash: true,
      }
    : {}),
};

module.exports = nextConfig;
