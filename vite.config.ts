import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  root: '.',
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    proxy: { '/api': { target: process.env.AGENTOPS_API_URL ?? 'http://127.0.0.1:8000', changeOrigin: false } },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return;
          if (id.includes('/node_modules/recharts/')) return 'recharts';
          const d3Package = id.match(/\/node_modules\/(d3-[^/]+)\//)?.[1];
          if (d3Package) return d3Package;
          return 'vendor';
        },
      },
    },
  },
});
