export const meta = {
  name: 'forge-onda',
  description: 'Executa uma onda do plano forge: executor e, conforme a equipe da tarefa, revisores e testador',
  whenToUse: 'Chamado pela skill /forge com o args gerado por `forge.py onda`',
  phases: [
    { title: 'Executar', detail: 'executor faz, testa e commita a tarefa' },
    { title: 'Revisar', detail: 'revisor de contrato e revisor de padrões em paralelo, se estão na equipe' },
    { title: 'Testar', detail: 'testador independente confere e escreve os testes que faltam, se está na equipe' },
  ],
}

// args = { plano, filas: [{ id, repo, tarefas: [{ id, titulo, equipe, briefings: { executor, revisor_contrato?, revisor_padroes?, testador? }, modelos }] }], fora }
// Cada fila é um repositório: as tarefas dela rodam em sequência; filas diferentes rodam em paralelo.
// Só roda o papel que tem briefing: a equipe de cada tarefa sai da complexidade (ou da escolha na tarefa).
// As mensagens entre os agentes seguem o FCP (references/fcp.md): um envelope curto e igual para todos.

const TESTES = {
  type: 'array',
  items: {
    type: 'object',
    properties: {
      case: { type: 'string' },
      cmd: { type: 'string' },
      result: { type: 'string', enum: ['pass', 'fail', 'skip'] },
    },
    required: ['cmd', 'result'],
  },
}
const ACHADOS = {
  type: 'array',
  items: {
    type: 'object',
    properties: {
      sev: { type: 'string', enum: ['block', 'major', 'minor'] },
      kind: { type: 'string' },
      at: { type: 'string' },
      msg: { type: 'string' },
      fix: { type: 'string' },
    },
    required: ['sev', 'msg'],
  },
}
const fcp = (status, extra = {}, obrigatorios = []) => ({
  type: 'object',
  properties: {
    id: { type: 'string' },
    status: { type: 'string', enum: status },
    commits: { type: 'array', items: { type: 'string' } },
    tests: TESTES,
    blockers: { type: 'array', items: { type: 'string' } },
    notes: { type: 'array', items: { type: 'string' }, maxItems: 5 },
    ...extra,
  },
  required: ['id', 'status', 'commits', 'tests', 'blockers', 'notes', ...obrigatorios],
})
const EXECUCAO = fcp(['ok', 'blocked', 'contract'])
const REVISAO = fcp(['ok', 'fail', 'blocked'], {
  findings: ACHADOS,
  sources: { type: 'array', items: { type: 'string' } },
  generalization: { type: 'string' },
}, ['findings'])
const TESTE = fcp(['ok', 'fail', 'blocked'])

// Modelo e esforço do papel nesta tarefa (vêm do `forge.py onda`, pela complexidade). Sem eles, herda a sessão.
const opcoes = (t, papel) => {
  const m = t.modelos && t.modelos[papel]
  return m ? { model: m.model, effort: m.effort } : {}
}
const ler = (caminho) => `Leia o briefing em \`${caminho}\` e siga-o à risca. Ele é a sua tarefa inteira.`
// FCP para o próximo agente: só os campos pedidos, sem os vazios, em JSON compacto
const enxuto = (msg, campos) =>
  Object.fromEntries(campos.filter((c) => msg[c] != null && msg[c] !== '' && !(Array.isArray(msg[c]) && !msg[c].length)).map((c) => [c, msg[c]]))
const anexo = (titulo, valor) => `\n\n## ${titulo} (FCP)\n\n\`\`\`json\n${JSON.stringify(valor)}\n\`\`\``
const PASSA = ['id', 'commits', 'tests', 'notes']

if (args.fora && args.fora.length) log(`Ficam para a próxima onda (limite de tarefas): ${args.fora.join(', ')}`)

async function rodarTarefa(t) {
  const b = t.briefings
  const execucao = await agent(ler(b.executor), { label: `executor:${t.id}`, phase: 'Executar', schema: EXECUCAO, ...opcoes(t, 'executor') })
  if (!execucao) return { id: t.id, status: 'fail', equipe: t.equipe, notes: ['o executor não voltou'] }
  if (execucao.status !== 'ok') return { id: t.id, status: execucao.status, equipe: t.equipe, executor: execucao }

  const feito = anexo('Executor', enxuto(execucao, PASSA))
  const revisoes = await parallel([
    async () => (b.revisor_contrato ? agent(ler(b.revisor_contrato) + feito, { label: `rev-contrato:${t.id}`, phase: 'Revisar', schema: REVISAO, ...opcoes(t, 'revisor_contrato') }) : null),
    async () => (b.revisor_padroes ? agent(ler(b.revisor_padroes) + feito, { label: `rev-padroes:${t.id}`, phase: 'Revisar', schema: REVISAO, ...opcoes(t, 'revisor_padroes') }) : null),
  ])
  const [contrato, padroes] = revisoes
  const bloqueantes = revisoes.filter(Boolean).flatMap((r) => (r.findings || []).filter((x) => x.sev === 'block'))

  // Uma rodada de correção só: o que sobrar depois dela volta para a sessão principal decidir.
  let correcao = null
  if (bloqueantes.length) {
    correcao = await agent(
      ler(b.executor) +
        feito +
        '\n\n## Correção pedida pelos revisores\n\nVocê já fez esta tarefa. Corrija **só** os achados `block` abaixo, ' +
        'em commit novo com o mesmo ID. Se discordar de um achado, não corrija: diga por quê em `notes`.' +
        anexo('Achados block', bloqueantes),
      { label: `correcao:${t.id}`, phase: 'Executar', schema: EXECUCAO, ...opcoes(t, 'executor') },
    )
  }

  const teste = b.testador
    ? await agent(
        ler(b.testador) + feito + (correcao ? anexo('Correção depois da revisão', enxuto(correcao, PASSA)) : ''),
        { label: `testador:${t.id}`, phase: 'Testar', schema: TESTE, ...opcoes(t, 'testador') },
      )
    : null

  // Cada papel da equipe precisa ter voltado e aprovado; papel fora da equipe não conta.
  const voltou = (papel, msg) => !b[papel] || (!!msg && msg.status === 'ok')
  const revisado = (papel, msg) => !b[papel] || (!!msg && msg.status !== 'blocked')
  const pronto =
    revisado('revisor_contrato', contrato) && revisado('revisor_padroes', padroes) &&
    voltou('testador', teste) && (!bloqueantes.length || (!!correcao && correcao.status === 'ok'))
  const saida = { id: t.id, status: pronto ? 'ok' : 'fail', equipe: t.equipe, executor: execucao }
  for (const [nome, msg] of [['rev_contrato', contrato], ['rev_padroes', padroes], ['correcao', correcao], ['testador', teste]]) {
    if (msg) saida[nome] = msg
  }
  return saida
}

const resultado = await pipeline(args.filas, async (fila) => {
  const saida = []
  for (const t of fila.tarefas) {
    const r = await rodarTarefa(t)
    saida.push(r)
    if (r.status !== 'ok') {
      const resto = fila.tarefas.slice(fila.tarefas.indexOf(t) + 1).map((x) => x.id)
      if (resto.length) log(`Fila ${fila.id}: ${t.id} terminou como "${r.status}"; ${resto.join(', ')} ficam para a próxima onda`)
      break
    }
  }
  return { fila: fila.id, repo: fila.repo, tarefas: saida }
})

return { plano: args.plano, filas: resultado.filter(Boolean), fora: args.fora || [] }
