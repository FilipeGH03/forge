"""Testes do fluxo.json (contrato 1.3) gerado pelo extrair.py a partir do SKILL.md.

    python -m unittest discover -s site/scripts        (da raiz da skill)
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

import extrair

TITULOS = re.compile(r"^## Fase (\d+) — (.+)$", re.M)


class TestFluxo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = extrair.SKILL_MD.read_text(encoding="utf-8")
        cls.dados = extrair.gerar_fluxo()

    def test_formato_estrito(self):
        self.assertEqual(set(self.dados), {"fases", "transversais", "onda"})
        for f in self.dados["fases"]:
            self.assertEqual(set(f), {"id", "n", "titulo", "resumo", "parada"})
            self.assertIsInstance(f["n"], int)
            self.assertIsInstance(f["parada"], bool)
        for t in self.dados["transversais"]:
            self.assertEqual(set(t), {"id", "titulo", "resumo"})
        self.assertEqual(set(self.dados["onda"]), {"papeis", "etapas"})
        for p in self.dados["onda"]["papeis"]:
            self.assertEqual(set(p), {"id", "nome", "faz", "escreve_codigo"})
            self.assertIn(p["escreve_codigo"], {"sim", "não", "só testes"})
        for e in self.dados["onda"]["etapas"]:
            self.assertEqual(set(e), {"papeis", "condicional", "rotulo"})

    def test_fases_0_a_7_com_os_titulos_do_skill_md(self):
        esperado = [(int(n), t.strip()) for n, t in TITULOS.findall(self.skill)]
        self.assertEqual([n for n, _ in esperado], list(range(8)))
        self.assertEqual([(f["n"], f["titulo"]) for f in self.dados["fases"]], esperado)
        self.assertEqual([f["id"] for f in self.dados["fases"]], [f"fase-{n}" for n in range(8)])

    def test_parada_so_na_fase_4(self):
        self.assertEqual([f["n"] for f in self.dados["fases"] if f["parada"]], [4])
        self.assertEqual(self.dados["fases"][4]["titulo"], "Aprovação (parada obrigatória)")

    def test_resumos_em_texto_puro(self):
        itens = self.dados["fases"] + self.dados["transversais"]
        for item in itens + self.dados["onda"]["papeis"]:
            for campo in ("resumo", "faz"):
                if campo in item:
                    texto = item[campo]
                    self.assertTrue(texto.strip(), item)
                    self.assertNotRegex(texto, r"`|\*|\]\(|\n|^\d+\. |^- ", item)

    def test_resumo_e_a_linha_em_italico_abaixo_do_titulo(self):
        """D13: cada fase e transversal tem, logo abaixo do título no SKILL.md, uma linha em itálico; o resumo
        é ela, sem os asteriscos."""
        italicos = dict(re.findall(r"^## (.+)\n\n\*(.+)\*$", self.skill, re.M))
        for item in self.dados["fases"]:
            self.assertEqual(item["resumo"], italicos[f"Fase {item['n']} — {item['titulo']}"])
        self.assertEqual(self.dados["transversais"][0]["resumo"], italicos["Decisões no meio do projeto"])

    def test_resumo_da_fase_4_diz_que_o_fluxo_para(self):
        self.assertIn("para", self.dados["fases"][4]["resumo"])
        self.assertIn("aprovar", self.dados["fases"][4]["resumo"])

    def test_decisoes_no_meio_do_projeto(self):
        self.assertEqual([(t["id"], t["titulo"]) for t in self.dados["transversais"]],
                         [("decisoes", "Decisões no meio do projeto")])

    def test_resumos_com_ate_300_caracteres_e_sem_caminho_local(self):
        for item in self.dados["fases"] + self.dados["transversais"]:
            self.assertLessEqual(len(item["resumo"]), extrair.MAX_RESUMO, item["id"])
            self.assertNotRegex(item["resumo"], extrair.CAMINHO_LOCAL, item["id"])
            self.assertNotRegex(item["resumo"], r"[A-Za-z]:[\\/]|/Users/|/home/", item["id"])

    def test_secoes_de_referencia_nao_viram_transversal(self):
        titulos = [t for t, _ in extrair.secoes(self.skill)]
        self.assertTrue(any(t.startswith("Peças") for t in titulos))
        self.assertTrue(any(t.startswith("Regras") for t in titulos))
        self.assertTrue(any(t.startswith("Hooks") for t in titulos))
        self.assertTrue(extrair.REFERENCIA <= {extrair.texto_puro(t) for t in titulos})
        self.assertFalse({t["titulo"] for t in self.dados["transversais"]} & extrair.REFERENCIA)

    def test_papeis_vem_do_PAPEIS_do_forge_py(self):
        forge = extrair.carregar_forge()
        self.assertEqual([(p["id"], p["nome"], p["escreve_codigo"]) for p in self.dados["onda"]["papeis"]],
                         [(i, p["nome"], p["escreve_codigo"]) for i, p in forge.PAPEIS.items()])

    def test_etapas_na_ordem_do_workflow_onda(self):
        """A constante ETAPAS confere com o references/workflow-onda.js: ordem das chamadas de agente,
        quem roda em paralelo e quem só roda sob condição."""
        js = (extrair.RAIZ_SKILL / "references" / "workflow-onda.js").read_text(encoding="utf-8")
        corpo = js[js.index("async function rodarTarefa"):]
        chamadas = [(m.start(), m.group(1).replace("_", "-")) for m in re.finditer(r"ler\(b\.(\w+)\)", corpo)]
        etapas = extrair.ETAPAS
        self.assertEqual([p for _, p in chamadas], [p for e in etapas for p in e["papeis"]])

        paralelo = re.search(r"parallel\(\[.*?\n  \]\)", corpo, re.S)
        condicional = re.search(r"\n  if \([^)]*\) \{.*?\n  \}", corpo, re.S)
        self.assertIsNotNone(paralelo)
        self.assertIsNotNone(condicional)
        dentro = lambda bloco: [p for pos, p in chamadas if bloco.start() <= pos < bloco.end()]
        self.assertEqual(dentro(paralelo), [p for e in etapas if len(e["papeis"]) > 1 for p in e["papeis"]])
        self.assertEqual(dentro(condicional), [p for e in etapas if e["condicional"] for p in e["papeis"]])

    def test_etapas_devolvidas_sao_copia(self):
        dados = extrair.gerar_fluxo()
        dados["onda"]["etapas"][0]["papeis"].append("x")
        self.assertEqual(extrair.ETAPAS[0]["papeis"], ["executor"])

    def test_papeis_e_etapas(self):
        papeis = self.dados["onda"]["papeis"]
        self.assertEqual([p["id"] for p in papeis], list(extrair.carregar_forge().PAPEIS))
        self.assertEqual([p["escreve_codigo"] for p in papeis], ["sim", "não", "não", "só testes"])
        self.assertEqual(papeis[0]["nome"], "Executor")
        self.assertEqual(self.dados["onda"]["etapas"], [
            {"papeis": ["executor"], "condicional": False, "rotulo": None},
            {"papeis": ["revisor-contrato", "revisor-padroes"], "condicional": False, "rotulo": "em paralelo"},
            {"papeis": ["executor"], "condicional": True, "rotulo": "correção, se houver bloqueante"},
            {"papeis": ["testador"], "condicional": False, "rotulo": None},
        ])

    def test_mudar_um_titulo_numa_copia_muda_o_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            copia = Path(tmp) / "SKILL.md"
            copia.write_text(self.skill.replace("## Fase 2 — Levantamento", "## Fase 2 — Leitura do código"),
                             encoding="utf-8")
            outro = extrair.gerar_fluxo(skill_md=copia)
        self.assertNotEqual(outro, self.dados)
        self.assertEqual(outro["fases"][2]["titulo"], "Leitura do código")
        self.assertEqual(outro["fases"][:2], self.dados["fases"][:2])

    def test_secao_de_fase_dentro_de_bloco_de_codigo_e_ignorada(self):
        with tempfile.TemporaryDirectory() as tmp:
            copia = Path(tmp) / "SKILL.md"
            copia.write_text(self.skill.replace("## Fase 3 —", "```md\n## Fase 9 — falsa\n```\n\n## Fase 3 —", 1),
                             encoding="utf-8")
            outro = extrair.gerar_fluxo(skill_md=copia)
        self.assertEqual([f["n"] for f in outro["fases"]], list(range(8)))

    def test_tirar_a_linha_de_resumo_de_uma_fase_quebra(self):
        alvo = re.search(r"^(## Fase 3 — .+\n\n)\*.+\*\n\n", self.skill, re.M)
        with tempfile.TemporaryDirectory() as tmp:
            copia = Path(tmp) / "SKILL.md"
            copia.write_text(self.skill.replace(alvo.group(0), alvo.group(1)), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Fase 3 — .*resumo em itálico"):
                extrair.gerar_fluxo(skill_md=copia)

    def test_skill_md_sem_fases_quebra(self):
        with tempfile.TemporaryDirectory() as tmp:
            copia = Path(tmp) / "SKILL.md"
            copia.write_text("# forge\n\n## Peças\n\ntexto\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                extrair.gerar_fluxo(skill_md=copia)

    def test_texto_puro(self):
        self.assertEqual(extrair.texto_puro("Rode `forge lista` e **pare**: [doc](x.md), *como testar*."),
                         "Rode forge lista e pare: doc, como testar.")
        self.assertEqual(extrair.texto_puro("um  \n dois"), "um dois")

    def test_arquivo_commitado_bate_com_a_geracao(self):
        commitado = extrair.DESTINO_FLUXO.read_text(encoding="utf-8")
        self.assertEqual(commitado, json.dumps(self.dados, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
