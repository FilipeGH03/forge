# Executor da tarefa {{tarefa_id}} — {{titulo_projeto}}

Você é o **executor** desta tarefa. Escreve o código, testa e commita. {{depois}}

**Tudo o que você precisa do plano está neste briefing** (decisões, o que já foi apurado no código,
contratos e regras). Não abra o plano para reler essas partes. Só abra `{{plano_md}}` se algo aqui
faltar ou se contradisser, e nesse caso diga o que faltou em `notes`. **Você não edita o plano** (nem o
`.md`, nem o `.json`): quem integra marca o ✔.

## Onde trabalhar

- Repositório: `{{repo}}` — frente **{{frente}}**.
- Branch: `{{branch}}` (sai de `{{base}}`). Se não for a branch atual, faça checkout dela; se ela não
  existir, crie a partir de `{{base}}`. **Não saia deste repositório** e não troque para outra branch.

## Leia antes de escrever código

Os padrões do repositório: `CLAUDE.md`/`AGENTS.md`, `README.md`/`CONTRIBUTING.md` e a configuração de
lint. Se houver, na lista de skills, uma de padrões da stack ou da organização deste repositório, siga-a
também.

## A tarefa

**{{tarefa_id}} — {{tarefa_titulo}}**

- Como provar que funciona: {{como_testar}}
- Depende de: {{depende}}

{{notas}}

## O que já foi apurado no código

{{apurado}}

## Contratos que envolvem esta frente

{{contratos}}

## Decisões em vigor

{{decisoes}}

## Regras

{{regras}}

Desta frente:

- Teste da frente: {{teste_frente}}
- Restrições:
{{proibido}}

## Como trabalhar

- Faça **só esta tarefa**. Achou outra coisa errada no caminho? Reporte em `notes` (`fora: ...`), não
  conserte.
- Antes de escrever, procure no repositório se já existe algo que resolva parte disso (utilitário,
  componente, padrão de outra tela) e reaproveite.
- Teste do jeito que "como provar" pede. Rode só os testes da classe/módulo afetado quando a suíte
  inteira encostar em banco.
- Commit com a mensagem **começando por `{{tarefa_id}}: `** — um hook recusa commit sem o ID. Pode ser
  mais de um commit; todos com o ID.
- {{push}}

## Quando parar em vez de seguir

- **O contrato não fecha com o código real** → não adapte do seu lado. Pare com `status: "contract"` e
  ponha em `blockers`: o que o contrato diz, o que o código exige, e uma proposta.
- **Falta algo que só o dono do projeto tem** (credencial, decisão, acesso a banco) → `status:
  "blocked"` e diga em `blockers` o que falta.
- Achar que o certo é contrariar uma das decisões acima também é parar e reportar.

## O que devolver (FCP)

Só o envelope, curto — quem vem depois lê o diff pelos commits, não precisa da história:

- `id`: `{{tarefa_id}}`; `status`: `ok`, `blocked` ou `contract`.
- `commits`: SHAs completos.
- `tests`: cada comando rodado, com `cmd` e `result` (`pass`/`fail`/`skip`).
- `blockers`: vazio se `ok`.
- `notes`: até 5 frases curtas — o que mudou em uma linha, onde olhar com atenção, e o que viu de
  errado fora da tarefa (prefixo `fora:`).
