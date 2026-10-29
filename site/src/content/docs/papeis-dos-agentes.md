---
titulo: Papéis dos agentes
descricao: Executor, revisor de contrato, revisor de padrões e testador — o que cada um faz, o que pode tocar e o que devolve.
secao: conceitos
ordem: 4
---

Numa onda, cada tarefa passa por até quatro papéis: os da **equipe** dela. Cada agente recebe um
**briefing** próprio, gerado do plano a partir de um modelo da skill (`references/briefing-<papel>.md`),
com a parte do plano de que o papel precisa: a tarefa, o que foi apurado na frente, os contratos da
frente, as decisões em vigor, as regras e as restrições. Como o briefing já traz tudo isso, o agente
**não abre o plano** para reler essas partes; só abre se algo faltar, e diz o que faltou.

| Papel | O que faz | Escreve código? |
|---|---|---|
| **Executor** | Faz a tarefa, testa e commita com o ID na mensagem. | sim |
| **Revisor de contrato** | Adversarial: procura onde a mudança contraria uma decisão, quebra um contrato ou outra frente. | não |
| **Revisor de padrões** | Padrões do repositório e simplicidade; sempre procura uma forma mais simples, reutilizável ou genérica de fazer o mesmo. | não |
| **Testador** | Independente: confere o *como testar*, escreve o teste que falta e roda. Não corrige código de produção. | só testes |

Nenhum deles edita o plano. Quem muda o plano é a sessão principal, ao integrar.

## A equipe de cada tarefa

Não se usa uma bazuca para matar uma barata: trocar uma função de somar dois números não pede dois
revisores e um testador; mexer no fluxo de pagamento pede o time todo. O executor roda sempre; os
outros papéis, conforme a complexidade da tarefa:

| Complexidade | Equipe |
|---|---|
| `baixa` | Executor |
| `media` | Executor, revisor de contrato e testador |
| `alta` | Executor, revisor de contrato, revisor de padrões e testador |

`agentes.equipes` no JSON muda esse padrão no plano todo. Quando a importância da tarefa destoa da
dificuldade, a equipe se escolhe na própria tarefa, com [`equipe`](/comandos/#equipe) ou
`tarefa --equipe`: `solo`, `completa` ou os papéis separados por vírgula. A seção 7 do plano mostra a
equipe de cada tarefa.

## FCP: como os agentes se falam

Toda mensagem de um agente segue o **FCP** (Forge Compact Protocol, `references/fcp.md`): um JSON
pequeno, com o mesmo envelope para todos, que leva só o que o próximo precisa.

```json
{
  "id": "A3",
  "status": "ok",
  "commits": ["a1b2c3d"],
  "tests": [{ "cmd": "pytest -q", "result": "pass" }],
  "blockers": [],
  "notes": []
}
```

Os revisores acrescentam `findings` (cada um com `sev`, `kind`, `at`, `msg` e `fix`); o revisor de
padrões, também `sources` e `generalization`. O workflow não repassa a mensagem inteira: os revisores
e o testador recebem do executor só `id`, `commits`, `tests` e `notes`, e a correção recebe só os
achados `block`. Quem vem depois lê o diff pelos commits.

## Executor

Trabalha na branch da frente, sem sair do repositório. Antes de escrever, lê os padrões do repositório
e procura o que já existe para reaproveitar; as decisões, o apurado e os contratos já vêm no briefing.
Faz **só a tarefa** — o que achar de errado no caminho vai para as notas, não para o código. Quando a
equipe da tarefa é só ele, o briefing avisa: o teste dele é a única prova. Commita com a
mensagem começando pelo ID (`A3: ...`); um [hook](/docs/hooks/) recusa o commit sem ele.

Devolve um de três `status`:

| Status | Quando |
|---|---|
| `ok` | Feito, testado e commitado. |
| `contract` | O contrato não fecha com o código real. Para e põe em `blockers` o que o contrato diz, o que o código exige e uma proposta. |
| `blocked` | Falta algo que só o dono tem: credencial, decisão, acesso. |

Com os commits, os testes rodados e notas curtas para quem vem depois.

## Revisor de contrato

O viés é **adversarial**: parte do princípio de que a mudança quebra alguma coisa fora dela e tenta
provar. Lê o diff de cada commit, não só o resumo do executor, e procura em cinco lugares: o contrato
(campo a mais, a menos, com outro nome ou tipo), as decisões, as outras frentes (quem consome e quem
produz), o próprio texto do contrato e se o "como provar" foi de fato provado.

Quando o código está certo e o contrato é que está errado ou ambíguo, o achado tem o `kind`
`contrato-errado`. O briefing traz os repositórios das frentes do outro lado dos contratos, para ele ler
o lado de lá.

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

| `sev` | Significa |
|---|---|
| `block` | Não pode entrar assim: quebra contrato, decisão ou outra frente, viola um padrão escrito ou obriga a refazer outra tarefa. |
| `major` | Risco real, duplicação ou complexidade sem motivo, mas não quebra nada hoje. |
| `minor` | O resto. |

Achado `block` de qualquer um dos dois provoca **uma** rodada de correção: o executor volta e corrige
só esses achados, em commit novo com o mesmo ID. Se discordar de um achado, não corrige — explica nas
notas.

## Testador

Independente do executor: não confia no relatório, confere. Roda os testes que o executor diz ter
rodado, monta os casos a partir do "como provar" e do contrato — o caminho feliz, os limites, o erro
esperado e o que **não** pode acontecer — e escreve o teste que falta, no padrão do repositório,
commitado com o ID da tarefa.

Pode escrever e commitar testes, mas **não corrige código de produção**: defeito achado é reportado,
com o passo a passo para reproduzir. Cada caso volta em `tests` como `pass`, `fail` ou `skip` — este
último para o que precisa de banco, servidor, navegador ou aparelho, com o roteiro para o dono
executar no `cmd`.

## A sessão principal

Não é um papel da onda, mas fecha o ciclo. Ela confere os commits de cada tarefa que voltou `ok` e
marca o ✔; leva ao dono o que voltou com problema; transforma achados aceitos em tarefa ou decisão; e
registra a rodada. Veja [Tarefas e ondas](/docs/tarefas-e-ondas/).
