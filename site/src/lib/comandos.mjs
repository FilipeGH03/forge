/**
 * Montagem dos textos da página /comandos/ a partir do src/data/comandos.json (contrato 1.2).
 * Puro, sem Astro: o src/pages/comandos.astro e o tests/b4.test.mjs usam estas funções.
 */

/** Largura em que a linha de uso quebra (como o `usage:` do argparse). */
const LARGURA_USO = 60;

const ehFlag = (arg) => arg.nome.startsWith('--');

/** O nome do valor de uma flag, no estilo do argparse: `--dir` vira `DIR`, `--sem-git` não tem. */
const valorDa = (arg) => arg.nome.replace(/^--/, '').replace(/-/g, '_').toUpperCase();

/** Como um argumento aparece na linha de uso. */
function pecaDeUso(arg) {
  if (!ehFlag(arg)) {
    const nome = `<${arg.nome}>${arg.multiplo ? '...' : ''}`;
    return arg.obrigatorio ? nome : `[${nome}]`;
  }
  const flag = arg.recebe_valor ? `${arg.nome} ${valorDa(arg)}${arg.multiplo ? ' ...' : ''}` : arg.nome;
  return arg.obrigatorio ? flag : `[${flag}]`;
}

/**
 * A linha de uso de um comando: `forge.py <nome> <plano> <posicionais> --flags`.
 * Quebra em várias linhas, recuadas, quando passa de LARGURA_USO.
 * @param {{ nome: string, usa_plano: boolean, argumentos: any[] }} comando
 * @param {string} [programa]
 */
export function montarUso(comando, programa = 'forge.py') {
  // Posicionais primeiro, depois as flags (a ordem do argparse dentro de cada grupo).
  const posicionais = comando.argumentos.filter((a) => !ehFlag(a));
  const flags = comando.argumentos.filter(ehFlag);
  const pecas = [
    ...(comando.usa_plano ? ['<plano>'] : []),
    ...posicionais.map(pecaDeUso),
    ...flags.map(pecaDeUso),
  ];
  const linhas = [];
  let atual = `${programa} ${comando.nome}`;
  for (const peca of pecas) {
    if (atual.length + 1 + peca.length > LARGURA_USO) {
      linhas.push(atual);
      atual = `  ${peca}`;
    } else {
      atual += ` ${peca}`;
    }
  }
  linhas.push(atual);
  return linhas.join('\n');
}

/** Primeira letra maiúscula e ponto final: a `ajuda` do argparse vem em minúscula e sem ponto. */
export function frase(texto) {
  if (!texto) return '';
  const t = texto.trim();
  const inicial = t.charAt(0).toUpperCase() + t.slice(1);
  return /[.!?:]$/.test(inicial) ? inicial : `${inicial}.`;
}

/**
 * As marcas de um argumento, em texto: se é posicional ou flag, se é obrigatório, se pega valor.
 * @returns {string[]}
 */
export function marcasDoArgumento(arg) {
  const marcas = [ehFlag(arg) ? (arg.recebe_valor ? 'flag com valor' : 'flag, sem valor') : 'posicional'];
  marcas.push(arg.obrigatorio ? 'obrigatório' : 'opcional');
  if (arg.multiplo) marcas.push(ehFlag(arg) ? 'pode repetir' : 'um ou mais');
  return marcas;
}

/** O que o argumento aceita além do valor livre: o `padrao` e a lista de `valores` (vazio quando não há nada). */
export function metaDoArgumento(arg) {
  const meta = [];
  if (arg.padrao !== null && arg.padrao !== undefined) meta.push({ rotulo: 'Padrão', valores: [String(arg.padrao)] });
  if (arg.valores?.length) meta.push({ rotulo: 'Valores aceitos', valores: arg.valores });
  return meta;
}

/** Saída com mais linhas que isto fica recolhida (`<details>`) na página. */
export const LINHAS_SAIDA_CURTA = 12;

export const contarLinhas = (texto) => texto.split('\n').length;
