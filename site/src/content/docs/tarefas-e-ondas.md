---
titulo: Tarefas e ondas
descricao: Tarefas pequenas que se provam sozinhas, agrupadas em ondas pelas dependências; cada onda roda os agentes da equipe de cada tarefa e fecha com a integração.
secao: fluxo
ordem: 1
---

## Tarefas

Uma tarefa faz **uma coisa só**, termina e é testada sozinha. Toda tarefa tem:

| Campo | Regra |
|---|---|
| ID | A letra da frente seguida de um número: `A1`, `B3`. O comando [`tarefa`](/comandos/#tarefa) dá o próximo. |
| Título | O que a tarefa entrega. |
| Como testar | **Obrigatório.** Como provar que ela funciona sozinha — o plano não é gravado sem ele. |
| Depende de | Os IDs de que ela precisa prontos. Só IDs que existem, e sem ciclo. |
| Estado | `pendente` ☐, `feito` ✔ ou `revisar` ⟳. |
| Commits | Os SHAs que a cumprem, achados pelo ID na mensagem. |
| Complexidade | `baixa`, `media` ou `alta`: escolhe o modelo de cada agente e a equipe padrão. |
| Equipe | Opcional: quem roda na tarefa, quando a importância pede outra equipe que a da complexidade. |

O estado `revisar` (⟳) é o de uma tarefa que estava feita e voltou por causa de uma
[decisão posterior](/docs/decisoes-no-meio-do-projeto/). A próxima onda a pega, e o briefing do
executor diz que é uma revisão, para ajustar o que existe e não refazer do zero.

Deixe o caminho crítico curto: o que destrava as outras frentes vem primeiro.

### O ID no commit

Todo commit de uma tarefa começa pelo ID dela. É assim que o forge liga o código ao plano, sem
ninguém copiar SHA à mão. Os formatos reconhecidos no começo da mensagem:

```text
A3: botão de filtro
A3, A4: ajuste compartilhado
A27 (T9): correção
B2 e C4: renomeia o campo
```

Um commit pode servir a mais de uma tarefa (`A3, A4: ...`), e uma tarefa pode ter muitos commits —
nunca menos de um.

## Ondas

As dependências organizam as tarefas em níveis: quem não depende de nada fica na onda 1; quem depende
só de tarefas da onda 1 fica na 2, e assim por diante. A seção 8 do plano mostra essas ondas.

Na hora de executar, o comando [`onda`](/comandos/#onda) escolhe o que entra agora:

- uma tarefa não feita entra quando as dependências dela estão **feitas**, ou vêm **antes dela na mesma
  fila**;
- há uma **fila por repositório**: as tarefas da fila rodam em sequência, e filas diferentes rodam em
  paralelo. Frentes que dividem um repositório viram uma fila só;
- `--max` limita quantas tarefas entram (padrão 3); as que sobram ficam listadas em `fora`, para a
  onda seguinte.

O comando também grava, em `forge-<slug>.briefings/`, os briefings dos papéis da equipe de cada tarefa e
imprime o `args` do workflow:

```json
{
  "plano": "<pasta>/forge-exemplo.json",
  "filas": [
    {
      "id": "A",
      "repo": "<pasta>/repo-a",
      "tarefas": [
        { "id": "A1", "titulo": "...", "complexidade": "media", "equipe": ["executor", "revisor-contrato", "testador"],
          "briefings": { "executor": "...", "revisor_contrato": "...", "testador": "..." }, "modelos": { "...": "..." } }
      ]
    }
  ],
  "fora": []
}
```

## Uma tarefa dentro da onda

O workflow da skill (`references/workflow-onda.js`) roda cada tarefa assim, pulando o papel que não
está na equipe dela:

1. **Executor** faz, testa e commita. Se não voltar `ok` (voltou `blocked` ou `contract`), a tarefa
   para aqui e vai para a sessão principal.
2. **Revisor de contrato** e **revisor de padrões**, em paralelo, leem o que ele fez.
3. **Correção**, só se houver achado `block`: o executor volta uma vez, para corrigir só esses
   achados. O que sobrar depois dela vai para a sessão principal decidir.
4. **Testador** confere e escreve os testes que faltam.

A tarefa termina `ok` quando cada papel da equipe voltou, o testador (se está na equipe) aprovou e não
sobrou `block` sem correção. Senão, termina como `fail` — e as tarefas seguintes da mesma fila ficam
para a próxima onda. As mensagens entre os passos seguem o
[FCP](/docs/papeis-dos-agentes/).

São de um (equipe solo) a cinco agentes por tarefa (equipe completa com correção). Os papéis estão em [Papéis dos agentes](/docs/papeis-dos-agentes/).

### Antes da onda

1. [`drift`](/comandos/#drift) limpo e [`branches`](/comandos/#branches) conferido. Árvore suja num
   repositório da onda: pergunte antes de seguir.
2. [`fase em-execucao`](/comandos/#fase), na primeira onda.
3. [`onda`](/comandos/#onda) com `--saida`, e o arquivo lido: quais tarefas entram, a equipe de cada uma
   e quantos agentes isso dá. Invocar `/forge` já autoriza o workflow, mas a primeira onda da sessão é confirmada com o dono.

Para uma tarefa muito pequena, ou sem contrato, há o **modo enxuto**: os papéis da equipe dela rodam
direto na sessão, com os briefings de [`briefing`](/comandos/#briefing), sem workflow.

## Integração

Só a sessão principal integra. Para cada tarefa que voltou:

| Voltou | O que se faz |
|---|---|
| `ok` | Confere os commits no repositório e roda [`marcar`](/comandos/#marcar), que acha os commits pelo ID. |
| `fail`, `blocked` ou `contract` | **Não marca.** Leva ao dono o achado concreto. Problema de contrato vira dúvida ou decisão, nunca adaptação silenciosa. |

Os achados `major` e `minor` dos revisores, e a generalização proposta pelo revisor de padrões, são
resumidos para o dono; o que ele aceitar vira tarefa nova ou decisão. Os testes `skip` do testador
viram pendências do dono, com [`dono --add`](/comandos/#dono). Tarefa que rodou com equipe enxuta e
voltou com um defeito que um revisor ou o testador pegaria pede equipe maior — nela e nas parecidas.

A onda fecha com [`rodada`](/comandos/#rodada): os commits por repositório, o que os testes cobriram,
o que mudou de comportamento e os furos em aberto. `--dono` registra o que fica com o dono; `--licao`, o
que a onda ensinou sobre os agentes — as lições aparecem na seção 9 do plano.
