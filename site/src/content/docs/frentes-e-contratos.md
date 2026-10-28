---
titulo: Frentes e contratos
descricao: Como dividir o trabalho em frentes que andam em paralelo sem se pisar, e fechar por escrito tudo o que passa de uma para outra.
secao: conceitos
ordem: 3
---

## Frentes

Uma frente é um repositório, ou uma área de um repositório que nunca encosta nos arquivos de outra.
Uma boa divisão atende três critérios:

- **Anda em paralelo** sem um pisar no outro.
- **Tem um jeito próprio de testar** — escrito no plano, em `como_testar` da frente.
- **Tem dono claro.**

Cada frente leva uma letra: A, B, C… — de uma a três letras maiúsculas. **D, Q e R são reservadas**,
porque já numeram decisões, dúvidas e requisitos; uma frente com essas letras confundiria os IDs.

O que a frente não pode fazer vai em `proibido`: "a suíte inteira encosta em banco: rode por classe",
"não mexe na pasta X, que é da outra frente". Essas restrições entram no briefing de cada agente da
frente.

Por padrão, todas as frentes trabalham na branch do plano, saindo da base do plano. Uma frente pode ter
`branch` e `base` próprios, que valem só para ela.

### Frentes no mesmo repositório

Duas frentes podem dividir um repositório, separadas por pasta. Nesse caso o forge as trata como uma
**fila só**: as tarefas delas rodam em sequência na mesma onda, nunca em paralelo, porque dividiriam a
mesma árvore de trabalho. Os commits também contam uma vez só, mesmo aparecendo no `git log` das duas.

## Contratos

Tudo o que atravessa frentes vira contrato: formato de requisição e resposta, evento, nome de rota,
tabela compartilhada, arquivo que um lado gera e o outro lê. **Sem contrato fechado, o agente decide
sozinho e erra** — e o erro só aparece na integração.

Um bom contrato tem exemplo concreto:

- um JSON de exemplo, completo;
- uma tabela de campos, com o que é obrigatório e a regra de cada um;
- os códigos de resposta, o que acontece com vazio, nulo ou fora do domínio.

No plano, cada contrato tem um `id` (como `1.1`), um título, as frentes `entre` as quais ele vale e o
texto em Markdown. O briefing de um agente traz todos os contratos que envolvem a frente dele.

### Contrato não se muda de um lado só

É a regra mais importante do forge. Quem esbarrar num problema com um contrato **para e reporta** —
não adapta do seu lado. Uma frente que adapta em silêncio quebra as outras.

Por isso o executor tem um estado próprio para isso, `contrato`, e o revisor de contrato tem um tipo de
achado próprio, `contrato-errado`: às vezes o código está certo e é o texto do contrato que não
funciona na prática. É o achado mais valioso que uma onda pode trazer.

A mudança de um contrato é uma [decisão](/docs/decisoes-no-meio-do-projeto/) e precisa do OK explícito
do dono, porque mexe em mais de uma frente. Registrada com `--contrato`, ela marca o contrato no
documento como "alterado pela D&lt;n&gt;"; o texto do contrato é editado no JSON em seguida.

```bash
forge.py decisao forge-exemplo.json --assunto "Campo tipo" \
  --texto "O campo tipo pode vir vazio." --contrato 1.1 --afeta A2 B3
```

Aprovação do plano não autoriza mudar contrato depois: cada mudança é uma decisão nova.

## Decisões e dúvidas

Na proposta (fase 3), tudo o que foi escolhido vira [`decisao`](/comandos/#decisao) e tudo o que falta
decidir vira [`duvida`](/comandos/#duvida). Uma dúvida em aberto que bloqueia uma tarefa é dita na nota
da tarefa. Quando a resposta chega, [`responder`](/comandos/#responder) a registra; se ela mudou
alguma coisa, vira decisão com `--duvida Q<n>`.
