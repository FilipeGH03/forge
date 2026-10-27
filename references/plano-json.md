# Formato do `forge-<slug>.json`

Edite o JSON direto só para o que não tem comando no `forge.py` (objetivo, requisitos, frentes,
apurado, contratos, regras). Depois de editar, rode `forge.py md <plano>`: ele valida e regenera o
Markdown. Plano inválido não é gravado.

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

Regras que o `validar` confere:

- `fase` ∈ requisitos, aguardando-aprovacao, aprovado, em-execucao, fechado.
- Frente: 1 a 3 letras maiúsculas, sem D, Q ou R, com `repo`. `branch`/`base` da frente são
  opcionais e sobrepõem os do plano.
- Tarefa: ID = letra da frente + número; `estado` ∈ pendente, feito, revisar; `como_testar`
  obrigatório; `depende` só com IDs existentes e sem ciclo.
- Decisão: `revoga`, `afeta` e `contratos` só apontam para o que existe.
- Contrato: `entre` só com frentes existentes.
