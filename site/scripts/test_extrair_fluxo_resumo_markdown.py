"""Testes do testador da A2 (contrato 1.3): limite do resumo, o saneador de caminhos pega os formatos do
contrato (inclusive caminho dentro de URL file:///) e uma cópia do SKILL.md muda o JSON. Os testes do resumo
tirado de Markdown arbitrário (D12) saíram com a D13: o resumo agora é a linha em itálico escrita no SKILL.md.

    python -m unittest discover -s site/scripts        (da raiz da skill)
"""
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import extrair


class TestLimiteSemFrase(unittest.TestCase):
    def test_palavra_unica_maior_que_300_corta_em_300_com_reticencias(self):
        saida = extrair.limitar("a" * 400)
        self.assertEqual(len(saida), 300)
        self.assertTrue(saida.endswith("…"))

    def test_frase_que_passa_de_300_por_um_caractere_nao_entra(self):
        frase1, frase2 = "a" * 100 + ".", " " + "b" * 198 + "."
        self.assertEqual(len(frase1 + frase2), 301)
        self.assertEqual(extrair.limitar(frase1 + frase2), frase1)


class TestCaminhosDoContrato(unittest.TestCase):
    """Caminho local nunca chega ao JSON: ou vira relativo à skill, ou é erro de geração."""

    def assertQuebra(self, texto):
        with self.assertRaises(RuntimeError):
            extrair.sem_caminhos_locais(texto)

    def test_users_do_mac_quebra(self):
        self.assertQuebra("veja /Users/joao/projeto/x.txt")

    def test_outra_unidade_windows_quebra(self):
        self.assertQuebra(r"veja D:\dados\x.txt")

    def test_unidade_minuscula_quebra(self):
        self.assertQuebra("veja c:/dados/x.txt")

    def test_caminho_entre_parenteses_quebra(self):
        self.assertQuebra("(C:/dados/x.txt)")

    def test_url_de_arquivo_quebra(self):
        self.assertQuebra("file:///C:/dados/x.txt")

    def test_url_til_e_barras_de_texto_ficam(self):
        for texto in ("https://github.com/a/b", "~/.claude/settings.json", "e/ou", "fases 4/5", "<pasta>/a/b"):
            self.assertEqual(extrair.sem_caminhos_locais(texto), texto)

    def test_caminho_da_skill_com_c_minusculo_do_git_bash_vira_relativo(self):
        posix = extrair.RAIZ_SKILL.as_posix()
        if not posix[1:3] == ":/":
            self.skipTest("só no Windows")
        bash = f"/{posix[0].lower()}{posix[2:]}/SKILL.md"
        self.assertEqual(extrair.sem_caminhos_locais(f"veja {bash}."), "veja SKILL.md.")


class TestCopiaDoSkillMd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"FORGE_REGISTRO": str(self.pasta / "registro")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def gerar(self, texto):
        caminho = self.pasta / "SKILL.md"
        caminho.write_text(texto, encoding="utf-8", newline="\n")
        return extrair.gerar_fluxo(skill_md=caminho)

    def test_mudar_o_resumo_da_fase_numa_copia_muda_o_json(self):
        original = extrair.SKILL_MD.read_text(encoding="utf-8")
        alvo = re.search(r"^## Fase 2 — Levantamento\n\n(\*.+\*)\n", original, re.M)
        self.assertIsNotNone(alvo)
        dados = self.gerar(original.replace(alvo.group(1), "*Frase nova da cópia.*", 1))
        fase2 = next(f for f in dados["fases"] if f["n"] == 2)
        self.assertEqual(fase2["resumo"], "Frase nova da cópia.")
        self.assertEqual([f["resumo"] for f in dados["fases"] if f["n"] != 2],
                         [f["resumo"] for f in extrair.gerar_fluxo()["fases"] if f["n"] != 2])

    def test_copia_identica_gera_o_mesmo_json_do_original(self):
        self.assertEqual(self.gerar(extrair.SKILL_MD.read_text(encoding="utf-8")), extrair.gerar_fluxo())

    def test_secao_nova_no_fim_vira_transversal(self):
        original = extrair.SKILL_MD.read_text(encoding="utf-8")
        dados = self.gerar(original.rstrip("\n") + "\n\n## Glossário\n\n*Termos do forge.*\n")
        self.assertEqual([t["id"] for t in dados["transversais"]], ["decisoes", "glossario"])

    def test_fases_0_a_7_em_ordem_e_uma_parada(self):
        dados = extrair.gerar_fluxo()
        self.assertEqual([f["n"] for f in dados["fases"]], list(range(8)))
        self.assertEqual([f["n"] for f in dados["fases"] if f["parada"]], [4])


if __name__ == "__main__":
    unittest.main()
