---
titulo: Hooks
descricao: Os dois hooks globais do forge — o estado do plano ao abrir uma sessão, e a trava de banco e do ID de tarefa no commit.
secao: referencia
ordem: 1
---

O forge instala dois hooks no `~/.claude/settings.json`, que valem para todas as sessões do Claude
Code. Os dois são o mesmo script, `hooks/forge_hook.py`, chamado em modos diferentes.

## Instalar e remover

```bash
python ~/.claude/skills/forge/hooks/instalar.py
python ~/.claude/skills/forge/hooks/instalar.py --remover
```

O instalador é idempotente: reconhece as entradas do forge pelo caminho do `forge_hook.py`, então
rodar duas vezes não duplica nada, e as entradas de outros hooks ficam como estão. Antes de gravar,
guarda uma cópia do settings em `settings.json.bak-forge`.

## SessionStart: o estado do plano

Ao abrir uma sessão, o hook procura nos planos registrados os que interessam à pasta da sessão — a
pasta do próprio plano ou o repositório de uma das frentes — e injeta o `status` de cada um no contexto.
Assim a sessão já começa sabendo que há um projeto em andamento e em que pé ele está.

- Planos `fechado` não aparecem.
- Um plano que não dá para ler não esconde os outros: aparece uma linha com o erro.
- O texto é cortado em 6 000 caracteres; o resto se vê com [`status`](/comandos/#status).

## PreToolUse: as travas

Roda antes de cada comando de Bash ou PowerShell e pode recusá-lo.

### Banco de dados

Bloqueia os clientes de banco (`psql`, `pg_dump`, `mysql`, `sqlcmd`, `sqlite3`, `mongosh`,
`redis-cli` e outros) e as URLs de conexão (inclusive JDBC) que apontem para um banco que não é
**local** (`localhost`, `127.0.0.1` ou `::1`). Sem host no comando, o banco vale como local.

Para apertar a regra sem mexer na skill, defina no ambiente:

| Variável | Efeito |
|---|---|
| `FORGE_BANCO_PREFIXO` | Só libera bancos cujo nome começa com esse prefixo. |
| `FORGE_BANCOS_PROIBIDOS` | Nomes separados por vírgula que nunca são liberados, nem locais. |

Uma URL citada por um comando só de leitura (`grep`, `cat`, `git`, `echo`…) não é bloqueada. A regra
vale além do que o hook consegue pegar — ele é uma rede de segurança, não a regra.

### ID de tarefa no commit

Num repositório que é frente de um plano em andamento, **na branch do plano**, recusa `git commit` cuja
mensagem não comece pelo ID de uma tarefa existente. A recusa diz qual é o plano e lista as tarefas
pendentes da frente. Trabalho fora do plano vira tarefa antes, com [`tarefa`](/comandos/#tarefa).

O hook lê a mensagem de `-m`/`--message`, de um heredoc ou de uma here-string do PowerShell. Commit com
`-F arquivo`, pelo editor ou com `--no-edit` não é conferido aqui — o [drift](/docs/sincronizacao-e-drift/)
pega depois. Fora da branch do plano, ou num repositório que não é frente de nenhum plano, o commit
passa sem conferência.

```text
[forge] commit recusado: este repositório é a frente A do plano forge 'exemplo' (branch exemplo),
e a mensagem precisa começar pelo ID de uma tarefa do plano (ex.: `A1: ...`). ...
```

## Quando o hook falha

Qualquer erro inesperado dentro do hook **libera** a ação: um hook quebrado não pode travar o
trabalho. Por isso as regras continuam valendo mesmo quando o hook não pega o comando.
