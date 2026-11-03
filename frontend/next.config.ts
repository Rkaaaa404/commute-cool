import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dishub CCTV streams are served over plain HTTP, which browsers block on an
  // HTTPS page (mixed content). Proxy them through our own origin instead.
  async rewrites() {
    return [
      {
        source: "/cctv-hls/:path*",
        destination: "http://36.66.208.101:5000/hls/:path*",
      },
    ];
  },
};

export default nextConfig;
