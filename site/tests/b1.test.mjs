// Testes da B1 (esqueleto Astro, contrato 1.1 e base /forge nos links do Markdown).
//
//     node --test tests/        (rodado de site/, depois do npm install)
//
// Os builds rodam numa cópia temporária do site (tests/apoio.mjs), para não tocar em
// src/content/ (frente A).
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { baseNosLinks } from '../src/plugins/base-nos-links.mjs';
import { comBase as prefixarBase } from '../src/lib/base.mjs';
import { apagarCopia, construir as construirSite, copiarSite, SITE } from './apoio.mjs';

function frontmatter(campos) {
  const linhas = Object.entries(campos).map(([k, v]) => `${k}: ${v}`);
  return `---\n${linhas.join('\n')}\n---\n`;
}

const VALIDO = { titulo: 'Página de teste', descricao: 'Descrição curta.', secao: 'comece', ordem: 1 };

function sem(campo) {
  const copia = { ...VALIDO };
  delete copia[campo];
  return copia;
}

/** Monta um site com os arquivos dados ({ 'slug.md': conteúdo }) e roda o astro build. */
function construir(arquivos) {
  const dir = copiarSite('b1', { semConteudo: true });
  for (const [nome, conteudo] of Object.entries(arquivos)) {
    const alvo = path.join(dir, 'src', 'content', 'docs', nome);
    fs.mkdirSync(path.dirname(alvo), { recursive: true });
    fs.writeFileSync(alvo, conteudo);
  }
  const { ok, saida, dist } = construirSite(dir);
  const ler = (rel) => fs.readFileSync(path.join(dist, rel), 'utf8');
  const existe = (rel) => fs.existsSync(path.join(dist, rel));
  const limpar = () => apagarCopia(dir);
  return { ok, saida, ler, existe, limpar };
}

function deveQuebrar(arquivos, motivo) {
  const b = construir(arquivos);
  try {
    assert.equal(b.ok, false, `o build deveria quebrar (${motivo}), mas passou`);
    // Quebrou pelo motivo certo (schema ou slug), não por outra falha qualquer.
    assert.match(b.saida, /InvalidContentEntryDataError|fora do contrato 1\.1/, b.saida);
  } finally {
    b.limpar();
  }
}

function devePassar(arquivos) {
  const b = construir(arquivos);
  try {
    assert.equal(b.ok, true, b.saida);
  } finally {
    b.limpar();
  }
}

describe('prefixarBase', () => {
  const casos = [
    ['/docs/inicio/', '/forge/docs/inicio/'],
    ['/comandos/', '/forge/comandos/'],
    ['/comandos/#status', '/forge/comandos/#status'],
    ['/', '/forge/'],
    ['/forgeries/', '/forge/forgeries/'],
    ['/forge-x/', '/forge/forge-x/'],
    ['/forge/', '/forge/'],
    ['/forge', '/forge'],
    ['/forge/docs/x/', '/forge/docs/x/'],
    ['/forge#a', '/forge#a'],
    ['/forge?q=1', '/forge?q=1'],
    ['https://example.com/x', 'https://example.com/x'],
    ['//cdn.example.com/a', '//cdn.example.com/a'],
    ['#ancora', '#ancora'],
    ['relativo/x/', 'relativo/x/'],
    ['../x/', '../x/'],
    ['mailto:a@b.c', 'mailto:a@b.c'],
    ['', ''],
  ];
  for (const [entrada, esperado] of casos) {
    test(`${JSON.stringify(entrada)} -> ${JSON.stringify(esperado)}`, () => {
      assert.equal(prefixarBase(entrada, '/forge'), esperado);
    });
  }
  test('base vazio não mexe no link', () => {
    assert.equal(prefixarBase('/docs/x/', ''), '/docs/x/');
  });
});

describe('baseNosLinks', () => {
  for (const base of ['/forge', '/forge/', '/forge//']) {
    test(`base ${base} vira /forge e só age em <a> e <img>`, () => {
      const p = baseNosLinks(base);
      assert.deepEqual(p.element.filter, ['a', 'img']);
      const gravados = [];
      const ctx = { setProperty: (no, k, v) => gravados.push([k, v]) };
      p.element.visit({ tagName: 'a', properties: { href: '/docs/x/' } }, ctx);
      p.element.visit({ tagName: 'a', properties: { href: '/forge/docs/x/' } }, ctx);
      p.element.visit({ tagName: 'a', properties: {} }, ctx);
      p.element.visit({}, ctx);
      assert.deepEqual(gravados, [['href', '/forge/docs/x/']]);
    });
  }
});

describe('configuração', () => {
  test('package.json tem dev, build, dados e prebuild do contrato 1.2', () => {
    const pkg = JSON.parse(fs.readFileSync(path.join(SITE, 'package.json'), 'utf8'));
    assert.equal(pkg.scripts.dados, 'python scripts/extrair.py');
    assert.equal(pkg.scripts.prebuild, 'npm run dados');
    assert.ok(pkg.scripts.dev);
    assert.ok(pkg.scripts.build);
    assert.match(pkg.dependencies.astro, /^\^?7\./);
  });
  test('astro.config: site, base /forge e saída estática', () => {
    const cfg = fs.readFileSync(path.join(SITE, 'astro.config.mjs'), 'utf8');
    assert.match(cfg, /'https:\/\/filipegh03\.github\.io'/);
    assert.match(cfg, /base = '\/forge'/);
    assert.match(cfg, /output: 'static'/);
  });
  test('.gitignore ignora node_modules e dist', () => {
    const linhas = fs.readFileSync(path.join(SITE, '.gitignore'), 'utf8').split(/\r?\n/);
    assert.ok(linhas.includes('node_modules/'));
    assert.ok(linhas.includes('dist/'));
  });
  // A impeccable fica só na máquina do dono, fora do git (D20): no runner do Actions ela não existe.
  const skillImpeccable = path.join(SITE, '.claude', 'skills', 'impeccable', 'SKILL.md');
  test('impeccable 3.9.1 em site/.claude/skills/impeccable', { skip: !fs.existsSync(skillImpeccable) && 'impeccable local, fora do git' }, () => {
    const skill = fs.readFileSync(skillImpeccable, 'utf8');
    assert.match(skill, /^version: 3\.9\.1\r?$/m);
  });
});

describe('build com a coleção docs', () => {
  test('caminho feliz: página gerada, título, descrição e links com o base', () => {
    const corpo = [
      '## Seção',
      '',
      'Veja [outra](/docs/outra-pagina/), [comandos](/comandos/) e [status](/comandos/#status).',
      '',
      'Externo [ex](https://example.com/x), âncora [a](#secao), protocolo [p](//cdn.example.com/a),',
      'relativo [r](../x/) e já com base [j](/forge/docs/y/).',
      '',
      'Por referência: [ref][r1].',
      '',
      '[r1]: /docs/ref/',
      '',
      '```sh',
      'echo "/docs/nao-e-link/"',
      '```',
    ].join('\n');
    const b = construir({
      'exemplo-b1.md': frontmatter({ ...VALIDO, titulo: 'Exemplo da B1', descricao: 'Linha de descrição.' }) + corpo,
    });
    try {
      assert.equal(b.ok, true, b.saida);
      assert.ok(b.existe('docs/exemplo-b1/index.html'));
      const html = b.ler('docs/exemplo-b1/index.html');
      assert.match(html, /<title>Exemplo da B1 · forge<\/title>/);
      assert.match(html, /<meta name="description" content="Linha de descrição\.">/);
      assert.match(html, /<h1>Exemplo da B1<\/h1>/);
      assert.equal((html.match(/<h1[ >]/g) || []).length, 1, 'um h1 só');
      assert.match(html, /<html lang="pt-BR">/);
      for (const href of [
        '/forge/docs/outra-pagina/',
        '/forge/comandos/',
        '/forge/comandos/#status',
        'https://example.com/x',
        '#secao',
        '//cdn.example.com/a',
        '../x/',
        '/forge/docs/y/',
        '/forge/docs/ref/',
      ]) {
        assert.ok(html.includes(`href="${href}"`), `faltou href="${href}"`);
      }
      assert.ok(!html.includes('href="/docs/'), 'sobrou link sem o base');
      assert.ok(!html.includes('/forge/forge/'), 'base duplicado');
      assert.ok(html.includes('/docs/nao-e-link/'), 'texto do bloco de código intacto');
      assert.ok(!html.includes('/forge/docs/nao-e-link/'), 'bloco de código não é link');
      const indice = b.ler('index.html');
      assert.ok(indice.includes('href="/forge/docs/exemplo-b1/"'), 'índice linka com o base');
    } finally {
      b.limpar();
    }
  });

  test('várias páginas geram uma rota cada', () => {
    const b = construir({
      'a-um.md': frontmatter({ ...VALIDO, secao: 'fluxo', ordem: 2 }) + 'x',
      'b-dois.md': frontmatter({ ...VALIDO, secao: 'referencia', ordem: 1 }) + 'y',
    });
    try {
      assert.equal(b.ok, true, b.saida);
      assert.ok(b.existe('docs/a-um/index.html'));
      assert.ok(b.existe('docs/b-dois/index.html'));
    } finally {
      b.limpar();
    }
  });

  test('limites que passam: descricao com 160, ordem 0 e negativa, destaque true/false, sem destaque, cada seção', () => {
    devePassar({
      'p1.md': frontmatter({ ...VALIDO, descricao: 'a'.repeat(160) }) + 'x',
      'p2.md': frontmatter({ ...VALIDO, ordem: 0, destaque: 'true', secao: 'conceitos' }) + 'x',
      'p3.md': frontmatter({ ...VALIDO, ordem: -1, destaque: 'false', secao: 'fluxo' }) + 'x',
      'p4.md': frontmatter({ ...VALIDO, secao: 'referencia', descricao: `"${'ç'.repeat(160)}"` }) + 'x',
      'pagina-com-hifen-2.md': frontmatter(VALIDO) + 'x',
    });
  });

  const invalidos = [
    ['campo a mais', { ...VALIDO, autor: 'x' }],
    ['sem titulo', sem('titulo')],
    ['sem descricao', sem('descricao')],
    ['sem secao', sem('secao')],
    ['sem ordem', sem('ordem')],
    ['titulo vazio', { ...VALIDO, titulo: '""' }],
    ['titulo só espaços', { ...VALIDO, titulo: '"   "' }],
    ['titulo nulo', { ...VALIDO, titulo: 'null' }],
    ['descricao vazia', { ...VALIDO, descricao: '""' }],
    ['descricao com 161', { ...VALIDO, descricao: 'a'.repeat(161) }],
    ['secao fora do domínio', { ...VALIDO, secao: 'outra' }],
    ['secao com maiúscula', { ...VALIDO, secao: 'Comece' }],
    ['ordem decimal', { ...VALIDO, ordem: 1.5 }],
    ['ordem em texto', { ...VALIDO, ordem: '"1"' }],
    ['destaque em texto', { ...VALIDO, destaque: 'sim' }],
    ['destaque nulo', { ...VALIDO, destaque: 'null' }],
  ];
  for (const [motivo, campos] of invalidos) {
    test(`frontmatter fora do 1.1 quebra o build: ${motivo}`, () => {
      deveQuebrar({ 'pagina.md': frontmatter(campos) + 'x' }, motivo);
    });
  }

  for (const nome of ['Maiuscula.md', 'com_sublinhado.md', 'com espaco.md', 'sub/pasta.md', '-hifen-inicial.md', 'duplo--hifen.md']) {
    test(`slug fora do 1.1 quebra o build: ${nome}`, () => {
      deveQuebrar({ [nome]: frontmatter(VALIDO) + 'x' }, nome);
    });
  }
});
