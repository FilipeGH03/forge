export const meta = {
  name: 'forge-onda',
  description: 'Executa uma onda do plano forge: executor, dois revisores e testador por tarefa',
  whenToUse: 'Chamado pela skill /forge com o args gerado por `forge.py onda`',
  phases: [
    { title: 'Executar', detail: 'executor faz, testa e commita a tarefa' },
    { title: 'Revisar', detail: 'revisor de contrato e revisor de padrões em paralelo' },
    { title: 'Testar', detail: 'testador independente confere e escreve os testes que faltam' },
  ],
}

// args = { plano, filas: [{ id, repo, tarefas: [{ id, titulo, briefings: { executor, revisor_contrato, revisor_padroes, testador } }] }], fora }
// Cada fila é um repositório: as tarefas dela rodam em sequência; filas diferentes rodam em paralelo.

const EXECUCAO = {
  type: 'object',
  properties: {
    estado: { type: 'string', enum: ['pronto', 'travou', 'contrato'] },
    commits: { type: 'array', items: { type: 'string' } },
    resumo: { type: 'string' },
    testes_rodados: { type: 'string' },
    problema_contrato: { type: 'string' },
    notas: { type: 'string' },
  },
  required: ['estado', 'commits', 'resumo', 'testes_rodados'],
}

const REVISAO = {
  type: 'object',
  properties: {
    aprovado: { type: 'boolean' },
    fontes: { type: 'array', items: { type: 'string' } },
    achados: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severidade: { type: 'string', enum: ['bloqueante', 'importante', 'sugestao'] },
          tipo: { type: 'string' },
          arquivo: { type: 'string' },
          linha: { type: 'integer' },
          texto: { type: 'string' },
          proposta: { type: 'string' },
        },
        required: ['severidade', 'texto'],
      },
    },
    generalizacao: { type: 'string' },
  },
  required: ['aprovado', 'achados'],
}

const TESTE = {
  type: 'object',
  properties: {
    aprovado: { type: 'boolean' },
    casos: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          caso: { type: 'string' },
          como: { type: 'string' },
          resultado: { type: 'string', enum: ['passou', 'falhou', 'nao-executado'] },
        },
        required: ['caso', 'resultado'],
      },
    },
    commits: { type: 'array', items: { type: 'string' } },
    notas: { type: 'string' },
  },
  required: ['aprovado', 'casos'],
}

// Modelo e esforço do papel nesta tarefa (vêm do `forge.py onda`, pela complexidade). Sem eles, herda a sessão.
const opcoes = (t, papel) => {
  const m = t.modelos && t.modelos[papel]
  return m ? { model: m.model, effort: m.effort } : {}
}
const ler = (caminho) => `Leia o briefing em \`${caminho}\` e siga-o à risca. Ele é a sua tarefa inteira.`
const anexo = (titulo, valor) => `\n\n## ${titulo}\n\n\`\`\`json\n${JSON.stringify(valor, null, 2)}\n\`\`\``

if (args.fora && args.fora.length) log(`Ficam para a próxima onda (limite de tarefas): ${args.fora.join(', ')}`)

async function rodarTarefa(t) {
  const b = t.briefings
  const execucao = await agent(ler(b.executor), { label: `executor:${t.id}`, phase: 'Executar', schema: EXECUCAO, ...opcoes(t, 'executor') })
  if (!execucao) return { id: t.id, estado: 'falhou', motivo: 'o executor não voltou' }
  if (execucao.estado !== 'pronto') return { id: t.id, estado: execucao.estado, execucao }

  const feito = anexo('Resultado do executor', execucao)
  const revisoes = await parallel([
    () => agent(ler(b.revisor_contrato) + feito, { label: `rev-contrato:${t.id}`, phase: 'Revisar', schema: REVISAO, ...opcoes(t, 'revisor_contrato') }),
    () => agent(ler(b.revisor_padroes) + feito, { label: `rev-padroes:${t.id}`, phase: 'Revisar', schema: REVISAO, ...opcoes(t, 'revisor_padroes') }),
  ])
  const [contrato, padroes] = revisoes
  const bloqueantes = revisoes.filter(Boolean).flatMap((r) => r.achados.filter((x) => x.severidade === 'bloqueante'))

  // Uma rodada de correção só: o que sobrar depois dela volta para a sessão principal decidir.
  let correcao = null
  if (bloqueantes.length) {
    correcao = await agent(
      ler(b.executor) +
        feito +
        '\n\n## Correção pedida pelos revisores\n\nVocê já fez esta tarefa. Corrija **só** os achados bloqueantes abaixo, ' +
        'em commit novo com o mesmo ID. Se discordar de um achado, não corrija: explique em `notas`.' +
        anexo('Achados bloqueantes', bloqueantes),
      { label: `correcao:${t.id}`, phase: 'Executar', schema: EXECUCAO, ...opcoes(t, 'executor') },
    )
  }

  const teste = await agent(
    ler(b.testador) + feito + (correcao ? anexo('Correção depois da revisão', correcao) : ''),
    { label: `testador:${t.id}`, phase: 'Testar', schema: TESTE, ...opcoes(t, 'testador') },
  )

  const pronto = !!teste && teste.aprovado && !!contrato && !!padroes && (!bloqueantes.length || (correcao && correcao.estado === 'pronto'))
  return { id: t.id, estado: pronto ? 'pronto' : 'revisar', execucao, contrato, padroes, correcao, teste }
}

const resultado = await pipeline(args.filas, async (fila) => {
  const saida = []
  for (const t of fila.tarefas) {
    const r = await rodarTarefa(t)
    saida.push(r)
    if (r.estado !== 'pronto') {
      const resto = fila.tarefas.slice(fila.tarefas.indexOf(t) + 1).map((x) => x.id)
      if (resto.length) log(`Fila ${fila.id}: ${t.id} terminou como "${r.estado}"; ${resto.join(', ')} ficam para a próxima onda`)
      break
    }
  }
  return { fila: fila.id, repo: fila.repo, tarefas: saida }
})

return { plano: args.plano, filas: resultado.filter(Boolean), fora: args.fora || [] }
