// Apoio dos testes do site (não é um teste: o `npm test` só roda *.test.mjs).
//
// - A cópia temporária do site para os builds: os testes nunca constroem em site/ mesmo, para não deixar
//   src/data/ modificado pelo prebuild nem tocar em src/content/ (frente A).
// - O contraste WCAG das cores OKLCH do global.css.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const SITE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const BASE = '/forge';

const IGNORAR = new Set(['node_modules', 'dist', '.astro', '.claude', 'tests']);

// ---------- A cópia do site ----------

/**
 * Copia o site para uma pasta temporária (`forge-<prefixo>-...`) e devolve o caminho.
 *
 * O node_modules da cópia é próprio, com uma junção para cada pacote, menos .astro e .vite: o data-store
 * do Astro mora em node_modules/.astro e, compartilhado, atropelaria os builds dos outros arquivos de
 * teste (o node --test roda os arquivos em paralelo).
 *
 * `semConteudo`: a cópia sai com src/content/docs/ vazia, para o teste escrever as próprias páginas.
 */
export function copiarSite(prefixo, { semConteudo = false } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `forge-${prefixo}-`));
  for (const nome of fs.readdirSync(SITE)) {
    if (IGNORAR.has(nome)) continue;
    fs.cpSync(path.join(SITE, nome), path.join(dir, nome), { recursive: true });
  }
  if (semConteudo) {
    fs.rmSync(path.join(dir, 'src', 'content'), { recursive: true, force: true });
    fs.mkdirSync(path.join(dir, 'src', 'content', 'docs'), { recursive: true });
  }
  fs.mkdirSync(path.join(dir, 'node_modules'));
  for (const nome of fs.readdirSync(path.join(SITE, 'node_modules'))) {
    if (nome === '.astro' || nome === '.vite') continue;
    fs.symlinkSync(path.join(SITE, 'node_modules', nome), path.join(dir, 'node_modules', nome), 'junction');
  }
  return dir;
}

/** Roda o `astro build` (sem o prebuild) na cópia. */
export function construir(dir) {
  const r = spawnSync(process.execPath, [path.join(SITE, 'node_modules', 'astro', 'bin', 'astro.mjs'), 'build'], {
    cwd: dir,
    encoding: 'utf8',
    env: { ...process.env, ASTRO_TELEMETRY_DISABLED: '1', NO_COLOR: '1' },
  });
  return { ok: r.status === 0, saida: `${r.stdout}\n${r.stderr}`, dist: path.join(dir, 'dist') };
}

/** Copia o site, deixa `preparar(dir)` mexer na cópia e constrói: o build tem de passar. Devolve a pasta e o dist. */
export function construirCopia(prefixo, preparar = () => {}) {
  const dir = copiarSite(prefixo);
  preparar(dir);
  const b = construir(dir);
  assert.ok(b.ok, `astro build falhou:\n${b.saida}`);
  return { dir, dist: b.dist };
}

/** Apaga a cópia. Desfaz as junções antes do rm -r, para não apagar o node_modules de verdade. */
export function apagarCopia(dir) {
  if (!dir) return;
  try {
    for (const nome of fs.readdirSync(path.join(dir, 'node_modules'))) fs.unlinkSync(path.join(dir, 'node_modules', nome));
  } catch {}
  fs.rmSync(dir, { recursive: true, force: true });
}

// ---------- OKLCH -> sRGB -> contraste WCAG ----------

/** Os três números de um `oklch(L C h)` simples. */
export function oklch(texto) {
  const m = texto.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)/);
  assert.ok(m, `não é um oklch() simples: ${texto}`);
  return [Number(m[1]), Number(m[2]), Number(m[3])];
}

/** Luminância relativa (WCAG) de uma cor OKLCH, já cortada para o sRGB. */
export function luminancia([L, C, h]) {
  const a = C * Math.cos((h * Math.PI) / 180);
  const b = C * Math.sin((h * Math.PI) / 180);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const lin = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ].map((v) => Math.min(1, Math.max(0, v)));
  return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
}

/** Razão de contraste WCAG entre duas cores `oklch(...)`. */
export function contraste(a, b) {
  const [x, y] = [luminancia(oklch(a)), luminancia(oklch(b))].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

/** Tokens `--nome: valor;` de um trecho do CSS. */
export function tokens(bloco) {
  const out = {};
  for (const m of bloco.matchAll(/(--[\w-]+):\s*([^;]+);/g)) out[m[1]] = m[2].trim();
  return out;
}
