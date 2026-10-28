---
titulo: Início rápido
descricao: Instale a skill e os hooks e leve um projeto pequeno do novo ao fechado, comando a comando, com a saída real de cada passo.
secao: comece
ordem: 1
destaque: true
---

Nesta página você instala o forge e conduz um projeto de verdade, pequeno, do primeiro comando ao
plano fechado. No dia a dia quem roda os comandos é a sessão do Claude Code, quando você chama
`/forge`. Aqui você roda cada um à mão, para ver o que ele faz e o que devolve. As saídas abaixo são
reais; os caminhos aparecem abreviados com `~` e os SHAs dos commits mudam de uma máquina para outra.

## Antes de começar

- O **Claude Code** instalado.
- **git** e **Python 3**, este chamado de `python` no terminal: é assim que a skill e os hooks o
  chamam.
- Um terminal **bash**. No Windows, o Git Bash, que vem com o git.

## 1. Instale a skill

O Claude Code acha as skills em `~/.claude/skills/<nome>/`. Clone o repositório do forge ali:

```bash
git clone https://github.com/FilipeGH03/forge.git ~/.claude/skills/forge
```

Pronto: numa sessão nova do Claude Code, `/forge` já aparece. Para atualizar depois, um `git pull`
nessa pasta basta.

## 2. Instale os hooks

Os hooks são opcionais, mas são eles que mostram o estado do plano ao abrir uma sessão e que recusam
um commit sem o ID da tarefa. O instalador os grava no seu `~/.claude/settings.json`, sem mexer nos
hooks que já estão lá:

```bash
python ~/.claude/skills/forge/hooks/instalar.py
```

```text
instalados os hooks do forge em ~/.claude/settings.json
```

Rodar de novo não duplica nada, e `--remover` tira só as entradas do forge. O que cada hook faz está
em [Hooks](/docs/hooks/).

## 3. Um projeto pequeno, do novo ao fechado

O projeto de exemplo é uma API que ganha uma rota `GET /saude`, para o balanceador saber se ela está
de pé. São uma frente (o repositório da API) e duas tarefas: a rota e o teste dela.

Os planos que você cria entram no registro de planos (`~/.claude/forge/registro.json`), que é onde os
hooks e o comando `lista` os procuram. Para treinar sem misturar com os seus planos, aponte a variável
`FORGE_REGISTRO` para outro arquivo antes de começar. Nesse caso, os hooks do Claude Code não veem o
plano de treino.

### O repositório

Uma API mínima, num repositório git com a branch base `main`:

```bash
mkdir -p ~/projetos/api && cd ~/projetos/api
git init -q -b main
echo "# API" > README.md
git add README.md && git commit -q -m "estado inicial"
```

### Requisitos: o plano nasce

O plano mora **fora** dos repositórios, na pasta do projeto. O comando
[`novo`](/comandos/#novo) cria o JSON e o Markdown, registra o plano e devolve o caminho dele:

```bash
cd ~/projetos
python ~/.claude/skills/forge/scripts/forge.py novo saude --titulo "Rota de saúde" --dono voce@exemplo.com --dir . --base main
```

```text
~/projetos/forge-saude.json
```

O plano começa na fase `requisitos`. A branch de trabalho, quando não se passa `--branch`, é o
próprio slug: `saude`.

### Objetivo, requisitos e frentes

O que não tem comando entra editando o JSON, como descreve o [formato do JSON](/docs/formato-do-json/).
Abra o `forge-saude.json` e preencha estes três campos. Em `repo`, use o caminho absoluto do seu
`~/projetos/api` (no Windows, com a letra do disco e barras normais):

```json
{
  "objetivo": "Uma rota GET /saude para o balanceador saber se a API está de pé.",
  "requisitos": [
    { "id": "R1", "texto": "GET /saude devolve 200, sem login.", "fonte": "você, hoje" }
  ],
  "frentes": [
    {
      "id": "A",
      "nome": "API",
      "repo": "/Users/voce/projetos/api",
      "stack": "Python",
      "como_testar": "python -m unittest",
      "proibido": []
    }
  ]
}
```

Depois de editar, o [`md`](/comandos/#md) valida o JSON e gera de novo o documento do projeto. Um
plano inválido não é gravado.

```bash
python ~/.claude/skills/forge/scripts/forge.py md forge-saude.json
```

```text
gerado: forge-saude.md
```

Abra o `forge-saude.md`: é o documento que o dono do projeto lê e aprova. Veja
[Plano vivo](/docs/plano-vivo/).

### Proposta: as tarefas

Cada tarefa diz como provar que funciona sozinha, e a segunda depende da primeira. O
[`tarefa`](/comandos/#tarefa) dá o próximo ID da frente:

```bash
python ~/.claude/skills/forge/scripts/forge.py tarefa forge-saude.json --frente A --titulo "Rota GET /saude" --testar "GET /saude devolve 200"
python ~/.claude/skills/forge/scripts/forge.py tarefa forge-saude.json --frente A --titulo "Teste da rota /saude" --testar "python -m unittest passa" --depende A1
python ~/.claude/skills/forge/scripts/forge.py validar forge-saude.json
```

```text
A1
A2
ok
```

### Aprovação

Com o `/forge`, o fluxo **para aqui** até o dono aprovar o plano: nenhum agente é lançado e nenhum
código é escrito antes disso. O [`fase`](/comandos/#fase) registra cada passo:

```bash
python ~/.claude/skills/forge/scripts/forge.py fase forge-saude.json aguardando-aprovacao
python ~/.claude/skills/forge/scripts/forge.py fase forge-saude.json aprovado
python ~/.claude/skills/forge/scripts/forge.py lista
```

```text
fase: aguardando-aprovacao
fase: aprovado
aprovado               0/2  ~/projetos/forge-saude.json
```

A [`lista`](/comandos/#lista) mostra todos os planos do registro. Se você já tiver outros, eles
aparecem junto.

### Execução

Com o `/forge`, é aqui que o [`onda`](/comandos/#onda) escolhe as tarefas desbloqueadas e cada uma
passa pelos quatro agentes (veja [Tarefas e ondas](/docs/tarefas-e-ondas/)). No exemplo, quem executa
é você: entre na branch do plano e faça a A1, com o ID da tarefa no começo da mensagem do commit.

```bash
python ~/.claude/skills/forge/scripts/forge.py fase forge-saude.json em-execucao
cd ~/projetos/api
git checkout -q -b saude
cat > saude.py <<'EOF'
def saude():
    return 200, "ok"
EOF
git add saude.py && git commit -q -m "A1: rota GET /saude"
```

Dentro do Claude Code, o hook de commit não deixaria passar uma mensagem sem o ID. Dá para ver a
recusa sem abrir uma sessão, entregando ao hook o comando como o Claude Code entregaria:

```bash
echo '{"tool_input": {"command": "git commit -m \"ajuste na rota\""}, "cwd": "."}' | python ~/.claude/skills/forge/hooks/forge_hook.py pre-tool
```

```text
[forge] commit recusado: este repositório é a frente A do plano forge 'saude' (branch saude), e a mensagem precisa começar pelo ID de uma tarefa do plano (ex.: `A1: ...`). Pendentes desta frente: A1, A2. Trabalho fora do plano vira tarefa antes (`forge.py tarefa`).
```

O commit da A1 está na branch, mas o plano ainda não sabe que ela está feita. O
[`status`](/comandos/#status) acha o commit pelo ID e avisa; o [`drift`](/comandos/#drift) aponta a
divergência e sai com código 1:

```bash
cd ~/projetos
python ~/.claude/skills/forge/scripts/forge.py status forge-saude.json
python ~/.claude/skills/forge/scripts/forge.py drift forge-saude.json
```

```text
forge-saude.json — Rota de saúde · fase em-execucao · atualizado 2026-10-27
Tarefas: 0/2 ✔
  A · API — 0/2  [~/projetos/api @ saude]
    ☐ A1 Rota GET /saude — desbloqueada · já tem commit (2222b90b) — marcar?
    ☐ A2 Teste da rota /saude — espera A1
Próximas: A1
Drift: 1 divergência(s) — rode `drift` para ver
[commit-sem-feito] A1 tem commit (2222b90b) mas está ☐ — rode `marcar A1`
1 divergência(s)
```

### Integração

Só a sessão principal marca uma tarefa como feita, depois de conferir o commit. O
[`marcar`](/comandos/#marcar) acha os commits pelo ID, sem ninguém copiar SHA à mão:

```bash
python ~/.claude/skills/forge/scripts/forge.py marcar forge-saude.json A1
```

```text
✔ A1 Rota GET /saude
```

A A2 ficou desbloqueada. Faça o teste, rode e marque:

```bash
cd ~/projetos/api
cat > test_saude.py <<'EOF'
import unittest

from saude import saude


class TesteSaude(unittest.TestCase):
    def test_devolve_200(self):
        self.assertEqual(saude()[0], 200)
EOF
python -m unittest -q
git add test_saude.py && git commit -q -m "A2: teste da rota /saude"
cd ~/projetos
python ~/.claude/skills/forge/scripts/forge.py marcar forge-saude.json A2
```

```text
----------------------------------------------------------------------
Ran 1 test in 0.000s

OK
✔ A2 Teste da rota /saude
```

### Sincronização e fechamento

Antes de fechar, plano e código precisam contar a mesma história: o `drift` tem de sair limpo (veja
[Sincronização e drift](/docs/sincronizacao-e-drift/)).

```bash
python ~/.claude/skills/forge/scripts/forge.py drift forge-saude.json
python ~/.claude/skills/forge/scripts/forge.py status forge-saude.json
```

```text
sem divergências
forge-saude.json — Rota de saúde · fase em-execucao · atualizado 2026-10-27
Tarefas: 2/2 ✔
  A · API — 2/2  [~/projetos/api @ saude]
    ✔ A1 Rota GET /saude — 2222b90b
    ✔ A2 Teste da rota /saude — 979f92c3
Próximas: nenhuma
```

Tudo feito: feche o plano. Um plano `fechado` deixa de aparecer ao abrir uma sessão.

```bash
python ~/.claude/skills/forge/scripts/forge.py fase forge-saude.json fechado
python ~/.claude/skills/forge/scripts/forge.py lista
```

```text
fase: fechado
fechado                2/2  ~/projetos/forge-saude.json
```

## Com o Claude Code

O mesmo projeto, do jeito de todo dia: abra uma sessão em `~/projetos` e peça

```text
/forge uma rota GET /saude na API em ~/projetos/api, para o balanceador
```

A sessão faz as perguntas em lote, lê o código, propõe frentes, contratos e tarefas e **para** para
você aprovar. Depois roda as ondas de agentes, integra o que volta e mantém o plano em dia com os
commits.

## Para continuar

- [Visão geral](/docs/visao-geral/): o problema que o forge resolve e como as peças se encaixam.
- [Frentes e contratos](/docs/frentes-e-contratos/): quando um projeto tem mais de um repositório.
- [Decisões no meio do projeto](/docs/decisoes-no-meio-do-projeto/): o que fazer quando o escopo muda
  depois da aprovação.
- [Referência de comandos](/comandos/): todos os comandos do `forge.py`, com exemplo.
