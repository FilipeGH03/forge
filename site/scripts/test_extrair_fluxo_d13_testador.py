"""Testes do testador para a D13 (contrato 1.3): a frase de resumo em itálico abaixo do título.

    python -m unittest discover -s site/scripts        (da raiz da skill)
"""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import extrair

RAIZ = Path(extrair.__file__).resolve().parents[2]

REFERENCIAS = """
## Peças

p

## Regras que não se negociam

r

## Hooks (instalados em `~/.claude/settings.json`)

h
"""


def skill(fases):
    return "# forge\n" + REFERENCIAS + fases


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def gerar(self, texto):
        caminho = Path(self.tmp.name) / "SKILL.md"
        caminho.write_text(texto, encoding="utf-8")
        return extrair.gerar_fluxo(caminho)


class TestSkillMdReal(unittest.TestCase):
    def test_diff_da_d13_no_skill_md_so_acrescenta_linhas_em_italico(self):
        """Restrição da D13: no SKILL.md só entram as linhas de resumo; nada do resto muda.
        Compara com a main (a base do plano), que pode evoluir a skill sem quebrar este teste."""
        r = subprocess.run(["git", "-C", str(RAIZ), "diff", "--unified=0", "main", "HEAD", "--", "SKILL.md"],
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            self.skipTest("branch main indisponível")
        linhas = [l for l in r.stdout.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        removidas = [l for l in linhas if l.startswith("-")]
        acrescidas = [l[1:] for l in linhas if l.startswith("+") and l[1:].strip()]
        self.assertEqual(removidas, [])
        self.assertEqual(len(acrescidas), 9)
        for l in acrescidas:
            self.assertRegex(l, r"^\*[^*\s].*[^*\s]\*$")

    def test_cada_fase_e_transversal_do_real_tem_a_linha_em_italico_logo_abaixo(self):
        for titulo, corpo in extrair.secoes(extrair.SKILL_MD.read_text(encoding="utf-8")):
            if extrair.texto_puro(titulo) in extrair.REFERENCIA:
                continue
            primeira = next(l.strip() for l in corpo.splitlines() if l.strip())
            self.assertTrue(extrair.RESUMO.fullmatch(primeira), titulo)

    def test_fluxo_json_commitado_e_o_que_o_script_gera(self):
        gravado = json.loads((extrair.DESTINO_FLUXO).read_text(encoding="utf-8"))
        self.assertEqual(gravado, extrair.gerar_fluxo())

    def test_resumo_do_real_e_a_frase_inteira_sem_markdown_nem_caminho(self):
        f = extrair.gerar_fluxo()
        for item in f["fases"] + f["transversais"]:
            r = item["resumo"]
            self.assertTrue(0 < len(r) <= 300, item["id"])
            self.assertNotRegex(r, r"[*`_\[\]]", item["id"])
            self.assertNotRegex(r, r"[A-Za-z]:[\\/]|/Users/|/home/|file://", item["id"])
            self.assertFalse(r.endswith("…"), f"{item['id']} foi cortado: a frase escrita deve caber")

    def test_so_a_aprovacao_para_e_o_resumo_dela_diz_que_para(self):
        fases = extrair.gerar_fluxo()["fases"]
        self.assertEqual([f["n"] for f in fases if f["parada"]], [4])
        self.assertIn("para", fases[4]["resumo"])


class TestLinhaEmItalico(Base):
    def test_linha_vazia_entre_titulo_e_italico_vale(self):
        f = self.gerar(skill("## Fase 0 — A\n\n\n   \n*Frase.*\n"))
        self.assertEqual(f["fases"][0]["resumo"], "Frase.")

    def test_so_a_primeira_linha_em_italico_entra(self):
        f = self.gerar(skill("## Fase 0 — A\n*Um.*\n*Dois.*\n"))
        self.assertEqual(f["fases"][0]["resumo"], "Um.")

    def test_negrito_e_codigo_dentro_saem_em_texto_puro(self):
        f = self.gerar(skill("## Fase 0 — A\n*Rode `forge lista` e **pare**.*\n"))
        self.assertEqual(f["fases"][0]["resumo"], "Rode forge lista e pare.")

    def test_formas_que_nao_sao_a_linha_em_italico_quebram(self):
        for linha in ("**x**", "* x*", "*x *", "*a*b*", "*x* e mais", "texto *x*", "***x***", "> *x*", "# *x*"):
            with self.subTest(linha=linha), self.assertRaisesRegex(RuntimeError, "frase de resumo"):
                self.gerar(skill(f"## Fase 0 — A\n{linha}\n"))

    def test_bloco_de_codigo_antes_da_frase_quebra(self):
        with self.assertRaisesRegex(RuntimeError, "frase de resumo"):
            self.gerar(skill("## Fase 0 — A\n```text\nx\n```\n*Frase.*\n"))

    def test_caminho_local_fora_da_skill_na_frase_quebra(self):
        with self.assertRaisesRegex(RuntimeError, "fora da skill"):
            self.gerar(skill("## Fase 0 — A\n*Veja C:/qualquer/coisa.txt.*\n"))

    def test_frase_de_300_caracteres_fica_inteira(self):
        frase = ("x" * 299) + "."
        f = self.gerar(skill(f"## Fase 0 — A\n*{frase}*\n"))
        self.assertEqual(f["fases"][0]["resumo"], frase)

    def test_italico_que_vira_texto_vazio_quebra(self):
        """Contrato 1.3: sem frase de resumo é erro de geração. Um itálico sem texto (só código vazio ou link
        sem texto) não é uma frase, e não pode virar "resumo": "" no fluxo.json."""
        for linha in ("*``*", "*[](x.md)*", "*`  `*"):
            with self.subTest(linha=linha), self.assertRaises(RuntimeError):
                self.gerar(skill(f"## Fase 0 — A\n{linha}\n"))

    def test_mudar_so_a_frase_numa_copia_muda_so_aquele_resumo(self):
        texto = extrair.SKILL_MD.read_text(encoding="utf-8")
        original = extrair.gerar_fluxo()
        frase = original["fases"][2]["resumo"]
        alvo = next(l for l in texto.splitlines() if l.startswith("*") and frase[:40] in l)
        novo = self.gerar(texto.replace(alvo, "*Frase trocada pelo testador.*"))
        self.assertEqual(novo["fases"][2]["resumo"], "Frase trocada pelo testador.")
        novo["fases"][2]["resumo"] = frase
        self.assertEqual(novo, original)


class TestReferencias(Base):
    def test_referencia_duplicada_nao_vira_transversal(self):
        f = self.gerar(skill("## Fase 0 — A\n*F.*\n\n## Peças\n\noutra\n"))
        self.assertEqual(f["transversais"], [])

    def test_referencia_com_titulo_em_markdown_diferente_mas_mesmo_texto_vale(self):
        texto = skill("## Fase 0 — A\n*F.*\n").replace("## Peças", "## **Peças**")
        self.assertEqual(self.gerar(texto)["transversais"], [])

    def test_referencia_dentro_de_bloco_de_codigo_nao_conta(self):
        texto = skill("## Fase 0 — A\n*F.*\n").replace("## Peças\n", "```md\n## Peças\n```\n")
        with self.assertRaisesRegex(RuntimeError, "referência não encontrada"):
            self.gerar(texto)


if __name__ == "__main__":
    unittest.main()
