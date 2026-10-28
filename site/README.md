# Site do forge

A documentação da skill forge: o método, a referência de cada comando do `forge.py` com a saída real, o
diagrama do fluxo e o início rápido. O site é estático, feito em [Astro](https://astro.build), e não tem
backend. É publicado em <https://filipegh03.github.io/forge/>.

## Como rodar

Você precisa do Node 22.23.4 ou mais novo e do Python 3 no `PATH` como `python`. O `prebuild` chama o
Python para gerar os dados.

Rode tudo de dentro de `site/`:

```bash
npm install          # dependências (Astro, fontes, Shiki)
npm run build        # gera os dados (prebuild) e o site em dist/
npm run preview      # serve o dist/ em http://localhost:4321/forge/
npm run dev          # servidor de desenvolvimento, que recarrega a cada mudança
```

O `npm run dev` **não** gera os dados. Se você mudou o `scripts/forge.py` ou o `SKILL.md`, rode
`npm run dados` antes.

Para conferir:

```bash
npm test                                         # testes do Node (tests/*.test.mjs)
npm run links                                    # todo link interno do dist/ existe (rode depois do build)
cd .. && python -m unittest discover -s site/scripts   # testes do Python (extrair.py e conteúdo)
```

Os testes do Node constroem o site numa cópia temporária, com o `tests/apoio.mjs`. Assim, eles nunca
mexem no `dist/`, no `src/data/` nem no `src/content/` de verdade.

## Como os dados são gerados

A referência de comandos e o diagrama do fluxo **não são escritos à mão**. O `npm run dados`
(`python scripts/extrair.py`) gera os dois a cada build, a partir dos arquivos da skill. Por isso o site
acompanha a skill sem precisar de uma tarefa de sincronização.

| Arquivo | De onde vem |
|---|---|
| `src/data/comandos.json` | O `montar_parser()` do `scripts/forge.py` traz todos os subcomandos, na ordem do argparse, com os argumentos, os obrigatórios, os `choices` e os valores padrão. Cada comando ganha um exemplo de saída real. Os exemplos rodam num plano de exemplo, numa pasta temporária, com o `FORGE_REGISTRO` apontando para dentro dela, então o seu registro de planos nunca é tocado. A data é fixa (2026-01-15) e os caminhos locais saem como `forge-exemplo.json` e `<pasta>`. Assim, o arquivo não muda de um build para outro. |
| `src/data/fluxo.json` | As fases e as seções transversais vêm do `SKILL.md`, cada uma com a frase de resumo em itálico escrita logo abaixo do título. Os papéis da onda vêm do `PAPEIS` do `forge.py`, os mesmos que montam a tabela da seção 9 de todo plano. As etapas da onda vêm da constante `ETAPAS` do `extrair.py`, que um teste confere contra o `references/workflow-onda.js`. |

O formato dos dois arquivos está nos contratos 1.2 e 1.3 do plano do site. Quando a fonte sai do
combinado, o `extrair.py` para com erro em vez de gerar um dado errado. Isso acontece, por exemplo, com
uma fase sem a frase de resumo, uma seção de referência renomeada ou um `id` repetido.

Escritos à mão:

- `src/content/docs/*.md`: as páginas da documentação. O frontmatter segue o contrato 1.1 (`titulo`,
  `descricao`, `secao`, `ordem` e `destaque`), e o build quebra quando ele sai do contrato. Os links
  internos são escritos sem o `/forge` (`/docs/<slug>/`, `/comandos/#<nome>`), porque o build põe o
  prefixo.
- `src/data/projetos.json`: a seção "Feito com forge" da página inicial.

## Onde fica cada coisa

| Caminho | O que é |
|---|---|
| `src/pages/` | A página inicial (`index.astro`), `docs/[slug].astro`, `comandos.astro` e `fluxo.astro`. |
| `src/layouts/Base.astro` | O topo, o botão de claro/escuro, a navegação lateral, a abertura em ferrugem, o sumário, a paginação e o rodapé. |
| `src/components/` | A logo das quatro fitas, a navegação, o sumário, a paginação, o rodapé e o diagrama do fluxo. |
| `src/estilos/global.css` | Todos os estilos e os tokens de cor (OKLCH), com o claro e o escuro. |
| `src/plugins/` | Os plugins do Markdown: o base nos links, as tabelas roláveis e o link direto em cada `##` e `###`. |
| `src/lib/` | A navegação por seção e ordem, o base, a linha de uso dos comandos e a geometria do diagrama. |
| `scripts/` | O `extrair.py` e os testes em Python. |
| `tests/` | Os testes do Node e o conferidor de links (`conferir-links.mjs`). |
| `.claude/skills/impeccable/` | A skill de design (impeccable 3.9.1), com o `PRODUCT.md` e o `DESIGN.md`: tudo só na máquina do dono, fora do git. Os testes que dependem deles pulam quando não estão presentes. |

## Publicação

O workflow `.github/workflows/pages.yml`, na raiz do repositório, roda a cada push na `main`. Ele passa
os testes do Node e do Python, faz o build e publica o `dist/` no GitHub Pages. No GitHub, a origem do
Pages precisa estar em **Settings > Pages > Source = GitHub Actions**.
