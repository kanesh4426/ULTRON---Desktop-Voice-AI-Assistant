import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';
import fs from 'node:fs';

// Dev-only stub — served in browser dev mode only, never written to build/
const qwebchannelStub = `
window.QWebChannel = window.QWebChannel || function(transport, initCallback) {
  console.warn('[Dev] QWebChannel stub — no real Qt bridge in browser mode');
  this.objects = { pyBridge: null };
  setTimeout(() => initCallback(this), 0);
};
`;

// Real qwebchannel.js — copy from your Qt installation into public/ once:
// cp $(python -c "import PySide6; import os; print(os.path.join(os.path.dirname(PySide6.__file__), 'Qt', 'resources', 'qtwebchannel', 'qwebchannel.js'))") ./public/qwebchannel.js
function qwebchannelPlugin() {
  let isBuild = false;

  return {
    name: 'qwebchannel-plugin',

    config(_cfg: any, { command }: { command: string }) {
      isBuild = command === 'build';
    },

    // DEV only: serve the stub so imports don't 404
    configureServer(server: any) {
      server.middlewares.use((req: any, res: any, next: any) => {
        if (req.url === '/qwebchannel.js') {
          res.setHeader('Content-Type', 'application/javascript');
          res.end(qwebchannelStub);
        } else {
          next();
        }
      });
    },

    // BUILD only: copy the REAL qwebchannel.js into the output directory
    generateBundle() {
      const realFile = path.resolve(__dirname, 'public', 'qwebchannel.js');

      if (fs.existsSync(realFile)) {
        // Use the real Qt file if available in public/
        (this as any).emitFile({
          type: 'asset',
          fileName: 'qwebchannel.js',
          source: fs.readFileSync(realFile, 'utf-8'),
        });
      } else {
        // Fallback: emit stub with a loud warning
        console.warn(
          '[vite] qwebchannel.js not found in public/. ' +
          'Copy it from your Qt installation: ' +
          'python -c "import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), \'Qt\', \'resources\', \'qtwebchannel\', \'qwebchannel.js\'))"'
        );
        (this as any).emitFile({
          type: 'asset',
          fileName: 'qwebchannel.js',
          source: qwebchannelStub,
        });
      }
    },
  };
}

export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss(), qwebchannelPlugin()],
  resolve: { /* ... your existing aliases ... */ },
  build: {
    target: 'esnext',
    outDir: 'build',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    open: true,
  },
});