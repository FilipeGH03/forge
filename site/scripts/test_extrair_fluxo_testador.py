"""Testes do testador da A2 (contrato 1.3): limites do resumo, caminhos locais e a parada.

    python -m unittest discover -s site/scripts        (da raiz da skill)
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import extrair


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"FORGE_REGISTRO": str(self.pasta / "registro")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def fluxo(self, texto):
        caminho = self.pasta / "SKILL.md"
        caminho.write_text(texto, encoding="utf-8", newline="\n")
        return extrair.gerar_fluxo(skill_md=caminho)


class TestLimite(unittest.TestCase):
    def test_texto_com_300_caracteres_fica_inteiro(self):
        texto = "a" * 299 + "."
        self.assertEqual(extrair.limitar(texto), texto)

    def test_texto_com_301_caracteres_e_cortado(self):
        self.assertLessEqual(len(extrair.limitar("a " * 150 + "b")), 300)

    def test_frase_que_termina_exatamente_no_caractere_300_cabe(self):
        frase1, frase2 = "a" * 100 + ".", " " + "b" * 197 + "."
        texto = frase1 + frase2 + " Mais uma frase depois."
        self.assertEqual(len(frase1 + frase2), 300)
        self.assertEqual(extrair.limitar(texto), frase1 + frase2)

    def test_resumo_vazio_fica_vazio(self):
        self.assertEqual(extrair.limitar(""), "")


class TestCaminhoLocal(unittest.TestCase):
    def assertSemCaminho(self, caminho):
        try:
            saida = extrair.sem_caminhos_locais(f"veja {caminho} aqui")
        except RuntimeError:
            return  # erro de geração também atende: o caminho não chega ao JSON
        self.assertNotIn(caminho, saida)

    def test_caminho_windows_com_barra_invertida(self):
        self.assertSemCaminho(r"C:\Users\DEV\projeto\x.txt")

    def test_caminho_do_git_bash(self):
        # formato de caminho que o Git Bash do Windows mostra: /c/Users/<usuário>/...
        self.assertSemCaminho("/c/Users/DEV/projeto/x.txt")

    def test_caminho_da_skill_em_barra_invertida_vira_relativo(self):
        absoluto = str(extrair.RAIZ_SKILL / "references" / "workflow-onda.js")
        self.assertEqual(extrair.sem_caminhos_locais(f"veja {absoluto}."), "veja references/workflow-onda.js.")


class TestParada(Base):
    def test_parada_so_na_aprovacao_mesmo_com_parada_em_outro_titulo(self):
        dados = self.fluxo("## Fase 0 — Execução (sem parada)\n\n*Texto.*\n\n"
                           "## Fase 1 — Aprovação (parada obrigatória)\n\n*Texto.*\n\n"
                           "## Peças\n\np\n\n## Regras que não se negociam\n\nr\n\n"
                           "## Hooks (instalados em `~/.claude/settings.json`)\n\nh\n")
        self.assertEqual([f["parada"] for f in dados["fases"]], [False, True])


class TestSkillMdReal(Base):
    def test_nenhum_resumo_passa_de_300_nem_fica_vazio(self):
        dados = extrair.gerar_fluxo()
        for item in dados["fases"] + dados["transversais"]:
            self.assertTrue(0 < len(item["resumo"]) <= 300, item["id"])

    def test_ids_unicos_e_transversais_esperadas(self):
        dados = extrair.gerar_fluxo()
        ids = [i["id"] for i in dados["fases"] + dados["transversais"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual([t["id"] for t in dados["transversais"]], ["decisoes"])

    def test_papeis_na_ordem_e_dominio(self):
        papeis = extrair.gerar_fluxo()["onda"]["papeis"]
        self.assertEqual([(p["id"], p["escreve_codigo"]) for p in papeis], [
            ("executor", "sim"), ("revisor-contrato", "não"), ("revisor-padroes", "não"), ("testador", "só testes")])
        for p in papeis:
            self.assertNotIn("*", p["faz"])


if __name__ == "__main__":
    unittest.main()
