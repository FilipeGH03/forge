// Testes de conferência independente da B6 (testador): propriedades do dist das páginas de docs, /comandos/,
// /fluxo/ e da página inicial que valem para qualquer página nova da frente A.
//
//     node --test tests/b6-testador.test.mjs        (rodado de site/, depois do npm install)
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { apagarCopia, BASE, construirCopia, SITE } from './apoio.mjs';

const docs = fs
  .readdirSync(path.join(SITE, 'src', 'content', 'docs'))
  .filter((f) => f.endsWith('.md'))
  .map((f) => `docs/${f.replace(/\.md$/, '')}`);
const PAGINAS = [...docs, 'comandos', 'fluxo'];

let dir;
let dist;
const html = (p) => fs.readFileSync(path.join(dist, p, 'index.html'), 'utf8');

before(() => {
  ({ dir, dist } = construirCopia('b6t'));
});
after(() => apagarCopia(dir));

describe('páginas da B6: estrutura que vale para qualquer página', () => {
  test('um <h1>, um <main> e o "Pular para o conteúdo" aponta para um id que existe', () => {
    for (const p of PAGINAS) {
      const h = html(p);
      assert.equal((h.match(/<h1[\s>]/g) || []).length, 1, `${p}: <h1>`);
      assert.equal((h.match(/<main[\s>]/g) || []).length, 1, `${p}: <main>`);
      const alvo = h.match(/class="pular" href="#([^"]+)"/)?.[1];
      assert.ok(alvo, `${p}: sem link de pular`);
      assert.ok(h.includes(`id="${alvo}"`), `${p}: #${alvo} não existe`);
    }
  });

  test('nenhum id repetido na página (a âncora de título não pode colidir com outro id)', () => {
    for (const p of [...PAGINAS, '']) {
      const ids = [...html(p).matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
      const repetidos = ids.filter((id, i) => ids.indexOf(id) !== i);
      assert.deepEqual([...new Set(repetidos)], [], `${p}: ids repetidos`);
    }
  });

  test('todo link para #fragmento dentro da página aponta para um id da própria página', () => {
    for (const p of PAGINAS) {
      const h = html(p);
      const ids = new Set([...h.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
      const soltos = [...h.matchAll(/\shref="#([^"]+)"/g)].map((m) => m[1]).filter((id) => !ids.has(id));
      assert.deepEqual(soltos, [], `${p}: âncoras sem alvo`);
    }
  });

  test('toda imagem tem alt e toda tabela está numa região rolável com nome', () => {
    for (const p of PAGINAS) {
      const h = html(p);
      for (const img of h.matchAll(/<img\b[^>]*>/g)) assert.match(img[0], /\salt="/, `${p}: ${img[0]}`);
      const tabelas = (h.match(/<table[\s>]/g) || []).length;
      const regioes = [...h.matchAll(/<div\b([^>]*)><table[\s>]/g)].filter(
        (m) => /\brole="region"/.test(m[1]) && /\btabindex="0"/.test(m[1]) && /\baria-label="Tabela[^"]*"/.test(m[1]),
      ).length;
      assert.equal(regioes, tabelas, `${p}: ${tabelas} tabelas, ${regioes} regiões com nome`);
    }
  });

  test('nenhuma página carrega recurso de outro domínio (fontes e ícones são locais); links externos só para o GitHub', () => {
    for (const p of [...PAGINAS, '']) {
      const h = html(p);
      const carregados = [...h.matchAll(/<(?:link|script|img|source)\b[^>]*\s(?:src|href)="(https?:\/\/[^"]+)"/g)].map((m) => m[1]);
      assert.deepEqual(carregados.filter((u) => !/^https:\/\/github\.com\//.test(u)), [], `${p}: recurso externo`);
      assert.doesNotMatch(h, /fonts\.googleapis|fonts\.gstatic|cdn\./, p);
    }
  });

  test('o link do topo e o do rodapé que saem do site abrem com rel noopener', () => {
    for (const p of PAGINAS) {
      for (const a of html(p).matchAll(/<a\b[^>]*target="_blank"[^>]*>/g)) assert.match(a[0], /rel="[^"]*noopener/, `${p}: ${a[0]}`);
    }
  });

  test('o dist não vaza o prefixo errado: todo href/src absoluto começa com o base', () => {
    for (const p of [...PAGINAS, '']) {
      const soltos = [...html(p).matchAll(/\s(?:href|src)="(\/[^"/][^"]*)"/g)].map((m) => m[1]).filter((u) => !u.startsWith(`${BASE}/`));
      assert.deepEqual(soltos, [], `${p}: caminho sem o base`);
    }
  });
});
