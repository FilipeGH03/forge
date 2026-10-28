/**
 * Único lugar que monta URL com o `base` do site (`/forge` no GitHub Pages).
 * Puro, sem Astro: o layout, os componentes (via src/lib/navegacao.ts) e o
 * plugin de Markdown (src/plugins/base-nos-links.mjs) usam estas funções.
 */

/** O `base` sem barra no fim (`/forge/` vira `/forge`; vazio quando o site mora na raiz). */
export function limparBase(base) {
  return (base ?? '').replace(/\/+$/, '');
}

/**
 * Põe o base na frente de um caminho absoluto da raiz (`/docs/x/` vira `/forge/docs/x/`).
 * Links externos, protocolo relativo (`//x`), relativos, âncoras (`#x`) e os que já têm o
 * base ficam como estão.
 * @param {string} caminho
 * @param {string} base
 */
export function comBase(caminho, base) {
  const b = limparBase(base);
  if (!b || !caminho.startsWith('/') || caminho.startsWith('//')) {
    return caminho;
  }
  const jaTemBase = caminho === b || ['/', '#', '?'].some((c) => caminho.startsWith(`${b}${c}`));
  return jaTemBase ? caminho : `${b}${caminho}`;
}
