---
titulo: Regras
descricao: As regras que não se negociam e as regras do jogo que todo plano traz — para a sessão principal e para os agentes.
secao: referencia
ordem: 2
---

## As que não se negociam

Valem em todo projeto forge, para a sessão principal e para os agentes:

- **Banco:** nunca conectar nem executar SQL, exceto banco local (`localhost`/`127.0.0.1`) cujo nome
  começa com `torge_`; **nunca** `autenticacao`, `producao01` ou `desenvolvimento`. O
  [hook](/docs/hooks/) bloqueia os clientes de banco, mas a regra vale além do que ele pega.
- **O plano só muda pelo `forge.py`** (ou editando o JSON e rodando [`md`](/comandos/#md)), e só pela
  sessão principal.
- **Contrato não se muda de um lado só.** Aprovação do plano não autoriza mudar contrato depois.
- **Nada de lançar agentes antes da aprovação** da fase 4.

## As regras do jogo

Todo plano novo nasce com estas regras, que aparecem na seção 2 do documento e no briefing de cada
agente:

1. Contrato não se muda de um lado só. Quem esbarrar num problema com um contrato **para e reporta** —
   não adapta do seu lado.
2. Uma tarefa faz uma coisa só, termina e é testada sozinha. Quando depende de outra, a dependência
   está escrita nela.
3. Um commit por tarefa (ou mais, nunca menos), com a mensagem começando pelo ID: `A3: ...`.
4. Só a sessão principal altera o plano, e sempre pelo `forge.py`. Agentes reportam; quem integra marca
   o ✔.
5. Se o repositório e o plano discordarem, o repositório tem razão — corrija o plano.
6. Decisão nova é linha nova. As antigas não são apagadas: são revogadas e viram histórico.
7. Nada de conectar em banco nem executar SQL, exceto banco local `torge_*`. Migration e DAO se
   escrevem e se revisam; quem roda é o dono do projeto.
8. Restrição escrita no plano envelhece: confira com um teste de um minuto antes de repassar para um
   agente.

As regras ficam no campo `regras` do JSON. Um projeto pode acrescentar as suas — veja
[Formato do JSON](/docs/formato-do-json/).

## Por que cada uma existe

| Regra | O que ela evita |
|---|---|
| Contrato de um lado só | Uma frente que adapta em silêncio quebra as outras, e o erro só aparece na integração. |
| Uma coisa por tarefa | Tarefa grande não se testa sozinha, e a revisão não tem por onde começar. |
| ID no commit | Sem ele, ligar código a plano vira trabalho manual — e o [drift](/docs/sincronizacao-e-drift/) não tem como conferir. |
| Só a sessão principal muda o plano | O ✔ só entra depois de alguém conferir os commits; agente que marca o próprio trabalho dispensa a conferência. |
| O repositório tem razão | O commit é o que sobrevive; o plano é a descrição dele. |
| Decisão nova é linha nova | Sem o histórico, ninguém sabe por que uma tarefa feita voltou. |
| Restrição envelhece | Uma restrição que já não existia fez duas frentes trabalharem uma noite inteira à toa, no projeto de onde o método saiu. |

## Restrições de cada frente

Além das regras do plano, cada frente tem as suas, no campo `proibido`: "a suíte inteira encosta em
banco: rode por classe", "não mexe na pasta da outra frente". Elas entram no briefing de cada agente
daquela frente, junto com o jeito de testar a frente. Veja
[Frentes e contratos](/docs/frentes-e-contratos/).
