---
titulo: Formato do JSON
descricao: Os campos do JSON do plano, para editar o que não tem comando, e as regras que o forge.py confere antes de gravar.
secao: referencia
ordem: 3
---

Edite o JSON direto só para o que não tem comando no `forge.py`: objetivo, requisitos, frentes,
apurado, contratos e regras. Depois de editar, rode [`md`](/comandos/#md): ele valida e regenera o
Markdown. Plano inválido não é gravado. Para só conferir, sem gravar nada, há o
[`validar`](/comandos/#validar).

## Exemplo

```json
{
  "forge": 1,
  "slug": "filtro-tipo",
  "titulo": "Filtro por tipo no histórico de notificações",
  "dono": "Fernando",
  "criado": "2026-10-27",
  "atualizado": "2026-10-27",
  "fase": "requisitos",
  "aprovado_em": null,
  "branch": "filtro-tipo",
  "base": "teste",
  "objetivo": "Markdown livre: o que precisa existir no fim e para quem.",
  "requisitos": [
    { "id": "R1", "texto": "Filtrar o histórico por um tipo só", "fonte": "usuário em 27/10" }
  ],
  "regras": ["... as regras padrão vêm preenchidas; acrescente as do projeto ..."],
  "frentes": [
    {
      "id": "A",
      "nome": "Serviço de Avisos",
      "repo": "C:/Projetos/avisos",
      "stack": "Java 21, Spring Boot",
      "como_testar": "mvn test -Dtest=<Classe>",
      "proibido": ["Nunca ligar -Davisos.testes.banco=true"],
      "branch": null,
      "base": null
    }
  ],
  "decisoes": [
    { "id": "D1", "data": "2026-10-27", "assunto": "Quantos tipos", "texto": "Um tipo só.", "afeta": [], "revoga": null, "contratos": [] }
  ],
  "apurado": [
    { "area": "avisos — HistoricoController", "texto": "Markdown com fatos, arquivo e linha." }
  ],
  "duvidas": [
    { "id": "Q1", "texto": "O contador respeita o filtro?", "resposta": null, "decisao": null }
  ],
  "contratos": [
    { "id": "1.1", "titulo": "GET /avisos?tipo=", "entre": ["A", "C"], "texto": "Markdown: exemplo, tabela de campos, respostas." }
  ],
  "tarefas": [
    {
      "id": "A1", "frente": "A", "titulo": "Parâmetro tipo no GET /avisos",
      "como_testar": "Teste: com tipo=CR só volta CR; tipo inválido dá 400",
      "depende": [], "estado": "pendente", "commits": [], "rodada": 1, "notas": ""
    }
  ],
  "rodadas": [
    { "n": 1, "data": "2026-10-28", "titulo": "Primeira onda", "registro": "Markdown" }
  ],
  "agentes": { "push": false, "licoes": [] },
  "pendencias_dono": [ { "texto": "Rodar X contra o banco", "feito": false, "rodada": 1 } ],
  "md_sha": "gerado pelo forge.py — não mexer"
}
```

## Os campos

| Campo | O que guarda | Muda por |
|---|---|---|
| `forge` | A versão do formato (hoje, `1`). | — |
| `slug`, `titulo`, `dono` | Identidade do plano. | [`novo`](/comandos/#novo) |
| `criado`, `atualizado` | Datas; `atualizado` é carimbada a cada gravação. | o próprio `forge.py` |
| `fase`, `aprovado_em` | A fase do plano e quando foi aprovado. | [`fase`](/comandos/#fase) |
| `branch`, `base` | A branch de trabalho em todos os repositórios e a branch de onde ela sai. | [`novo`](/comandos/#novo) |
| `objetivo` | Markdown livre: o que precisa existir no fim e para quem. | JSON |
| `requisitos` | R1, R2… com a fonte de cada um. | JSON |
| `regras` | As [regras do jogo](/docs/regras/); as padrão vêm preenchidas. | JSON |
| `frentes` | Repositório, stack, como testar, restrições e, opcionalmente, `branch`/`base` próprios. | JSON |
| `decisoes` | D1, D2…, com o que afetam, revogam e os contratos que alteram. | [`decisao`](/comandos/#decisao) |
| `apurado` | Fatos lidos no código, um por área. `frentes` (opcional) diz a quais frentes o fato interessa: o briefing de uma tarefa leva os da frente dela e os sem `frentes`. | JSON |
| `duvidas` | Q1, Q2…, a resposta e a decisão em que viraram. | [`duvida`](/comandos/#duvida), [`responder`](/comandos/#responder) |
| `contratos` | Id, título, frentes envolvidas e o texto em Markdown. | JSON |
| `tarefas` | As tarefas, com estado, dependências, commits, complexidade e, opcionalmente, a `equipe` (quem roda nela). | [`tarefa`](/comandos/#tarefa), [`marcar`](/comandos/#marcar), [`complexidade`](/comandos/#complexidade), [`equipe`](/comandos/#equipe) |
| `rodadas` | O registro de cada onda fechada. | [`rodada`](/comandos/#rodada) |
| `agentes` | Se os agentes dão `push` (padrão: não, só commit local), as lições das rodadas e, opcionais, `modelos` e `equipes` por complexidade, que sobrepõem o padrão. | JSON, [`rodada --licao`](/comandos/#rodada) |
| `pendencias_dono` | O que só o dono pode fazer. | [`dono`](/comandos/#dono), [`rodada --dono`](/comandos/#rodada) |
| `md_sha` | O hash do Markdown gerado, para o [drift](/docs/sincronizacao-e-drift/) achar edição à mão. | o próprio `forge.py` — não mexer |

## O que o `validar` confere

- `fase` é uma de: `requisitos`, `aguardando-aprovacao`, `aprovado`, `em-execucao`, `fechado`.
- **Frente:** de 1 a 3 letras maiúsculas, sem D, Q ou R, sem repetir, e com `repo`.
- **Tarefa:** o ID é a letra da frente seguida de número, sem repetir; a frente existe; o `estado` é
  `pendente`, `feito` ou `revisar`; `como_testar` é obrigatório; `depende` só aponta para IDs que
  existem, e sem ciclo; `complexidade` é `baixa`, `media` ou `alta`; a `equipe`, quando existe, só tem
  papéis conhecidos e sempre o executor.
- **Agentes:** cada equipe de `agentes.equipes` segue a mesma regra da equipe da tarefa.
- **Decisão:** `revoga`, `afeta` e `contratos` só apontam para o que existe.
- **Contrato:** `entre` só cita frentes que existem.

Quando algo falha, nada é gravado e o comando lista cada problema:

```text
forge: plano inválido, nada foi gravado:
  - tarefa A2: falta 'como_testar' — toda tarefa precisa provar que funciona sozinha
```
