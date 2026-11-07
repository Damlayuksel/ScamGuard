// Fails the web image build when the exported site contains an inline <script> whose
// SHA-256 hash is not allowed by the CSP in security-headers.inc.template. This catches
// Expo/Expo Router upgrades that change the inline hydration script.
//
// Usage: node check-csp.mjs <dist dir> <security-headers template>

import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const [distDir, headersTemplate] = process.argv.slice(2);

function htmlFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return htmlFiles(path);
    return name.endsWith('.html') ? [path] : [];
  });
}

const allowed = new Set(readFileSync(headersTemplate, 'utf8').match(/sha256-[A-Za-z0-9+/=]+/g) ?? []);
const inlineScript = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g;

const missing = new Map();
for (const file of htmlFiles(distDir)) {
  for (const [, body] of readFileSync(file, 'utf8').matchAll(inlineScript)) {
    if (!body.trim()) continue;
    const hash = `sha256-${createHash('sha256').update(body).digest('base64')}`;
    if (!allowed.has(hash)) missing.set(hash, file);
  }
}

if (missing.size > 0) {
  for (const [hash, file] of missing) {
    console.error(`CSP does not allow inline script in ${file}: '${hash}'`);
  }
  console.error('Add the hash to infra/nginx/templates/security-headers.inc.template.');
  process.exit(1);
}
console.log(`CSP check passed (${htmlFiles(distDir).length} HTML files).`);
