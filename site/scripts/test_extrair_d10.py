"""Testes do testador para a D10 (recebe_valor/padrao) e a data fixa dos exemplos (contrato 1.2).

    python -m unittest discover -s site/scripts        (da raiz da skill)
"""
import argparse
import json
import re
import tempfile
import unittest
from pathlib import Path

import extrair


def parser_sintetico():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="comando")
    s = sub.add_parser("um", description="com plano")
    s.add_argument("plano")
    s.add_argument("--liga", action="store_true")
    s.add_argument("--desliga", action="store_false")
    s.add_argument("--nome", default="x")
    s.add_argument("--qtd", type=int, default=0)
    s.add_argument("--lista", nargs="+")
    s.add_argument("--talvez", nargs="*", default=[])
    s.add_argument("--escondido", default=argparse.SUPPRESS)
    s.add_argument("--cor", choices=("azul", "verde"), default="azul")
    s.add_argument("alvo")
    sub.add_parser("vazio", description="sem argumentos")
    s = sub.add_parser("outro", description="primeiro posicional não é plano")
    s.add_argument("arquivo")
    s.add_argument("plano")
    return p


class TestArgumentoSintetico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cmds = {c["nome"]: c for c in extrair.comandos(parser_sintetico())}
        cls.args = {a["nome"]: a for a in cls.cmds["um"]["argumentos"]}

    def test_ordem_e_usa_plano(self):
        self.assertEqual(list(self.cmds), ["um", "vazio", "outro"])
        self.assertTrue(self.cmds["um"]["usa_plano"])
        self.assertFalse(self.cmds["vazio"]["usa_plano"])
        self.assertEqual(self.cmds["vazio"]["argumentos"], [])
        self.assertFalse(self.cmds["outro"]["usa_plano"])
        self.assertEqual([a["nome"] for a in self.cmds["outro"]["argumentos"]], ["arquivo", "plano"])
        self.assertNotIn("plano", self.args)
        self.assertEqual(self.cmds["um"]["ajuda"], "com plano")

    def test_ordem_das_chaves_do_contrato(self):
        self.assertEqual(list(self.args["--liga"]),
                         ["nome", "obrigatorio", "recebe_valor", "padrao", "ajuda", "valores", "multiplo"])

    def test_flags(self):
        for nome in ("--liga", "--desliga"):
            self.assertFalse(self.args[nome]["recebe_valor"], nome)
            self.assertIsNone(self.args[nome]["padrao"], nome)  # store_false tem default True: vira null

    def test_padroes(self):
        self.assertEqual(self.args["--nome"]["padrao"], "x")
        self.assertEqual(self.args["--qtd"]["padrao"], 0)  # zero não vira null
        self.assertIsNone(self.args["--lista"]["padrao"])
        self.assertEqual(self.args["--talvez"]["padrao"], [])  # lista vazia não vira null
        self.assertIsNone(self.args["--escondido"]["padrao"])  # SUPPRESS vira null
        self.assertEqual(self.args["--cor"]["padrao"], "azul")
        for a in self.args.values():
            if a["nome"] not in ("--liga", "--desliga"):
                self.assertTrue(a["recebe_valor"], a["nome"])

    def test_multiplo_valores_e_posicional(self):
        self.assertTrue(self.args["--lista"]["multiplo"])
        self.assertTrue(self.args["--talvez"]["multiplo"])
        self.assertFalse(self.args["--nome"]["multiplo"])
        self.assertEqual(self.args["--cor"]["valores"], ["azul", "verde"])  # tupla vira lista
        self.assertTrue(self.args["alvo"]["obrigatorio"])
        self.assertIsNone(self.args["alvo"]["padrao"])

    def test_serializavel(self):
        json.dumps(list(self.cmds.values()))


class TestGuardaDoParserReal(unittest.TestCase):
    """recebe_valor só olha store_true/store_false: se o forge.py ganhar count/store_const/append_const,
    este teste avisa que o contrato precisa ser revisto."""

    def test_so_acoes_cobertas_pelo_contrato(self):
        parser = extrair.carregar_forge().montar_parser()
        permitidas = (argparse._StoreAction, argparse._StoreTrueAction, argparse._StoreFalseAction,
                      argparse._HelpAction)
        for nome, s in extrair.subparsers(parser).items():
            for acao in s._actions:
                self.assertIsInstance(acao, permitidas, f"{nome} {acao.dest}: {type(acao).__name__}")


class TestDataFixa(unittest.TestCase):
    def test_forge_tem_uma_fonte_de_data(self):
        # A data fixa só troca datetime.date: outra fonte de "agora" no forge.py escaparia dela
        fonte = extrair.FORGE_PY.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"date\.today\(\)", fonte)), 1)
        for proibido in (r"datetime\.now", r"datetime\.utcnow", r"\btime\.time\(", r"strftime\(", r"localtime"):
            self.assertIsNone(re.search(proibido, fonte), proibido)

    def test_unica_data_no_arquivo_e_a_do_exemplo(self):
        texto = extrair.DESTINO_COMANDOS.read_text(encoding="utf-8")
        datas = set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", texto))
        self.assertEqual(datas, {extrair.DATA_EXEMPLO})

    def test_bootstrap_nao_muda_ajuda_nem_codigo_de_saida(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Path(tmp) / "registro.json"
            for args in (["-h"], ["status", "-h"], [], ["validar", "nao-existe.json"]):
                direto = extrair.executar(args, tmp, reg)
                fixo = extrair.executar(args, tmp, reg, data="2021-03-04")
                self.assertEqual((fixo.returncode, fixo.stdout, fixo.stderr),
                                 (direto.returncode, direto.stdout, direto.stderr), args)
            self.assertFalse(reg.exists())

    def test_data_invalida_falha(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = extrair.executar(["-h"], tmp, Path(tmp) / "registro.json", data="2021-13-40")
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
