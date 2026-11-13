// Copies the released app (repo root) into desktop/www so Electron can serve it. Run before start/dist.
const fs = require("fs"), path = require("path");
const root = path.join(__dirname, "..");
const www = path.join(__dirname, "www");
fs.rmSync(www, { recursive: true, force: true });
fs.mkdirSync(www, { recursive: true });
for (const f of ["index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png"]) fs.copyFileSync(path.join(root, f), path.join(www, f));
for (const d of ["lib", "model"]) fs.cpSync(path.join(root, d), path.join(www, d), { recursive: true });
fs.copyFileSync(path.join(root, "icon-512.png"), path.join(__dirname, "icon.png"));
console.log("desktop/www ready");
