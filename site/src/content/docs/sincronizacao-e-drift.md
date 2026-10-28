---
titulo: Sincronização e drift
descricao: Ao fim de cada onda, plano e código contam a mesma história — o drift aponta cada divergência, e cada uma se resolve, não se ignora.
secao: fluxo
ordem: 3
---

O plano diz o que foi feito; o `git log` diz o que de fato foi commitado. O comando
[`drift`](/comandos/#drift) compara os dois e lista cada divergência. Ele sai com código 1 quando acha
alguma, então serve também num script.

Quando o plano e o repositório discordam, **o repositório tem razão** — e é o plano que se corrige.

## Onde o forge procura

Em cada frente, o forge lê os commits da branch do plano que ainda não estão na base (sem os de merge)
e tira o ID de tarefa do começo de cada mensagem. Frentes que dividem um repositório leem o mesmo
`git log`, e cada commit conta uma vez só.

## As divergências

| Tipo | O que quer dizer | Como resolver |
|---|---|---|
| `repo` | O repositório de uma frente não existe. | Corrija o `repo` da frente no JSON. |
| `branch` | A branch do plano não existe no repositório, e o plano já está em execução (ou a frente já tem tarefa feita). | Crie a branch ou corrija o `branch` do plano ou da frente. |
| `sem-tarefa` | Um commit da branch não começa por nenhum ID de tarefa. | Trabalho fora do plano vira tarefa antes; o commit é refeito ou explicado. |
| `tarefa-inexistente` | Um commit cita um ID que não está no plano. | Crie a tarefa ou corrija a mensagem. |
| `feito-sem-commit` | A tarefa está ✔, mas nenhum commit cita o ID dela. | Ache o commit (`marcar --commit`) ou volte a tarefa (`marcar --pendente`). |
| `commit-sem-feito` | A tarefa tem commit, mas está ☐. | [`marcar`](/comandos/#marcar) a tarefa. |
| `decisao-posterior` | A tarefa foi feita antes de uma decisão que a afeta. | Revise (`marcar --revisar`) e mande para a próxima onda. |
| `md-editado` | O Markdown do plano foi editado à mão. | Passe a mudança para o JSON e rode [`md`](/comandos/#md). |
| `md-ausente` | O Markdown do plano não existe. | Rode [`md`](/comandos/#md). |

O [`status`](/comandos/#status) também avisa, numa linha, quantas divergências há, e mostra quando uma
tarefa ainda não marcada já tem commit ("já tem commit — marcar?").

## Ao fim de cada onda

Antes de encerrar a sessão:

1. **O drift precisa sair limpo.** Commit sem ID, ✔ sem commit, commit sem ✔, decisão posterior a uma
   tarefa feita, Markdown editado à mão — cada um se resolve, não se ignora.
2. **README e CLAUDE.md dos repositórios tocados.** Se uma tarefa mudou como rodar, configurar ou subir
   o projeto, atualizar isso é uma tarefa (ou parte dela) — não fica só no plano.
3. **Decisão que mudou** é uma decisão nova com `--revoga D<n>`; a antiga nunca é apagada.
4. **Plano terminado:** [`fase fechado`](/comandos/#fase). O hook para de mostrá-lo ao abrir uma
   sessão.

## Ao retomar

No começo de uma sessão (a fase 0), o forge roda [`status`](/comandos/#status) e
[`drift`](/comandos/#drift) e mostra em poucas linhas onde o trabalho parou. Divergência se resolve
**antes** de qualquer onda.

[`branches`](/comandos/#branches) completa o quadro: em cada repositório, quanto a branch de trabalho
está à frente ou atrás da base, se já foi publicada e quantos arquivos estão alterados na árvore.
