/**
 * Montagem do diagrama do fluxo a partir do src/data/fluxo.json (contrato 1.3).
 * Puro, sem Astro: o src/components/DiagramaFluxo.astro desenha o que sai daqui e o
 * tests/b5.test.mjs confere a geometria, os textos e a descrição acessível.
 *
 * Tudo é calculado no build, em unidades do viewBox. O SVG não mede texto, então a quebra
 * de linha usa uma largura média por caractere (um pouco folgada) em vez da medida real.
 *
 * O que cada marca quer dizer sempre vem escrito junto (nada depende só de cor):
 *   - fase de parada: octógono no lugar do círculo, borda grossa e a frase "Para até o dono aprovar";
 *   - etapa condicional: borda tracejada e o rótulo "correção, se houver bloqueante" (o do fluxo.json);
 *   - etapas em paralelo: caixas lado a lado, saindo e voltando para a mesma linha, com o rótulo;
 *   - transversal: losango com a inicial e a frase "Vale para o projeto todo".
 */

export const LARGURA = 340;
export const PARTES = ['fases', 'onda', 'transversais'];

const TAMANHO_NOME = 15;
const TAMANHO_SUB = 13;
const ALTURA_LINHA_NOME = 19;
const ALTURA_LINHA_SUB = 17;
const ALTURA_LINHA_ROTULO = 16;
const FATOR_NOME = 0.54;
const FATOR_SUB = 0.52;
const PAD = 12;

// Fases: o emblema (número) à esquerda, a caixa à direita.
const EMBLEMA_CX = 22;
const EMBLEMA_R = 15;
const FASE_X = 50;
const FASE_L = LARGURA - FASE_X - 2;
const FASE_ESPACO = 26;
const ALTURA_MIN = 46;

// Onda: as caixas ocupam o miolo, o desvio da etapa condicional corre à direita.
const ONDA_X0 = 36;
const ONDA_X1 = 304;
const ONDA_CX = (ONDA_X0 + ONDA_X1) / 2;
const ONDA_VAO = 8;
const ONDA_DESVIO_X = 324;
const ONDA_ESPACO = 30;
const ROTULO_FIM_X = ONDA_CX - 10;

const LEGENDA_ALTURA = 24;

const ESCREVE_CODIGO = {
  sim: 'Escreve código',
  não: 'Não escreve código',
  'só testes': 'Só escreve testes',
};

/** Quebra o texto em linhas de até `max` caracteres (palavra inteira; palavra maior que `max` fica sozinha). */
export function quebrar(texto, max) {
  const linhas = [];
  let atual = '';
  for (const palavra of String(texto).trim().split(/\s+/)) {
    if (atual && atual.length + 1 + palavra.length > max) {
      linhas.push(atual);
      atual = palavra;
    } else {
      atual = atual ? `${atual} ${palavra}` : palavra;
    }
  }
  if (atual) linhas.push(atual);
  return linhas;
}

const caber = (largura, tamanho, fator) => Math.max(8, Math.floor(largura / (tamanho * fator)));

/** `a`, `a e b`, `a, b e c`. */
const lista = (itens) => (itens.length < 2 ? itens.join('') : `${itens.slice(0, -1).join(', ')} e ${itens.at(-1)}`);

/** Primeira letra maiúscula, para as frases que vêm minúsculas do fluxo.json (`em paralelo`). */
const inicial = (t) => t.charAt(0).toUpperCase() + t.slice(1);

/** Os papéis de uma etapa, pelo `id`. Papel que não existe é erro: o fluxo.json e o diagrama não podem divergir. */
function papeisDe(etapa, papeis) {
  return etapa.papeis.map((id) => {
    const papel = papeis.find((p) => p.id === id);
    if (!papel) throw new Error(`Etapa da onda cita o papel "${id}", que não está em onda.papeis do fluxo.json.`);
    return papel;
  });
}

/** O que o papel escreve, em texto (`Escreve código`): o mapa único do `escreve_codigo` do fluxo.json, usado no
 * diagrama e na lista da página /fluxo/. */
export const subDoPapel = (papel) => ESCREVE_CODIGO[papel.escreve_codigo] ?? papel.escreve_codigo;

/** Texto corrido do que o diagrama mostra: é o `<desc>` do SVG, para quem não vê o desenho. */
function descreverFases(fases) {
  const itens = fases.map((f) => `Fase ${f.n}, ${f.titulo}`);
  const paradas = fases.filter((f) => f.parada);
  const nota = paradas.length
    ? ` ${lista(paradas.map((f) => `A fase ${f.n}`))} é uma parada obrigatória: o fluxo espera o dono aprovar. Ela aparece como octógono, com borda grossa e o aviso escrito.`
    : '';
  return `${fases.length} fases em sequência, de cima para baixo: ${itens.join('; ')}.${nota}`;
}

function descreverOnda(etapas, papeis) {
  const passos = etapas.map((etapa, i) => {
    const quem = papeisDe(etapa, papeis).map((p) => `${p.nome} (${subDoPapel(p).toLowerCase()})`);
    const rotulo = etapa.rotulo ? `${etapa.rotulo}: ` : '';
    return `etapa ${i + 1}, ${rotulo}${lista(quem)}${etapa.condicional ? '; tracejada, só acontece se for preciso, e o fluxo pode seguir direto para a etapa seguinte' : ''}`;
  });
  return `Cada tarefa da onda passa por ${etapas.length} etapas, de cima para baixo: ${passos.join('; ')}.`;
}

function descreverTransversais(transversais) {
  return `Vale para o projeto todo, fora da sequência: ${lista(transversais.map((t) => t.titulo))}. Aparece num losango.`;
}

const TITULOS = {
  fases: 'as fases do projeto',
  onda: 'a onda de cada tarefa',
  transversais: 'o que vale em todas as fases',
};

const LEGENDAS = {
  fases: 'Fases do projeto',
  onda: 'A onda de cada tarefa',
  transversais: 'Ao longo do projeto',
};

/** Linhas de texto de uma caixa, com a primeira baseline em `topo` (linha centrada na altura da linha). */
function bloco(x, topo, linhas, altura) {
  return linhas.map((texto, i) => ({ texto, x, y: topo + (i + 0.5) * altura }));
}

function desenharFases(fases, y0) {
  const formas = [];
  let y = y0;
  let anterior = null;
  for (const fase of fases) {
    const linhas = quebrar(fase.titulo, caber(FASE_L - 2 * PAD, TAMANHO_NOME, FATOR_NOME)).slice(0, 4);
    const aviso = fase.parada ? ['Para até o dono aprovar'] : [];
    const altura = Math.max(ALTURA_MIN, 2 * PAD + linhas.length * ALTURA_LINHA_NOME + aviso.length * ALTURA_LINHA_SUB);
    const cy = y + altura / 2;
    if (anterior !== null) {
      // O fio entre os emblemas: da borda de baixo de um à de cima do seguinte.
      formas.push({ tipo: 'fio', d: `M ${EMBLEMA_CX} ${anterior + EMBLEMA_R} V ${cy - EMBLEMA_R - 1}`, seta: true });
    }
    formas.push({ tipo: 'caixa', x: FASE_X, y, w: FASE_L, h: altura, classe: fase.parada ? 'dg-caixa dg-parada' : 'dg-caixa' });
    formas.push({ tipo: 'emblema', forma: fase.parada ? 'octogono' : 'circulo', cx: EMBLEMA_CX, cy, r: EMBLEMA_R, texto: String(fase.n), classe: fase.parada ? 'dg-emblema dg-parada' : 'dg-emblema' });
    formas.push({ tipo: 'texto', classe: 'dg-nome', linhas: bloco(FASE_X + PAD, y + PAD, linhas, ALTURA_LINHA_NOME) });
    if (aviso.length) {
      formas.push({ tipo: 'texto', classe: 'dg-sub dg-aviso', linhas: bloco(FASE_X + PAD, y + PAD + linhas.length * ALTURA_LINHA_NOME, aviso, ALTURA_LINHA_SUB) });
    }
    anterior = cy;
    y += altura + FASE_ESPACO;
  }
  return { formas, fim: y - FASE_ESPACO };
}

function desenharTransversais(transversais, y0) {
  const formas = [];
  let y = y0;
  for (const t of transversais) {
    const linhas = quebrar(t.titulo, caber(FASE_L - 2 * PAD, TAMANHO_NOME, FATOR_NOME)).slice(0, 4);
    const sub = ['Vale para o projeto todo'];
    const altura = Math.max(ALTURA_MIN, 2 * PAD + linhas.length * ALTURA_LINHA_NOME + sub.length * ALTURA_LINHA_SUB);
    formas.push({ tipo: 'caixa', x: FASE_X, y, w: FASE_L, h: altura, classe: 'dg-caixa dg-transversal' });
    formas.push({ tipo: 'emblema', forma: 'losango', cx: EMBLEMA_CX, cy: y + altura / 2, r: EMBLEMA_R + 2, texto: t.titulo.charAt(0).toUpperCase(), classe: 'dg-emblema dg-transversal' });
    formas.push({ tipo: 'texto', classe: 'dg-nome', linhas: bloco(FASE_X + PAD, y + PAD, linhas, ALTURA_LINHA_NOME) });
    formas.push({ tipo: 'texto', classe: 'dg-sub', linhas: bloco(FASE_X + PAD, y + PAD + linhas.length * ALTURA_LINHA_NOME, sub, ALTURA_LINHA_SUB) });
    y += altura + FASE_ESPACO;
  }
  return { formas, fim: y - FASE_ESPACO };
}

/** Caixas de uma etapa, lado a lado, todas da mesma altura. */
function caixasDaEtapa(etapa, papeis, y) {
  const quem = papeisDe(etapa, papeis);
  const n = quem.length;
  const largura = (ONDA_X1 - ONDA_X0 - (n - 1) * ONDA_VAO) / n;
  const cartoes = quem.map((papel) => ({
    papel,
    nome: quebrar(papel.nome, caber(largura - 2 * PAD, TAMANHO_NOME, FATOR_NOME)),
    sub: quebrar(subDoPapel(papel), caber(largura - 2 * PAD, TAMANHO_SUB, FATOR_SUB)),
  }));
  const altura = Math.max(
    ALTURA_MIN,
    ...cartoes.map((c) => 2 * PAD + c.nome.length * ALTURA_LINHA_NOME + c.sub.length * ALTURA_LINHA_SUB),
  );
  const formas = [];
  const centros = [];
  cartoes.forEach((c, i) => {
    const x = ONDA_X0 + i * (largura + ONDA_VAO);
    centros.push(x + largura / 2);
    formas.push({ tipo: 'caixa', x, y, w: largura, h: altura, classe: etapa.condicional ? 'dg-caixa dg-condicional' : 'dg-caixa' });
    formas.push({ tipo: 'texto', classe: 'dg-nome', linhas: bloco(x + PAD, y + PAD, c.nome, ALTURA_LINHA_NOME) });
    formas.push({ tipo: 'texto', classe: 'dg-sub', linhas: bloco(x + PAD, y + PAD + c.nome.length * ALTURA_LINHA_NOME, c.sub, ALTURA_LINHA_SUB) });
  });
  return { formas, centros, altura };
}

function desenharOnda(onda, y0) {
  const formas = [];
  let y = y0;
  let anterior = null; // { fundo, centros }
  onda.etapas.forEach((etapa, i) => {
    const rotulo = etapa.rotulo ? quebrar(inicial(etapa.rotulo), caber(ROTULO_FIM_X - 8, TAMANHO_SUB, FATOR_SUB)).slice(0, 3) : [];
    const topo = y + (anterior ? ONDA_ESPACO + rotulo.length * ALTURA_LINHA_ROTULO : 0);
    const caixas = caixasDaEtapa(etapa, onda.papeis, topo);
    // De onde sai o desvio da etapa condicional: um ponto da linha que entra nela.
    let partida = null;

    if (anterior) {
      const fontes = anterior.centros;
      const alvos = caixas.centros;
      const juntar = fontes.length > 1;
      const abrir = alvos.length > 1;
      if (!juntar && !abrir) {
        formas.push({ tipo: 'fio', d: `M ${fontes[0]} ${anterior.fundo} V ${topo}`, seta: true });
        partida = { x: fontes[0], y: anterior.fundo + 12 };
      } else {
        // A barra onde as linhas se juntam (logo embaixo das fontes) ou se abrem (logo em cima dos alvos).
        const barra = juntar && !abrir ? anterior.fundo + 14 : abrir && !juntar ? topo - 14 : (anterior.fundo + topo) / 2;
        for (const x of fontes) formas.push({ tipo: 'fio', d: `M ${x} ${anterior.fundo} V ${barra}` });
        const xs = [...fontes, ...alvos];
        formas.push({ tipo: 'fio', d: `M ${Math.min(...xs)} ${barra} H ${Math.max(...xs)}` });
        for (const x of alvos) formas.push({ tipo: 'fio', d: `M ${x} ${barra} V ${topo}`, seta: true });
        partida = { x: ONDA_CX, y: barra };
      }
      if (rotulo.length) {
        // Quando as linhas se juntam embaixo das fontes, o rótulo desce para perto da caixa; senão fica logo abaixo delas.
        const topoRotulo = juntar && !abrir ? topo - 6 - rotulo.length * ALTURA_LINHA_ROTULO : anterior.fundo + 6;
        formas.push({ tipo: 'texto', classe: 'dg-rotulo', ancora: 'end', linhas: bloco(ROTULO_FIM_X, topoRotulo, rotulo, ALTURA_LINHA_ROTULO) });
      }
    }
    formas.push(...caixas.formas);
    y = topo + caixas.altura;
    anterior = { fundo: y, centros: caixas.centros };

    // Etapa condicional no meio: uma linha corre pela direita e volta à linha que sai dela, para quem
    // lê ver que dá para seguir sem passar por ela.
    if (etapa.condicional && partida && i < onda.etapas.length - 1) {
      const volta = y + 12;
      formas.push({
        tipo: 'fio',
        d: `M ${partida.x} ${partida.y} H ${ONDA_DESVIO_X} V ${volta} H ${caixas.centros[0]}`,
        classe: 'dg-desvio',
      });
    }
  });
  return { formas, fim: y };
}

/**
 * @param {object} fluxo  o conteúdo do fluxo.json (contrato 1.3)
 * @param {{ partes?: ('fases'|'onda'|'transversais')[], id?: string, legendas?: boolean }} [opcoes]
 *   `partes`: o que desenhar, na ordem em que vêm; `id`: prefixo dos ids do SVG (único na página);
 *   `legendas`: um título dentro do desenho para cada parte (padrão: só quando há mais de uma).
 * @returns {{ id: string, largura: number, altura: number, titulo: string, descricao: string, formas: object[] }}
 */
export function montarDiagrama(fluxo, { partes = PARTES, id = 'fluxo', legendas = partes.length > 1 } = {}) {
  for (const p of partes) {
    if (!PARTES.includes(p)) throw new Error(`Parte "${p}" do diagrama não existe (use ${PARTES.join(', ')}).`);
  }
  const formas = [];
  const descricoes = [];
  let y = 4;
  partes.forEach((parte, i) => {
    if (i > 0) y += 34;
    if (legendas) {
      formas.push({ tipo: 'texto', classe: 'dg-legenda', linhas: bloco(2, y, [LEGENDAS[parte]], LEGENDA_ALTURA) });
      y += LEGENDA_ALTURA + 6;
    }
    let r;
    if (parte === 'fases') {
      r = desenharFases(fluxo.fases, y);
      descricoes.push(descreverFases(fluxo.fases));
    } else if (parte === 'onda') {
      r = desenharOnda(fluxo.onda, y);
      descricoes.push(descreverOnda(fluxo.onda.etapas, fluxo.onda.papeis));
    } else {
      r = desenharTransversais(fluxo.transversais, y);
      descricoes.push(descreverTransversais(fluxo.transversais));
    }
    formas.push(...r.formas);
    y = r.fim;
  });
  return {
    id,
    largura: LARGURA,
    altura: Math.ceil(y + 6),
    titulo: `Fluxo do forge: ${lista(partes.map((p) => TITULOS[p]))}`,
    descricao: descricoes.join(' '),
    formas,
  };
}

/** Os pontos de um polígono regular (o octógono da fase de parada, o losango das transversais). */
export function pontos(forma, cx, cy, r) {
  const n = forma === 'losango' ? 4 : 8;
  const giro = forma === 'losango' ? 0 : Math.PI / 8;
  return Array.from({ length: n }, (_, k) => {
    const a = giro + (2 * Math.PI * k) / n - (forma === 'losango' ? Math.PI / 2 : 0);
    return `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`;
  }).join(' ');
}
