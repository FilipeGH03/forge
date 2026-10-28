// Testes da B5 (diagrama do fluxo: componente SVG acessível a partir do fluxo.json, contrato 1.3, e a
// página /fluxo/).
//
//     node --test tests/b5.test.mjs        (rodado de site/, depois do npm install)
//
// O build roda numa cópia temporária do site (tests/apoio.mjs). Nela entram duas mudanças que a
// cópia de produção não tem: um título de fase trocado no fluxo.json (o diagrama tem de acompanhar o dado)
// e uma página de teste que usa o componente sem nenhuma prop, como o dono vai usar na página inicial.
// O que precisa de navegador (screenshots em claro/escuro e 375px) fica fora daqui.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { LARGURA, montarDiagrama, pontos, quebrar } from '../src/lib/diagrama.mjs';
import { apagarCopia, BASE, construirCopia, contraste, SITE, tokens } from './apoio.mjs';
import { conferirLinks } from './conferir-links.mjs';

const fluxo = JSON.parse(fs.readFileSync(path.join(SITE, 'src', 'data', 'fluxo.json'), 'utf8'));
// No Windows o working tree pode vir com CRLF (autocrlf): os seletores de várias linhas pedem LF.
const css = fs.readFileSync(path.join(SITE, 'src', 'estilos', 'global.css'), 'utf8').replace(/\r\n/g, '\n');
const TITULO_NOVO = 'Levantamento renomeado no teste';

/** Entidades que o Astro escreve no HTML, de volta para texto. */
const desescapar = (t) =>
  t
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/&amp;/g, '&');

const semTags = (t) => desescapar(t.replace(/<[^>]+>/g, ''));
// Só os SVGs do diagrama: a logo do topo (D16) também é um <svg>, mas não é o que estes testes olham.
const svgsDe = (html) => [...html.matchAll(/<svg\b[^>]*\bclass="diagrama"[^>]*>[\s\S]*?<\/svg>/g)].map((m) => m[0]);
const textosDe = (svg) => [...svg.matchAll(/<tspan\b[^>]*>([\s\S]*?)<\/tspan>/g)].map((m) => desescapar(m[1].trim()));
const juntar = (linhas) => linhas.join(' ').replace(/\s+/g, ' ');

// ---------- A geometria e os textos (puro, sem build) ----------

describe('quebrar: linhas de até N caracteres', () => {
  test('quebra por palavra e não perde nada', () => {
    const linhas = quebrar('Proposta: frentes, contratos e tarefas', 20);
    assert.deepEqual(linhas, ['Proposta: frentes,', 'contratos e tarefas']);
  });

  test('palavra maior que o limite fica inteira numa linha', () => {
    assert.deepEqual(quebrar('a supercalifragilistico b', 8), ['a', 'supercalifragilistico', 'b']);
  });
});

describe('montarDiagrama: fases', () => {
  const d = montarDiagrama(fluxo, { partes: ['fases'] });
  const emblemas = d.formas.filter((f) => f.tipo === 'emblema');

  test('um emblema por fase, na ordem do fluxo.json, de cima para baixo', () => {
    assert.deepEqual(emblemas.map((e) => e.texto), fluxo.fases.map((f) => String(f.n)));
    const ys = emblemas.map((e) => e.cy);
    assert.deepEqual([...ys].sort((a, b) => a - b), ys);
  });

  test('todo título de fase está escrito no desenho', () => {
    const escrito = juntar(d.formas.filter((f) => f.tipo === 'texto').flatMap((f) => f.linhas.map((l) => l.texto)));
    for (const fase of fluxo.fases) {
      assert.ok(escrito.includes(fase.titulo), `título da fase ${fase.n} fora do desenho`);
    }
  });

  test('a parada se marca por forma, borda e texto, não só por cor', () => {
    const paradas = fluxo.fases.filter((f) => f.parada);
    assert.equal(paradas.length, 1);
    assert.deepEqual(emblemas.filter((e) => e.forma === 'octogono').map((e) => e.texto), paradas.map((f) => String(f.n)));
    assert.equal(emblemas.filter((e) => e.forma === 'circulo').length, fluxo.fases.length - paradas.length);
    assert.equal(d.formas.filter((f) => f.tipo === 'caixa' && f.classe.includes('dg-parada')).length, 1);
    const avisos = d.formas.filter((f) => f.tipo === 'texto' && f.classe.includes('dg-aviso'));
    assert.equal(avisos.length, 1);
    assert.match(avisos[0].linhas[0].texto, /dono aprovar/);
  });

  test('um fio com seta entre cada par de fases', () => {
    const fios = d.formas.filter((f) => f.tipo === 'fio');
    assert.equal(fios.length, fluxo.fases.length - 1);
    assert.ok(fios.every((f) => f.seta));
  });

  test('a descrição lista as fases e diz qual é a parada', () => {
    for (const fase of fluxo.fases) assert.ok(d.descricao.includes(`Fase ${fase.n}, ${fase.titulo}`), `fase ${fase.n} fora da descrição`);
    assert.match(d.descricao, /A fase 4 é uma parada obrigatória/);
  });

  test('sem fase de parada, sem aviso de parada', () => {
    const sem = { ...fluxo, fases: fluxo.fases.map((f) => ({ ...f, parada: false })) };
    const x = montarDiagrama(sem, { partes: ['fases'] });
    assert.ok(!x.formas.some((f) => f.tipo === 'emblema' && f.forma === 'octogono'));
    assert.ok(!/é uma parada obrigatória/.test(x.descricao));
  });
});

describe('montarDiagrama: onda', () => {
  const d = montarDiagrama(fluxo, { partes: ['onda'] });
  const caixas = d.formas.filter((f) => f.tipo === 'caixa');
  const porEtapa = [];
  let i = 0;
  for (const e of fluxo.onda.etapas) {
    porEtapa.push(caixas.slice(i, i + e.papeis.length));
    i += e.papeis.length;
  }

  test('uma caixa por papel de cada etapa, na ordem das etapas', () => {
    const esperados = fluxo.onda.etapas.flatMap((e) => e.papeis);
    assert.equal(caixas.length, esperados.length);
    const nomes = d.formas.filter((f) => f.tipo === 'texto' && f.classe === 'dg-nome').map((f) => juntar(f.linhas.map((l) => l.texto)));
    assert.deepEqual(nomes, esperados.map((id) => fluxo.onda.papeis.find((p) => p.id === id).nome));
  });

  test('etapas em paralelo ficam lado a lado, na mesma altura e sem se tocar', () => {
    const paralelas = porEtapa.filter((par) => par.length > 1);
    assert.ok(paralelas.length >= 1);
    for (const par of paralelas) {
      assert.equal(new Set(par.map((c) => c.y)).size, 1);
      assert.equal(new Set(par.map((c) => c.h)).size, 1);
      for (let k = 1; k < par.length; k++) assert.ok(par[k].x >= par[k - 1].x + par[k - 1].w, 'caixas em paralelo se tocam');
    }
  });

  test('etapas em sequência não se sobrepõem na vertical', () => {
    for (let k = 1; k < porEtapa.length; k++) {
      assert.ok(porEtapa[k][0].y > porEtapa[k - 1][0].y + porEtapa[k - 1][0].h, `etapa ${k + 1} encosta na anterior`);
    }
  });

  test('a etapa condicional é tracejada, tem o rótulo escrito e um desvio para a etapa seguinte', () => {
    const condicionais = fluxo.onda.etapas.filter((e) => e.condicional);
    assert.ok(condicionais.length >= 1);
    assert.equal(caixas.filter((c) => c.classe.includes('dg-condicional')).length, condicionais.reduce((n, e) => n + e.papeis.length, 0));
    const rotulos = d.formas.filter((f) => f.tipo === 'texto' && f.classe === 'dg-rotulo').map((f) => juntar(f.linhas.map((l) => l.texto)).toLowerCase());
    for (const e of fluxo.onda.etapas.filter((x) => x.rotulo)) assert.ok(rotulos.includes(e.rotulo.toLowerCase()), `rótulo "${e.rotulo}" fora do desenho`);
    assert.equal(d.formas.filter((f) => f.tipo === 'fio' && f.classe === 'dg-desvio').length, condicionais.length);
  });

  test('cada papel diz, em texto, se escreve código', () => {
    const subs = d.formas.filter((f) => f.tipo === 'texto' && f.classe === 'dg-sub').map((f) => juntar(f.linhas.map((l) => l.texto)));
    assert.equal(subs.filter((t) => t === 'Escreve código').length, fluxo.onda.etapas.flatMap((e) => e.papeis).filter((id) => fluxo.onda.papeis.find((p) => p.id === id).escreve_codigo === 'sim').length);
    assert.equal(subs.filter((t) => t === 'Não escreve código').length, 2);
    assert.equal(subs.filter((t) => t === 'Só escreve testes').length, 1);
  });

  test('a descrição conta as etapas, o paralelo e o condicional', () => {
    assert.match(d.descricao, /4 etapas/);
    assert.match(d.descricao, /em paralelo: Revisor de contrato .* e Revisor de padrões/);
    assert.match(d.descricao, /tracejada, só acontece se for preciso/);
    assert.match(d.descricao, /Testador \(só escreve testes\)/);
  });

  test('papel citado numa etapa e ausente de onda.papeis é erro, não desenho calado', () => {
    const ruim = structuredClone(fluxo);
    ruim.onda.etapas[0].papeis = ['fantasma'];
    assert.throws(() => montarDiagrama(ruim, { partes: ['onda'] }), /fantasma/);
  });
});

describe('montarDiagrama: o conjunto', () => {
  test('tudo dentro do viewBox e sem coordenada inválida', () => {
    for (const partes of [['fases'], ['onda'], ['transversais'], ['fases', 'onda', 'transversais']]) {
      const d = montarDiagrama(fluxo, { partes });
      assert.equal(d.largura, LARGURA);
      for (const f of d.formas) {
        if (f.tipo === 'caixa') {
          assert.ok(f.x >= 0 && f.x + f.w <= LARGURA && f.y >= 0 && f.y + f.h <= d.altura, `caixa fora do viewBox em ${partes}`);
        } else if (f.tipo === 'fio') {
          assert.ok(!/NaN|undefined|Infinity/.test(f.d), `fio inválido: ${f.d}`);
          const nums = f.d.match(/-?\d+(\.\d+)?/g).map(Number);
          assert.ok(nums.every((n) => n >= 0 && n <= Math.max(LARGURA, d.altura)), `fio fora do viewBox: ${f.d}`);
        } else if (f.tipo === 'texto') {
          for (const l of f.linhas) assert.ok(l.x >= 0 && l.x <= LARGURA && l.y >= 0 && l.y <= d.altura, `texto fora: ${l.texto}`);
        }
      }
    }
  });

  test('legendas só quando há mais de uma parte, e podem ser ligadas ou desligadas', () => {
    const tem = (d) => d.formas.some((f) => f.tipo === 'texto' && f.classe === 'dg-legenda');
    assert.ok(!tem(montarDiagrama(fluxo, { partes: ['fases'] })));
    assert.ok(tem(montarDiagrama(fluxo)));
    assert.ok(!tem(montarDiagrama(fluxo, { legendas: false })));
    assert.ok(tem(montarDiagrama(fluxo, { partes: ['onda'], legendas: true })));
  });

  test('transversais: um losango com a inicial e a frase escrita', () => {
    const d = montarDiagrama(fluxo, { partes: ['transversais'] });
    const losangos = d.formas.filter((f) => f.tipo === 'emblema' && f.forma === 'losango');
    assert.deepEqual(losangos.map((e) => e.texto), fluxo.transversais.map((t) => t.titulo[0].toUpperCase()));
    assert.ok(d.formas.some((f) => f.tipo === 'texto' && f.linhas.some((l) => /Vale para o projeto todo/.test(l.texto))));
  });

  test('título e descrição existem, e parte inexistente é erro', () => {
    const d = montarDiagrama(fluxo);
    assert.match(d.titulo, /^Fluxo do forge: /);
    assert.ok(d.descricao.length > 100);
    assert.throws(() => montarDiagrama(fluxo, { partes: ['nada'] }), /nada/);
  });

  test('pontos: octógono tem 8 e losango tem 4 vértices', () => {
    assert.equal(pontos('octogono', 0, 0, 10).split(' ').length, 8);
    assert.equal(pontos('losango', 0, 0, 10).split(' ').length, 4);
  });
});

// ---------- As cores do desenho: contraste nos dois modos (WCAG) ----------

describe('cores do diagrama (global.css)', () => {
  const claro = tokens(css.slice(css.indexOf(':root {'), css.indexOf('@media (prefers-color-scheme: dark)')));
  const escuro = { ...claro, ...tokens(css.slice(css.indexOf('@media (prefers-color-scheme: dark)'), css.indexOf('@media (min-width: 40rem)'))) };
  const regra = (seletor) => {
    const i = css.indexOf(`${seletor} {`);
    assert.ok(i >= 0, `regra ${seletor} não existe`);
    return css.slice(i, css.indexOf('}', i));
  };

  test('só usa tokens do site: nenhuma cor escrita no bloco do diagrama', () => {
    const bloco = css.slice(css.indexOf('/* ---------- Diagrama do fluxo'), css.indexOf('/* ---------- Movimento'));
    assert.ok(bloco.length > 500);
    assert.ok(!/#[0-9a-f]{3,8}\b|oklch\(|rgb\(|hsl\(/i.test(bloco), 'cor fora dos tokens');
  });

  for (const [modo, t] of [['claro', claro], ['escuro', escuro]]) {
    test(`texto e traço do diagrama com contraste suficiente no modo ${modo}`, () => {
      const pares = [
        ['tinta na superfície (nome do papel e da fase)', t['--tinta'], t['--superficie'], 4.5],
        ['suave na superfície (subtítulo)', t['--suave'], t['--superficie'], 4.5],
        ['suave no fundo (rótulo e legenda)', t['--suave'], t['--fundo'], 4.5],
        ['brasa de texto no fundo de brasa (aviso e número da parada)', t['--brasa-texto'], t['--brasa-fundo'], 4.5],
        ['tinta do ferro no ferro (número da fase)', t['--ferro-tinta'], t['--ferro'], 4.5],
        ['traço (suave) no fundo: fios, setas e bordas', t['--suave'], t['--fundo'], 3],
        ['brasa de texto no fundo (borda da parada)', t['--brasa-texto'], t['--fundo'], 3],
      ];
      for (const [nome, a, b, minimo] of pares) {
        const c = contraste(a, b);
        assert.ok(c >= minimo, `${nome}: ${c.toFixed(2)}:1 (mínimo ${minimo}:1) no modo ${modo}`);
      }
    });
  }

  test('a diferença entre parada e condicional não é só de cor: borda grossa e tracejado', () => {
    assert.match(regra('.diagrama .dg-caixa.dg-parada'), /stroke-width:\s*2\.5/);
    assert.match(regra('.diagrama .dg-caixa'), /stroke-width:\s*1\.25/);
    assert.match(regra('.diagrama .dg-caixa.dg-condicional'), /stroke-dasharray/);
  });

  test('texto do SVG em 13px ou mais (unidades do viewBox de 340: escala ~1 em 375px)', () => {
    for (const seletor of ['.diagrama .dg-nome', '.diagrama .dg-sub,\n.diagrama .dg-rotulo', '.diagrama .dg-legenda', '.diagrama .dg-numero']) {
      const m = regra(seletor).match(/font-size:\s*(\d+)px/);
      assert.ok(m && Number(m[1]) >= 13, `${seletor} sem font-size de 13px ou mais`);
    }
  });
});

// ---------- O build ----------

let dir;
let dist;
let pagina;
let teste;
const lerDist = (rel) => fs.readFileSync(path.join(dist, rel), 'utf8');

before(() => {
  ({ dir, dist } = construirCopia('b5', (copia) => {
    // O dado muda na cópia: o diagrama tem de acompanhar.
    const f = path.join(copia, 'src', 'data', 'fluxo.json');
    const dados = JSON.parse(fs.readFileSync(f, 'utf8'));
    dados.fases[2].titulo = TITULO_NOVO;
    fs.writeFileSync(f, JSON.stringify(dados, null, 2));
    // A página de teste usa o componente do jeito mais simples, como a página inicial do dono vai usar.
    fs.writeFileSync(
      path.join(copia, 'src', 'pages', 'uso-do-componente.astro'),
      `---\nimport Base from '../layouts/Base.astro';\nimport DiagramaFluxo from '../components/DiagramaFluxo.astro';\n---\n<Base titulo="Uso" descricao="Uso do componente."><DiagramaFluxo /></Base>\n`,
    );
  }));
  pagina = lerDist('fluxo/index.html');
  teste = lerDist('uso-do-componente/index.html');
});

after(() => apagarCopia(dir));

describe('página /fluxo/', () => {
  test('tem dois diagramas (fases e onda), cada um um SVG com role="img"', () => {
    const svgs = svgsDe(pagina);
    assert.equal(svgs.length, 2);
    for (const svg of svgs) {
      assert.match(svg, /^<svg\b[^>]*\brole="img"/);
      assert.match(svg, /\bviewBox="0 0 340 \d+"/);
    }
  });

  test('o nome acessível vem do <title> e da <desc>: existem, não estão vazios e têm id único na página', () => {
    for (const svg of svgsDe(pagina)) {
      const ref = svg.match(/aria-labelledby="([^"]+)"/)[1].split(' ');
      assert.equal(ref.length, 2);
      for (const id of ref) {
        const m = svg.match(new RegExp(`<(title|desc) id="${id}">([\\s\\S]*?)</\\1>`));
        assert.ok(m, `aria-labelledby aponta para ${id}, que não existe`);
        assert.ok(semTags(m[2]).trim().length > 20, `${id} vazio ou curto demais`);
      }
    }
    const todos = [...pagina.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
    assert.equal(new Set(todos).size, todos.length, 'id repetido na página');
  });

  test('o diagrama das fases escreve cada título, o aviso da parada e usa octógono só nela', () => {
    const [fases] = svgsDe(pagina);
    const texto = juntar(textosDe(fases));
    for (const f of fluxo.fases) {
      const titulo = f.n === 2 ? TITULO_NOVO : f.titulo;
      assert.ok(texto.includes(titulo), `fase ${f.n} fora do SVG: ${titulo}`);
    }
    assert.match(texto, /Para até o dono aprovar/);
    assert.equal((fases.match(/<polygon class="dg-emblema dg-parada"/g) ?? []).length, 1);
    assert.equal((fases.match(/<circle class="dg-emblema"/g) ?? []).length, fluxo.fases.length - 1);
  });

  test('o diagrama acompanha o dado: o título trocado no fluxo.json está no SVG e na lista', () => {
    assert.ok(juntar(textosDe(svgsDe(pagina)[0])).includes(TITULO_NOVO));
    assert.ok(pagina.includes(`Fase 2 · ${TITULO_NOVO}`));
  });

  test('o diagrama da onda escreve os papéis, o paralelo e o condicional, com a caixa tracejada', () => {
    const onda = svgsDe(pagina)[1];
    const texto = juntar(textosDe(onda));
    for (const p of fluxo.onda.papeis) assert.ok(texto.includes(p.nome.split(' ')[0]), `papel ${p.nome} fora do SVG`);
    assert.match(texto, /Em paralelo/);
    assert.match(texto, /Correção, se houver/);
    assert.match(texto, /Só escreve testes/);
    assert.equal((onda.match(/class="dg-caixa dg-condicional"/g) ?? []).length, 1);
    assert.match(onda, /class="dg-desvio"/);
    assert.ok((onda.match(/marker-end="url\(#fluxo-onda-seta\)"/g) ?? []).length >= 4);
    assert.match(onda, /<marker id="fluxo-onda-seta"/);
  });

  test('nada de cor escrita dentro do SVG: fill e stroke vêm do CSS, nos dois modos', () => {
    for (const svg of svgsDe(pagina)) {
      assert.ok(!/\s(fill|stroke|style)="/.test(svg), 'atributo de cor ou estilo no SVG');
      assert.ok(!/<style\b/.test(svg), '<style> dentro do SVG');
    }
  });

  test('a mesma informação vem em texto, fora do SVG: as fases, as transversais e os papéis', () => {
    const partes = pagina.split('<ul class="fluxo-lista"');
    assert.equal(partes.length, 3);
    const fases = semTags(partes[1]);
    for (const f of fluxo.fases) assert.ok(fases.includes(f.resumo), `resumo da fase ${f.n} fora da lista`);
    assert.match(fases, /Parada obrigatória/);
    for (const t of fluxo.transversais) assert.ok(fases.includes(t.resumo));
    const papeis = semTags(partes[2]);
    for (const p of fluxo.onda.papeis) assert.ok(papeis.includes(p.faz), `"faz" do papel ${p.id} fora da lista`);
  });

  test('é uma página do site: título, h1, âncoras do sumário e navegação com a página marcada como atual', () => {
    assert.match(pagina, /<title>Diagrama do fluxo · forge<\/title>/);
    assert.match(pagina, /<h1>Diagrama do fluxo<\/h1>/);
    assert.match(pagina, /<h2 id="fases-do-projeto">/);
    assert.match(pagina, /<h2 id="onda-de-cada-tarefa">/);
    const nav = pagina.match(/<nav aria-label="Documentação">([\s\S]*?)<\/nav>/)[1];
    const atuais = [...nav.matchAll(/<a href="([^"]+)" aria-current="page"/g)].map((m) => m[1]);
    assert.deepEqual(atuais, [`${BASE}/fluxo/`]);
    assert.match(pagina, /<span class="menu-atual">Diagrama do fluxo<\/span>/);
  });

  test('o link do diagrama abre a seção Fluxo, antes de tarefas e ondas, em todas as páginas', () => {
    for (const rel of ['index.html', 'comandos/index.html', 'docs/regras/index.html', 'fluxo/index.html']) {
      const nav = lerDist(rel).match(/<nav aria-label="Documentação">([\s\S]*?)<\/nav>/)[1];
      const links = [...nav.matchAll(/<a href="([^"]+)"/g)].map((m) => m[1]);
      const i = links.indexOf(`${BASE}/fluxo/`);
      assert.ok(i >= 0, `sem link do fluxo em ${rel}`);
      assert.equal(links[i + 1], `${BASE}/docs/tarefas-e-ondas/`, `o fluxo deve vir antes de tarefas e ondas em ${rel}`);
    }
  });

  test('nenhum link quebrado no dist (com o base) nem âncora sem destino', () => {
    assert.deepEqual(conferirLinks(dist, BASE), []);
  });
});

describe('o componente pronto para a página inicial', () => {
  test('sem nenhuma prop desenha o fluxo todo num SVG só, com legenda por parte', () => {
    const svgs = svgsDe(teste);
    assert.equal(svgs.length, 1);
    const texto = juntar(textosDe(svgs[0]));
    for (const legenda of ['Fases do projeto', 'A onda de cada tarefa', 'Ao longo do projeto']) assert.ok(texto.includes(legenda), legenda);
    assert.ok(texto.includes(TITULO_NOVO));
    assert.match(svgs[0], /role="img"/);
    assert.match(svgs[0], /aria-labelledby="fluxo-titulo fluxo-desc"/);
  });

  test('a descrição do SVG inteiro cobre as três partes', () => {
    const desc = desescapar(teste.match(/<desc id="fluxo-desc">([\s\S]*?)<\/desc>/)[1]);
    assert.match(desc, /fases em sequência/);
    assert.match(desc, /etapas/);
    assert.match(desc, /Vale para o projeto todo/);
  });
});
