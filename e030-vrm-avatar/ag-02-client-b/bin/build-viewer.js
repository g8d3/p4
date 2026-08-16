import { build } from 'esbuild';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');

mkdirSync(resolve(root, 'dist'), { recursive: true });

await build({
  entryPoints: [resolve(root, 'viewer-src/client-b.js')],
  bundle: true,
  format: 'esm',
  outfile: resolve(root, 'dist/viewer-b.js'),
  sourcemap: false,
  minify: false,
  logLevel: 'info',
  define: {
    'process.env.NODE_ENV': '"production"',
  },
});

console.log('built dist/viewer-b.js');
