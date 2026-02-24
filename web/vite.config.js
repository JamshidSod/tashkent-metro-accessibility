import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Serve /public/data/ as static files during dev
  // (data/ dir at project root is symlinked or copied to web/public/data/)
  server: {
    port: 5173,
    open: true,
  },
  build: {
    outDir: 'dist',
  },
});
