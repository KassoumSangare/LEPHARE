import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// API Django : runserver en développement, serveur_production.py (waitress) en production
const proxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  // Fichiers envoyés (liens signés, core/fichiers.py)
  '/media': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
};

export default defineConfig({
  plugins: [react()],
  // npm run dev : développement uniquement (modules servis un par un, recompilés à la demande : très lent sur un
  // serveur partagé). En production : npm run production (build puis vite preview), voir LISEZMOI_PRODUCTION.md
  server: {
    port: 3000,
    host: true,
    allowedHosts: true,
    proxy,
  },
  // Production : fichiers compilés et minifiés du dossier dist, mêmes adresses que le développement
  preview: {
    port: 3000,
    host: true,
    allowedHosts: true,
    proxy,
  },
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // Bibliothèques dans des fichiers à part : gardées en cache par le navigateur d'une version à l'autre
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          icones: ['lucide-react'],
          outils: ['axios', 'qrcode'],
        },
      },
    },
  },
});
