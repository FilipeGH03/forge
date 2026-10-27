---
name: forge
description: Conduz um projeto dividido em frentes e tocado por agentes, com um plano de trabalho vivo (JSON → Markdown) como fonte da verdade — coleta os requisitos, levanta o código, propõe frentes, contratos e tarefas, gera o documento do projeto para aprovação, executa em ondas (executor, revisor de contrato, revisor de padrões e testador por tarefa) e mantém o documento sincronizado com o código. Use quando o usuário chamar /forge, pedir para "planejar/tocar um projeto em frentes", "montar o plano de trabalho", "dividir entre agentes", "retomar o projeto X", "continuar o plano", "rodar a próxima onda", "sincronizar o plano com o código", ou abrir uma sessão numa pasta que tem um plano forge registrado.
---

# forge

Método extraído do Serviço de Avisos (`C:\Projetos\plano-avisos.md`), generalizado: um
**documento vivo** é a fonte da verdade, o trabalho anda em **frentes** independentes amarradas por
**contratos**, cada tarefa é pequena e testável sozinha, e agentes executam enquanto a sessão
principal integra.

## Peças

| Peça | Onde | Para quê |
|---|---|---|
| `forge-<slug>.json` | na pasta do projeto, **fora** dos repositórios (ex.: `C:\Projetos`) | O estado. Única coisa que se edita. |
| `forge-<slug>.md` | ao lado do JSON | O documento do projeto, **gerado** a cada alteração. Nunca editar à mão. |
| `forge-<slug>.briefings/` | ao lado do JSON | Briefings gerados para cada agente da onda. |
| `scripts/forge.py` | nesta skill | Todos os comandos sobre o plano. |
| `references/workflow-onda.js` | nesta skill | O Workflow que executa uma onda. |
| `references/briefing-*.md` | nesta skill | Modelos dos briefings dos quatro papéis. |
| `references/plano-json.md` | nesta skill | Formato do JSON, para editar campos que não têm comando. |
| `hooks/forge_hook.py` | nesta skill | Hooks globais: estado ao abrir sessão, trava de banco, ID no commit. |

Chame o script sempre assim (abreviado como `forge` daqui em diante):

```bash
python "C:/Users/DEV/.claude/skills/forge/scripts/forge.py" <comando> <plano.json> ...
```

| Comando | Faz |
|---|---|
| `novo <slug> --titulo --dono --dir [--branch] [--base]` | Cria JSON + MD e registra o plano |
| `status` / `drift` | Estado com commits / divergências plano × repositórios |
| `md` / `validar` | Regenera o MD depois de editar o JSON à mão / só valida |
| `tarefa --frente --titulo --testar [--depende]` | Nova tarefa com o próximo ID |
| `decisao --assunto --texto [--afeta] [--revoga] [--contrato] [--duvida]` | Nova decisão D<n>; tarefas feitas em `--afeta` voltam como ⟳ |
| `duvida "texto"` / `responder Q<n> "resposta"` | Dúvidas |
| `marcar <ID> [--commit] [--revisar\|--pendente]` | ✔ achando os commits pelo ID |
| `fase <fase>` | `requisitos → aguardando-aprovacao → aprovado → em-execucao → fechado` |
| `onda [--max N] --saida <arq>` | Escolhe a próxima onda, grava os briefings, gera o `args` do workflow |
| `briefing <ID> --papel` | Mostra um briefing |
| `rodada --titulo --arquivo [--dono ...] [--licao ...]` | Registra o fechamento de uma rodada |
| `dono [--add] [--feito N]` | Pendências que só o dono resolve |
| `branches` | À frente/atrás da base, publicada ou não, arquivos alterados — por repositório |
| `ponteiros` | Escreve um `FORGE.md` em cada repositório apontando para o plano |
| `lista` / `registrar` / `contexto` | Planos registrados (usados pelos hooks) |

## Fase 0 — Descobrir onde está

Rode `forge lista`. Se o hook de SessionStart já trouxe o estado de um plano, ou o usuário nomeou
um, é **retomada**: rode `status` e `drift`, mostre em poucas linhas onde o trabalho parou, e siga
pela fase em que o plano está. Divergência no `drift` se resolve **antes** de qualquer onda: o
repositório tem razão — corrija o plano (`marcar`, `decisao`, edição do JSON + `md`).

Senão, é projeto novo: siga a fase 1.

## Fase 1 — Requisitos

1. Pergunte o mínimo para entender o objetivo, **em lote** (AskUserQuestion, até 4 perguntas por
   vez): o que precisa existir no fim, para quem, o que fica de fora, quais repositórios, se há prazo
   ou restrição, quem decide as dúvidas. Não pergunte o que dá para descobrir lendo o código.
2. `forge novo <slug> --titulo ... --dono ... --dir <pasta do projeto> --base <branch base>`.
3. Preencha `objetivo` e `requisitos` (R1, R2... com a fonte: "usuário em 27/10", "ticket DEV-123")
   editando o JSON, e rode `md`.

## Fase 2 — Levantamento

Leia o código antes de propor qualquer coisa. Para vários repositórios, use subagentes `Explore` em
paralelo, um por repositório, pedindo **fatos com arquivo e linha** — não opinião. Registre em
`apurado` (uma entrada por área) o que alguém precisaria redescobrir: onde a mudança encaixa, os
padrões de cada repositório, o que já existe e pode ser reaproveitado, e **como compilar e testar
cada repositório nesta máquina — testado agora, não suposto** (a lição de 21/09 dos avisos: duas
frentes trabalharam uma noite inteira com uma restrição que já não existia).

## Fase 3 — Proposta: frentes, contratos e tarefas

**Frentes.** Uma frente é um repositório (ou uma área de um repositório que nunca encosta nos
arquivos de outra). Critérios: dá para andar em paralelo sem um pisar no outro; tem um jeito próprio
de testar; tem dono claro. Letras A, B, C... (D, Q e R são reservadas). Em `proibido`, as restrições
da frente (ex.: "suíte inteira encosta em banco: rode por classe").

**Contratos.** Tudo o que atravessa frentes — formato de requisição/resposta, evento, nome de rota,
tabela compartilhada — vira contrato, com exemplo concreto (JSON, tabela de campos com obrigatório e
regra, códigos de resposta). Sem contrato fechado, o agente decide sozinho e erra.

**Tarefas.** Pequenas, uma coisa só, cada uma com **como provar que funciona sozinha** e dependências
explícitas. ID = letra da frente + número. Deixe o caminho crítico curto: o que destrava as outras
frentes vem primeiro.

**Decisões e dúvidas.** Tudo o que foi escolhido vira `decisao`; tudo o que falta decidir vira
`duvida`. Dúvida em aberto que bloqueia tarefa: diga qual na nota da tarefa.

Cadastre com os comandos (ou editando o JSON, ver `references/plano-json.md`) e rode `validar`.

## Fase 4 — Aprovação (parada obrigatória)

1. `forge fase <plano> aguardando-aprovacao`.
2. Apresente o `forge-<slug>.md`: link para o arquivo, e no chat um resumo de **frentes, contratos,
   número de tarefas por frente, primeira onda e dúvidas em aberto**.
3. **Pare e espere a aprovação explícita.** Não crie branch, não lance agente, não escreva código.
   Pedido de mudança → altere o plano, regenere e apresente de novo.
4. Aprovado: `forge fase <plano> aprovado`. Pergunte se os agentes podem dar **push** (grava em
   `agentes.push`; padrão é só commit local) e se quer os `FORGE.md` nos repositórios (`ponteiros`).

## Fase 5 — Execução em ondas

1. `forge drift` limpo e `forge branches` conferido (árvore suja num repositório da onda: pergunte
   antes de seguir).
2. `forge fase <plano> em-execucao` (na primeira onda).
3. `forge onda <plano> --max 3 --saida <scratchpad>/onda.json`. Leia o arquivo: ele traz as filas
   (uma por repositório; tarefas da fila em sequência, filas em paralelo) e o que ficou de fora.
4. Diga ao usuário quais tarefas entram na onda e quantos agentes isso dá (até 5 por tarefa:
   executor, 2 revisores, correção se houver bloqueante, testador). Invocar `/forge` já autoriza o
   Workflow; mesmo assim, confirme antes da **primeira** onda da sessão.
5. Rode o Workflow com `scriptPath: "C:/Users/DEV/.claude/skills/forge/references/workflow-onda.js"`
   e `args` = o objeto do `onda.json` (o objeto, não o texto). Se o `scriptPath` for recusado, passe o
   conteúdo do arquivo em `script`.

Modo enxuto, para tarefa muito pequena ou sem contrato: rode o executor e os revisores pela
ferramenta Agent na sessão, com os briefings de `forge briefing`, sem Workflow.

## Fase 6 — Integração (só a sessão principal)

Para cada tarefa que voltou:

- `pronto` → confira os commits no repositório (`git show`) e rode `forge marcar <ID>`.
- `revisar` / `travou` / `contrato` → **não marque**. Leve ao usuário o achado concreto. Problema de
  contrato é o resultado mais valioso: vira `duvida` ou `decisao` (+ `--afeta`), nunca adaptação
  silenciosa.
- Achados `importante`/`sugestao` dos revisores e a `generalizacao` do revisor de padrões: resuma
  para o usuário; o que for aceito vira tarefa nova (`tarefa`) ou decisão.
- Casos `nao-executado` do testador → `dono --add` com o roteiro.

Feche a onda com `forge rodada --titulo ... --arquivo <registro.md>`: commits por repositório, o que
os testes cobriram, o que mudou de comportamento, furos em aberto, "SQL a olhar". `--dono` para o que
fica com o dono, `--licao` para o que a onda ensinou sobre os agentes.

## Decisões no meio do projeto

Vale em qualquer fase depois da aprovação: o plano é a fonte da verdade, não a conversa. **Toda
resposta ou pedido do usuário que muda escopo, desenho, contrato ou comportamento vira decisão na
hora**, mesmo que ele não use a palavra "decisão" ("na verdade quero vários tipos", "tira o botão",
"o campo pode vir vazio"). O mesmo vale para o que voltar dos agentes e for aceito: problema de
contrato, generalização proposta pelo revisor de padrões, defeito que muda a regra.

1. **Diga o impacto antes de registrar:** quais decisões ela substitui, quais contratos muda,
   quais tarefas feitas precisam ser revistas e quais pendentes mudam de texto. Mudança de
   **contrato** precisa do OK explícito do usuário, porque mexe em mais de uma frente.
2. **Registre:**
   `forge decisao <plano> --assunto ... --texto ... [--revoga D<n>] [--contrato <id>] [--afeta <tarefas>] [--duvida Q<n>]`.
   - `--revoga`: a decisão antiga fica riscada no documento, nunca apagada.
   - `--afeta`: as tarefas **feitas** voltam como ⟳. A próxima onda as pega, e o briefing do executor
     diz que é uma revisão por causa desta decisão, para ajustar e não refazer.
   - `--contrato`: depois, edite o texto do contrato no JSON e rode `md`. O documento marca o
     contrato como "alterado pela D<n>". Passe em `--afeta` as tarefas das frentes do contrato que já
     o usam.
3. **Ajuste o resto:** requisito novo vira `R<n>` no JSON, tarefa nova com `tarefa`, e tarefa
   pendente que mudou de sentido tem o título e o "como testar" editados no JSON. Uma tarefa que
   deixou de fazer sentido não é apagada: vira nota "cancelada pela D<n>" e é marcada com
   `marcar --forcar`.
4. **Se uma onda estiver rodando** e a decisão atingir uma tarefa dela, avise o usuário. O resultado
   dessa tarefa não é marcado como ✔, e sim como ⟳, que entra na onda seguinte com o briefing
   novo.
5. Rode `forge drift`. A `decisao-posterior` aponta tarefa feita antes da decisão que a afeta e que
   foi marcada ✔ sem commit novo.

## Fase 7 — Documento e código sincronizados

Ao fim de cada onda e antes de encerrar a sessão:

1. `forge drift` precisa sair limpo. Commit sem ID, ✔ sem commit, commit sem ✔, decisão posterior a
   uma tarefa feita que ela afeta (`marcar --revisar`), MD editado à mão — cada um se resolve, não se
   ignora.
2. README/CLAUDE.md dos repositórios tocados: se uma tarefa mudou como rodar, configurar ou subir,
   isso é uma tarefa (ou parte dela) — não fica só no plano.
3. Decisão que mudou: `decisao --revoga D<n>`, nunca apagar a antiga.
4. Plano terminado: `forge fase <plano> fechado` (o hook para de mostrá-lo ao abrir sessão).

## Regras que não se negociam

- **Banco:** nunca conectar nem executar SQL, exceto banco local (`localhost`/`127.0.0.1`) cujo nome
  começa com `torge_`; **nunca** `autenticacao`, `producao01` ou `desenvolvimento`. Vale para
  agentes. O hook bloqueia os clientes de banco, mas a regra vale além do que ele pega.
- O plano só muda pelo `forge.py` (ou JSON + `md`), e só pela sessão principal.
- Contrato não se muda de um lado só. Aprovação do plano não autoriza mudar contrato depois.
- Nada de lançar agentes antes da aprovação da fase 4.

## Hooks (instalados em `~/.claude/settings.json`)

- **SessionStart:** se a pasta da sessão é a de um plano registrado ou de uma de suas frentes,
  injeta o `status` no contexto.
- **PreToolUse (Bash/PowerShell):** bloqueia `psql`, `pg_dump`, `mysql`, `sqlcmd` etc. e URLs JDBC
  fora da regra de banco; num repositório de frente, na branch do plano, recusa `git commit -m` sem
  um ID de tarefa existente no começo da mensagem.

Instalar/remover: `python "C:/Users/DEV/.claude/skills/forge/hooks/instalar.py" [--remover]`.
