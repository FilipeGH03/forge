/**
 * Plugin hast do Sätteri que embrulha cada `<table>` do Markdown numa região
 * rolável na horizontal: em 375px as tabelas largas rolam dentro da caixa, sem
 * empurrar a página para os lados. A região recebe foco pelo teclado (tabindex)
 * para quem não usa mouse conseguir rolar, e o nome dela diz qual tabela é: as
 * colunas do cabeçalho ("Tabela: Arquivo, O que é").
 */

/** Texto puro de um nó hast. */
function texto(no) {
  if (no.type === 'text') return no.value;
  return (no.children ?? []).map(texto).join('');
}

/** Os títulos das colunas: os `<th>` da primeira linha da tabela. */
export function colunas(tabela) {
  const fila = [...(tabela.children ?? [])];
  while (fila.length) {
    const no = fila.shift();
    if (no.type !== 'element') continue;
    if (no.tagName === 'tr') {
      return no.children.filter((c) => c.type === 'element' && c.tagName === 'th').map((c) => texto(c).trim()).filter(Boolean);
    }
    fila.push(...(no.children ?? []));
  }
  return [];
}

const escapar = (t) => t.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** O nome acessível da região: "Tabela" e as colunas, quando o cabeçalho tem texto. */
export function rotulo(tabela) {
  const nomes = colunas(tabela);
  return nomes.length ? `Tabela: ${nomes.join(', ')}` : 'Tabela';
}

export function embrulho(tabela) {
  return `<div class="tabela" role="region" tabindex="0" aria-label="${escapar(rotulo(tabela))}"></div>`;
}

export function tabelasRolaveis() {
  return {
    name: 'tabelas-rolaveis',
    element: {
      filter: ['table'],
      /** @param {any} no @param {any} ctx */
      visit(no, ctx) {
        ctx.wrapNode(no, { raw: embrulho(no) });
      },
    },
  };
}
