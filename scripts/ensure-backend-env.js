const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const envPath = path.join(root, 'backend', '.env');
const examplePath = path.join(root, 'backend', '.env.example');

if (!fs.existsSync(envPath) && fs.existsSync(examplePath)) {
  fs.copyFileSync(examplePath, envPath);
  // eslint-disable-next-line no-console
  console.warn('[assessment-engine] Created backend/.env from .env.example — set strong JWT secrets for anything beyond local dev.');
}
