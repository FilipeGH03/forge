// Testes da B6 (polimento final e a direção visual da página inicial nas páginas de docs, /comandos/ e
// /fluxo/: abertura em ferrugem, rodapé, botão de claro/escuro, fontes pré-carregadas, rótulo das tabelas,
// link direto nos títulos, favicon, README e o apoio único dos testes).
//
//     node --test tests/b6.test.mjs        (rodado de site/, depois do npm install)
//
// O build roda numa cópia temporária do site (tests/apoio.mjs). O que precisa de navegador (a seção atual
// no sumário ao rolar, o clique no botão de tema, screenshots em claro/escuro e 375px) foi conferido à mão.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { ancora, ancorasNosTitulos } from '../src/plugins/ancoras-nos-titulos.mjs';
import { colunas, embrulho, rotulo, tabelasRolaveis } from '../src/plugins/tabelas-rolaveis.mjs';
import { apagarCopia, BASE, construirCopia, contraste, oklch, SITE, tokens } from './apoio.mjs';

const ler = (rel) => fs.readFileSync(path.join(SITE, rel), 'utf8').replace(/\r\n/g, '\n');
const css = ler('src/estilos/global.css');

const docs = fs
  .readdirSync(path.join(SITE, 'src', 'content', 'docs'))
  .filter((f) => f.endsWith('.md'))
  .map((f) => f.replace(/\.md$/, ''));
// As páginas que a B6 leva para a direção da página inicial: as de docs, /comandos/ e /fluxo/.
const PAGINAS = [...docs.map((slug) => `docs/${slug}`), 'comandos', 'fluxo'];

let dir;
let dist;
const lerDist = (rel) => fs.readFileSync(path.join(dist, rel), 'utf8');

before(() => {
  ({ dir, dist } = construirCopia('b6'));
});

after(() => apagarCopia(dir));

// ---------- Nós hast de mentira, para os plugins ----------

const texto = (value) => ({ type: 'text', value });
const el = (tagName, children = [], properties = {}) => ({ type: 'element', tagName, properties, children });
const tabela = (...titulos) =>
  el('table', [el('thead', [el('tr', titulos.map((t) => el('th', [texto(t)])))]), el('tbody', [el('tr', [el('td', [texto('x')])])])]);

/** Texto puro de um nó, como o `ctx.textContent` do Sätteri. */
const textoDe = (no) => (no.type === 'text' ? no.value : (no.children ?? []).map(textoDe).join(''));

/** O contexto do Sätteri que os plugins usam, gravando o que eles fazem. */
function contexto() {
  const feitos = [];
  return {
    feitos,
    textContent: textoDe,
    setProperty: (no, k, v) => {
      no.properties[k] = v;
      feitos.push(['id', no.tagName, v]);
    },
    appendChild: (no, filho) => {
      no.children.push(filho);
      feitos.push(['link', no.tagName, filho.properties.href]);
    },
    wrapNode: (no, { raw }) => feitos.push(['embrulho', raw]),
  };
}

// ---------- Tabelas roláveis: o rótulo de cada região ----------

describe('plugin tabelas-rolaveis', () => {
  test('as colunas são os <th> da primeira linha, em texto puro', () => {
    const t = tabela('Arquivo', 'O que é');
    t.children[0].children[0].children[1].children = [el('code', [texto('O que')]), texto(' é')];
    assert.deepEqual(colunas(t), ['Arquivo', 'O que é']);
  });

  test('tabela sem cabeçalho (ou com th vazio) fica só "Tabela"', () => {
    assert.equal(rotulo(el('table', [el('tbody', [el('tr', [el('td', [texto('a')])])])])), 'Tabela');
    assert.equal(rotulo(tabela('', ' ')), 'Tabela');
    assert.equal(rotulo(tabela('Campo', '', 'Regra')), 'Tabela: Campo, Regra');
  });

  test('o rótulo é escapado no atributo', () => {
    assert.equal(
      embrulho(tabela('A "b"', '<c> & d')),
      '<div class="tabela" role="region" tabindex="0" aria-label="Tabela: A &quot;b&quot;, &lt;c&gt; &amp; d"></div>',
    );
  });

  test('o plugin embrulha cada <table> com o rótulo das colunas dela', () => {
    const p = tabelasRolaveis();
    assert.deepEqual(p.element.filter, ['table']);
    const ctx = contexto();
    p.element.visit(tabela('Opção', 'O que faz'), ctx);
    assert.deepEqual(ctx.feitos, [['embrulho', '<div class="tabela" role="region" tabindex="0" aria-label="Tabela: Opção, O que faz"></div>']]);
  });

  test('no dist, cada região de tabela tem o nome das colunas da própria tabela', () => {
    let total = 0;
    for (const slug of docs) {
      const html = lerDist(`docs/${slug}/index.html`);
      const regioes = [...html.matchAll(/<div class="tabela" role="region" tabindex="0" aria-label="([^"]*)"><table>\s*<thead>\s*<tr>([\s\S]*?)<\/tr>/g)];
      assert.equal(regioes.length, (html.match(/<table/g) || []).length, `${slug}: tabela sem região com rótulo`);
      for (const [, nome, linha] of regioes) {
        const ths = [...linha.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)].map((t) => t[1].replace(/<[^>]+>/g, '').trim()).filter(Boolean);
        assert.equal(nome.replace(/&#38;|&amp;/g, '&'), `Tabela: ${ths.join(', ')}`, slug);
      }
      total += regioes.length;
    }
    assert.ok(total > 3, 'quase nenhuma tabela no conteúdo: o teste não provou nada');
  });
});

// ---------- Link direto nos títulos ----------

describe('plugin ancoras-nos-titulos', () => {
  test('dá o id do github-slugger e põe o link no ## e no ###, não no # nem no ####', () => {
    const fazer = ancorasNosTitulos()();
    assert.deepEqual(fazer.element.filter, ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']);
    const ctx = contexto();
    const titulos = [el('h1', [texto('Página')]), el('h2', [texto('Por que JSON?')]), el('h3', [texto('Retomar numa sessão nova')]), el('h4', [texto('Fundo')])];
    for (const t of titulos) fazer.element.visit(t, ctx);
    assert.deepEqual(ctx.feitos, [
      ['id', 'h1', 'página'],
      ['id', 'h2', 'por-que-json'],
      ['link', 'h2', '#por-que-json'],
      ['id', 'h3', 'retomar-numa-sessão-nova'],
      ['link', 'h3', '#retomar-numa-sessão-nova'],
      ['id', 'h4', 'fundo'],
    ]);
  });

  test('título repetido ganha sufixo, id escrito à mão é respeitado, e cada página recomeça a contagem', () => {
    const fabrica = ancorasNosTitulos();
    const uma = fabrica();
    const ctx = contexto();
    for (const t of [el('h2', [texto('Exemplo')]), el('h2', [texto('Exemplo')]), el('h2', [texto('Outro')], { id: 'meu-id' })]) uma.element.visit(t, ctx);
    assert.deepEqual(
      ctx.feitos.filter((f) => f[0] === 'link').map((f) => f[2]),
      ['#exemplo', '#exemplo-1', '#meu-id'],
    );
    const outra = fabrica();
    const ctx2 = contexto();
    outra.element.visit(el('h2', [texto('Exemplo')]), ctx2);
    assert.deepEqual(ctx2.feitos, [['id', 'h2', 'exemplo'], ['link', 'h2', '#exemplo']]);
  });

  test('o link não tem texto (o "#" vem do CSS) e tem nome acessível', () => {
    const a = ancora('x', 'Seção X');
    assert.deepEqual(a.children, []);
    assert.equal(a.properties.ariaLabel, 'Link direto para a seção Seção X');
    assert.match(css, /\.ancora::before\s*{\s*content: '#';/);
  });

  test('no dist, todo ## e ### das docs tem o link para o próprio id, e o sumário não ganha o "#"', () => {
    for (const slug of docs) {
      const html = lerDist(`docs/${slug}/index.html`);
      const prosa = html.slice(html.indexOf('<div class="prosa">'));
      const titulos = [...prosa.matchAll(/<h([23]) id="([^"]+)">([\s\S]*?)<\/h\1>/g)];
      assert.ok(titulos.length > 0, `${slug}: nenhum título`);
      for (const [, , id, corpo] of titulos) {
        assert.match(corpo, new RegExp(`<a class="ancora" href="#${id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}" aria-label="Link direto para a seção [^"]+"></a>$`), `${slug}#${id}`);
      }
      const sumario = html.match(/<details class="sumario"[\s\S]*?<\/details>/)?.[0] ?? '';
      assert.ok(!/ancora|>#</.test(sumario), `${slug}: o sumário pegou o link do título`);
    }
  });

  test('/comandos/ e /fluxo/ também têm o link direto nos títulos de seção', () => {
    for (const p of ['comandos', 'fluxo']) {
      const html = lerDist(`${p}/index.html`);
      const h2 = [...html.matchAll(/<h2 id="([^"]+)"[^>]*>([\s\S]*?)<\/h2>/g)];
      assert.ok(h2.length >= 2, p);
      for (const [, id, corpo] of h2) assert.match(corpo, new RegExp(`<a class="ancora" href="#${id}"`), `${p}#${id}`);
    }
  });
});

// ---------- A direção da página inicial (D16, D17) nas outras páginas ----------

describe('direção visual da página inicial nas docs, /comandos/ e /fluxo/', () => {
  test('cada página abre com a faixa em ferrugem: o <h1> e a descrição dentro dela', () => {
    for (const p of PAGINAS) {
      const html = lerDist(`${p}/index.html`);
      const abertura = html.match(/<header class="abertura-pagina">([\s\S]*?)<\/header>/)?.[1];
      assert.ok(abertura, `${p}: sem a abertura`);
      assert.match(abertura, /<h1>[^<]+<\/h1>/, p);
      assert.match(abertura, /<p class="descricao">[^<]+<\/p>/, p);
      assert.equal((html.match(/<h1\b/g) || []).length, 1, `${p}: mais de um h1`);
    }
    // Todas as regras com o seletor sozinho, juntas: a de dentro da @media do desktop só põe a faixa na grade.
    const regras = [...css.matchAll(/(?:^|\n)\s*\.abertura-pagina \{([^}]*)\}/g)].map((m) => m[1]).join('\n');
    assert.match(regras, /background: var\(--ferrugem\);/);
    assert.match(regras, /color: var\(--ferrugem-tinta\);/);
  });

  test('a abertura das páginas não tem animação: a entrada animada é só da página inicial', () => {
    const blocos = [...css.matchAll(/([^{}]*\.abertura-pagina[^{}]*)\{([^}]*)\}/g)];
    assert.ok(blocos.length > 0);
    for (const [, seletor, corpo] of blocos) assert.ok(!/animation|transition/.test(corpo), `${seletor.trim()} anima`);
  });

  test('o rodapé em ferro com o mapa da documentação aparece em todas, com os mesmos links da navegação', () => {
    for (const p of PAGINAS) {
      const html = lerDist(`${p}/index.html`);
      const rodape = html.match(/<footer class="rodape">([\s\S]*?)<\/footer>/)?.[1];
      assert.ok(rodape, `${p}: sem rodapé`);
      const doMapa = [...rodape.matchAll(/<a href="([^"]+)"/g)].map((m) => m[1]).filter((h) => h !== `${BASE}/`);
      const daNav = [...html.match(/<details class="menu"[\s\S]*?<\/details>/)[0].matchAll(/<a href="([^"]+)"/g)].map((m) => m[1]);
      assert.deepEqual(doMapa, daNav, `${p}: o mapa do rodapé difere da navegação lateral`);
    }
  });

  test('a página inicial continua com o rodapé dela (D14): o layout só usa o Rodape.astro sem o slot', () => {
    const inicio = lerDist('index.html');
    assert.equal((inicio.match(/<footer class="rodape"/g) || []).length, 1);
    assert.match(ler('src/layouts/Base.astro'), /Astro\.slots\.has\('rodape'\) \? <slot name="rodape" \/> : <Rodape \/>/);
  });

  test('nenhuma palavra colada num link ou código: o Astro come a quebra de linha entre texto e tag', () => {
    const colado = /[\p{L}\d,;:]<(a|code|strong|em|kbd)\b(?![^>]*class="ancora")|<\/(a|code|strong|em|kbd)>[\p{L}\d(]/gu;
    for (const p of PAGINAS) {
      const html = lerDist(`${p}/index.html`);
      const achados = [...html.matchAll(colado)].map((m) => html.slice(Math.max(0, m.index - 30), m.index + 30));
      assert.deepEqual(achados, [], p);
    }
  });

  test('o atalho do topo marca a seção aberta: Docs nas docs e no fluxo, Comandos na /comandos/', () => {
    const atual = (p) => [...lerDist(`${p}/index.html`).match(/<nav class="topo-links"[\s\S]*?<\/nav>/)[0].matchAll(/<a [^>]*aria-current="true"[^>]*>([^<]+)</g)].map((m) => m[1]);
    for (const slug of docs) assert.deepEqual(atual(`docs/${slug}`), ['Docs'], slug);
    assert.deepEqual(atual('fluxo'), ['Docs']);
    assert.deepEqual(atual('comandos'), ['Comandos']);
    assert.deepEqual(atual(''), []);
  });

  test('nenhum commit da B6 mexe na página inicial (D14)', () => {
    // O pathspec é relativo ao cwd (site/): com 'site/src/...' o git procuraria site/site/src/... e o teste nunca falharia.
    const r = spawnSync('git', ['log', '--format=%h %s', '--grep=^B6', 'HEAD', '--', 'src/pages/index.astro'], { cwd: SITE, encoding: 'utf8' });
    assert.equal(r.status, 0, r.stderr);
    assert.equal(r.stdout.trim(), '');
  });
});

// ---------- Cores novas: contraste (WCAG) ----------

describe('contraste das cores da direção nova', () => {
  const claro = tokens(css.slice(css.indexOf(':root {'), css.indexOf('/* Escuro:')));
  const blocoSistema = css.slice(css.indexOf('@media (prefers-color-scheme: dark)'), css.indexOf("/* ...ou o escolhido no botão"));
  const blocoBotao = css.slice(css.indexOf(":root[data-tema='escuro'] {"), css.indexOf(":root[data-tema='claro']"));
  const escuro = { ...claro, ...tokens(blocoSistema) };

  /** color-mix(in oklch, a p%, b) de duas cores do mesmo matiz. */
  const misturar = (a, p, b) => {
    const [x, y] = [oklch(a), oklch(b)];
    return `oklch(${x.map((v, i) => (i === 2 ? v : v * p + y[i] * (1 - p))).join(' ')})`;
  };

  test('o escuro escolhido no botão tem exatamente os valores do escuro do sistema', () => {
    const doSistema = tokens(blocoSistema);
    assert.ok(Object.keys(doSistema).length >= 10);
    assert.deepEqual(tokens(blocoBotao), doSistema);
    assert.match(blocoSistema, /:root:not\(\[data-tema='claro'\]\)/, 'o claro escolhido no botão precisa vencer o escuro do sistema');
  });

  for (const [modo, t] of [['claro', claro], ['escuro', escuro]]) {
    test(`texto na ferrugem e no ferro com contraste suficiente no modo ${modo}`, () => {
      const pares = [
        ['título da abertura (tinta na ferrugem)', t['--ferrugem-tinta'], t['--ferrugem'], 4.5],
        ['descrição da abertura (lide na ferrugem)', t['--ferrugem-lide'], t['--ferrugem'], 4.5],
        ['menu do celular (tinta do ferro)', t['--ferro-tinta'], t['--ferro'], 7],
        ['"Páginas" e grupo do menu do celular (suave do ferro)', t['--ferro-suave'], t['--ferro'], 4.5],
        ['página aberta no menu do celular (brasa no ferro sobre o realce)', t['--brasa-no-ferro'], misturar(t['--ferro-tinta'], 0.1, t['--ferro']), 4.5],
        ['atalho do topo e botão de tema (tinta do ferro)', t['--ferro-tinta'], t['--ferro'], 4.5],
        ['seção atual no sumário (tinta no fundo)', t['--tinta'], t['--fundo'], 7],
      ];
      for (const [nome, a, b, minimo] of pares) {
        const c = contraste(a, b);
        assert.ok(c >= minimo, `${nome}: ${c.toFixed(2)}:1 (mínimo ${minimo}:1) no modo ${modo}`);
      }
    });
  }

  test('o anel de foco troca de cor onde a brasa sumiria: na ferrugem, no topo e no menu em ferro', () => {
    assert.match(css, /\.abertura-pagina :focus-visible \{\s*outline-color: var\(--ferrugem-tinta\);/);
    assert.match(css, /\.topo :focus-visible \{\s*outline-color: var\(--brasa-no-ferro\);/);
    assert.match(css, /\.menu :focus-visible \{\s*outline-color: var\(--brasa-no-ferro\);/);
  });
});

// ---------- Claro/escuro manual ----------

describe('botão de claro/escuro', () => {
  const base = ler('src/layouts/Base.astro');

  test('o tema salvo é aplicado no <head>, antes da pintura, e só aceita claro ou escuro', () => {
    const head = base.slice(base.indexOf('<head>'), base.indexOf('</head>'));
    assert.match(head, /localStorage\.getItem\('forge-tema'\)/);
    assert.match(head, /tema === 'claro' \|\| tema === 'escuro'/);
    assert.match(head, /try \{[\s\S]*\} catch \{\}/, 'localStorage pode lançar (modo privado): tem de estar em try');
  });

  test('o botão nasce escondido (sem JS ele não faria nada) e é um toggle com nome e estado', () => {
    for (const p of [...PAGINAS, '']) {
      const html = lerDist(`${p ? `${p}/` : ''}index.html`);
      const botao = html.match(/<button class="tema"[^>]*>/)?.[0];
      assert.ok(botao, `${p || 'início'}: sem o botão`);
      assert.match(botao, /type="button"/);
      assert.match(botao, /aria-label="Modo escuro"/);
      assert.match(botao, /aria-pressed="false"/);
      assert.match(botao, /\shidden[\s>]/);
    }
  });

  test('o alvo do botão tem 44px', () => {
    const regra = css.match(/\.tema \{([^}]*)\}/)[1];
    assert.match(regra, /width: 2\.75rem/);
    assert.match(regra, /height: 2\.75rem/);
  });
});

// ---------- Fontes pré-carregadas ----------

describe('pré-carregamento das fontes', () => {
  test('cada página pré-carrega as duas fontes da primeira dobra, e o arquivo é o mesmo que o CSS usa', () => {
    const folhas = fs
      .readdirSync(path.join(dist, '_astro'))
      .filter((f) => f.endsWith('.css'))
      .map((f) => fs.readFileSync(path.join(dist, '_astro', f), 'utf8'))
      .join('\n');
    for (const p of [...PAGINAS, '']) {
      const html = lerDist(`${p ? `${p}/` : ''}index.html`);
      const preloads = [...html.matchAll(/<link rel="preload" href="([^"]+)" as="font" type="font\/woff2" crossorigin>/g)].map((m) => m[1]);
      assert.equal(preloads.length, 2, `${p || 'início'}: ${preloads.length} preloads`);
      assert.ok(preloads.some((h) => h.includes('archivo-latin-wdth-normal')), 'Archivo (títulos)');
      assert.ok(preloads.some((h) => h.includes('source-serif-4-latin-opsz-normal')), 'Source Serif 4 (texto)');
      for (const h of preloads) {
        assert.ok(h.startsWith(`${BASE}/_astro/`), h);
        assert.ok(fs.existsSync(path.join(dist, h.slice(BASE.length))), `${h} não existe no dist`);
        assert.ok(folhas.includes(h), `${h} não é o arquivo que o CSS carrega: o navegador baixaria duas vezes`);
      }
    }
  });
});

// ---------- Favicon e ícone ----------

describe('favicon e ícone da tela inicial', () => {
  const caminhos = (svg) => [...svg.matchAll(/ d="([^"]+)"/g)].map((m) => m[1]);

  test('o favicon é a logo das quatro fitas (os mesmos traços do Logo.astro)', () => {
    const logo = caminhos(ler('src/components/Logo.astro'));
    assert.equal(logo.length, 4);
    assert.deepEqual(caminhos(ler('public/favicon.svg')), logo);
  });

  test('as cores do favicon são hex (nem todo navegador lê oklch() no ícone) e o fundo é a ferrugem', () => {
    const svg = ler('public/favicon.svg');
    assert.ok(!/oklch\(/.test(svg.replace(/<!--[\s\S]*?-->/g, '')), 'oklch() fora do comentário');
    const fundo = svg.match(/<rect [^>]*fill="(#[0-9A-Fa-f]{6})"/)?.[1];
    assert.ok(fundo, 'sem o fundo em hex');
    // A ferrugem do global.css convertida para sRGB.
    const [L, C, h] = oklch(css.match(/--ferrugem: (oklch\([^)]+\));/)[1]);
    const a = C * Math.cos((h * Math.PI) / 180);
    const b = C * Math.sin((h * Math.PI) / 180);
    const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
    const hex = [
      4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
      -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
      -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
    ]
      .map((v) => Math.min(1, Math.max(0, v)))
      .map((v) => Math.round((v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055) * 255))
      .map((v) => v.toString(16).padStart(2, '0'))
      .join('');
    assert.equal(fundo.toLowerCase(), `#${hex}`);
  });

  test('o apple-touch-icon é um PNG de 180x180 e toda página aponta para ele com o base', () => {
    const png = fs.readFileSync(path.join(SITE, 'public', 'apple-touch-icon.png'));
    assert.equal(png.subarray(1, 4).toString(), 'PNG');
    assert.equal(png.readUInt32BE(16), 180);
    assert.equal(png.readUInt32BE(20), 180);
    for (const p of PAGINAS) {
      assert.match(lerDist(`${p}/index.html`), new RegExp(`<link rel="apple-touch-icon" href="${BASE}/apple-touch-icon.png">`), p);
    }
  });
});

// ---------- Sumário: a seção que está na tela ----------

describe('sumário', () => {
  test('a seção atual é marcada com aria-current e um estilo próprio', () => {
    const comp = ler('src/components/Sumario.astro');
    assert.match(comp, /setAttribute\('aria-current', 'location'\)/);
    // Os títulos vêm depois do sumário no HTML: procurá-los antes do DOMContentLoaded não acharia nenhum.
    assert.match(comp, /addEventListener\('DOMContentLoaded'/);
    assert.match(css, /\.sumario a\[aria-current\] \{/);
  });
});

// ---------- Limpeza que a onda 8 deixou para a B6 ----------

describe('limpeza', () => {
  test('um mapa só do escreve_codigo: a página /fluxo/ usa o do diagrama', () => {
    const pagina = ler('src/pages/fluxo.astro');
    assert.match(pagina, /import \{ subDoPapel \} from '\.\.\/lib\/diagrama\.mjs'/);
    assert.ok(!/só escreve testes|não escreve código/i.test(pagina), 'o fluxo.astro escreve o próprio mapa');
  });

  test('sem !important fora do bloco de movimento reduzido', () => {
    const semMovimento = css.replace(/@media \(prefers-reduced-motion: reduce\) \{[\s\S]*?\n\}/g, '');
    assert.equal((semMovimento.match(/!important/g) || []).length, 0);
  });

  test('um apoio só para copiar o site nos testes (tests/apoio.mjs)', () => {
    const testes = fs.readdirSync(path.join(SITE, 'tests')).filter((f) => f.endsWith('.test.mjs'));
    for (const f of testes) {
      const codigo = ler(`tests/${f}`);
      assert.ok(!/cpSync\(path\.join\(SITE/.test(codigo), `${f} copia o site por conta própria`);
      assert.ok(!/fs\.symlinkSync\(/.test(codigo), `${f} liga o node_modules por conta própria`);
      assert.ok(!/function luminancia\(/.test(codigo), `${f} tem a própria conta de contraste`);
    }
  });
});

// ---------- README do site ----------

describe('README do site', () => {
  const readme = ler('README.md');

  test('diz como rodar: os scripts do package.json existem', () => {
    const pkg = JSON.parse(ler('package.json'));
    for (const s of ['build', 'dev', 'preview', 'dados', 'links']) {
      assert.ok(pkg.scripts[s], `package.json sem ${s}`);
      assert.ok(readme.includes(`npm run ${s}`), `README não fala do npm run ${s}`);
    }
    assert.ok(readme.includes('npm test'));
    assert.ok(readme.includes('python -m unittest discover -s site/scripts'));
    assert.ok(readme.includes(pkg.engines.node.replace('>=', '')), 'README com outra versão do Node');
  });

  test('diz como os dados são gerados: o extrair.py, os dois JSON e de onde cada um vem', () => {
    for (const trecho of ['scripts/extrair.py', 'src/data/comandos.json', 'src/data/fluxo.json', 'montar_parser()', 'FORGE_REGISTRO', 'SKILL.md', 'PAPEIS', 'ETAPAS', 'src/data/projetos.json']) {
      assert.ok(readme.includes(trecho), `README sem ${trecho}`);
    }
  });

  test('todo caminho de arquivo que o README cita existe', () => {
    for (const [, c] of readme.matchAll(/`((?:src|scripts|tests|\.claude|\.github)\/[\w./\-[\]]*)`/g)) {
      // Caminhos de site/ ou da raiz da skill (scripts/forge.py, .github/workflows/pages.yml).
      const alvo = c.replace(/\*\.(md|test\.mjs)$/, '');
      // O que está no .gitignore (a impeccable, D20) só existe na máquina do dono: no Actions não está lá.
      const ignorado = spawnSync('git', ['check-ignore', '-q', alvo], { cwd: SITE }).status === 0;
      if (ignorado) continue;
      assert.ok([SITE, path.join(SITE, '..')].some((raiz) => fs.existsSync(path.join(raiz, alvo))), `README cita ${c}, que não existe`);
    }
  });
});
