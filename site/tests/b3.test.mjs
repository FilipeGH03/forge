// Testes da B3 (rotas /docs/<slug>/, anterior e seguinte, conferência de 404 no dist, utilitário
// único do base, plugin do base em img e HTML cru, prop `inicio` do layout).
//
//     node --test tests/b3.test.mjs        (rodado de site/, depois do npm install)
//
// O build roda numa cópia temporária do site (tests/apoio.mjs).
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { comBase } from '../src/lib/base.mjs';
import { baseNosLinks, prefixarNoHtml } from '../src/plugins/base-nos-links.mjs';
import { apagarCopia, BASE, construirCopia, SITE } from './apoio.mjs';
import { conferirLinks } from './conferir-links.mjs';

const SECOES = ['comece', 'conceitos', 'fluxo', 'referencia'];

// Páginas que outras tarefas ainda vão criar. Os links para elas dão 404 até lá, e só elas ficam fora
// da conferência. Quando a página existir no dist, o teste cobra tirá-la daqui. Vazio desde a B4
// (/comandos/ existe); a B5 (/fluxo/), se criar página nova, entra aqui antes de linkar para ela.
const PAGINAS_PENDENTES = [];

let dir;
let dist;
const lerDist = (rel) => fs.readFileSync(path.join(dist, rel), 'utf8');
const escapar = (texto) => texto.replace(/&/g, '&#38;');

const docs = fs
  .readdirSync(path.join(SITE, 'src', 'content', 'docs'))
  .filter((f) => f.endsWith('.md'))
  .map((f) => {
    const fm = fs.readFileSync(path.join(SITE, 'src', 'content', 'docs', f), 'utf8').split('---')[1];
    const campo = (k) => fm.match(new RegExp(`^${k}:\\s*(.+)$`, 'm'))?.[1].trim().replace(/^["']|["']$/g, '');
    return { slug: f.replace(/\.md$/, ''), titulo: campo('titulo'), secao: campo('secao'), ordem: Number(campo('ordem')) };
  });
const ordenados = [...docs].sort((a, b) => SECOES.indexOf(a.secao) - SECOES.indexOf(b.secao) || a.ordem - b.ordem);

before(() => {
  ({ dir, dist } = construirCopia('b3'));
});

after(() => apagarCopia(dir));

/** Os links de anterior e seguinte de uma página do dist. */
function vizinhasNoDist(slug) {
  const html = lerDist(`docs/${slug}/index.html`);
  const nav = html.match(/<nav class="paginacao"[^>]*>([\s\S]*?)<\/nav>/)?.[1] ?? '';
  return {
    anterior: nav.match(/<a class="paginacao-anterior" href="([^"]+)"/)?.[1],
    seguinte: nav.match(/<a class="paginacao-seguinte" href="([^"]+)"/)?.[1],
    nav,
  };
}

describe('rotas /docs/<slug>/', () => {
  test('cada arquivo da coleção vira docs/<slug>/index.html com o título e o h1', () => {
    assert.ok(docs.length >= 3, 'a coleção precisa de pelo menos três páginas');
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      assert.match(html, /<h1>[^<]+<\/h1>/, d.slug);
      assert.match(html, /<title>[^<]+ · forge<\/title>/, d.slug);
    }
  });
});

describe('anterior e seguinte', () => {
  test('cada página aponta para a vizinha certa, pela secao e pela ordem', () => {
    ordenados.forEach((d, i) => {
      const { anterior, seguinte } = vizinhasNoDist(d.slug);
      const esperadoAnt = ordenados[i - 1] ? `${BASE}/docs/${ordenados[i - 1].slug}/` : undefined;
      const esperadoSeg = ordenados[i + 1] ? `${BASE}/docs/${ordenados[i + 1].slug}/` : undefined;
      assert.equal(anterior, esperadoAnt, `anterior de ${d.slug}`);
      assert.equal(seguinte, esperadoSeg, `seguinte de ${d.slug}`);
    });
  });

  test('a primeira página não tem anterior e a última não tem seguinte', () => {
    assert.equal(vizinhasNoDist(ordenados[0].slug).anterior, undefined);
    assert.equal(vizinhasNoDist(ordenados.at(-1).slug).seguinte, undefined);
  });

  test('o rótulo mostra o título da vizinha e a navegação tem nome acessível', () => {
    const { nav } = vizinhasNoDist(ordenados[1].slug);
    assert.ok(nav.includes(escapar(ordenados[0].titulo)), 'título da anterior');
    assert.ok(nav.includes(escapar(ordenados[2].titulo)), 'título da seguinte');
    assert.match(lerDist(`docs/${ordenados[1].slug}/index.html`), /<nav class="paginacao" aria-label="[^"]+"/);
  });

  test('seguir só os "seguinte" passa por todas as páginas, na ordem, uma vez cada', () => {
    const visitadas = [];
    let atual = ordenados[0].slug;
    while (atual && visitadas.length <= docs.length) {
      visitadas.push(atual);
      const seg = vizinhasNoDist(atual).seguinte;
      atual = seg?.replace(`${BASE}/docs/`, '').replace(/\/$/, '');
    }
    assert.deepEqual(visitadas, ordenados.map((d) => d.slug));
  });
});

describe('404 no dist', () => {
  test('nenhum link interno do dist dá 404 (fora as páginas que outras tarefas criam)', () => {
    const quebrados = conferirLinks(dist, BASE).filter(
      (q) => !PAGINAS_PENDENTES.some((p) => q.link.startsWith(`${BASE}${p}`)),
    );
    assert.deepEqual(quebrados, []);
  });

  test('só as páginas pendentes ainda não existem: ao criar uma, tire-a de PAGINAS_PENDENTES', () => {
    for (const p of PAGINAS_PENDENTES) {
      assert.ok(!fs.existsSync(path.join(dist, p, 'index.html')), `${p} já existe no dist: tire-a de PAGINAS_PENDENTES`);
    }
  });

  test('o conferidor acha link quebrado, link sem o base e âncora que não existe', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'forge-b3-links-'));
    try {
      fs.mkdirSync(path.join(tmp, 'a'));
      fs.mkdirSync(path.join(tmp, 'b'));
      fs.writeFileSync(
        path.join(tmp, 'index.html'),
        '<a href="/forge/a/">a</a><a href="/forge/a/#sim">ok</a><a href="/forge/a/#nao">x</a><a href="/forge/c/">c</a>' +
          '<a href="/a/">sem base</a><a href="https://x.com/y">fora</a><img src="/forge/img.png"><a href="b/">rel</a><a href="d/">rel</a>',
      );
      fs.writeFileSync(path.join(tmp, 'a', 'index.html'), '<h2 id="sim">oi</h2><a href="#sim">ok</a><a href="#outro">x</a><a href="../b/">ok</a>');
      fs.writeFileSync(path.join(tmp, 'b', 'index.html'), '<p>b</p>');
      const q = conferirLinks(tmp, BASE).map((x) => `${x.pagina} ${x.link}`);
      assert.deepEqual(
        q.sort(),
        ['a/index.html #outro', 'index.html /a/', 'index.html /forge/a/#nao', 'index.html /forge/c/', 'index.html /forge/img.png', 'index.html d/'].sort(),
      );
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });
});

describe('utilitário único do base', () => {
  test('comBase prefixa só caminhos da raiz que ainda não têm o base', () => {
    assert.equal(comBase('/docs/x/', '/forge'), '/forge/docs/x/');
    assert.equal(comBase('/docs/x/', '/forge/'), '/forge/docs/x/');
    assert.equal(comBase('/forge/docs/x/', '/forge'), '/forge/docs/x/');
    assert.equal(comBase('//cdn/x', '/forge'), '//cdn/x');
    assert.equal(comBase('https://a.b/', '/forge'), 'https://a.b/');
    assert.equal(comBase('/docs/x/', ''), '/docs/x/');
  });

  test('ninguém mais monta URL com o base por conta própria', () => {
    for (const rel of ['src/layouts/Base.astro', 'src/components/NavLateral.astro', 'src/components/Paginacao.astro', 'src/pages/docs/[slug].astro']) {
      const fonte = fs.readFileSync(path.join(SITE, rel), 'utf8');
      assert.ok(!/BASE_URL/.test(fonte), `${rel} usa BASE_URL direto`);
    }
    const nav = fs.readFileSync(path.join(SITE, 'src/lib/navegacao.ts'), 'utf8');
    assert.match(nav, /from '\.\/base\.mjs'/);
    const plugin = fs.readFileSync(path.join(SITE, 'src/plugins/base-nos-links.mjs'), 'utf8');
    assert.match(plugin, /from '\.\.\/lib\/base\.mjs'/);
  });
});

describe('plugin base-nos-links: img e HTML cru', () => {
  test('prefixa o src de <img>, o href de <a> e ignora outros atributos', () => {
    const gravados = [];
    const ctx = { setProperty: (no, k, v) => gravados.push([k, v]) };
    const p = baseNosLinks('/forge');
    p.element.visit({ tagName: 'img', properties: { src: '/imagens/a.png' } }, ctx);
    p.element.visit({ tagName: 'img', properties: { src: 'https://x.com/a.png' } }, ctx);
    p.element.visit({ tagName: 'img', properties: { href: '/nada/' } }, ctx);
    p.element.visit({ tagName: 'a', properties: { src: '/nada/' } }, ctx);
    assert.deepEqual(gravados, [['src', '/forge/imagens/a.png']]);
  });

  test('prefixa href e src dentro de HTML cru e deixa o resto como está', () => {
    const entrada =
      '<p><a class="x" href="/docs/y/">y</a> <img alt="a" src=\'/img/a.png\'> <a href="https://x.com/">fora</a> <img src="/forge/b.png"> <span data-href="/docs/z/"></span></p>';
    const esperado =
      '<p><a class="x" href="/forge/docs/y/">y</a> <img alt="a" src=\'/forge/img/a.png\'> <a href="https://x.com/">fora</a> <img src="/forge/b.png"> <span data-href="/docs/z/"></span></p>';
    assert.equal(prefixarNoHtml(entrada, '/forge'), esperado);
  });

  test('o visitante de nó raw troca o HTML só quando muda', () => {
    const trocas = [];
    const ctx = { replaceNode: (no, novo) => trocas.push(novo) };
    const p = baseNosLinks('/forge');
    p.raw({ type: 'raw', value: '<img src="/a.png">' }, ctx);
    p.raw({ type: 'raw', value: '<img src="https://x.com/a.png">' }, ctx);
    assert.deepEqual(trocas, [{ type: 'raw', value: '<img src="/forge/a.png">' }]);
  });
});

describe('layout: prop inicio', () => {
  test('o layout decide o título da aba pela prop inicio, não pelo texto do título', () => {
    const fonte = fs.readFileSync(path.join(SITE, 'src/layouts/Base.astro'), 'utf8');
    assert.match(fonte, /inicio\?: boolean/);
    assert.match(fonte, /\{inicio \?/);
    assert.ok(!/titulo === 'forge'/.test(fonte), 'ainda compara titulo === forge');
  });

  test('o dist não deixa um <img> ou <a> da raiz sem o base', () => {
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      assert.ok(!/<(?:a|img)\b[^>]*\s(?:href|src)="\/(?!forge\/|forge")/.test(html), `${d.slug} tem link sem o base`);
    }
  });
});
