---
titulo: Papéis dos agentes
descricao: Executor, revisor de contrato, revisor de padrões e testador — o que cada um faz, o que pode tocar e o que devolve.
secao: conceitos
ordem: 4
---

Numa onda, cada tarefa passa por quatro papéis. Cada agente recebe um **briefing** próprio, gerado do
plano a partir de um modelo da skill (`references/briefing-<papel>.md`), com a tarefa, os contratos da
frente, as decisões em vigor, as regras e as restrições da frente.

| Papel | O que faz | Escreve código? |
|---|---|---|
| **Executor** | Faz a tarefa, testa e commita com o ID na mensagem. | sim |
| **Revisor de contrato** | Adversarial: procura onde a mudança contraria uma decisão, quebra um contrato ou outra frente. | não |
| **Revisor de padrões** | Padrões do repositório e simplicidade; sempre procura uma forma mais simples, reutilizável ou genérica de fazer o mesmo. | não |
| **Testador** | Independente: confere o *como testar*, escreve o teste que falta e roda. Não corrige código de produção. | só testes |

Nenhum deles edita o plano. Quem muda o plano é a sessão principal, ao integrar.

## Executor

Trabalha na branch da frente, sem sair do repositório. Antes de escrever, lê os padrões do repositório
e as seções de decisões, apurado e contratos do plano, e procura o que já existe para reaproveitar. Faz
**só a tarefa** — o que achar de errado no caminho vai para as notas, não para o código. Commita com a
mensagem começando pelo ID (`A3: ...`); um [hook](/docs/hooks/) recusa o commit sem ele.

Devolve um de três estados:

| Estado | Quando |
|---|---|
| `pronto` | Feito, testado e commitado. |
| `contrato` | O contrato não fecha com o código real. Para e explica o que o contrato diz, o que o código exige e uma proposta. |
| `travou` | Falta algo que só o dono tem: credencial, decisão, acesso. |

Com os commits, um resumo, os testes rodados e as notas para os revisores.

## Revisor de contrato

O viés é **adversarial**: parte do princípio de que a mudança quebra alguma coisa fora dela e tenta
provar. Lê o diff de cada commit, não só o resumo do executor, e procura em cinco lugares: o contrato
(campo a mais, a menos, com outro nome ou tipo), as decisões, as outras frentes (quem consome e quem
produz), o próprio texto do contrato e se o "como provar" foi de fato provado.

Quando o código está certo e o contrato é que está errado ou ambíguo, o achado tem o tipo
`contrato-errado`.

## Revisor de padrões

Primeiro descobre quais são os padrões **deste** repositório, sem supor nenhum: instruções do projeto
(`CLAUDE.md`, `AGENTS.md`…), documentação, regras de lint e formatação, skills de padrões da stack e,
sem nada escrito, o que o código vizinho já faz. Padrão escrito é obrigatório; padrão só observado é
recomendado.

Depois, em toda revisão, responde quatro perguntas sobre generalização: isso **já existe** no
repositório? Dá para fazer **com menos**? Dá para **fugir do específico** e resolver a família de
casos? Ou ficou **genérico demais**, com abstração sem segundo uso?

## Severidade dos achados

Os dois revisores classificam cada achado do mesmo jeito:

| Severidade | Significa |
|---|---|
| `bloqueante` | Não pode entrar assim: quebra contrato, decisão ou outra frente, viola um padrão escrito ou obriga a refazer outra tarefa. |
| `importante` | Risco real, duplicação ou complexidade sem motivo, mas não quebra nada hoje. |
| `sugestao` | O resto. |

Achado bloqueante de qualquer um dos dois provoca **uma** rodada de correção: o executor volta e corrige
só esses achados, em commit novo com o mesmo ID. Se discordar de um achado, não corrige — explica nas
notas.

## Testador

Independente do executor: não confia no relatório, confere. Roda os testes que o executor diz ter
rodado, monta os casos a partir do "como provar" e do contrato — o caminho feliz, os limites, o erro
esperado e o que **não** pode acontecer — e escreve o teste que falta, no padrão do repositório,
commitado com o ID da tarefa.

Pode escrever e commitar testes, mas **não corrige código de produção**: defeito achado é reportado,
com o passo a passo para reproduzir. Cada caso volta como `passou`, `falhou` ou `nao-executado` — este
último para o que precisa de banco, servidor, navegador ou aparelho, com o roteiro para o dono
executar.

## A sessão principal

Não é um papel da onda, mas fecha o ciclo. Ela confere os commits de cada tarefa que voltou `pronto` e
marca o ✔; leva ao dono o que voltou com problema; transforma achados aceitos em tarefa ou decisão; e
registra a rodada. Veja [Tarefas e ondas](/docs/tarefas-e-ondas/).
