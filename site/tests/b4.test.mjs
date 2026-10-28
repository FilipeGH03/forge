// Testes da B4 (página /comandos/ a partir do comandos.json, contrato 1.2: uso, argumentos, exemplo
// real e âncora por comando).
//
//     node --test tests/b4.test.mjs        (rodado de site/, depois do npm install)
//
// O build roda numa cópia temporária do site (tests/apoio.mjs).
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { contarLinhas, frase, LINHAS_SAIDA_CURTA, marcasDoArgumento, metaDoArgumento, montarUso } from '../src/lib/comandos.mjs';
import { apagarCopia, BASE, construirCopia, SITE } from './apoio.mjs';
import { conferirLinks } from './conferir-links.mjs';

const { comandos } = JSON.parse(fs.readFileSync(path.join(SITE, 'src', 'data', 'comandos.json'), 'utf8'));
const doJson = (nome) => comandos.find((c) => c.nome === nome);

let dir;
let dist;
let html;
const lerDist = (rel) => fs.readFileSync(path.join(dist, rel), 'utf8');

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

before(() => {
  ({ dir, dist } = construirCopia('b4'));
  html = lerDist('comandos/index.html');
});

after(() => apagarCopia(dir));

/** O HTML de cada comando do dist, pelo nome. */
function secoes() {
  const mapa = new Map();
  for (const m of html.matchAll(/<section class="comando" aria-labelledby="([^"]+)">([\s\S]*?)<\/section>/g)) {
    mapa.set(m[1], m[2]);
  }
  return mapa;
}

describe('montarUso: a linha de uso a partir do comandos.json', () => {
  test('posicional vem entre colchetes angulares, flag obrigatória sem colchetes, opcional com', () => {
    assert.equal(
      montarUso(doJson('novo')),
      'forge.py novo <slug> --titulo TITULO --dono DONO [--dir DIR]\n  [--branch BRANCH] [--base BASE]',
    );
  });

  test('o plano é o primeiro posicional e flag sem valor não tem o nome do valor', () => {
    assert.equal(montarUso(doJson('status')), 'forge.py status <plano> [--sem-git] [--json]');
    assert.equal(montarUso(doJson('registrar')), 'forge.py registrar <plano>');
    assert.equal(montarUso(doJson('lista')), 'forge.py lista');
  });

  test('argumento múltiplo leva reticências, posicional e flag', () => {
    assert.equal(montarUso(doJson('complexidade')), 'forge.py complexidade <plano> <nivel> <ids>...');
    assert.match(montarUso(doJson('marcar')), /\[--commit COMMIT \.\.\.\]/);
  });

  test('posicional vai antes das flags e o nome do valor troca o hífen por sublinhado', () => {
    const uso = montarUso({
      nome: 'x',
      usa_plano: false,
      argumentos: [
        { nome: '--a-b', obrigatorio: false, recebe_valor: true, padrao: null, ajuda: null, valores: null, multiplo: false },
        { nome: 'p', obrigatorio: true, recebe_valor: true, padrao: null, ajuda: null, valores: null, multiplo: false },
      ],
    });
    assert.equal(uso, 'forge.py x <p> [--a-b A_B]');
  });

  test('toda linha de uso do JSON cabe em 60 colunas, ou é uma peça só, e nenhuma peça se perde', () => {
    for (const c of comandos) {
      const uso = montarUso(c);
      for (const linha of uso.split('\n')) {
        const pecas = linha.trim().split(' ');
        assert.ok(linha.length <= 60 || pecas.length <= 3, `${c.nome}: linha larga: ${linha}`);
      }
      assert.ok(uso.startsWith(`forge.py ${c.nome}`));
      for (const a of c.argumentos) {
        assert.ok(uso.includes(a.nome.replace(/^--/, '')), `${c.nome}: ${a.nome} sumiu da linha de uso`);
      }
      assert.equal(uso.includes('<plano>'), c.usa_plano, `${c.nome}: <plano> só quando usa_plano`);
    }
  });
});

describe('textos dos argumentos', () => {
  test('frase põe maiúscula e ponto final sem duplicar a pontuação', () => {
    assert.equal(frase('estado das tarefas'), 'Estado das tarefas.');
    assert.equal(frase('já tem ponto.'), 'Já tem ponto.');
    assert.equal(frase('termina em dois pontos:'), 'Termina em dois pontos:');
    assert.equal(frase(null), '');
  });

  test('marcas: posicional ou flag, obrigatório ou opcional, valor e repetição', () => {
    const base = { obrigatorio: false, recebe_valor: true, padrao: null, ajuda: null, valores: null, multiplo: false };
    assert.deepEqual(marcasDoArgumento({ ...base, nome: 'id', obrigatorio: true }), ['posicional', 'obrigatório']);
    assert.deepEqual(marcasDoArgumento({ ...base, nome: '--json', recebe_valor: false }), ['flag, sem valor', 'opcional']);
    assert.deepEqual(marcasDoArgumento({ ...base, nome: '--commit', multiplo: true }), ['flag com valor', 'opcional', 'pode repetir']);
    assert.deepEqual(marcasDoArgumento({ ...base, nome: 'ids', obrigatorio: true, multiplo: true }), [
      'posicional',
      'obrigatório',
      'um ou mais',
    ]);
  });

  test('meta: o padrão (mesmo 0) e os valores aceitos; nada quando não há', () => {
    const base = { nome: '--x', obrigatorio: false, recebe_valor: true, padrao: null, ajuda: null, valores: null, multiplo: false };
    assert.deepEqual(metaDoArgumento(base), []);
    assert.deepEqual(metaDoArgumento({ ...base, padrao: 0 }), [{ rotulo: 'Padrão', valores: ['0'] }]);
    assert.deepEqual(metaDoArgumento({ ...base, padrao: 'media', valores: ['baixa', 'media'] }), [
      { rotulo: 'Padrão', valores: ['media'] },
      { rotulo: 'Valores aceitos', valores: ['baixa', 'media'] },
    ]);
  });
});

describe('a página /comandos/ no dist', () => {
  test('existe, com um <h1> "Comandos", o título da aba e a descrição', () => {
    assert.equal((html.match(/<h1[ >]/g) ?? []).length, 1);
    assert.match(html, /<h1>Comandos<\/h1>/);
    assert.match(html, /<title>Comandos · forge<\/title>/);
    assert.match(html, /<meta name="description" content="[^"]{20,160}"/);
    assert.match(html, /<html lang="pt-BR"/);
  });

  test('todo comando do JSON aparece, na ordem, com um <h2 id="<nome>"> e uma seção só', () => {
    const ids = [...html.matchAll(/<h2 id="([^"]+)"><code>/g)].map((m) => m[1]);
    assert.deepEqual(ids, comandos.map((c) => c.nome));
    assert.equal(secoes().size, comandos.length);
  });

  test('os ids da página são únicos (a âncora de um comando não colide com nenhum outro)', () => {
    const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
    assert.equal(new Set(ids).size, ids.length, `ids repetidos: ${ids.filter((id, i) => ids.indexOf(id) !== i)}`);
  });

  test('a âncora /comandos/#<nome> funciona: o índice, o sumário e o link do título apontam para ela', () => {
    const idsDaPagina = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
    for (const c of comandos) {
      assert.ok(idsDaPagina.has(c.nome), `falta o id ${c.nome}`);
      assert.ok(html.includes(`class="indice-nome" href="#${c.nome}"`), `${c.nome}: falta no índice`);
      assert.ok(html.includes(`<li><a href="#${c.nome}">${c.nome}</a></li>`), `${c.nome}: falta no sumário`);
      assert.ok(html.includes(`<a class="ancora" href="#${c.nome}"`), `${c.nome}: falta o link do título`);
    }
  });

  test('todo link /comandos/#x das páginas de docs aponta para um comando que existe', () => {
    const nomes = new Set(comandos.map((c) => c.nome));
    let achados = 0;
    for (const arquivo of fs.readdirSync(path.join(dist, 'docs'))) {
      const pagina = lerDist(`docs/${arquivo}/index.html`);
      for (const m of pagina.matchAll(/href="\/forge\/comandos\/#([^"]+)"/g)) {
        achados += 1;
        assert.ok(nomes.has(m[1]), `docs/${arquivo}: /comandos/#${m[1]} não é um comando`);
      }
    }
    assert.ok(achados > 0, 'nenhuma página de docs aponta para /comandos/#<nome>');
    assert.deepEqual(conferirLinks(dist, BASE), []);
  });

  test('cada comando mostra a ajuda, a linha de uso e os argumentos do JSON', () => {
    const porNome = secoes();
    for (const c of comandos) {
      const sec = porNome.get(c.nome);
      assert.ok(sec, `${c.nome}: sem seção`);
      const texto = semTags(sec);
      assert.ok(texto.includes(frase(c.ajuda)), `${c.nome}: ajuda`);
      assert.ok(texto.includes(montarUso(c)), `${c.nome}: linha de uso`);
      const nomesNaPagina = [...sec.matchAll(/<code class="arg-nome">([^<]+)<\/code>/g)].map((m) => m[1]);
      assert.deepEqual(nomesNaPagina, c.argumentos.map((a) => a.nome), `${c.nome}: argumentos, na ordem`);
    }
  });

  test('o argumento obrigatório e o opcional se distinguem, e o padrão e os valores aparecem', () => {
    const tarefa = semTags(secoes().get('tarefa'));
    assert.match(tarefa, /--frente\s*flag com valor · obrigatório/);
    assert.match(tarefa, /--depende\s*flag com valor · opcional · pode repetir/);
    assert.match(tarefa, /Padrão: media/);
    assert.match(tarefa, /Valores aceitos: baixa media alta/);
    assert.match(semTags(secoes().get('status')), /--sem-git\s*flag, sem valor · opcional/);
    assert.match(semTags(secoes().get('novo')), /slug\s*posicional · obrigatório/);
    assert.match(semTags(secoes().get('registrar')), /Só o caminho do plano\./);
    assert.match(semTags(secoes().get('lista')), /Argumentos\s*Nenhum\./);
  });

  test('o exemplo é o do JSON: o comando e a saída real, sem recolher o que é curto', () => {
    const porNome = secoes();
    for (const c of comandos) {
      const sec = porNome.get(c.nome);
      if (!c.exemplo) {
        assert.ok(!sec.includes('class="exemplo"'), `${c.nome}: sem exemplo no JSON, sem bloco`);
        continue;
      }
      const blocos = [...sec.matchAll(/<pre class="astro-code" data-language="(bash|text)" tabindex="0"><code>([\s\S]*?)<\/code><\/pre>/g)];
      const comandosNoHtml = blocos.filter((b) => b[1] === 'bash').map((b) => desescapar(b[2]));
      const saidas = blocos.filter((b) => b[1] === 'text').map((b) => desescapar(b[2]));
      assert.ok(comandosNoHtml.includes(c.exemplo.comando), `${c.nome}: comando do exemplo`);
      assert.deepEqual(saidas, [c.exemplo.saida], `${c.nome}: saída do exemplo, igual ao JSON`);
      const longa = contarLinhas(c.exemplo.saida) > LINHAS_SAIDA_CURTA;
      assert.equal(sec.includes('<details class="saida">'), longa, `${c.nome}: saída longa fica recolhida`);
    }
  });

  test('a saída longa está em <details> com o número de linhas', () => {
    const onda = secoes().get('onda');
    const n = contarLinhas(doJson('onda').exemplo.saida);
    assert.ok(n > LINHAS_SAIDA_CURTA);
    assert.match(onda, new RegExp(`<summary>Ver a saída \\(${n} linhas\\)</summary>`));
  });

  test('os exemplos não vazam caminho da máquina nem de pasta temporária', () => {
    const texto = semTags(html);
    assert.doesNotMatch(texto, /[A-Za-z]:\\|\/Users\/|\/tmp\/|AppData|Temp\\/);
  });

  test('a navegação lateral marca Comandos como a página atual, e só nela', () => {
    assert.match(html, /<a href="\/forge\/comandos\/" aria-current="page">\s*Comandos\s*<\/a>/);
    assert.match(html, /<span class="menu-atual">Comandos<\/span>/);
    assert.equal((html.match(/aria-current="page"/g) ?? []).length, 1);
    const doc = lerDist('docs/hooks/index.html');
    assert.match(doc, /<a href="\/forge\/comandos\/">\s*Comandos\s*<\/a>/);
    assert.doesNotMatch(doc, /<a href="\/forge\/comandos\/" aria-current/);
  });

  test('Comandos fica no fim da seção Referência', () => {
    const nav = html.match(/<nav aria-label="Documentação">([\s\S]*?)<\/nav>/)[1];
    const referencia = nav.slice(nav.indexOf('id="menu-referencia"'));
    const ultimo = [...referencia.matchAll(/<a href="([^"]+)"/g)].pop()[1];
    assert.equal(ultimo, '/forge/comandos/');
  });

  test('o sumário "Nesta página" lista o índice e todos os comandos', () => {
    const sumario = html.match(/<details class="sumario"[\s\S]*?<\/details>/)?.[0] ?? '';
    assert.ok(sumario.includes('href="#indice-de-comandos"'));
    for (const c of comandos) assert.ok(sumario.includes(`href="#${c.nome}"`), `${c.nome} no sumário`);
  });

  test('a página não tem estilo inline nem estilo com escopo: tudo vem do global.css', () => {
    const corpo = html.slice(html.indexOf('<main'));
    assert.doesNotMatch(corpo, /style="/);
    assert.doesNotMatch(html, /data-astro-cid-/);
  });
});
