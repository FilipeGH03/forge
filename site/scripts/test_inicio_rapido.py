"""A página de início rápido (src/content/docs/inicio-rapido.md) funciona do começo ao fim.

    python -m unittest discover -s site/scripts        (da raiz da skill)

Roda os blocos ```bash da página, na ordem, num bash só, com uma HOME temporária e o FORGE_REGISTRO
apontando para dentro dela: nem o registro de planos nem o settings.json de quem roda são tocados. O clone
da skill sai deste repositório (não da rede), e o bloco ```json é aplicado ao plano como o leitor faria à
mão, com o "repo" trocado pelo caminho do repositório de exemplo.

Cada bloco ```text logo depois de um ```bash é a saída dele, conferida com a saída real, a menos de
caminhos (a HOME temporária vira ~), SHAs, datas e o tempo do unittest.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import extrair

PAGINA = extrair.SITE / "src" / "content" / "docs" / "inicio-rapido.md"
CLONE = "https://github.com/FilipeGH03/forge.git"
MARCA = "@@bloco {}@@"


def bash():
    """O bash do Git no Windows (o de System32 é o do WSL, que não enxerga esta máquina); o do PATH fora dele."""
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            for raiz in (Path(git).resolve().parent.parent, Path(git).resolve().parent.parent.parent):
                candidato = raiz / "bin" / "bash.exe"
                if candidato.exists():
                    return str(candidato)
        return None
    return shutil.which("bash")


def blocos(texto):
    """[(linguagem, conteúdo, só_espaço_antes)] dos blocos cercados, na ordem; o terceiro diz se entre o bloco
    anterior e este só há linhas em branco."""
    saida, fim = [], 0
    for m in re.finditer(r"^```(\w+)\n(.*?)^```\s*$", texto, re.S | re.M):
        saida.append((m.group(1), m.group(2), not texto[fim:m.start()].strip()))
        fim = m.end()
    return saida


def normalizar(texto, home=None):
    if home is not None:
        formas = {str(home), home.as_posix()}
        if re.match(r"[A-Za-z]:/", home.as_posix()):
            formas.add(f"/{home.as_posix()[0].lower()}{home.as_posix()[2:]}")
        for forma in sorted(formas, key=len, reverse=True):
            texto = re.sub(re.escape(forma) + r"[^\s\]]*", lambda m: "~" + m.group(0)[len(forma):].replace("\\", "/"),
                           texto)
    texto = re.sub(r"\b[0-9a-f]{8}\b", "<sha>", texto)
    texto = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "<data>", texto)
    texto = re.sub(r"Ran (\d+) tests? in [\d.]+s", r"Ran \1 test(s)", texto)
    return "\n".join(linha.rstrip() for linha in texto.strip().splitlines())


APLICAR_JSON = """import json, sys
from pathlib import Path
trecho = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for f in trecho.get("frentes", []):
    f["repo"] = sys.argv[2]
planos = sorted(Path.cwd().glob("forge-*.json"))
assert len(planos) == 1, planos
plano = json.loads(planos[0].read_text(encoding="utf-8"))
plano.update(trecho)
planos[0].write_text(json.dumps(plano, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
"""


@unittest.skipUnless(bash() and shutil.which("git"), "precisa de bash e git")
class TestInicioRapido(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="forge-inicio-")
        raiz = Path(cls.tmp.name).resolve()
        cls.home = raiz / "home"
        cls.home.mkdir()
        cls.registro = raiz / "registro.json"
        cls.blocos = blocos(PAGINA.read_text(encoding="utf-8"))

        partes = ["exec 2>&1"]
        for i, (lingua, conteudo, _) in enumerate(cls.blocos):
            if lingua == "bash":
                partes += [f"echo '{MARCA.format(i)}'", conteudo.replace(CLONE, extrair.RAIZ_SKILL.as_posix())]
            elif lingua == "json":
                (raiz / f"trecho{i}.json").write_text(conteudo, encoding="utf-8")
                (raiz / "aplicar.py").write_text(APLICAR_JSON, encoding="utf-8")
                partes.append(f'python "{(raiz / "aplicar.py").as_posix()}" "{(raiz / f"trecho{i}.json").as_posix()}" '
                              f'"{(cls.home / "projetos" / "api").as_posix()}"')
        partes.append(f"echo '{MARCA.format('fim')}'")

        env = {**os.environ, "HOME": cls.home.as_posix(), "USERPROFILE": str(cls.home),
               "FORGE_REGISTRO": str(cls.registro), "PYTHONIOENCODING": "utf-8", "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_CONFIG_GLOBAL": (cls.home / ".gitconfig").as_posix(),
               "GIT_AUTHOR_NAME": "Voce", "GIT_AUTHOR_EMAIL": "voce@exemplo.com",
               "GIT_COMMITTER_NAME": "Voce", "GIT_COMMITTER_EMAIL": "voce@exemplo.com",
               "PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", "")}
        r = subprocess.run([bash(), "-c", "\n".join(partes)], cwd=raiz, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        cls.saida_bruta = r.stdout
        cls.saidas = {}
        pedacos = re.split(r"^@@bloco (\w+)@@\n?", r.stdout, flags=re.M)
        for chave, texto in zip(pedacos[1::2], pedacos[2::2]):
            cls.saidas[chave] = texto

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def plano(self):
        return json.loads((self.home / "projetos" / "forge-saude.json").read_text(encoding="utf-8"))

    def test_todos_os_blocos_rodaram(self):
        esperados = {str(i) for i, (lingua, _, _) in enumerate(self.blocos) if lingua == "bash"} | {"fim"}
        self.assertEqual(set(self.saidas), esperados, self.saida_bruta[-3000:])

    def test_cada_saida_da_pagina_e_a_saida_real(self):
        conferidas = 0
        for i, (lingua, conteudo, colado) in enumerate(self.blocos):
            if lingua == "text" and colado and i and self.blocos[i - 1][0] == "bash":
                with self.subTest(bloco=self.blocos[i - 1][1].splitlines()[-1][:80]):
                    self.assertEqual(normalizar(self.saidas.get(str(i - 1), ""), self.home), normalizar(conteudo))
                conferidas += 1
        self.assertGreaterEqual(conferidas, 8)

    def test_o_plano_termina_fechado_com_tudo_feito(self):
        plano = self.plano()
        self.assertEqual(plano["fase"], "fechado")
        self.assertEqual([(t["id"], t["estado"]) for t in plano["tarefas"]], [("A1", "feito"), ("A2", "feito")])
        self.assertTrue(all(t["commits"] for t in plano["tarefas"]))

    def test_hooks_instalados_na_home_temporaria(self):
        settings = json.loads((self.home / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(set(settings["hooks"]), {"SessionStart", "PreToolUse"})

    def test_so_o_registro_isolado_foi_usado(self):
        registro = json.loads(self.registro.read_text(encoding="utf-8"))
        self.assertEqual(len(registro["planos"]), 1)
        self.assertFalse((self.home / ".claude" / "forge" / "registro.json").exists())

    def test_o_comando_de_clone_e_o_do_remoto(self):
        # o teste troca a URL pelo repositório local; a página precisa ter a URL de verdade (D9)
        self.assertIn(f"git clone {CLONE} ~/.claude/skills/forge", PAGINA.read_text(encoding="utf-8"))


FORGE = extrair.RAIZ_SKILL / "scripts" / "forge.py"
INSTALAR = extrair.RAIZ_SKILL / "hooks" / "instalar.py"
HOOK_PY = extrair.RAIZ_SKILL / "hooks" / "forge_hook.py"


class TestAfirmacoesDaPagina(unittest.TestCase):
    """O que a página afirma e o roteiro não confere: instalar duas vezes não duplica e preserva os hooks
    alheios; --remover tira só o forge; plano fechado sai do SessionStart; drift sai com código 1 enquanto
    há divergência; md com plano inválido não grava nada. Cada teste tem a sua HOME e o seu registro."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="forge-afirm-")
        raiz = Path(self.tmp.name).resolve()
        self.home = raiz / "home"
        self.home.mkdir()
        self.projetos = raiz / "projetos"
        self.projetos.mkdir()
        self.registro = raiz / "registro.json"
        self.env = {**os.environ, "HOME": self.home.as_posix(), "USERPROFILE": str(self.home),
                    "FORGE_REGISTRO": str(self.registro), "PYTHONIOENCODING": "utf-8",
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": (self.home / ".gitconfig").as_posix(),
                    "GIT_AUTHOR_NAME": "Voce", "GIT_AUTHOR_EMAIL": "voce@exemplo.com",
                    "GIT_COMMITTER_NAME": "Voce", "GIT_COMMITTER_EMAIL": "voce@exemplo.com"}

    def tearDown(self):
        self.tmp.cleanup()

    def rodar(self, *args, cwd=None, entrada=None):
        return subprocess.run([sys.executable, *map(str, args)], cwd=cwd or self.projetos, env=self.env,
                              input=entrada, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120)

    def forge(self, *args):
        r = self.rodar(FORGE, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def git(self, repo, *args):
        r = subprocess.run(["git", *args], cwd=repo, env=self.env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def plano_com_uma_tarefa(self):
        """Plano forge-saude.json com a frente A (um repositório git) e a tarefa A1, já com commit na branch."""
        repo = self.projetos / "api"
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "main")
        (repo / "README.md").write_text("# API\n", encoding="utf-8")
        self.git(repo, "add", "README.md")
        self.git(repo, "commit", "-q", "-m", "estado inicial")
        self.forge("novo", "saude", "--titulo", "Rota de saúde", "--dono", "voce@exemplo.com", "--dir", ".",
                   "--base", "main")
        plano = self.projetos / "forge-saude.json"
        dados = json.loads(plano.read_text(encoding="utf-8"))
        dados.update({
            "objetivo": "Uma rota GET /saude para o balanceador saber se a API está de pé.",
            "requisitos": [{"id": "R1", "texto": "GET /saude devolve 200, sem login.", "fonte": "você, hoje"}],
            "frentes": [{"id": "A", "nome": "API", "repo": repo.as_posix(), "stack": "Python",
                         "como_testar": "python -m unittest", "proibido": []}],
        })
        plano.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.forge("md", "forge-saude.json")
        self.forge("tarefa", "forge-saude.json", "--frente", "A", "--titulo", "Rota GET /saude",
                   "--testar", "GET /saude devolve 200")
        self.git(repo, "checkout", "-q", "-b", "saude")
        (repo / "saude.py").write_text("def saude():\n    return 200, 'ok'\n", encoding="utf-8")
        self.git(repo, "add", "saude.py")
        self.git(repo, "commit", "-q", "-m", "A1: rota GET /saude")
        return plano

    def settings(self):
        return json.loads((self.home / ".claude" / "settings.json").read_text(encoding="utf-8"))

    def settings_com_hook_alheio(self):
        (self.home / ".claude").mkdir()
        alheio = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo alheio", "timeout": 5}]}
        (self.home / ".claude" / "settings.json").write_text(
            json.dumps({"outra_config": 1, "hooks": {"PreToolUse": [alheio]}}), encoding="utf-8")
        return alheio

    def test_instalar_duas_vezes_nao_duplica_e_preserva_hooks_alheios(self):
        alheio = self.settings_com_hook_alheio()
        for _ in range(2):
            r = self.rodar(INSTALAR, cwd=self.home)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s = self.settings()
        self.assertEqual(s["outra_config"], 1)
        self.assertEqual(len(s["hooks"]["SessionStart"]), 1)
        self.assertEqual(s["hooks"]["PreToolUse"][0], alheio)
        self.assertEqual(len(s["hooks"]["PreToolUse"]), 2)

    def test_remover_tira_so_as_entradas_do_forge(self):
        alheio = self.settings_com_hook_alheio()
        self.rodar(INSTALAR, cwd=self.home)
        r = self.rodar(INSTALAR, "--remover", cwd=self.home)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.settings(), {"outra_config": 1, "hooks": {"PreToolUse": [alheio]}})

    def test_plano_fechado_sai_do_session_start(self):
        self.plano_com_uma_tarefa()
        entrada = json.dumps({"cwd": self.projetos.as_posix()})
        self.assertIn("forge-saude.json", self.rodar(HOOK_PY, "session-start", entrada=entrada).stdout)
        for fase in ("aguardando-aprovacao", "aprovado", "em-execucao"):
            self.forge("fase", "forge-saude.json", fase)
        self.forge("marcar", "forge-saude.json", "A1")
        self.forge("fase", "forge-saude.json", "fechado")
        self.assertEqual(self.rodar(HOOK_PY, "session-start", entrada=entrada).stdout.strip(), "")

    def test_drift_sai_1_com_divergencia_e_0_quando_limpo(self):
        self.plano_com_uma_tarefa()
        r = self.rodar(FORGE, "drift", "forge-saude.json")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("commit-sem-feito", r.stdout)
        self.forge("marcar", "forge-saude.json", "A1")
        r = self.rodar(FORGE, "drift", "forge-saude.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("sem divergências", r.stdout)

    def test_md_com_plano_invalido_nao_grava_nada(self):
        plano = self.plano_com_uma_tarefa()
        md = self.projetos / "forge-saude.md"
        md_antes = md.read_text(encoding="utf-8")
        dados = json.loads(plano.read_text(encoding="utf-8"))
        dados["tarefas"][0]["estado"] = "pronto-demais"  # o validador recusa estado fora da lista
        plano.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        json_antes = plano.read_text(encoding="utf-8")
        r = self.rodar(FORGE, "md", "forge-saude.json")
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(md.read_text(encoding="utf-8"), md_antes)
        self.assertEqual(plano.read_text(encoding="utf-8"), json_antes)


if __name__ == "__main__":
    unittest.main()
