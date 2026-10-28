"""Testes de borda do fluxo.json (contrato 1.3): variações do SKILL.md e da tabela de papéis do forge.py.

    python -m unittest discover -s site/scripts        (da raiz da skill)
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import extrair

MINIMO = """# forge

## Peças

antes da primeira fase

## Antes de tudo

*Transversal antes da primeira fase.*

Corpo da transversal.

## Fase 0 — Começo

*Resumo da fase zero.*

Primeiro parágrafo da fase zero, fora do resumo.

## Fase 1 — Aprovação (parada obrigatória)
*Resumo colado no título, com `forge fase` e **negrito**.*

1. Primeiro item da lista.

## Notas soltas

*Texto da transversal com [link](x.md).*

## Fase 2 — Fim

*Resumo do fim.*

Apresenta:

- um
- dois

## Regras que não se negociam

depois da última fase

## Hooks (instalados em `~/.claude/settings.json`)

referência

## Depois de tudo

*Transversal depois da última fase.*
"""

# As seções de referência que todo SKILL.md precisa ter (D13: faltar uma é erro de geração)
REFERENCIAS = """
## Peças

p

## Regras que não se negociam

r

## Hooks (instalados em `~/.claude/settings.json`)

h
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp.name)
        # gerar_fluxo importa o forge.py: o registro real de planos nunca pode ser tocado
        self.env = mock.patch.dict(os.environ, {"FORGE_REGISTRO": str(self.pasta / "registro")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def skill(self, texto, nome="SKILL.md", newline="\n"):
        caminho = self.pasta / nome
        with open(caminho, "w", encoding="utf-8", newline=newline) as f:
            f.write(texto)
        return caminho

    def fluxo(self, texto):
        """O fluxo de um SKILL.md com o texto dado mais as seções de referência."""
        return extrair.gerar_fluxo(skill_md=self.skill(texto + REFERENCIAS))


class TestSkillMdSintetico(Base):
    def setUp(self):
        super().setUp()
        self.dados = extrair.gerar_fluxo(skill_md=self.skill(MINIMO))

    def test_fases_na_ordem_e_parada_so_na_aprovacao(self):
        self.assertEqual([(f["id"], f["n"], f["titulo"], f["parada"]) for f in self.dados["fases"]], [
            ("fase-0", 0, "Começo", False),
            ("fase-1", 1, "Aprovação (parada obrigatória)", True),
            ("fase-2", 2, "Fim", False),
        ])

    def test_resumo_e_a_linha_em_italico_sem_o_italico(self):
        # D13: só a linha em itálico logo abaixo do título; o resto do corpo fica fora
        self.assertEqual([f["resumo"] for f in self.dados["fases"]],
                         ["Resumo da fase zero.", "Resumo colado no título, com forge fase e negrito.",
                          "Resumo do fim."])

    def test_transversal_em_qualquer_posicao_menos_as_de_referencia(self):
        self.assertEqual(self.dados["transversais"], [
            {"id": "antes", "titulo": "Antes de tudo", "resumo": "Transversal antes da primeira fase."},
            {"id": "notas", "titulo": "Notas soltas", "resumo": "Texto da transversal com link."},
            {"id": "depois", "titulo": "Depois de tudo", "resumo": "Transversal depois da última fase."},
        ])

    def test_onda_nao_depende_do_skill_md(self):
        self.assertEqual(self.dados["onda"], extrair.gerar_fluxo()["onda"])


class TestBordasSkillMd(Base):
    def test_crlf_gera_o_mesmo_json(self):
        real = extrair.SKILL_MD.read_text(encoding="utf-8")
        self.assertEqual(extrair.gerar_fluxo(skill_md=self.skill(real, newline="\r\n")), extrair.gerar_fluxo())

    def test_geracao_e_deterministica(self):
        self.assertEqual(extrair.gerar_fluxo(), extrair.gerar_fluxo())

    def test_fase_com_dois_digitos_e_titulo_com_markdown(self):
        dados = self.fluxo("## Fase 10 — Rodar `forge md` **já**\n\n*texto*\n")
        self.assertEqual(dados["fases"], [
            {"id": "fase-10", "n": 10, "titulo": "Rodar forge md já", "resumo": "texto", "parada": False}])
        self.assertEqual(dados["transversais"], [])

    def test_fase_sem_corpo_quebra(self):
        with self.assertRaisesRegex(RuntimeError, "Fase 0 — A.*resumo em itálico"):
            self.fluxo("## Fase 0 — A\n\n## Fase 1 — B\n\n*b*\n")

    def test_fase_sem_a_linha_em_italico_quebra(self):
        for corpo in ("Parágrafo comum.", "**Negrito, não itálico.**", "_Itálico com sublinhado._",
                      "*Itálico que continua\nna linha de baixo.*", "*Itálico* seguido de texto.",
                      "- *item de lista em itálico*", "Texto antes.\n\n*Itálico depois.*", "* *", "*Um* e *outro*"):
            with self.subTest(corpo=corpo), self.assertRaisesRegex(RuntimeError, "resumo em itálico"):
                self.fluxo(f"## Fase 0 — A\n\n{corpo}\n")

    def test_transversal_sem_a_linha_em_italico_quebra(self):
        with self.assertRaisesRegex(RuntimeError, "Notas soltas.*resumo em itálico"):
            self.fluxo("## Fase 0 — A\n\n*a*\n\n## Notas soltas\n\nx\n")

    def test_linha_em_italico_com_espacos_em_volta_vale(self):
        dados = self.fluxo("## Fase 0 — A\n\n   *Resumo.*   \n\nx\n")
        self.assertEqual(dados["fases"][0]["resumo"], "Resumo.")

    def test_secao_de_referencia_renomeada_quebra(self):
        for velho, novo in (("## Peças", "## Peças do forge"), ("## Regras que não se negociam", "## Regras"),
                            ("## Hooks (instalados em `~/.claude/settings.json`)", "## Hooks")):
            with self.subTest(novo=novo), self.assertRaisesRegex(RuntimeError, "referência não encontrada"):
                extrair.gerar_fluxo(skill_md=self.skill("## Fase 0 — A\n\n*a*\n" + REFERENCIAS.replace(velho, novo)))

    def test_skill_md_real_com_referencia_renomeada_quebra(self):
        real = extrair.SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("\n## Peças\n", real)
        with self.assertRaisesRegex(RuntimeError, "referência não encontrada.*Peças"):
            extrair.gerar_fluxo(skill_md=self.skill(real.replace("\n## Peças\n", "\n## Peças e comandos\n")))

    def test_subtitulo_de_fase_nao_vira_fase(self):
        dados = self.fluxo("## Fase 0 — A\n\n*a*\n\n### Fase 5 — sub\n\nx\n")
        self.assertEqual([f["n"] for f in dados["fases"]], [0])

    def test_secao_de_referencia_e_pelo_titulo_inteiro(self):
        dados = self.fluxo("## Fase 0 — A\n\n*a*\n\n## Regras do jogo\n\n*r*\n")
        self.assertEqual(dados["transversais"], [{"id": "regras", "titulo": "Regras do jogo", "resumo": "r"}])

    def test_id_pula_o_que_nao_e_letra_nem_numero(self):
        self.assertEqual(extrair.ident("— Notas soltas"), "notas")
        with self.assertRaisesRegex(RuntimeError, "título sem letra"):
            self.fluxo("## Fase 0 — A\n\n*a*\n\n## —\n\n*x*\n")

    def test_transversal_com_id_repetido_quebra(self):
        with self.assertRaisesRegex(RuntimeError, "repetido.*'notas'"):
            self.fluxo("## Fase 0 — A\n\n*a*\n\n## Notas um\n\n*x*\n\n## Notas dois\n\n*y*\n")

    def test_fase_repetida_quebra(self):
        with self.assertRaisesRegex(RuntimeError, "fase-0"):
            self.fluxo("## Fase 0 — A\n\n*a*\n\n## Fase 0 — B\n\n*b*\n")

    def test_resumo_longo_corta_na_ultima_frase_que_cabe(self):
        frase = "Uma frase de exatamente cinquenta caracteres, ok. "
        self.assertEqual(len(frase), 50)
        dados = self.fluxo("## Fase 0 — A\n\n*" + (frase * 10).strip() + "*\n")
        resumo = dados["fases"][0]["resumo"]
        self.assertEqual(resumo, (frase * 6).strip())
        self.assertLessEqual(len(resumo), extrair.MAX_RESUMO)

    def test_resumo_longo_sem_frase_corta_na_palavra_com_reticencias(self):
        resumo = extrair.limitar("palavra " * 60)
        self.assertLessEqual(len(resumo), extrair.MAX_RESUMO)
        self.assertTrue(resumo.endswith("palavra…"), resumo)
        self.assertEqual(extrair.limitar("curto."), "curto.")

    def test_caminho_local_de_arquivo_da_skill_vira_relativo(self):
        texto = r"rode `C:/Users/X/.claude/skills/forge/references/workflow-onda.js` ou C:\a\scripts\forge.py"
        dados = self.fluxo(f"## Fase 0 — A\n\n*{texto}.*\n")
        self.assertEqual(dados["fases"][0]["resumo"], "rode references/workflow-onda.js ou scripts/forge.py.")
        self.assertEqual(extrair.sem_caminhos_locais("em /home/runner/work/forge/forge/SKILL.md"), "em SKILL.md")

    def test_caminho_local_fora_da_skill_quebra(self):
        with self.assertRaisesRegex(RuntimeError, "caminho local"):
            self.fluxo("## Fase 0 — A\n\n*veja C:/Users/X/segredo.txt*\n")

    def test_caminho_relativo_e_til_ficam(self):
        self.assertEqual(extrair.sem_caminhos_locais("references/x.md e ~/.claude/settings.json"),
                         "references/x.md e ~/.claude/settings.json")

    def test_skill_md_vazio_quebra(self):
        with self.assertRaises(RuntimeError):
            extrair.gerar_fluxo(skill_md=self.skill(""))

    def test_skill_md_inexistente_quebra(self):
        with self.assertRaises(FileNotFoundError):
            extrair.gerar_fluxo(skill_md=self.pasta / "nao-existe.md")


class TestBordasPapeis(Base):
    def forge(self, trocar, por):
        texto = extrair.FORGE_PY.read_text(encoding="utf-8")
        self.assertIn(trocar, texto)
        caminho = self.pasta / "forge.py"
        caminho.write_text(texto.replace(trocar, por, 1), encoding="utf-8")
        return caminho

    def test_papel_usado_numa_etapa_sem_estar_no_PAPEIS_quebra(self):
        copia = self.forge('    "testador": {', '    "verificador": {')
        with self.assertRaisesRegex(RuntimeError, "papel desconhecido"):
            extrair.gerar_fluxo(forge_py=copia)

    def test_escreve_codigo_fora_do_dominio_quebra(self):
        copia = self.forge('"escreve_codigo": "só testes"', '"escreve_codigo": "talvez"')
        with self.assertRaisesRegex(ValueError, "escreve_codigo"):
            extrair.gerar_fluxo(forge_py=copia)

    def test_texto_do_papel_vem_do_forge_py_em_texto_puro(self):
        copia = self.forge('"faz": "Faz a tarefa, testa', '"faz": "Faz a `tarefa`, **testa**')
        papel = extrair.gerar_fluxo(forge_py=copia)["onda"]["papeis"][0]
        self.assertEqual(papel["faz"], "Faz a tarefa, testa e commita com o ID na mensagem.")

    def test_papel_novo_no_PAPEIS_aparece_no_fluxo(self):
        copia = self.forge('    "testador": {', '    "auditor": {"nome": "Auditor", "faz": "Audita.", '
                                                  '"escreve_codigo": "não"},\n    "testador": {')
        papeis = extrair.gerar_fluxo(forge_py=copia)["onda"]["papeis"]
        self.assertEqual([p["id"] for p in papeis][-2:], ["auditor", "testador"])


if __name__ == "__main__":
    unittest.main()
