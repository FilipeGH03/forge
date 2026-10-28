import type { CollectionEntry } from 'astro:content';
import { SECOES } from '../content.config';
import { comBase as comBaseDe } from './base.mjs';

type Doc = CollectionEntry<'docs'>;
type Secao = (typeof SECOES)[number];

/** Como cada `secao` do contrato 1.1 aparece na navegação. */
export const ROTULOS: Record<Secao, string> = {
  comece: 'Comece aqui',
  conceitos: 'Conceitos',
  fluxo: 'Fluxo',
  referencia: 'Referência',
};

/** Caminho da raiz do site (`/docs/x/`) com o base na frente (`/forge/docs/x/`). */
export function comBase(caminho: string): string {
  return comBaseDe(caminho, import.meta.env.BASE_URL);
}

/** Ordem da navegação: pela `secao`, na ordem do contrato, e pela `ordem` dentro dela. */
export function ordenar(docs: Doc[]): Doc[] {
  return [...docs].sort(
    (a, b) => SECOES.indexOf(a.data.secao) - SECOES.indexOf(b.data.secao) || a.data.ordem - b.data.ordem,
  );
}

/** As seções que têm páginas, na ordem do contrato, cada uma com as suas páginas já ordenadas. */
export function agrupar(docs: Doc[]): { secao: Secao; rotulo: string; docs: Doc[] }[] {
  const ordenados = ordenar(docs);
  return SECOES.map((secao) => ({
    secao,
    rotulo: ROTULOS[secao],
    docs: ordenados.filter((doc) => doc.data.secao === secao),
  })).filter((grupo) => grupo.docs.length > 0);
}

// Páginas que não são da coleção `docs` (são feitas dos dados gerados): cada uma entra numa seção, no início ou no fim.
// Comandos (comandos.json) fecha a Referência; o Diagrama do fluxo (fluxo.json) abre o Fluxo.
export const EXTRAS = [
  { id: 'fluxo', secao: 'fluxo', posicao: 'inicio', titulo: 'Diagrama do fluxo', href: '/fluxo/' },
  { id: 'comandos', secao: 'referencia', posicao: 'fim', titulo: 'Comandos', href: '/comandos/' },
] as const;

export interface ItemNavegacao {
  id: string;
  href: string;
  titulo: string;
  ehAtual: boolean;
}

/** A navegação inteira (seções e, em cada uma, extras e páginas na ordem), com a página `atual` marcada.
 * Serve à navegação lateral das docs e ao mapa do rodapé da página inicial. */
export function navegacao(docs: Doc[], atual?: string): { secao: Secao; rotulo: string; itens: ItemNavegacao[] }[] {
  const link = (id: string, href: string, titulo: string) => ({ id, href: comBase(href), titulo, ehAtual: id === atual });
  return agrupar(docs).map((grupo) => {
    const extras = (posicao: string) =>
      EXTRAS.filter((e) => e.secao === grupo.secao && e.posicao === posicao).map((e) => link(e.id, e.href, e.titulo));
    const paginas = grupo.docs.map((doc) => link(doc.id, `/docs/${doc.id}/`, doc.data.titulo));
    return { secao: grupo.secao, rotulo: grupo.rotulo, itens: [...extras('inicio'), ...paginas, ...extras('fim')] };
  });
}

/** A página de antes e a de depois de `slug`, pela ordem da navegação (`ordenar`). Nas pontas, `undefined`. */
export function vizinhas(docs: Doc[], slug: string): { anterior?: Doc; seguinte?: Doc } {
  const ordenados = ordenar(docs);
  const i = ordenados.findIndex((doc) => doc.id === slug);
  if (i === -1) {
    return {};
  }
  return { anterior: ordenados[i - 1], seguinte: ordenados[i + 1] };
}
