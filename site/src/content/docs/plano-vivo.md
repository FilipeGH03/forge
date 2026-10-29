---
titulo: Plano vivo (JSON → Markdown)
descricao: O estado do projeto mora num JSON que só o forge.py grava; o Markdown que as pessoas leem é gerado dele e nunca se edita à mão.
secao: conceitos
ordem: 2
---

O plano de um projeto forge são dois arquivos lado a lado, na pasta do projeto e **fora** dos
repositórios:

| Arquivo | O que é |
|---|---|
| `forge-<slug>.json` | O estado: requisitos, frentes, decisões, contratos, tarefas, rodadas. É o que se edita. |
| `forge-<slug>.md` | O documento do projeto, **gerado** do JSON a cada gravação. É o que se lê. |

Ficar fora dos repositórios é de propósito: o plano é de todas as frentes, não de uma delas.

## Por que JSON e Markdown

O JSON é fácil de validar e de alterar por comando; o Markdown é fácil de ler e de mandar para
alguém. Cada um faz o que faz bem, e um nunca diverge do outro, porque o Markdown é sempre
reescrito a partir do JSON.

Toda gravação pelo `forge.py` segue o mesmo caminho:

1. **Valida** o plano inteiro. Plano inválido não é gravado — o comando para e lista os problemas.
2. **Carimba** a data em `atualizado`.
3. **Gera** o Markdown e guarda um hash dele em `md_sha`.
4. **Grava** o JSON e o Markdown.

O hash é como o forge descobre que alguém editou o Markdown à mão: na próxima conferência, o
[drift](/docs/sincronizacao-e-drift/) acusa `md-editado`. A edição não se perde em silêncio, mas também
não vale: passe a mudança para o JSON e rode [`md`](/comandos/#md).

## Como se altera

- **Pelos comandos**, sempre que existir um: [`tarefa`](/comandos/#tarefa),
  [`decisao`](/comandos/#decisao), [`duvida`](/comandos/#duvida), [`responder`](/comandos/#responder),
  [`marcar`](/comandos/#marcar), [`fase`](/comandos/#fase), [`rodada`](/comandos/#rodada),
  [`dono`](/comandos/#dono).
- **Editando o JSON**, para o que não tem comando: objetivo, requisitos, frentes, o que foi apurado,
  contratos e regras. Depois, rode [`md`](/comandos/#md), que valida e regenera. O formato está em
  [Formato do JSON](/docs/formato-do-json/).
- **Só a sessão principal** altera o plano. Os agentes leem e reportam; quem integra marca o ✔.

## O que o documento traz

O Markdown gerado tem sempre as mesmas seções, na mesma ordem — quem já leu um plano forge acha o que
procura em qualquer outro:

| Seção | Conteúdo |
|---|---|
| 0. Estado atual | Fase, data, dono, branch, tarefas feitas por frente, próximas desbloqueadas, dúvidas e pendências. Começa por aqui. |
| 1. Objetivo e requisitos | O objetivo e os requisitos R1, R2… com a fonte de cada um. |
| 2. Como vamos trabalhar | As frentes (repositório, stack, como testar, restrições) e as regras do jogo. |
| 3. Decisões já tomadas | D1, D2…; as revogadas aparecem riscadas, nunca apagadas. |
| 4. O que foi apurado no código | Fatos lidos nos repositórios, por área. |
| 5. Dúvidas | Q1, Q2…, a resposta e a decisão em que viraram. |
| 6. Contratos entre as frentes | Cada contrato, com as frentes envolvidas e as decisões que o alteraram. |
| 7. Tarefas | Por frente: estado, como testar, dependências e commits. |
| 8. Ordem e dependências | As ondas calculadas a partir das dependências. |
| 9. Tocar o trabalho com agentes | Os quatro papéis, a equipe e os modelos por complexidade, se os agentes dão push e as lições das rodadas. |
| 10. Rodadas | O registro de cada onda fechada. |
| 11. O que fica com o dono | O que só o dono pode fazer. |

## As fases do plano

O campo `fase` anda nesta ordem, pelo comando [`fase`](/comandos/#fase):

```text
requisitos → aguardando-aprovacao → aprovado → em-execucao → fechado
```

Duas travas: um plano sem tarefas não pode ir para `aprovado` nem para `em-execucao`, e o comando
[`onda`](/comandos/#onda) só roda com o plano `aprovado` ou `em-execucao`. Um plano `fechado` deixa de
aparecer quando se abre uma sessão.

## O registro de planos

Ao ser criado com [`novo`](/comandos/#novo), o plano entra num registro global
(`~/.claude/forge/registro.json`). É por ele que os [hooks](/docs/hooks/) acham o plano que interessa à
pasta da sessão, e que [`lista`](/comandos/#lista) mostra todos. Um plano criado de outro jeito entra
com [`registrar`](/comandos/#registrar).

A variável de ambiente `FORGE_REGISTRO` troca o caminho do registro — é o jeito de experimentar
comandos numa pasta temporária sem sujar o registro de verdade.

## Retomar numa sessão nova

Agente não sobrevive à troca de sessão; o que sobrevive é o commit e o ✔. Para retomar, chame `/forge`
(ou rode [`status`](/comandos/#status) e [`drift`](/comandos/#drift)). O que vale é o que está
commitado nas branches: se o plano discordar do `git log`, o repositório tem razão, e é o plano que se
corrige.
