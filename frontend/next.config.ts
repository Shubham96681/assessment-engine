import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Monorepo has lockfiles at repo root + frontend — pin tracing to this app
  outputFileTracingRoot: path.join(__dirname),
  // Smaller dev bundles — helps avoid OOM on /generate compile
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts"],
  },
};

export default nextConfig;
