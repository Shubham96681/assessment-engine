import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname), '')
  const tunnelMode = env.VITE_TUNNEL === '1' || env.VITE_TUNNEL === 'true'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      // tunnels forward to this machine; listen on all interfaces
      host: true,
      // Allow Cloudflare Quick Tunnel / ngrok Host headers
      allowedHosts: true,
      // HTTPS page → ws://localhost HMR is blocked (mixed / wrong origin) → blank screen; disable for tunnel mode only
      hmr: tunnelMode ? false : undefined,
      proxy: {
        '/api': {
          target: 'http://localhost:3000',
          changeOrigin: true,
        },
      },
    },
    preview: {
      allowedHosts: true,
      proxy: {
        '/api': {
          target: 'http://localhost:3000',
          changeOrigin: true,
        },
      },
    },
  }
})
