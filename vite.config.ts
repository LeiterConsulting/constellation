import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  build: {
    outDir: 'dist',
    manifest: true,
    rollupOptions: { output: { entryFileNames: 'constellation-[hash].js', assetFileNames: '[name]-[hash][extname]' } },
  },
});
