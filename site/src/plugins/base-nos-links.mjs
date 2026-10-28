/**
 * Plugin hast do Sätteri (o processador de Markdown padrão do Astro 7) que
 * prefixa o `base` do site nos links e imagens internos do Markdown.
 *
 * O conteúdo (contrato 1.1) escreve `/docs/<slug>/`, `/comandos/` e
 * `/comandos/#<nome>` sem o `/forge` do GitHub Pages. Aqui, todo `href` de `<a>` e
 * todo `src` de `<img>` absoluto da raiz ganha o base na frente, tanto no Markdown
 * (`[x](/docs/y/)`, `![x](/a.png)`) quanto em HTML cru escrito no corpo (`<a href="/x/">`).
 * A regra de quais caminhos mudam mora em src/lib/base.mjs.
 */
import { comBase, limparBase } from '../lib/base.mjs';

/** Atributo que carrega a URL em cada tag que o plugin trata. */
const ATRIBUTO = { a: 'href', img: 'src' };

/** Reescreve `href="/x"` e `src='/x'` dentro de um trecho de HTML cru. */
export function prefixarNoHtml(html, base) {
  return html.replace(/(<(?:a|img)\b[^>]*?\s)(href|src)=(["'])([^"']*)\3/gi, (todo, antes, atributo, aspas, valor) => {
    const tag = /^<(\w+)/.exec(antes)?.[1].toLowerCase();
    if (ATRIBUTO[tag] !== atributo.toLowerCase()) {
      return todo;
    }
    return `${antes}${atributo}=${aspas}${comBase(valor, base)}${aspas}`;
  });
}

/** @param {string} baseDoSite  o `base` do astro.config (`/forge` ou `/forge/`) */
export function baseNosLinks(baseDoSite) {
  const base = limparBase(baseDoSite);
  return {
    name: 'base-nos-links',
    element: {
      filter: ['a', 'img'],
      /** @param {any} no @param {any} ctx */
      visit(no, ctx) {
        const atributo = ATRIBUTO[no.tagName];
        const valor = atributo && no.properties?.[atributo];
        if (typeof valor === 'string') {
          const novo = comBase(valor, base);
          if (novo !== valor) {
            ctx.setProperty(no, atributo, novo);
          }
        }
      },
    },
    /** HTML cru do Markdown chega como nó `raw`. @param {any} no @param {any} ctx */
    raw(no, ctx) {
      const novo = prefixarNoHtml(no.value, base);
      if (novo !== no.value) {
        ctx.replaceNode(no, { type: 'raw', value: novo });
      }
    },
  };
}
