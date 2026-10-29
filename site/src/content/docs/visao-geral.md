---
titulo: Visão geral
descricao: O que é o forge, que problema ele resolve e como as peças se encaixam — plano vivo, frentes, contratos, tarefas e ondas de agentes.
secao: conceitos
ordem: 1
destaque: true
---

O forge é uma skill do Claude Code para tocar um projeto que atravessa mais de um repositório (ou mais
de uma área de um repositório) com agentes trabalhando em paralelo. Você chama `/forge`, e ele conduz o
projeto do levantamento dos requisitos até o fechamento, com um **plano de trabalho vivo** como fonte
da verdade.

## O problema

Projeto tocado por agentes costuma se perder de três jeitos:

- **A conversa vira a fonte da verdade.** O que foi decidido fica espalhado no histórico do chat, e a
  próxima sessão não sabe.
- **Cada agente decide sozinho o que passa de um lado para o outro.** O formato de uma resposta, o nome
  de um campo, uma rota: se ninguém escreveu, cada lado inventa o seu, e o erro só aparece na
  integração.
- **O plano e o código se separam.** Uma tarefa marcada como feita sem commit, um commit que não é de
  tarefa nenhuma, uma decisão que mudou depois que a tarefa estava pronta.

## A ideia

O método foi extraído de um projeto real e generalizado em quatro ideias:

1. **Um documento vivo é a fonte da verdade.** O estado mora num JSON; o Markdown que as pessoas leem é
   gerado dele a cada alteração. Veja [Plano vivo](/docs/plano-vivo/).
2. **O trabalho anda em frentes amarradas por contratos.** Cada frente é um repositório (ou uma área que
   nunca encosta nos arquivos de outra); tudo o que atravessa frentes é escrito antes, com exemplo. Veja
   [Frentes e contratos](/docs/frentes-e-contratos/).
3. **Cada tarefa é pequena e se prova sozinha.** Tem um "como testar" e dependências explícitas, e o
   commit carrega o ID dela. Veja [Tarefas e ondas](/docs/tarefas-e-ondas/).
4. **Agentes executam, a sessão principal integra.** Cada tarefa passa por executor, dois revisores e um
   testador; só a sessão principal muda o plano. Veja [Papéis dos agentes](/docs/papeis-dos-agentes/).

## As peças

| Peça | Onde mora | Para quê |
|---|---|---|
| `forge-<slug>.json` | na pasta do projeto, **fora** dos repositórios | O estado. É a única coisa que se edita. |
| `forge-<slug>.md` | ao lado do JSON | O documento do projeto, gerado a cada alteração. Nunca se edita à mão. |
| `forge-<slug>.briefings/` | ao lado do JSON | Os briefings gerados para cada agente da onda. |
| `scripts/forge.py` | na skill | Todos os comandos sobre o plano — veja a [referência de comandos](/comandos/). |
| `references/workflow-onda.js` | na skill | O workflow que executa uma onda. |
| `references/briefing-*.md` | na skill | Os modelos dos briefings dos quatro papéis, cada um com a parte do plano que o papel precisa. |
| `references/fcp.md` | na skill | O FCP: o formato curto das mensagens entre os agentes. |
| `references/plano-json.md` | na skill | O formato do JSON, para os campos que não têm comando. |
| `hooks/forge_hook.py` | na skill | Os hooks globais — veja [Hooks](/docs/hooks/). |

## O fluxo, em uma linha por fase

| Fase | O que acontece |
|---|---|
| 0 — Descobrir onde está | Já existe plano? Retoma conferindo plano contra código. Senão, começa um novo. |
| 1 — Requisitos | Poucas perguntas, em lote; o plano nasce com os requisitos e a origem de cada um. |
| 2 — Levantamento | Lê o código antes de propor e anota os fatos, inclusive como compilar e testar cada repositório. |
| 3 — Proposta | Frentes, contratos, tarefas, decisões e dúvidas. |
| 4 — Aprovação | **Parada obrigatória:** nada de agente nem de código antes do sim do dono. |
| 5 — Execução em ondas | Cada tarefa passa por executor, revisores e testador. |
| 6 — Integração | A sessão principal confere, marca o ✔ e leva ao dono o que voltou com problema. |
| 7 — Sincronização | Plano e código contam a mesma história: o [drift](/docs/sincronizacao-e-drift/) sai limpo. |

Depois da aprovação, em qualquer fase, toda mudança de escopo, desenho ou contrato vira uma decisão
registrada — veja [Decisões no meio do projeto](/docs/decisoes-no-meio-do-projeto/).

## Como se chama

Na sessão do Claude Code, `/forge` — ou pedidos como "planejar um projeto em frentes", "rodar a próxima
onda", "retomar o projeto X" ou "sincronizar o plano com o código". Por baixo, a skill usa o
`forge.py`:

```bash
python ~/.claude/skills/forge/scripts/forge.py <comando> <plano.json> ...
```
