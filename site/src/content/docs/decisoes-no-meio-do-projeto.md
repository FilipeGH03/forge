---
titulo: Decisões no meio do projeto
descricao: Depois da aprovação, toda mudança de escopo, desenho ou contrato vira uma decisão registrada, com o impacto dito antes.
secao: fluxo
ordem: 2
---

Depois da aprovação, o plano é a fonte da verdade — não a conversa. **Toda resposta ou pedido do dono
que muda escopo, desenho, contrato ou comportamento vira decisão na hora**, mesmo sem a palavra
"decisão": "na verdade quero vários tipos", "tira o botão", "o campo pode vir vazio".

O mesmo vale para o que volta dos agentes e é aceito: um problema de contrato, uma generalização
proposta pelo revisor de padrões, um defeito que muda a regra.

## 1. Diga o impacto antes de registrar

Antes de gravar, diga ao dono:

- quais decisões ela substitui;
- quais contratos ela muda;
- quais tarefas feitas precisam ser revistas;
- quais tarefas pendentes mudam de texto.

Mudança de **contrato** precisa do OK explícito do dono, porque mexe em mais de uma frente.

## 2. Registre

```bash
forge.py decisao forge-exemplo.json --assunto "Tipos do filtro" \
  --texto "O filtro aceita vários tipos." --revoga D1 --contrato 1.1 --afeta A1 B2 --duvida Q1
```

| Opção | O que faz |
|---|---|
| `--revoga D<n>` | A decisão antiga fica **riscada** no documento, nunca apagada. Decisão nova é linha nova. |
| `--afeta` | As tarefas **feitas** da lista voltam como ⟳. A próxima onda as pega, e o briefing do executor diz que é uma revisão por causa desta decisão. |
| `--contrato` | O documento marca o contrato como "alterado pela D&lt;n&gt;". Depois, edite o texto do contrato no JSON e rode `md`. Passe em `--afeta` as tarefas das frentes do contrato que já o usam. |
| `--duvida Q<n>` | Liga a decisão à dúvida que ela responde. |
| `--data` | A data da decisão, quando não é hoje. |

A referência completa está em [`decisao`](/comandos/#decisao).

## 3. Ajuste o resto

- Requisito novo vira um `R<n>` no JSON.
- Tarefa nova entra com [`tarefa`](/comandos/#tarefa).
- Tarefa pendente que mudou de sentido tem o título e o "como testar" editados no JSON.
- Tarefa que deixou de fazer sentido **não é apagada**: ganha a nota "cancelada pela D&lt;n&gt;" e é
  marcada com `marcar --forcar`.

## 4. Se uma onda estiver rodando

Se a decisão atinge uma tarefa da onda em andamento, avise o dono. O resultado dessa tarefa não é
marcado ✔: ela fica ⟳ e entra na onda seguinte, com o briefing novo.

## 5. Confira com o drift

Rode [`drift`](/comandos/#drift). O tipo `decisao-posterior` aponta a tarefa que foi feita antes de uma
decisão que a afeta e foi marcada ✔ sem commit novo — sinal de que a revisão não aconteceu. Veja
[Sincronização e drift](/docs/sincronizacao-e-drift/).

## Por que assim

Uma decisão que fica só na conversa some na próxima sessão, e os agentes — que só leem o plano —
continuam trabalhando com a regra velha. Registrada, ela entra no briefing de todos os agentes da onda
seguinte, volta as tarefas afetadas para a fila e fica no histórico, riscada quando for substituída.
