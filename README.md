# forge

Skill do [Claude Code](https://claude.com/claude-code) para tocar um projeto que atravessa mais de um
repositório (ou mais de uma área de um repositório) com agentes trabalhando em paralelo. Você chama
`/forge`, e ele conduz o projeto do levantamento dos requisitos até o fechamento, com um **plano de
trabalho vivo** como fonte da verdade.

**Documentação:** https://filipegh03.github.io/forge/

## O problema

Projeto tocado por agentes costuma se perder de três jeitos:

- **A conversa vira a fonte da verdade.** O que foi decidido fica espalhado no chat, e a próxima sessão
  não sabe.
- **Cada agente inventa o seu lado do contrato.** Se ninguém escreveu o formato do que passa entre duas
  partes, cada lado supõe um, e o erro só aparece na integração.
- **O plano e o código se separam.** Tarefa marcada como feita sem commit, commit que não é de tarefa
  nenhuma, decisão que mudou depois que a tarefa estava pronta.

## A ideia

1. **Um documento vivo é a fonte da verdade.** O estado mora num JSON (`forge-<slug>.json`); o Markdown
   que as pessoas leem é gerado dele a cada alteração.
2. **O trabalho anda em frentes amarradas por contratos.** Cada frente é um repositório, e tudo o que
   atravessa frentes é escrito antes, com exemplo.
3. **Cada tarefa é pequena e se prova sozinha**, com um "como testar", dependências explícitas e o ID
   dela no commit.
4. **Agentes executam, a sessão principal integra.** Cada tarefa passa por um executor, dois revisores
   (contrato e padrões) e um testador, com o modelo de cada um escolhido pela complexidade da tarefa.

O fluxo para numa fase só: **nenhum agente roda antes de o dono aprovar o plano**. Depois disso, toda
mudança de rumo vira uma decisão registrada, e o `drift` confere o plano contra os commits de cada
repositório.

## Instalação

Precisa de Claude Code, git e Python 3 (no Windows, com o Git Bash).

```bash
git clone https://github.com/FilipeGH03/forge.git ~/.claude/skills/forge
python ~/.claude/skills/forge/hooks/instalar.py
```

Os hooks mostram o estado do plano ao abrir uma sessão na pasta do projeto, recusam commit sem ID de
tarefa nas branches do plano e bloqueiam clientes de banco de dados (`psql`, `mysql`, URLs JDBC...) fora
da regra em `hooks/forge_hook.py` — hoje, só banco local cujo nome começa com `torge_`. Para tirar:
`python ~/.claude/skills/forge/hooks/instalar.py --remover`.

## Uso

Numa sessão do Claude Code, na pasta onde o plano vai morar:

```text
/forge quero uma rota GET /saude no serviço X, com teste
```

O passo a passo completo, com as saídas reais, está no
[início rápido](https://filipegh03.github.io/forge/docs/inicio-rapido/). Todos os comandos do
`scripts/forge.py` estão na [referência de comandos](https://filipegh03.github.io/forge/comandos/).

## O que tem aqui

| Pasta | Conteúdo |
|---|---|
| `SKILL.md` | As instruções da skill: as fases, as regras e os comandos. |
| `scripts/forge.py` | Todos os comandos sobre o plano (criar, tarefas, decisões, status, drift, ondas...). |
| `references/` | O workflow que executa uma onda, os briefings dos quatro papéis e o formato do JSON. |
| `hooks/` | Os hooks globais e o instalador. |
| `site/` | O site de documentação (Astro, publicado no GitHub Pages) — ele mesmo feito com o forge. |
