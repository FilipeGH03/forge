"""Testes de borda do extrair.py (contrato 1.2): formato estrito, arquivo commitado, erro no roteiro.

    python -m unittest discover -s site/scripts        (da raiz da skill)
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import extrair

CAMPOS_COMANDO = {"nome", "ajuda", "usa_plano", "argumentos", "exemplo"}
CAMPOS_ARGUMENTO = {"nome", "obrigatorio", "recebe_valor", "padrao", "ajuda", "valores", "multiplo"}


def temporarias():
    return set(Path(tempfile.gettempdir()).glob("forge-exemplo-*"))


class TestFormatoDoContrato(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dados = extrair.gerar()

    def test_chaves_e_tipos_estritos(self):
        self.assertEqual(set(self.dados), {"gerado_de", "comandos"})
        self.assertIsInstance(self.dados["comandos"], list)
        for c in self.dados["comandos"]:
            self.assertEqual(set(c), CAMPOS_COMANDO, c["nome"])
            self.assertIsInstance(c["nome"], str)
            self.assertIsInstance(c["ajuda"], str)
            self.assertTrue(c["ajuda"].strip(), c["nome"])
            self.assertIsInstance(c["usa_plano"], bool)
            for a in c["argumentos"]:
                self.assertEqual(set(a), CAMPOS_ARGUMENTO)
                self.assertIsInstance(a["nome"], str)
                self.assertIsInstance(a["obrigatorio"], bool)
                self.assertIsInstance(a["multiplo"], bool)
                self.assertIsInstance(a["recebe_valor"], bool)
                self.assertTrue(a["padrao"] is None or isinstance(a["padrao"], (str, int, float, list)),
                                f"{c['nome']} {a['nome']}")
                if not a["recebe_valor"]:
                    self.assertIsNone(a["padrao"], f"{c['nome']} {a['nome']}")
                self.assertTrue(a["ajuda"] is None or isinstance(a["ajuda"], str))
                v = a["valores"]
                self.assertTrue(v is None or (isinstance(v, list) and v and all(isinstance(x, str) for x in v)),
                                f"{c['nome']} {a['nome']}")
                self.assertNotEqual(a["nome"], "plano" if c["usa_plano"] else None)
            e = c["exemplo"]
            if e is not None:
                self.assertEqual(set(e), {"comando", "saida"})
                self.assertIsInstance(e["comando"], str)
                self.assertIsInstance(e["saida"], str)

    def test_nomes_unicos(self):
        nomes = [c["nome"] for c in self.dados["comandos"]]
        self.assertEqual(len(nomes), len(set(nomes)))
        for c in self.dados["comandos"]:
            args = [a["nome"] for a in c["argumentos"]]
            self.assertEqual(len(args), len(set(args)), c["nome"])

    def test_comandos_dos_exemplos_usam_o_plano_de_exemplo(self):
        for c in self.dados["comandos"]:
            if c["usa_plano"]:
                self.assertTrue(c["exemplo"]["comando"].startswith(f"forge.py {c['nome']} forge-exemplo.json"),
                                c["exemplo"]["comando"])

    def test_arquivo_commitado_bate_com_a_geracao(self):
        # Igual, sem tolerância: nada no arquivo depende do dia em que foi gerado (datas dos exemplos fixas)
        commitado = extrair.DESTINO_COMANDOS.read_text(encoding="utf-8")
        gerado = json.dumps(self.dados, ensure_ascii=False, indent=2) + "\n"
        self.assertEqual(commitado, gerado)


class TestBordas(unittest.TestCase):
    def test_comando_exibido_aspas(self):
        self.assertEqual(extrair.comando_exibido(["a", ""]), 'forge.py a ""')
        self.assertEqual(extrair.comando_exibido(["duvida", "pode?"]), 'forge.py duvida "pode?"')
        self.assertEqual(extrair.comando_exibido(["x", "um dois"]), 'forge.py x "um dois"')
        self.assertEqual(extrair.comando_exibido(["lista"]), "forge.py lista")

    def test_sem_caminhos_locais_sem_ocorrencia_nao_muda(self):
        pasta = Path("C:/Temp/forge-exemplo-y") if os.name == "nt" else Path("/tmp/forge-exemplo-y")
        texto = "nada aqui; outro/lugar e forge-exemplo.json"
        self.assertEqual(extrair.sem_caminhos_locais(texto, pasta), texto)
        self.assertEqual(extrair.sem_caminhos_locais("", pasta), "")

    def test_caminho_local_fora_da_pasta_dos_exemplos_quebra(self):
        pasta = Path("C:/Temp/forge-exemplo-y") if os.name == "nt" else Path("/tmp/forge-exemplo-y")
        for caminho in ("C:/outro/lugar", r"C:\outro\lugar", "/c/outro/lugar", "/home/x/lugar"):
            with self.assertRaisesRegex(RuntimeError, "caminho local", msg=caminho):
                extrair.sem_caminhos_locais(f"veja {caminho}", pasta)

    @unittest.skipUnless(os.name == "nt", "a forma do Git Bash só existe no Windows")
    def test_pasta_dos_exemplos_na_forma_do_git_bash(self):
        pasta = Path("C:/Temp/forge-exemplo-y")
        self.assertEqual(extrair.sem_caminhos_locais("em /c/Temp/forge-exemplo-y/repo e /c/Temp/forge-exemplo-y/"
                                                     "forge-exemplo.json", pasta),
                         "em <pasta>/repo e forge-exemplo.json")

    def test_sem_caminhos_locais_para_no_delimitador(self):
        pasta = Path("C:/Temp/forge-exemplo-y") if os.name == "nt" else Path("/tmp/forge-exemplo-y")
        texto = f'"{pasta.as_posix()}/repo" e `{pasta}{os.sep}x`'
        self.assertEqual(extrair.sem_caminhos_locais(texto, pasta), '"<pasta>/repo" e `<pasta>/x`')

    def test_passo_com_codigo_errado_quebra_e_limpa(self):
        antes = temporarias()
        roteiro = [(["novo", "x", "--titulo", "X", "--dono", "d", "--dir", "."], 0),
                   (["validar", "nao-existe.json"], 0)]  # plano inexistente: sai com erro, não com 0
        with mock.patch.object(extrair, "ROTEIRO", roteiro):
            with self.assertRaises(RuntimeError) as ctx:
                extrair.exemplos()
        self.assertIn("esperado 0", str(ctx.exception))
        self.assertEqual(temporarias(), antes)

    def test_forge_registro_do_ambiente_e_ignorado(self):
        # Mesmo com um FORGE_REGISTRO já definido em quem roda o build, o roteiro usa o da pasta temporária
        with tempfile.TemporaryDirectory() as tmp:
            sentinela = Path(tmp) / "registro.json"
            sentinela.write_text('{"planos": []}\n', encoding="utf-8")
            conteudo = sentinela.read_bytes()
            with mock.patch.dict(os.environ, {"FORGE_REGISTRO": str(sentinela)}):
                extrair.exemplos()
            self.assertEqual(sentinela.read_bytes(), conteudo)

    def test_main_grava_no_destino_de_qualquer_pasta(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "sub" / "comandos.json"
            destino_fluxo = Path(tmp) / "sub" / "fluxo.json"
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                with mock.patch.object(extrair, "DESTINO_COMANDOS", destino), \
                        mock.patch.object(extrair, "DESTINO_FLUXO", destino_fluxo), \
                        mock.patch.object(extrair, "SITE", Path(tmp)), \
                        mock.patch("builtins.print"):
                    extrair.main()
            finally:
                os.chdir(cwd)
            bruto = destino.read_bytes()
            self.assertNotIn(b"\r\n", bruto)
            self.assertTrue(bruto.endswith(b"}\n"))
            dados = json.loads(bruto.decode("utf-8"))
            self.assertEqual(len(dados["comandos"]),
                             len(extrair.subparsers(extrair.carregar_forge().montar_parser())))
            bruto = destino_fluxo.read_bytes()
            self.assertNotIn(b"\r\n", bruto)
            self.assertEqual(len(json.loads(bruto.decode("utf-8"))["fases"]), 8)


if __name__ == "__main__":
    unittest.main()
