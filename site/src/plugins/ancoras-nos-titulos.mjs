/**
 * Plugin hast do Sätteri que põe um link direto (`<a class="ancora" href="#id">`) no fim de cada
 * `##` e `###` do Markdown, para copiar o endereço de uma seção.
 *
 * O Astro dá o `id` dos títulos num passo dele, depois dos plugins do site, e respeita o `id` que já
 * existe. Por isso este plugin dá os ids antes, com o mesmo github-slugger e na mesma ordem (todos os
 * títulos, do h1 ao h6), e o link já sai apontando para eles. O link não tem texto (o "#" vem do CSS):
 * assim o texto do título, que o Astro lê para o sumário, não muda.
 */
import GithubSlugger from 'github-slugger';

const TITULOS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
const COM_LINK = new Set(['h2', 'h3']);

/** Um link direto para o título de `id` com o texto `texto`. */
export function ancora(id, texto) {
  return {
    type: 'element',
    tagName: 'a',
    properties: { className: ['ancora'], href: `#${id}`, ariaLabel: `Link direto para a seção ${texto}` },
    children: [],
  };
}

/** Uma instância por documento (o Sätteri aceita a fábrica): os ids recomeçam a cada página. */
export function ancorasNosTitulos() {
  return () => {
    const slugger = new GithubSlugger();
    return {
      name: 'ancoras-nos-titulos',
      element: {
        filter: TITULOS,
        /** @param {any} no @param {any} ctx */
        visit(no, ctx) {
          const texto = ctx.textContent(no);
          const existente = no.properties?.id;
          const id = typeof existente === 'string' ? existente : slugger.slug(texto);
          if (typeof existente !== 'string') {
            ctx.setProperty(no, 'id', id);
          }
          if (COM_LINK.has(no.tagName)) {
            ctx.appendChild(no, ancora(id, texto));
          }
        },
      },
    };
  };
}
