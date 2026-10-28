// Testes da B7 (workflow .github/workflows/pages.yml: build de site/ e deploy no GitHub Pages).
//
//     node --test tests/        (rodado de site/)
//
// Não há parser de YAML nas dependências do site, então a estrutura é conferida por
// leitura das linhas. O teste de YAML válido de verdade usa o PyYAML, se ele estiver instalado.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const WORKFLOW = path.join(RAIZ, '.github', 'workflows', 'pages.yml');
const OFICIAIS = new Set([
  'actions/checkout',
  'actions/setup-node',
  'actions/setup-python',
  'actions/upload-pages-artifact',
  'actions/deploy-pages',
]);

const texto = fs.readFileSync(WORKFLOW, 'utf8');
const linhas = texto.split(/\r?\n/);
const ativas = linhas.filter((l) => l.trim() !== '' && !l.trim().startsWith('#'));

// Usos de actions: "uses: owner/repo@ref", com ou sem "- " na frente.
const usos = linhas
  .map((l) => l.match(/^\s*(?:-\s*)?uses:\s*(\S+)\s*$/))
  .filter(Boolean)
  .map((m) => m[1]);

function posicao(trecho) {
  const i = linhas.findIndex((l) => l.includes(trecho));
  assert.ok(i >= 0, `trecho não encontrado no workflow: ${trecho}`);
  return i;
}

describe('B7: workflow pages.yml', () => {
  test('o arquivo existe na raiz do repositório, em .github/workflows', () => {
    assert.ok(fs.existsSync(WORKFLOW));
  });

  test('YAML válido (PyYAML, quando instalado)', (t) => {
    const check = spawnSync('python', ['-c', 'import yaml'], { encoding: 'utf8' });
    if (check.status !== 0) return t.skip('PyYAML não instalado');
    const r = spawnSync(
      'python',
      ['-c', 'import sys,yaml; d=yaml.safe_load(open(sys.argv[1],encoding="utf-8")); print(sorted(d["jobs"]))', WORKFLOW],
      { encoding: 'utf8' },
    );
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /'build'.*'deploy'/);
  });

  test('a indentação é só de espaços, em múltiplos de 2, e não há tabs', () => {
    assert.ok(!texto.includes('\t'), 'há tab no workflow');
    for (const l of ativas) {
      const espacos = l.match(/^ */)[0].length;
      assert.equal(espacos % 2, 0, `indentação ímpar: "${l}"`);
    }
  });

  test('usa só actions oficiais, cada uma com versão fixa', () => {
    assert.ok(usos.length > 0);
    for (const uso of usos) {
      const [nome, versao] = uso.split('@');
      assert.ok(OFICIAIS.has(nome), `action fora da lista oficial: ${uso}`);
      assert.match(versao ?? '', /^v\d+$/, `action sem versão maior fixa: ${uso}`);
    }
  });

  test('tem as cinco actions do fluxo de Pages', () => {
    const nomes = new Set(usos.map((u) => u.split('@')[0]));
    for (const oficial of OFICIAIS) assert.ok(nomes.has(oficial), `falta ${oficial}`);
  });

  test('dispara em push na main e manualmente, e não em pull_request nem em outras branches', () => {
    assert.ok(linhas.some((l) => /^\s*push:\s*$/.test(l)));
    assert.match(texto, /push:\s*\n\s*branches:\s*\[main\]/);
    assert.ok(linhas.some((l) => /^\s*workflow_dispatch:/.test(l)));
    assert.ok(!/pull_request/.test(texto), 'não deve publicar em pull_request');
  });

  test('permissões de Pages e OIDC estão declaradas no nível do workflow', () => {
    assert.match(texto, /permissions:\s*\n\s*contents: read\s*\n\s*pages: write\s*\n\s*id-token: write/);
  });

  test('um deploy por vez, e um deploy em andamento nunca é cancelado no meio', () => {
    assert.match(texto, /concurrency:\s*\n\s*group: pages\s*\n\s*cancel-in-progress: false/);
  });

  test('o deploy só roda depois do build e no ambiente github-pages', () => {
    assert.match(texto, /deploy:\s*\n\s*needs: build/);
    assert.match(texto, /name: github-pages/);
  });

  test('o build usa Node 22 e Python, e instala com npm ci', () => {
    assert.match(texto, /node-version: 22\b/);
    assert.match(texto, /python-version: "3\.12"/);
    assert.ok(posicao('npm ci') > posicao('actions/setup-node'));
    assert.ok(posicao('npm ci') > posicao('actions/setup-python'));
  });

  test('a ordem dos passos é testes do Node, testes do Python, build e só então o artefato', () => {
    const npmTest = posicao('run: npm test');
    const py = posicao('python -m unittest discover -s site/scripts');
    const build = posicao('run: npm run build');
    const upload = posicao('actions/upload-pages-artifact');
    assert.ok(npmTest < py && py < build && build < upload);
  });

  test('o checkout traz o histórico inteiro, porque os testes comparam com a main', () => {
    assert.match(texto, /fetch-depth: 0/);
  });

  test('o artefato publicado é site/dist', () => {
    assert.match(texto, /path: site\/dist/);
  });

  test('o build do site gera o dist com base /forge (testado pelo build local na B1)', () => {
    const cfg = fs.readFileSync(path.join(RAIZ, 'site', 'astro.config.mjs'), 'utf8');
    assert.match(cfg, /const base = ['"]\/forge['"];/);
    assert.match(cfg, /^\s*base,$/m);
  });
});

describe('B7: .gitattributes da raiz', () => {
  const attrs = fs.readFileSync(path.join(RAIZ, '.gitattributes'), 'utf8');

  test('texto sai com LF para o runner do Actions', () => {
    assert.match(attrs, /^\* text=auto eol=lf$/m);
  });

  test('binários de imagem e fonte não passam pelo filtro de texto', () => {
    for (const ext of ['png', 'jpg', 'woff2', 'ico']) {
      assert.match(attrs, new RegExp(`^\\*\\.${ext} binary$`, 'm'), `falta *.${ext} binary`);
    }
  });
});
