// Confere o dist: todo link interno (href e src) aponta para um arquivo que existe, com o base
// na frente, e toda âncora (#x) aponta para um id da página de destino. Nada de 404 no Pages.
//
//     node tests/conferir-links.mjs [pasta-do-dist] [base]       (padrão: dist, /forge)
//
// Também é importado pelo tests/b3.test.mjs. Sai com código 1 quando acha link quebrado.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/** Todos os .html de uma pasta, com o caminho relativo a ela (com `/`). */
function paginas(dist, sub = '') {
  const saida = [];
  for (const entrada of fs.readdirSync(path.join(dist, sub), { withFileTypes: true })) {
    const rel = sub ? `${sub}/${entrada.name}` : entrada.name;
    if (entrada.isDirectory()) saida.push(...paginas(dist, rel));
    else if (entrada.name.endsWith('.html')) saida.push(rel);
  }
  return saida;
}

/** O arquivo do dist que o Pages serve para um caminho (já sem o base), ou `null`. */
function arquivoDe(dist, caminho) {
  const rel = decodeURIComponent(caminho).replace(/^\/+/, '');
  const candidatos = caminho.endsWith('/') || rel === '' ? [path.join(rel, 'index.html')] : [rel, path.join(rel, 'index.html')];
  for (const c of candidatos) {
    const abs = path.join(dist, c);
    if (fs.existsSync(abs) && fs.statSync(abs).isFile()) return abs;
  }
  return null;
}

/** Quem a página de `rel` referencia: [{ atributo, valor }]. */
function referencias(html) {
  const sem = html.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, (m) => m.slice(0, m.indexOf('>') + 1));
  const achados = [];
  for (const m of sem.matchAll(/<(a|link|img|script|source|video|audio)\b[^>]*>/gi)) {
    for (const a of m[0].matchAll(/\s(href|src)=(?:"([^"]*)"|'([^']*)')/gi)) {
      achados.push({ tag: m[1].toLowerCase(), atributo: a[1].toLowerCase(), valor: a[2] ?? a[3] });
    }
  }
  return achados;
}

const idsDe = (html) => new Set([...html.matchAll(/\s(?:id|name)=(?:"([^"]*)"|'([^']*)')/gi)].map((m) => m[1] ?? m[2]));

/**
 * @param {string} dist  pasta da saída do build
 * @param {string} base  o base do site, sem barra no fim (`/forge`)
 * @returns {{ pagina: string, link: string, motivo: string }[]}
 */
export function conferirLinks(dist, base = '/forge') {
  const quebrados = [];
  const cacheIds = new Map();
  const ids = (arquivo) => {
    if (!cacheIds.has(arquivo)) cacheIds.set(arquivo, idsDe(fs.readFileSync(arquivo, 'utf8')));
    return cacheIds.get(arquivo);
  };

  for (const pagina of paginas(dist)) {
    const html = fs.readFileSync(path.join(dist, pagina), 'utf8');
    const urlDaPagina = `${base}/${pagina.replace(/(^|\/)index\.html$/, '$1')}`;
    for (const { valor } of referencias(html)) {
      if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(valor)) continue; // externo, mailto:, data:
      if (valor === '' ) continue;
      const falha = (motivo) => quebrados.push({ pagina, link: valor, motivo });

      const [semAncora, ancora = ''] = valor.split('#', 2);
      const [caminhoBruto] = semAncora.split('?', 1);
      let caminho = caminhoBruto;
      if (caminho === '') {
        caminho = urlDaPagina; // só âncora: a própria página
      } else if (!caminho.startsWith('/')) {
        caminho = new URL(caminho, `http://x${urlDaPagina}`).pathname; // relativo
      }
      if (caminho !== base && !caminho.startsWith(`${base}/`)) {
        falha(`sem o base ${base}: dá 404 no Pages`);
        continue;
      }
      const arquivo = arquivoDe(dist, caminho.slice(base.length) || '/');
      if (!arquivo) {
        falha('o arquivo não existe no dist (404)');
        continue;
      }
      if (ancora && arquivo.endsWith('.html') && !ids(arquivo).has(decodeURIComponent(ancora))) {
        falha(`a âncora #${ancora} não existe na página de destino`);
      }
    }
  }
  return quebrados;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [pasta = 'dist', base = '/forge'] = process.argv.slice(2);
  const quebrados = conferirLinks(path.resolve(pasta), base.replace(/\/+$/, ''));
  for (const q of quebrados) console.error(`${q.pagina}: ${q.link} — ${q.motivo}`);
  console.log(quebrados.length ? `${quebrados.length} link(s) quebrado(s)` : 'nenhum link interno quebrado');
  process.exit(quebrados.length ? 1 : 0);
}
