"""Testes do testador da A3: as páginas de src/content/docs seguem o contrato 1.1 e batem com as fontes.

    python -m unittest discover -s site/scripts        (da raiz da skill)

O contrato 1.1 (frontmatter, corpo, links) é conferido em todas as páginas da coleção, inclusive as que
outras tarefas acrescentarem. Os testes de fidelidade conferem as páginas da A3 contra o forge.py, o
SKILL.md e os hooks — se a fonte mudar, a página tem de mudar junto.
"""
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import extrair

DOCS = extrair.SITE / "src" / "content" / "docs"
COMANDOS = extrair.SITE / "src" / "data" / "comandos.json"
HOOK = extrair.RAIZ_SKILL / "hooks" / "forge_hook.py"

CAMPOS = {"titulo", "descricao", "secao", "ordem", "destaque"}
OBRIGATORIOS = {"titulo", "descricao", "secao", "ordem"}
SECOES = ("comece", "conceitos", "fluxo", "referencia")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
PAGINAS_A3 = ("visao-geral", "plano-vivo", "frentes-e-contratos", "papeis-dos-agentes", "tarefas-e-ondas",
              "decisoes-no-meio-do-projeto", "sincronizacao-e-drift", "hooks", "regras", "formato-do-json")


def ler_pagina(caminho):
    """(frontmatter como dict de texto bruto, corpo)."""
    texto = caminho.read_text(encoding="utf-8")
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", texto, re.S)
    if not m:
        raise AssertionError(f"{caminho.name}: sem frontmatter")
    campos = {}
    for linha in m.group(1).splitlines():
        if not linha.strip():
            continue
        chave, sep, valor = linha.partition(":")
        if not sep or linha[:1].isspace():
            raise AssertionError(f"{caminho.name}: linha de frontmatter inesperada: {linha!r}")
        campos[chave.strip()] = valor.strip()
    return campos, m.group(2)


def sem_codigo(corpo):
    """O corpo sem os blocos de código cercados e sem o código em linha."""
    corpo = re.sub(r"^(```+|~~~+).*?^\1\s*$", "", corpo, flags=re.S | re.M)
    return re.sub(r"`[^`\n]*`", "", corpo)


def links(corpo):
    texto = sem_codigo(corpo)
    alvos = re.findall(r"\]\(\s*<?([^)\s>]+)", texto)
    alvos += re.findall(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?\s*$", texto, re.M)
    alvos += re.findall(r"href=[\"']([^\"']+)", texto)
    return alvos


def texto_puro(md):
    return re.sub(r"\s+", " ", re.sub(r"[*`_]|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", md)).strip()


class Paginas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paginas = {p.stem: ler_pagina(p) for p in sorted(DOCS.glob("*.md"))}
        cls.comandos = {c["nome"] for c in json.loads(COMANDOS.read_text(encoding="utf-8"))["comandos"]}


class TestFrontmatter(Paginas):
    def test_as_dez_paginas_da_a3_existem(self):
        for slug in PAGINAS_A3:
            with self.subTest(slug=slug):
                self.assertIn(slug, self.paginas)

    def test_nada_fora_do_md_direto_na_pasta(self):
        for p in DOCS.rglob("*"):
            with self.subTest(arquivo=str(p.relative_to(DOCS))):
                self.assertTrue(p.is_file() and p.parent == DOCS and p.suffix == ".md")

    def test_slug_em_minusculas_com_hifen(self):
        for slug in self.paginas:
            with self.subTest(slug=slug):
                self.assertRegex(slug, rf"^{SLUG.pattern}$")

    def test_so_os_campos_do_contrato(self):
        for slug, (campos, _) in self.paginas.items():
            with self.subTest(slug=slug):
                self.assertLessEqual(set(campos), CAMPOS)
                self.assertLessEqual(OBRIGATORIOS, set(campos))

    def test_titulo_curto_e_nao_vazio(self):
        for slug, (campos, _) in self.paginas.items():
            with self.subTest(slug=slug):
                self.assertTrue(campos["titulo"])
                self.assertLessEqual(len(campos["titulo"]), 60)

    def test_descricao_ate_160_caracteres(self):
        for slug, (campos, _) in self.paginas.items():
            with self.subTest(slug=slug):
                self.assertTrue(campos["descricao"])
                self.assertLessEqual(len(campos["descricao"]), 160)

    def test_secao_no_dominio(self):
        for slug, (campos, _) in self.paginas.items():
            with self.subTest(slug=slug):
                self.assertIn(campos["secao"], SECOES)

    def test_ordem_inteira_e_unica_na_secao(self):
        vistos = {}
        for slug, (campos, _) in self.paginas.items():
            with self.subTest(slug=slug):
                self.assertRegex(campos["ordem"], r"^-?\d+$")
                chave = (campos["secao"], int(campos["ordem"]))
                self.assertNotIn(chave, vistos, f"mesma ordem que {vistos.get(chave)}")
                vistos[chave] = slug

    def test_destaque_booleano_quando_existe(self):
        for slug, (campos, _) in self.paginas.items():
            if "destaque" in campos:
                with self.subTest(slug=slug):
                    self.assertIn(campos["destaque"], ("true", "false"))

    def test_valores_sem_aspas_quebradas_nem_dois_pontos_soltos(self):
        # YAML lê "a: b" no meio de um valor sem aspas como erro; o build pegaria, mas aqui o aviso é mais claro
        for slug, (campos, _) in self.paginas.items():
            for chave, valor in campos.items():
                with self.subTest(slug=slug, campo=chave):
                    if not valor.startswith(("'", '"')):
                        self.assertNotRegex(valor, r":\s|#\s|^[\[{&*!|>%@]")

    def test_a3_nao_usa_a_secao_comece(self):
        # a seção comece é da A4 (início rápido); a A3 não disputa a ordem com ela
        for slug in PAGINAS_A3:
            with self.subTest(slug=slug):
                self.assertNotEqual(self.paginas[slug][0]["secao"], "comece")


class TestCorpo(Paginas):
    def test_sem_titulo_de_nivel_1(self):
        for slug, (_, corpo) in self.paginas.items():
            with self.subTest(slug=slug):
                self.assertNotRegex(sem_codigo(corpo), r"(?m)^#\s")
                self.assertNotRegex(sem_codigo(corpo), r"(?m)^[^\n]+\n=+\s*$")

    def test_niveis_de_titulo_nao_pulam(self):
        for slug, (_, corpo) in self.paginas.items():
            anterior = 1
            for m in re.finditer(r"(?m)^(#{2,6})\s", sem_codigo(corpo)):
                nivel = len(m.group(1))
                with self.subTest(slug=slug, titulo=m.group(0)):
                    self.assertLessEqual(nivel, anterior + 1)
                anterior = nivel

    def test_todo_bloco_de_codigo_tem_linguagem(self):
        for slug, (_, corpo) in self.paginas.items():
            dentro = False
            for linha in corpo.splitlines():
                m = re.match(r"\s*(```+|~~~+)\s*(\S*)", linha)
                if not m:
                    continue
                if not dentro:
                    with self.subTest(slug=slug, linha=linha):
                        self.assertTrue(m.group(2), "bloco de código sem linguagem")
                dentro = not dentro
            with self.subTest(slug=slug):
                self.assertFalse(dentro, "bloco de código não fechado")

    def test_sem_bloco_indentado_por_engano(self):
        # quatro espaços depois de linha em branco viram bloco de código sem linguagem
        for slug, (_, corpo) in self.paginas.items():
            texto = re.sub(r"^(```+).*?^\1\s*$", "", corpo, flags=re.S | re.M)
            with self.subTest(slug=slug):
                self.assertNotRegex(texto, r"\n\s*\n {4,}\S")


class TestLinks(Paginas):
    def test_links_internos_no_formato_do_contrato(self):
        for slug, (_, corpo) in self.paginas.items():
            for alvo in links(corpo):
                if re.match(r"[a-z]+:", alvo) or alvo.startswith("#"):
                    continue
                with self.subTest(slug=slug, alvo=alvo):
                    self.assertRegex(alvo, rf"^/(docs/{SLUG.pattern}/|comandos/(#[a-z][a-z0-9-]*)?)$")

    def test_sem_o_base_do_github_pages(self):
        for slug, (_, corpo) in self.paginas.items():
            for alvo in links(corpo):
                with self.subTest(slug=slug, alvo=alvo):
                    self.assertFalse(alvo.startswith("/forge"))

    def test_link_de_pagina_aponta_para_slug_que_existe(self):
        for slug, (_, corpo) in self.paginas.items():
            for alvo in links(corpo):
                m = re.fullmatch(r"/docs/([^/]+)/", alvo)
                if m:
                    with self.subTest(slug=slug, alvo=alvo):
                        self.assertIn(m.group(1), self.paginas)

    def test_ancora_de_comando_e_um_comando_do_comandos_json(self):
        for slug, (_, corpo) in self.paginas.items():
            for alvo in links(corpo):
                m = re.fullmatch(r"/comandos/#(.+)", alvo)
                if m:
                    with self.subTest(slug=slug, alvo=alvo):
                        self.assertIn(m.group(1), self.comandos)

    def test_sem_link_relativo_nem_para_md(self):
        for slug, (_, corpo) in self.paginas.items():
            for alvo in links(corpo):
                with self.subTest(slug=slug, alvo=alvo):
                    self.assertFalse(alvo.startswith(".") or alvo.endswith(".md"))

    def test_toda_pagina_da_a3_e_alcancavel_por_outra(self):
        alvos = {m.group(1) for _, corpo in self.paginas.values() for a in links(corpo)
                 if (m := re.fullmatch(r"/docs/([^/]+)/", a))}
        for slug in PAGINAS_A3:
            if slug == "visao-geral":
                continue
            with self.subTest(slug=slug):
                self.assertIn(slug, alvos)


class TestSemDadoDaMaquina(Paginas):
    def test_sem_caminho_do_usuario_da_maquina(self):
        # repositório público (D9): nada de C:/Users/<nome>, /home/<nome> ou do scratchpad
        for slug, (_, corpo) in self.paginas.items():
            with self.subTest(slug=slug):
                self.assertNotRegex(corpo, r"(?i)[a-z]:[\\/]+users[\\/]|/home/\w|AppData|scratchpad")

    def test_caminho_absoluto_so_no_exemplo_do_json(self):
        # o único caminho absoluto aceito é o "repo" de exemplo do formato do JSON (vem do references/plano-json.md)
        for slug, (_, corpo) in self.paginas.items():
            achados = re.findall(r"(?i)\b[a-z]:[\\/][^\s`\"')]*", corpo)
            with self.subTest(slug=slug):
                self.assertEqual(achados, ["C:/Projetos/avisos"] if slug == "formato-do-json" else [])


class Fontes(Paginas):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmp = tempfile.TemporaryDirectory()
        with mock.patch.dict(os.environ, {"FORGE_REGISTRO": str(Path(cls.tmp.name) / "registro.json")}):
            cls.forge = extrair.carregar_forge()
        cls.fonte = extrair.FORGE_PY.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def corpo(self, slug):
        return self.paginas[slug][1]


class TestFidelidade(Fontes):
    def test_tabela_de_papeis_bate_com_PAPEIS(self):
        corpo = self.corpo("papeis-dos-agentes")
        linhas = re.findall(r"(?m)^\| \*\*(.+?)\*\* \| (.+?) \| (.+?) \|$", corpo)
        self.assertEqual([n for n, _, _ in linhas], [p["nome"] for p in self.forge.PAPEIS.values()])
        self.assertEqual([e for _, _, e in linhas], [p["escreve_codigo"] for p in self.forge.PAPEIS.values()])

    def test_regras_do_jogo_sao_as_REGRAS_PADRAO_na_ordem(self):
        corpo = self.corpo("regras")
        trecho = corpo.split("## As regras do jogo", 1)[1].split("\n## ", 1)[0]
        itens = re.findall(r"(?ms)^\d+\. (.+?)(?=^\d+\. |^\S|\Z)", trecho)
        self.assertEqual(len(itens), len(self.forge.REGRAS_PADRAO))
        for pagina, fonte in zip(itens, self.forge.REGRAS_PADRAO):
            with self.subTest(regra=fonte[:40]):
                # a página pode encurtar, mas começa igual à regra do forge.py
                self.assertEqual(texto_puro(pagina)[:30], texto_puro(fonte)[:30])

    def test_secoes_do_documento_batem_com_gerar_md(self):
        geradas = re.findall(r'a\(f?"## (\d+)\. ([^\\"—]+)', self.fonte)
        pagina = re.findall(r"(?m)^\| (\d+)\. ([^|]+?) \|", self.corpo("plano-vivo"))
        self.assertEqual([n for n, _ in pagina], [n for n, _ in geradas])
        for (n, titulo_md), (_, titulo_fonte) in zip(pagina, geradas):
            with self.subTest(secao=n):
                self.assertEqual(titulo_md.strip(), titulo_fonte.strip())

    def test_fases_na_ordem_do_FASES(self):
        self.assertIn(" → ".join(self.forge.FASES), self.corpo("plano-vivo"))

    def test_tipos_de_drift_batem_com_achar_drift(self):
        inicio = self.fonte.index("def achar_drift")
        fim = self.fonte.index("\ndef ", inicio + 1)
        tipos = list(dict.fromkeys(re.findall(r'achados\.append\(\("([a-z-]+)"', self.fonte[inicio:fim])))
        pagina = re.findall(r"(?m)^\| `([a-z-]+)` \|", self.corpo("sincronizacao-e-drift"))
        self.assertEqual(pagina, tipos)

    def test_exemplos_de_id_no_commit_sao_reconhecidos(self):
        bloco = re.search(r"```text\n(.*?)```", self.corpo("tarefas-e-ondas"), re.S).group(1)
        for linha in bloco.strip().splitlines():
            with self.subTest(linha=linha):
                self.assertTrue(self.forge.ids_do_assunto(linha))
        self.assertEqual(self.forge.ids_do_assunto("B2 e C4: renomeia o campo"), ["B2", "C4"])
        self.assertEqual(self.forge.ids_do_assunto("A27 (T9): correção"), ["A27"])

    def test_max_da_onda_padrao_3(self):
        acao = next(a for s in extrair.subparsers(self.forge.montar_parser()).values() if s.prog.endswith(" onda")
                    for a in s._actions if a.dest == "max")
        self.assertEqual(acao.default, 3)
        self.assertIn("padrão 3", self.corpo("tarefas-e-ondas"))

    def test_estados_do_executor_batem_com_o_workflow(self):
        wf = (extrair.RAIZ_SKILL / "references" / "workflow-onda.js").read_text(encoding="utf-8")
        estados = json.loads(re.search(r"estado: \{ type: 'string', enum: (\[.*?\]) \}", wf).group(1).replace("'", '"'))
        pagina = re.findall(r"(?m)^\| `(pronto|contrato|travou|[a-z]+)` \| ", self.corpo("papeis-dos-agentes"))
        self.assertEqual(sorted(set(pagina) & {"pronto", "contrato", "travou"}), sorted(estados))

    def test_corte_do_hook_e_6000(self):
        hook = HOOK.read_text(encoding="utf-8")
        self.assertIn("len(texto) > 6000", hook)
        self.assertIn("6 000 caracteres", self.corpo("hooks"))

    def test_variaveis_do_banco_batem_com_o_hook(self):
        hook = HOOK.read_text(encoding="utf-8")
        variaveis = re.findall(r'VAR_\w+ = "(\w+)"', hook)
        self.assertEqual(len(variaveis), 2)
        for var in variaveis:
            with self.subTest(var=var):
                self.assertIn(f"`{var}`", self.corpo("hooks"))

    def test_clientes_citados_existem_no_hook(self):
        hook = HOOK.read_text(encoding="utf-8")
        clientes = set(re.findall(r'"([\w-]+)"', re.search(r"CLIENTES_BANCO = \{(.*?)\}", hook, re.S).group(1)))
        trecho = self.corpo("hooks").split("### Banco de dados", 1)[1].split("###", 1)[0]
        citados = re.findall(r"`([\w-]+)`", trecho.split(")", 1)[0])
        self.assertTrue(citados)
        self.assertLessEqual(set(citados), clientes)

    def test_letras_reservadas_batem_com_FRENTES_RESERVADAS(self):
        self.assertEqual(self.forge.FRENTES_RESERVADAS, {"D", "Q", "R"})
        self.assertIn("D, Q e R são reservadas", self.corpo("frentes-e-contratos"))

    def test_json_de_exemplo_e_um_plano_valido(self):
        bloco = re.search(r"```json\n(.*?)```", self.corpo("formato-do-json"), re.S).group(1)
        plano = json.loads(bloco)
        self.assertEqual(plano["forge"], self.forge.VERSAO)
        # o exemplo é um recorte: mostra só a frente A, e o contrato cita também a C. Fora isso, é válido.
        self.assertEqual([p for p in self.forge.validar(plano) if not re.fullmatch(r"contrato .*: frente \w+ não existe", p)], [])
        self.assertEqual(set(plano) - {"md_sha"}, set(self.forge.plano_vazio("x", "x", "x", None, "b")))

    def test_campos_da_tabela_cobrem_o_plano(self):
        pagina = set()
        for celula in re.findall(r"(?m)^\| ((?:`[a-z_]+`(?:, )?)+) \|", self.corpo("formato-do-json")):
            pagina |= set(re.findall(r"`([a-z_]+)`", celula))
        esperado = set(self.forge.plano_vazio("x", "x", "x", None, "b")) | {"md_sha"}
        self.assertEqual(pagina, esperado)

    def test_mensagem_de_plano_invalido_e_a_do_forge(self):
        self.assertIn('erro("plano inválido, nada foi gravado:', self.fonte)
        self.assertIn('print(f"forge: {msg}"', self.fonte)
        self.assertIn("falta 'como_testar' — toda tarefa precisa provar que funciona sozinha", self.fonte)

    def test_exemplos_de_comando_passam_no_parser(self):
        parser = self.forge.montar_parser()
        for slug, (_, corpo) in self.paginas.items():
            for bloco in re.findall(r"```bash\n(.*?)```", corpo, re.S):
                for cmd in bloco.replace("\\\n", " ").splitlines():
                    partes = cmd.split()
                    if "forge.py" not in cmd or "<comando>" in cmd:
                        continue
                    args = re.findall(r'"[^"]*"|\S+', cmd.split("forge.py", 1)[1])
                    args = [a.strip('"') for a in args]
                    with self.subTest(slug=slug, cmd=cmd):
                        self.assertTrue(partes)
                        parser.parse_args(args)


if __name__ == "__main__":
    unittest.main()
