# FCP — Forge Compact Protocol

O formato das mensagens entre os agentes de uma onda e deles para a sessão principal. Não é uma
linguagem secreta: é um JSON pequeno, sempre com o mesmo envelope, que leva **só o que o próximo
agente precisa**. Prosa longa, repetição do briefing e explicação do diff ficam de fora: quem vem
depois lê o diff pelos commits.

## Envelope (todo papel devolve)

```json
{
  "id": "A3",
  "status": "ok",
  "commits": ["a1b2c3d4e5f6..."],
  "tests": [{ "cmd": "pytest -q tests/test_soma.py", "result": "pass" }],
  "blockers": [],
  "notes": ["soma() aceita Decimal; atenção ao arredondamento em total()"]
}
```

| Campo | Regra |
|---|---|
| `id` | O ID da tarefa. |
| `status` | `ok` (cumpriu o papel), `fail` (revisão ou teste reprovou), `blocked` (falta algo que só o dono tem), `contract` (o contrato não fecha com o código). |
| `commits` | SHAs completos dos commits **deste** agente. Vazio para os revisores. |
| `tests` | O que foi rodado: `cmd` (comando exato), `result` (`pass`, `fail` ou `skip`) e, no testador, `case` (o caso). `skip` é o que não dá para rodar aqui; o `cmd` leva o roteiro para o dono. |
| `blockers` | O que impede seguir e não é achado de código: o problema de contrato (o que ele diz, o que o código exige, a proposta), a credencial ou decisão que falta. Uma frase por item. |
| `notes` | Frases curtas, no máximo 5: o que mudou (em uma linha), onde o próximo deve olhar com atenção, o que viu de errado fora da tarefa (com o prefixo `fora:`). |

## Campos dos revisores

| Campo | Regra |
|---|---|
| `findings` | `{ "sev", "kind", "at", "msg", "fix" }`. `sev`: `block` (não pode entrar assim), `major` (risco real, duplicação) ou `minor` (o resto). `at`: `arquivo:linha`. `msg`: o problema em uma frase. `fix`: a proposta em uma frase. |
| `sources` | Só o revisor de padrões: as fontes de padrão que encontrou. |
| `generalization` | Só o revisor de padrões: a resposta às quatro perguntas (já existe? dá com menos? dá para generalizar? ficou genérico demais?), em até 3 frases. |

`status` do revisor: `fail` se houver qualquer `block`; senão `ok`.

## O que passa de um agente para o outro

O workflow (`workflow-onda.js`) não repassa a mensagem inteira — repassa o mínimo, sem campos vazios:

| Para | Recebe |
|---|---|
| Revisores | Do executor: `id`, `commits`, `tests`, `notes`. |
| Executor, na correção | Só os `findings` com `sev: "block"`. |
| Testador | Do executor e da correção: `commits`, `tests`, `notes`. |
| Sessão principal | O `status` da tarefa (`ok`, `fail`, `blocked`, `contract`), a equipe que rodou e a mensagem de cada papel. |
