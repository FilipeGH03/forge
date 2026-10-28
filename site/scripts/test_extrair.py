"""Testes do extrair.py (contrato 1.2) e da extração do montar_parser() no forge.py.

    python -m unittest discover -s site/scripts        (da raiz da skill)
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import extrair

REGISTRO_REAL = Path.home() / ".claude" / "forge" / "registro.json"
CAMPOS_ARGUMENTO = {"nome", "obrigatorio", "recebe_valor", "padrao", "ajuda", "valores", "multiplo"}


def impressao(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest() if caminho.exists() else None


def rodar(forge_py, args, cwd, registro):
    r = extrair.executar(args, cwd, registro, forge_py=forge_py)
    return r.returncode, r.stdout, r.stderr


class TestExtrair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registro_antes = impressao(REGISTRO_REAL)
        cls.temp_antes = set(Path(tempfile.gettempdir()).glob("forge-exemplo-*"))
        cls.parser = extrair.carregar_forge().montar_parser()
        cls.dados = extrair.gerar()
        cls.por_nome = {c["nome"]: c for c in cls.dados["comandos"]}

    def test_todos_os_subcomandos_na_ordem_do_argparse(self):
        self.assertEqual(self.dados["gerado_de"], "scripts/forge.py")
        nomes = list(extrair.subparsers(self.parser))
        self.assertIn("complexidade", nomes)
        self.assertEqual([c["nome"] for c in self.dados["comandos"]], nomes)

    def test_argumentos_iguais_ao_parser(self):
        for nome, s in extrair.subparsers(self.parser).items():
            c = self.por_nome[nome]
            acoes = [a for a in s._actions if not isinstance(a, argparse._HelpAction)]
            self.assertEqual(c["usa_plano"], acoes[0].dest == "plano" if acoes else False, nome)
            if c["usa_plano"]:
                acoes = acoes[1:]
            self.assertEqual(len(c["argumentos"]), len(acoes), nome)
            for arg, acao in zip(c["argumentos"], acoes):
                self.assertEqual(set(arg), CAMPOS_ARGUMENTO)
                self.assertIn(arg["nome"], acao.option_strings or [acao.dest])
                self.assertEqual(arg["obrigatorio"], acao.required, f"{nome} {arg['nome']}")
                self.assertEqual(arg["valores"], list(acao.choices) if acao.choices is not None else None)
                self.assertEqual(arg["multiplo"], acao.nargs in ("*", "+"))
                flag = isinstance(acao, (argparse._StoreTrueAction, argparse._StoreFalseAction))
                self.assertEqual(arg["recebe_valor"], not flag, f"{nome} {arg['nome']}")
                self.assertEqual(arg["padrao"], None if flag else acao.default, f"{nome} {arg['nome']}")

    def test_obrigatorios_e_choices_conhecidos(self):
        def arg(comando, nome):
            return next(a for a in self.por_nome[comando]["argumentos"] if a["nome"] == nome)

        self.assertFalse(self.por_nome["novo"]["usa_plano"])
        self.assertTrue(arg("novo", "slug")["obrigatorio"])
        self.assertTrue(arg("novo", "--titulo")["obrigatorio"])
        self.assertFalse(arg("novo", "--branch")["obrigatorio"])
        self.assertTrue(arg("tarefa", "--testar")["obrigatorio"])
        self.assertTrue(arg("marcar", "--commit")["multiplo"])
        self.assertEqual(arg("fase", "fase")["valores"],
                         ["requisitos", "aguardando-aprovacao", "aprovado", "em-execucao", "fechado"])
        self.assertEqual(arg("briefing", "--papel")["valores"],
                         ["executor", "revisor-contrato", "revisor-padroes", "testador"])
        self.assertIsNone(arg("status", "--sem-git")["valores"])
        # D10: flags não recebem valor e não têm padrão; o resto traz o default do argparse
        self.assertFalse(arg("status", "--sem-git")["recebe_valor"])
        self.assertIsNone(arg("status", "--sem-git")["padrao"])
        self.assertFalse(arg("marcar", "--forcar")["recebe_valor"])
        self.assertTrue(arg("novo", "slug")["recebe_valor"])
        self.assertIsNone(arg("novo", "slug")["padrao"])
        self.assertEqual(arg("novo", "--base")["padrao"], "teste")
        self.assertEqual(arg("novo", "--dir")["padrao"], ".")
        self.assertEqual(arg("briefing", "--papel")["padrao"], "executor")
        self.assertEqual(arg("onda", "--max")["padrao"], 3)
        self.assertTrue(arg("onda", "--max")["recebe_valor"])
        self.assertTrue(arg("marcar", "--commit")["recebe_valor"])
        self.assertIsNone(arg("marcar", "--commit")["padrao"])
        self.assertEqual(self.por_nome["status"]["ajuda"], "estado das tarefas, com os commits de cada uma")
        self.assertTrue(self.por_nome["status"]["usa_plano"])

    def test_exemplos_reais(self):
        for c in self.dados["comandos"]:
            e = c["exemplo"]
            self.assertIsNotNone(e, c["nome"])
            self.assertTrue(e["comando"].startswith(f"forge.py {c['nome']}"), e["comando"])
            self.assertTrue(e["saida"].strip(), c["nome"])
            self.assertNotIn("Traceback", e["saida"])
        self.assertEqual(self.por_nome["validar"]["exemplo"]["saida"], "ok")
        self.assertEqual(self.por_nome["novo"]["exemplo"]["saida"], "forge-exemplo.json")
        self.assertIn("A1", self.por_nome["status"]["exemplo"]["saida"])

    def test_nenhum_caminho_temporario(self):
        texto = json.dumps(self.dados, ensure_ascii=False)
        for pasta in (Path(tempfile.gettempdir()).resolve(), Path.home()):
            for forma in (str(pasta), pasta.as_posix(), str(pasta).replace("\\", "\\\\")):
                self.assertNotIn(forma, texto)
        self.assertNotIn("forge-exemplo-", texto)
        self.assertIn("<pasta>/repo", texto)

    def test_registro_real_intocado_e_pasta_apagada(self):
        self.assertEqual(impressao(REGISTRO_REAL), self.registro_antes)
        self.assertEqual(set(Path(tempfile.gettempdir()).glob("forge-exemplo-*")), self.temp_antes)

    def test_saida_estavel(self):
        self.assertEqual(extrair.gerar(), self.dados)

    def test_data_fixa_nos_exemplos(self):
        texto = json.dumps(self.dados, ensure_ascii=False)
        self.assertIn(f"atualizado {extrair.DATA_EXEMPLO}", texto)
        hoje = datetime.date.today().isoformat()
        if hoje != extrair.DATA_EXEMPLO:
            self.assertNotIn(hoje, texto)

    def test_executar_com_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            registro = Path(tmp) / "registro.json"
            r = extrair.executar(["novo", "d", "--titulo", "D", "--dono", "x", "--dir", "."], tmp, registro,
                                 data="2020-02-29")
            self.assertEqual(r.returncode, 0, r.stderr)
            plano = json.loads((Path(tmp) / "forge-d.json").read_text(encoding="utf-8"))
            self.assertEqual((plano["criado"], plano["atualizado"]), ("2020-02-29", "2020-02-29"))
            planos = json.loads(registro.read_text(encoding="utf-8"))["planos"]
            self.assertEqual([Path(p).name for p in planos], ["forge-d.json"])

    def test_sem_caminhos_locais_com_a_pasta_dos_exemplos(self):
        pasta = Path("C:/Temp/forge-exemplo-x") if os.name == "nt" else Path("/tmp/forge-exemplo-x")
        nativo = str(pasta)
        self.assertEqual(extrair.sem_caminhos_locais(f"{nativo}{os.sep}forge-exemplo.json", pasta),
                         "forge-exemplo.json")
        self.assertEqual(extrair.sem_caminhos_locais(f"[{nativo}{os.sep}repo @ x]", pasta), "[<pasta>/repo @ x]")
        escapado = json.dumps(f"{nativo}{os.sep}b{os.sep}c.md")
        self.assertEqual(extrair.sem_caminhos_locais(escapado, pasta), '"<pasta>/b/c.md"')


class TestForgeInalterado(unittest.TestCase):
    """O forge.py depois da extração do montar_parser() responde igual ao da branch main."""

    @classmethod
    def setUpClass(cls):
        raiz = extrair.RAIZ_SKILL
        r = subprocess.run(["git", "-C", str(raiz), "show", "main:scripts/forge.py"], capture_output=True)
        if r.returncode != 0:
            raise unittest.SkipTest("sem a branch main para comparar")
        cls.tmp = tempfile.TemporaryDirectory()
        pasta = Path(cls.tmp.name)
        (pasta / "antigo").mkdir()
        cls.antigo = pasta / "antigo" / "forge.py"
        cls.antigo.write_bytes(r.stdout)
        cls.novo = extrair.FORGE_PY
        cls.pasta, cls.registro = pasta, pasta / "registro.json"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def comparar(self, args):
        antes = rodar(self.antigo, args, self.pasta, self.registro)
        depois = rodar(self.novo, args, self.pasta, self.registro)
        self.assertEqual(depois, antes, args)
        return depois

    def test_ajuda_igual(self):
        self.assertEqual(self.comparar(["-h"])[0], 0)
        for nome in extrair.subparsers(extrair.carregar_forge().montar_parser()):
            self.comparar([nome, "-h"])
        self.comparar([])  # sem comando: erro do argparse igual

    def test_status_igual(self):
        codigo, _, erro = rodar(self.novo, ["novo", "teste", "--titulo", "T", "--dono", "d", "--dir", "."],
                                self.pasta, self.registro)
        self.assertEqual(codigo, 0, erro)
        self.assertEqual(self.comparar(["status", "forge-teste.json", "--sem-git"])[0], 0)
        self.comparar(["status", "forge-teste.json", "--json"])

    def test_md_igual(self):
        """A tabela de papéis da seção 9 sai do PAPEIS, com o mesmo texto de antes."""
        md = {}
        for nome, forge_py in (("antigo", self.antigo), ("novo", self.novo)):
            for args in (["novo", "md-" + nome, "--titulo", "T", "--dono", "d", "--dir", "."],
                         ["md", f"forge-md-{nome}.json"]):
                r = extrair.executar(args, self.pasta, self.registro, forge_py=forge_py, data=extrair.DATA_EXEMPLO)
                self.assertEqual(r.returncode, 0, r.stderr)
            md[nome] = (self.pasta / f"forge-md-{nome}.md").read_text(encoding="utf-8").replace(f"md-{nome}", "")
        self.assertIn("| **Testador** |", md["novo"])
        self.assertEqual(md["novo"], md["antigo"])


if __name__ == "__main__":
    unittest.main()
