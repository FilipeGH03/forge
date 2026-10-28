// Testes da B2 (design: PRODUCT.md, DESIGN.md, paleta OKLCH, tipografia, navegação lateral,
// sumário, claro/escuro e 375px).
//
//     node --test tests/b2.test.mjs        (rodado de site/, depois do npm install)
//
// O build roda numa cópia temporária do site (tests/apoio.mjs), para não deixar src/data/
// modificado pelo prebuild (fim de linha) nem tocar em src/content/ (frente A).
// O que precisa de navegador (rolagem horizontal em 375px, alvo de toque) fica fora daqui.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { apagarCopia, BASE, construirCopia, contraste, oklch, SITE, tokens } from './apoio.mjs';

const SECOES = ['comece', 'conceitos', 'fluxo', 'referencia'];

const ler = (rel) => fs.readFileSync(path.join(SITE, rel), 'utf8');

const css = ler('src/estilos/global.css');
const claro = tokens(css.slice(css.indexOf(':root {'), css.indexOf('@media (prefers-color-scheme: dark)')));
const blocoEscuro = css.slice(css.indexOf('@media (prefers-color-scheme: dark)'));
const escuro = { ...claro, ...tokens(blocoEscuro.slice(0, blocoEscuro.indexOf('@media (min-width'))) };

/** Resolve `var(--x)` ate chegar num oklch(). */
function resolver(modo, valor) {
  let v = valor;
  for (let i = 0; i < 5 && v.startsWith('var('); i++) v = modo[v.match(/var\((--[\w-]+)\)/)[1]];
  return v;
}

// ---------- Build ----------

let dir;
let dist;
const lerDist = (rel) => fs.readFileSync(path.join(dist, rel), 'utf8');

const docs = fs
  .readdirSync(path.join(SITE, 'src', 'content', 'docs'))
  .filter((f) => f.endsWith('.md'))
  .map((f) => {
    const fm = fs.readFileSync(path.join(SITE, 'src', 'content', 'docs', f), 'utf8').split('---')[1];
    const campo = (k) => fm.match(new RegExp(`^${k}:\\s*(.+)$`, 'm'))?.[1].trim().replace(/^["']|["']$/g, '');
    return { slug: f.replace(/\.md$/, ''), titulo: campo('titulo'), secao: campo('secao'), ordem: Number(campo('ordem')) };
  });

before(() => {
  ({ dir, dist } = construirCopia('b2'));
});

after(() => apagarCopia(dir));

// ---------- PRODUCT.md e DESIGN.md ----------

// Os dois ficam só na máquina do dono (fora do git, D15): no runner do Actions não existem, e o grupo pula.
const ARQUIVOS_DA_IMPECCABLE = ['PRODUCT.md', 'DESIGN.md', path.join('.claude', 'skills', 'impeccable', 'scripts', 'palette.mjs')]
  .every((f) => fs.existsSync(path.join(SITE, f)));

describe('PRODUCT.md e DESIGN.md', { skip: !ARQUIVOS_DA_IMPECCABLE && 'PRODUCT.md e DESIGN.md são locais (fora do git)' }, () => {
  test('PRODUCT.md tem registro brand, plataforma web e as seções da impeccable', () => {
    const p = ler('PRODUCT.md');
    assert.match(p, /## Register\s+brand\b/);
    assert.match(p, /## Platform\s+web\b/);
    for (const s of ['Users', 'Product Purpose', 'Positioning', 'Brand Personality', 'Anti-references', 'Design Principles', 'Accessibility & Inclusion']) {
      assert.match(p, new RegExp(`^## ${s}$`, 'm'), `falta a seção ${s}`);
    }
  });

  test('DESIGN.md tem o frontmatter e as seis seções do formato', () => {
    const d = ler('DESIGN.md');
    assert.match(d, /^---\nname: forge\n/);
    for (const chave of ['colors:', 'typography:', 'rounded:', 'spacing:', 'components:']) {
      assert.ok(d.includes(`\n${chave}`), `frontmatter sem ${chave}`);
    }
    for (const n of [1, 2, 3, 4, 5, 6]) assert.match(d, new RegExp(`^## ${n}\\. `, 'm'), `falta a seção ${n}`);
  });

  test('a paleta do DESIGN.md é a do global.css (cada cor do frontmatter existe na folha)', () => {
    const d = ler('DESIGN.md');
    const fm = d.split('---')[1];
    const cores = [...fm.matchAll(/^\s{2}([\w-]+): "(oklch\([^)]*\))"/gm)].filter((m) => /^[a-z-]+$/.test(m[1]));
    const naFolha = new Set([...css.matchAll(/oklch\([^)]*\)/g)].map((m) => m[0].replace(/\s+/g, ' ')));
    const colors = fm.slice(fm.indexOf('colors:'), fm.indexOf('typography:'));
    const valores = [...colors.matchAll(/"(oklch\([^)]*\))"/g)].map((m) => m[1]);
    assert.ok(valores.length >= 20, 'poucas cores no DESIGN.md');
    for (const v of valores) assert.ok(naFolha.has(v), `${v} do DESIGN.md não está no global.css`);
    assert.ok(cores.length > 0);
  });

  test('a semente do DESIGN.md é a seed-042 do palette.mjs e a cor da marca é ela', () => {
    const palette = path.join(SITE, '.claude', 'skills', 'impeccable', 'scripts', 'palette.mjs');
    const r = spawnSync(process.execPath, [palette, '--id', 'seed-042'], { encoding: 'utf8' });
    const semente = r.stdout.match(/oklch\([^)]*\)/)?.[0];
    assert.equal(semente, 'oklch(0.688 0.133 35.8)');
    assert.equal(claro['--brasa'], semente);
    assert.ok(ler('DESIGN.md').includes(semente));
    // O favicon deixou de usar a semente: pela D16 ele é a logo sobre a ferrugem (tests/b6.test.mjs).
  });
});

// ---------- Contraste (WCAG AA) ----------

describe('contraste WCAG AA nos dois modos', () => {
  const pares = [
    // texto, fundo, minimo
    ['--tinta', '--fundo', 7],
    ['--tinta', '--superficie', 7],
    ['--suave', '--fundo', 4.5],
    ['--suave', '--superficie', 4.5],
    ['--brasa-texto', '--fundo', 4.5],
    ['--brasa-texto', '--superficie', 4.5],
    ['--brasa-texto', '--brasa-fundo', 4.5],
    ['--tinta', '--brasa-fundo', 4.5],
    ['--aco', '--fundo', 4.5],
    ['--ferro-tinta', '--ferro', 7],
    ['--codigo-token-keyword', '--ferro', 4.5],
    ['--codigo-token-function', '--ferro', 4.5],
    ['--codigo-token-string', '--ferro', 4.5],
    ['--codigo-token-string-expression', '--ferro', 4.5],
    ['--codigo-token-constant', '--ferro', 4.5],
    ['--codigo-token-parameter', '--ferro', 4.5],
    ['--codigo-token-comment', '--ferro', 4.5],
    ['--codigo-token-punctuation', '--ferro', 4.5],
    ['--codigo-token-link', '--ferro', 4.5],
  ];
  for (const [nome, modo] of [['claro', claro], ['escuro', escuro]]) {
    for (const [fg, bg, min] of pares) {
      test(`${nome}: ${fg} sobre ${bg} >= ${min}:1`, () => {
        const c = contraste(resolver(modo, modo[fg]), resolver(modo, modo[bg]));
        assert.ok(c >= min, `${fg} sobre ${bg} no ${nome}: ${c.toFixed(2)}:1`);
      });
    }
  }

  test('a cor da semente (--brasa) é decorativa: não passa como texto sobre o papel, e nenhum texto a usa', () => {
    assert.ok(contraste(claro['--brasa'], claro['--fundo']) < 4.5);
    // `color:` com --brasa (exceto --brasa-texto/--brasa-fundo) seria texto na cor decorativa
    assert.equal([...css.matchAll(/[^-]color:\s*var\(--brasa\)/g)].length, 0);
  });

  test('o fundo é branco puro no claro e neutro (croma 0) no escuro', () => {
    assert.equal(claro['--fundo'], 'oklch(1 0 0)');
    assert.equal(oklch(escuro['--fundo'])[1], 0);
  });
});

// ---------- Tipografia ----------

describe('tipografia', () => {
  const PROIBIDAS = ['Inter', 'DM Sans', 'Outfit', 'Plus Jakarta Sans', 'Space Grotesk', 'Fraunces', 'Playfair Display', 'IBM Plex', 'Instrument Sans', 'Newsreader', 'Lora', 'Crimson', 'Syne', 'Cormorant', 'Roboto'];

  test('as três fontes vêm do npm (sem CDN) e saem no dist', () => {
    const pkg = JSON.parse(ler('package.json'));
    for (const f of ['archivo', 'source-serif-4', 'jetbrains-mono']) assert.ok(pkg.dependencies[`@fontsource-variable/${f}`], f);
    const fontes = fs.readdirSync(path.join(dist, '_astro')).filter((f) => f.endsWith('.woff2'));
    for (const prefixo of ['archivo-latin-', 'source-serif-4-latin-', 'jetbrains-mono-latin-']) {
      assert.ok(fontes.some((f) => f.startsWith(prefixo)), `sem woff2 ${prefixo}`);
    }
    const html = lerDist('docs/visao-geral/index.html');
    assert.ok(!/fonts\.googleapis|fonts\.gstatic|cdn\./.test(html), 'fonte ou script de CDN no HTML');
    const cssSaida = fs.readdirSync(path.join(dist, '_astro')).filter((f) => f.endsWith('.css')).map((f) => fs.readFileSync(path.join(dist, '_astro', f), 'utf8')).join('\n');
    assert.ok(!/https?:\/\/(?!www\.w3\.org)/.test(cssSaida.replace(/url\([^)]*\)/g, '')), 'URL externa no CSS');
    assert.ok(!/url\(https?:/.test(cssSaida), 'recurso externo no CSS');
  });

  test('nenhuma fonte da lista de proibidas da impeccable', () => {
    const familias = [...css.matchAll(/--fonte-[\w-]+:\s*([^;]+);/g)].map((m) => m[1]).join(' ');
    for (const f of PROIBIDAS) assert.ok(!new RegExp(`['"]?${f}['"]?[,; ]`, 'i').test(familias + ' '), `fonte proibida: ${f}`);
  });

  test('cada família de texto tem alternativa de sistema', () => {
    for (const nome of ['--fonte-titulo', '--fonte-texto', '--fonte-codigo']) {
      assert.match(claro[nome], /,\s*[^,]+/, `${nome} sem fallback`);
    }
  });

  test('corpo em 17px ou mais e sem caixa-alta espaçada nos rótulos', () => {
    assert.equal(claro['--t-texto'], '1.0625rem');
    assert.ok(!/text-transform:\s*uppercase/.test(css), 'rótulo em caixa-alta');
  });

  test('nenhum tamanho de fonte fixo abaixo de 0.8125rem (13px)', () => {
    for (const m of css.matchAll(/font-size:\s*([\d.]+)(rem|px|em)/g)) {
      const px = m[2] === 'px' ? Number(m[1]) : Number(m[1]) * 16;
      if (m[2] === 'em') continue; // relativo ao pai (código na linha, 0.86em)
      assert.ok(px >= 13, `font-size ${m[0]} < 13px`);
    }
  });
});

// ---------- Layout de documentação: navegação lateral ----------

describe('navegação lateral por secao e ordem', () => {
  const esperada = SECOES.flatMap((s) => docs.filter((d) => d.secao === s).sort((a, b) => a.ordem - b.ordem));

  test('há 10 páginas de docs e a navegação as lista na ordem secao, ordem', () => {
    assert.ok(docs.length >= 10);
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      const nav = html.match(/<nav aria-label="Documentação">([\s\S]*?)<\/nav>/)[1];
      const links = [...nav.matchAll(/<a href="([^"]+)"/g)].map((m) => m[1]);
      // As páginas feitas dos dados gerados não são da coleção `docs`: o diagrama do fluxo (B5) abre a seção
      // Fluxo e os comandos (B4) fecham a Referência.
      const doc = (e) => `${BASE}/docs/${e.slug}/`;
      const ordem = esperada.flatMap((e, i) => [
        ...(e.secao === 'fluxo' && esperada[i - 1]?.secao !== 'fluxo' ? [`${BASE}/fluxo/`] : []),
        doc(e),
        ...(e.secao === 'referencia' && esperada[i + 1]?.secao !== 'referencia' ? [`${BASE}/comandos/`] : []),
      ]);
      assert.deepEqual(links, ordem, `ordem da nav em ${d.slug}`);
      const grupos = [...nav.matchAll(/class="menu-grupo"[^>]*>([^<]+)</g)].map((m) => m[1]);
      const presentes = SECOES.filter((s) => docs.some((x) => x.secao === s));
      assert.equal(grupos.length, presentes.length);
      const rotulo = { comece: 'Comece aqui', conceitos: 'Conceitos', fluxo: 'Fluxo', referencia: 'Referência' };
      assert.deepEqual(grupos, presentes.map((x) => rotulo[x]));
    }
  });

  test('só a página aberta tem aria-current="page", e ela aponta para si mesma', () => {
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      const atuais = [...html.matchAll(/<a href="([^"]+)" aria-current="page"/g)];
      assert.equal(atuais.length, 1, `aria-current em ${d.slug}`);
      assert.equal(atuais[0][1], `${BASE}/docs/${d.slug}/`);
      assert.match(html, /<span class="menu-atual">[^<]+<\/span>/, `${d.slug}: sem o título atual no resumo do menu`);
    }
  });

  test('todo link da navegação existe no dist', () => {
    const html = lerDist('docs/visao-geral/index.html');
    const nav = html.match(/<nav aria-label="Documentação">([\s\S]*?)<\/nav>/)[1];
    for (const m of nav.matchAll(/<a href="([^"]+)"/g)) {
      const rel = m[1].replace(BASE, '').replace(/^\//, '');
      assert.ok(fs.existsSync(path.join(dist, rel, 'index.html')), `link quebrado na nav: ${m[1]}`);
    }
  });

  test('cada grupo é uma lista rotulada pelo nome da seção (acessível)', () => {
    const html = lerDist('docs/visao-geral/index.html');
    for (const s of SECOES) {
      assert.ok(html.includes(`id="menu-${s}"`) && html.includes(`aria-labelledby="menu-${s}"`), s);
    }
  });

  test('a navegação não aparece na página inicial como duplicata nem quebra o título da home', () => {
    const home = lerDist('index.html');
    assert.match(home, /<title>forge<\/title>/);
    assert.equal((home.match(/<h1>/g) || []).length, 1);
  });
});

// ---------- Sumário ----------

describe('sumário "Nesta página"', () => {
  test('lista os ## e ### e cada âncora existe no corpo da página', () => {
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
      const sumario = html.match(/<nav aria-label="Nesta página">([\s\S]*?)<\/nav>/);
      const titulosCorpo = [...html.matchAll(/<h([23]) id="([^"]+)"/g)];
      if (titulosCorpo.length < 2) {
        assert.equal(sumario, null, `${d.slug}: sumário com menos de 2 títulos`);
        continue;
      }
      assert.ok(sumario, `${d.slug}: sem sumário`);
      const alvos = [...sumario[1].matchAll(/href="#([^"]+)"/g)].map((m) => m[1]);
      assert.deepEqual(alvos, titulosCorpo.map((m) => m[2]), `${d.slug}: sumário != títulos do corpo`);
      for (const a of alvos) assert.ok(ids.has(a), `${d.slug}: âncora #${a} sem alvo`);
    }
  });

  test('o <h1> não entra no sumário e continua sem atributos (contrato 1.1 / B1)', () => {
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      assert.equal((html.match(/<h1[ >]/g) || []).length, 1);
      assert.match(html, /<h1>[^<]+<\/h1>/);
      const sumario = html.match(/<nav aria-label="Nesta página">([\s\S]*?)<\/nav>/)?.[1] ?? '';
      assert.ok(!/<h1/.test(sumario) && !sumario.includes('href="#' + d.slug + '"'));
    }
  });

  test('ids repetidos no HTML não existem (âncoras do sumário seriam ambíguas)', () => {
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
      const repetidos = ids.filter((id, i) => ids.indexOf(id) !== i);
      assert.deepEqual(repetidos, [], `${d.slug}: ids repetidos`);
    }
  });
});

// ---------- Estrutura da página, acessibilidade e responsivo ----------

describe('estrutura, acessibilidade e 375px (estático)', () => {
  test('lang pt-BR, viewport, color-scheme, link de pular e landmarks', () => {
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      assert.match(html, /<html lang="pt-BR">/);
      assert.match(html, /<meta name="viewport" content="width=device-width, initial-scale=1">/);
      assert.match(html, /<meta name="color-scheme" content="light dark">/);
      assert.match(html, /<a class="pular" href="#conteudo">/);
      assert.equal((html.match(/<main id="conteudo">/g) || []).length, 1);
      assert.equal((html.match(/<header class="topo">/g) || []).length, 1);
      assert.ok(html.indexOf('class="pular"') < html.indexOf('class="topo"'), 'pular vem primeiro no foco');
    }
  });

  test('title e meta description do contrato 1.1 continuam (B1)', () => {
    const html = lerDist('docs/visao-geral/index.html');
    assert.match(html, /<title>Visão geral · forge<\/title>/);
    assert.match(html, /<meta name="description" content="[^"]{10,160}">/);
  });

  test('toda tabela do conteúdo está numa região rolável e focável', () => {
    let tabelas = 0;
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      const n = (html.match(/<table/g) || []).length;
      const em = (html.match(/<div class="tabela" role="region" tabindex="0" aria-label="Tabela[^"]*"><table/g) || []).length;
      assert.equal(em, n, `${d.slug}: ${n} tabelas, ${em} embrulhadas`);
      tabelas += n;
    }
    assert.ok(tabelas > 0, 'nenhuma tabela no conteúdo: o teste não provou nada');
  });

  test('todo bloco de código rola dentro da caixa e é focável pelo teclado', () => {
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      for (const m of html.matchAll(/<pre\b[^>]*>/g)) {
        assert.match(m[0], /overflow-x: ?auto/, `${d.slug}: pre sem overflow-x`);
        assert.match(m[0], /tabindex="0"/, `${d.slug}: pre sem tabindex`);
        assert.match(m[0], /data-language="[a-z]+"/, `${d.slug}: pre sem linguagem`);
      }
    }
  });

  test('o realce segue o tema (variáveis --codigo-), sem cor fixa nos tokens', () => {
    for (const d of docs) {
      const html = lerDist(`docs/${d.slug}/index.html`);
      for (const m of html.matchAll(/<span style="color:([^"]+)"/g)) {
        assert.match(m[1], /^var\(--codigo-/, `${d.slug}: token com cor fixa ${m[1]}`);
      }
      assert.ok(!/<pre[^>]*background-color:#/.test(html));
    }
  });

  test('sem estilo com escopo do Astro: nenhum data-astro-cid no HTML do conteúdo', () => {
    for (const d of docs) assert.ok(!lerDist(`docs/${d.slug}/index.html`).includes('data-astro-cid'), d.slug);
  });

  test('o CSS tem foco visível, alvo de toque de 44px, movimento reduzido e claro/escuro', () => {
    assert.match(css, /:focus-visible\s*{[^}]*outline:/);
    assert.match(css, /prefers-reduced-motion:\s*reduce/);
    assert.match(css, /prefers-color-scheme:\s*dark/);
    // Alvo de toque do menu no celular: 0.7rem*2 + 15px*1.35 = 42.65px. O DESIGN.md diz 44px
    // (WCAG 2.2 AAA, 2.5.5); o piso do AA (2.5.8) é 24px. Aqui vale o AA; a diferença vai em notas.
    assert.match(css, /\.menu nav a\s*{[^}]*padding:\s*0\.7rem/);
    const alvo = 0.7 * 16 * 2 + 0.9375 * 16 * 1.35;
    assert.ok(alvo >= 24, `alvo de toque do menu: ${alvo}px`);
  });

  test('nenhuma largura fixa em px que estoure 375px (min-width/width > 343px fora de @media)', () => {
    const fora = css.replace(/@media[^{]*{(?:[^{}]*{[^{}]*})*[^{}]*}/g, '');
    for (const m of fora.matchAll(/(?<![-\w])(?:min-)?width:\s*(\d+)px/g)) {
      assert.ok(Number(m[1]) <= 343, `largura fixa ${m[0]}`);
    }
  });

  test('sem JS os <details> ficam abertos (atributo open no HTML) e o script é inline e pequeno', () => {
    const html = lerDist('docs/visao-geral/index.html');
    assert.match(html, /<details class="menu" open>/);
    assert.match(html, /<details class="sumario" open>/);
    assert.ok(/fixarAberto\(document\.currentScript\.previousElementSibling, '\(min-width: 64rem\)'\)/.test(html));
    assert.ok(/fixarAberto\(document\.currentScript\.previousElementSibling, '\(min-width: 80rem\)'\)/.test(html));
  });

  test('favicon do dist e referenciado com o base', () => {
    assert.ok(fs.existsSync(path.join(dist, 'favicon.svg')));
    assert.ok(lerDist('docs/visao-geral/index.html').includes(`href="${BASE}/favicon.svg"`));
  });
});

// ---------- Não pode acontecer ----------

describe('o que não pode acontecer', () => {
  test('nenhum commit da B2 tocou em src/content, src/data nem scripts (frente A)', () => {
    // Só os commits da B2: a frente A e a main podem seguir mudando essas pastas sem quebrar este teste.
    const r = spawnSync('git', ['log', '--name-only', '--format=', '--grep=^B2', 'HEAD', '--', 'site/src/content', 'site/src/data', 'site/scripts'], {
      cwd: path.join(SITE, '..'),
      encoding: 'utf8',
    });
    if (r.status !== 0) return; // fora de um repositório git: nada a conferir
    assert.equal(r.stdout.trim(), '');
  });

  test('sem sombras em superfícies (plano); o brilho do lingote saiu com a logo nova (D16)', () => {
    const sombras = [...css.matchAll(/box-shadow:[^;]+;/g)].map((m) => m[0]);
    assert.deepEqual(sombras, []);
  });

  test('sem gradiente em texto e sem faixa lateral colorida (impeccable)', () => {
    assert.ok(!/background-clip:\s*text/.test(css));
    assert.ok(!/border-(left|right):\s*[2-9]px/.test(css));
  });
});
