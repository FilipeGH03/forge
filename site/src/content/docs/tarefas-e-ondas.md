---
titulo: Tarefas e ondas
descricao: Tarefas pequenas que se provam sozinhas, agrupadas em ondas pelas dependências; cada onda roda os quatro agentes por tarefa e fecha com a integração.
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

O comando também grava os briefings dos quatro papéis de cada tarefa em `forge-<slug>.briefings/` e
imprime o `args` do workflow:

```json
{
  "plano": "<pasta>/forge-exemplo.json",
  "filas": [
    {
      "id": "A",
      "repo": "<pasta>/repo-a",
      "tarefas": [
        { "id": "A1", "titulo": "...", "briefings": { "executor": "...", "revisor_contrato": "...", "revisor_padroes": "...", "testador": "..." } }
      ]
    }
  ],
  "fora": []
}
```

## Uma tarefa dentro da onda

O workflow da skill (`references/workflow-onda.js`) roda cada tarefa assim:

1. **Executor** faz, testa e commita. Se não voltar `pronto` (voltou `travou` ou `contrato`), a tarefa
   para aqui e vai para a sessão principal.
2. **Revisor de contrato** e **revisor de padrões**, em paralelo, leem o que ele fez.
3. **Correção**, só se houver achado bloqueante: o executor volta uma vez, para corrigir só esses
   achados. O que sobrar depois dela vai para a sessão principal decidir.
4. **Testador** confere e escreve os testes que faltam.

A tarefa termina `pronto` quando o testador aprova, os dois revisores voltaram e não sobrou bloqueante
sem correção. Senão, termina como `revisar` — e as tarefas seguintes da mesma fila ficam para a
próxima onda.

São até cinco agentes por tarefa. Os papéis estão em [Papéis dos agentes](/docs/papeis-dos-agentes/).

### Antes da onda

1. [`drift`](/comandos/#drift) limpo e [`branches`](/comandos/#branches) conferido. Árvore suja num
   repositório da onda: pergunte antes de seguir.
2. [`fase em-execucao`](/comandos/#fase), na primeira onda.
3. [`onda`](/comandos/#onda) com `--saida`, e o arquivo lido: quais tarefas entram e quantos agentes isso
   dá. Invocar `/forge` já autoriza o workflow, mas a primeira onda da sessão é confirmada com o dono.

Para uma tarefa muito pequena, ou sem contrato, há o **modo enxuto**: o executor e os revisores rodam
direto na sessão, com os briefings de [`briefing`](/comandos/#briefing), sem workflow.

## Integração

Só a sessão principal integra. Para cada tarefa que voltou:

| Voltou | O que se faz |
|---|---|
| `pronto` | Confere os commits no repositório e roda [`marcar`](/comandos/#marcar), que acha os commits pelo ID. |
| `revisar`, `travou` ou `contrato` | **Não marca.** Leva ao dono o achado concreto. Problema de contrato vira dúvida ou decisão, nunca adaptação silenciosa. |

Os achados `importante` e `sugestao` dos revisores, e a generalização proposta pelo revisor de padrões,
são resumidos para o dono; o que ele aceitar vira tarefa nova ou decisão. Os casos `nao-executado` do
testador viram pendências do dono, com [`dono --add`](/comandos/#dono).

A onda fecha com [`rodada`](/comandos/#rodada): os commits por repositório, o que os testes cobriram,
o que mudou de comportamento e os furos em aberto. `--dono` registra o que fica com o dono; `--licao`, o
que a onda ensinou sobre os agentes — as lições aparecem na seção 9 do plano.
