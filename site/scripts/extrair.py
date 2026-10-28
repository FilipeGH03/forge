#!/usr/bin/env python3
"""Gera os dados do site a partir dos arquivos da skill (contratos 1.2 e 1.3 do plano).

    python scripts/extrair.py        (rodado de site/, no prebuild)

src/data/comandos.json sai do montar_parser() do scripts/forge.py, com um exemplo de saída real por
comando. Os exemplos rodam num plano de exemplo numa pasta temporária, com FORGE_REGISTRO apontando
para dentro dela: o registro de planos de quem roda o build nunca é tocado.

src/data/fluxo.json sai do SKILL.md (fases e seções transversais, cada uma com a frase de resumo em itálico
escrita logo abaixo do título), do PAPEIS do forge.py (o mesmo que
monta a tabela da seção 9 de todo plano) e da constante ETAPAS, que um teste confere contra o
references/workflow-onda.js.
"""
import argparse
import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
RAIZ_SKILL = SITE.parent
FORGE_PY = RAIZ_SKILL / "scripts" / "forge.py"
SKILL_MD = RAIZ_SKILL / "SKILL.md"
DESTINO_COMANDOS = SITE / "src" / "data" / "comandos.json"
DESTINO_FLUXO = SITE / "src" / "data" / "fluxo.json"

PLANO = "forge-exemplo.json"
PASTA = "<pasta>"
# A data do projeto de exemplo. O forge.py roda com datetime.date.today() devolvendo ela, e os commits do
# repositório de exemplo levam ela também: a saída (datas e SHAs) não muda de um dia ou build para outro.
DATA_EXEMPLO = "2026-01-15"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Exemplo", "GIT_AUTHOR_EMAIL": "voce@exemplo.com",
    "GIT_COMMITTER_NAME": "Exemplo", "GIT_COMMITTER_EMAIL": "voce@exemplo.com",
    "GIT_AUTHOR_DATE": f"{DATA_EXEMPLO}T10:00:00+00:00", "GIT_COMMITTER_DATE": f"{DATA_EXEMPLO}T10:00:00+00:00",
}
# python -c FIXAR_DATA <data> <forge.py> <args...>: roda o forge.py como script, com o dia fixo
FIXAR_DATA = """import datetime, runpy, sys
DIA = datetime.date.fromisoformat(sys.argv[1])
class Data(datetime.date):
    @classmethod
    def today(cls):
        return cls(DIA.year, DIA.month, DIA.day)
datetime.date = Data
sys.argv = sys.argv[2:]
runpy.run_path(sys.argv[0], run_name="__main__")
"""

# Roteiro do projeto de exemplo, na ordem em que roda. Cada passo é (argumentos do forge.py, código de
# saída esperado). O primeiro passo de cada comando vira o exemplo dele; "{pasta}" é a pasta temporária.
# Entre os passos, as funções de preparo fazem o que não tem comando: frentes no JSON e commits no git.
ROTEIRO = [
    (["novo", "exemplo", "--titulo", "Exemplo", "--dono", "voce@exemplo.com", "--dir", ".", "--base", "main"], 0),
    "frentes",
    (["md", PLANO], 0),
    (["validar", PLANO], 0),
    (["tarefa", PLANO, "--frente", "A", "--titulo", "Rota GET /saude", "--testar", "GET /saude devolve 200"], 0),
    (["tarefa", PLANO, "--frente", "A", "--titulo", "Teste da rota /saude", "--testar", "o teste roda e passa",
      "--depende", "A1"], 0),
    (["complexidade", PLANO, "baixa", "A2"], 0),
    (["duvida", PLANO, "A rota /saude precisa de autenticação?"], 0),
    (["responder", PLANO, "Q1", "Não: é usada pelo balanceador, sem login."], 0),
    (["decisao", PLANO, "--assunto", "Autenticação", "--texto", "/saude é pública.", "--duvida", "Q1"], 0),
    (["fase", PLANO, "aprovado"], 0),
    (["registrar", PLANO], 0),
    (["lista"], 0),
    "commit",
    (["branches", PLANO], 0),
    (["status", PLANO], 0),
    (["drift", PLANO], 1),
    (["marcar", PLANO, "A1"], 0),
    (["briefing", PLANO, "A2", "--papel", "testador"], 0),
    (["onda", PLANO, "--max", "1"], 0),
    (["ponteiros", PLANO], 0),
    (["dono", PLANO, "--add", "Publicar a rota em produção"], 0),
    (["rodada", PLANO, "--titulo", "Primeira onda", "--registro", "A1 feita e testada."], 0),
    (["contexto", "--cwd", "{pasta}/repo"], 0),
]


def carregar_forge(forge_py=FORGE_PY):
    spec = importlib.util.spec_from_file_location("forge", forge_py)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# --------------------------------------------------------------------------- parser

def subparsers(parser):
    """{nome: subparser}, na ordem em que o argparse os recebeu."""
    for acao in parser._actions:
        if isinstance(acao, argparse._SubParsersAction):
            return dict(acao.choices)
    return {}


def argumento(acao):
    nome = max(acao.option_strings, key=len) if acao.option_strings else acao.dest
    flag = isinstance(acao, (argparse._StoreTrueAction, argparse._StoreFalseAction))
    padrao = None if flag or acao.default is argparse.SUPPRESS else acao.default
    return {
        "nome": nome,
        "obrigatorio": bool(acao.required),
        "recebe_valor": not flag,
        "padrao": padrao,
        "ajuda": acao.help,
        "valores": list(acao.choices) if acao.choices is not None else None,
        "multiplo": acao.nargs in ("*", "+"),
    }


def comandos(parser):
    saida = []
    for nome, s in subparsers(parser).items():
        acoes = [a for a in s._actions if not isinstance(a, argparse._HelpAction)]
        usa_plano = bool(acoes) and not acoes[0].option_strings and acoes[0].dest == "plano"
        saida.append({
            "nome": nome,
            "ajuda": s.description,
            "usa_plano": usa_plano,
            "argumentos": [argumento(a) for a in acoes[1 if usa_plano else 0:]],
            "exemplo": None,
        })
    return saida


# --------------------------------------------------------------------------- caminhos

# Caminho absoluto de uma máquina: C:/..., C:\..., /c/... (Git Bash), /Users/..., /home/..., também dentro de
# uma URL de arquivo (file:///C:/..., file:///home/...)
CAMINHO_LOCAL = re.compile(r"(?:\bfile://(?:/(?=[A-Za-z]:))?|(?<![\w/>]))"
                           r"(?:[A-Za-z]:[\\/]|/(?:[A-Za-z]|Users|home)/)[^\s`'\"()<>|,;]*")
URL_DE_ARQUIVO = re.compile(r"^file://(?:/(?=[A-Za-z]:))?")


def formas(pasta):
    """Como um caminho aparece num texto: nativo, com "/", no Git Bash (/c/...) e escapado dentro de JSON."""
    posix = pasta.as_posix()
    saida = {str(pasta), posix}
    if re.match(r"[A-Za-z]:/", posix):
        saida.add(f"/{posix[0].lower()}{posix[2:]}")
    return saida | {f.replace("\\", "\\\\") for f in saida}


def sem_caminhos_locais(texto, pasta=None):
    """Tira de um texto todo caminho absoluto desta máquina, em qualquer formato (o único saneador do script).

    Com `pasta` (a temporária dos exemplos), o plano de exemplo dentro dela vira forge-exemplo.json e o resto
    dela vira <pasta>/... . Depois, o caminho de um arquivo da skill vira relativo à raiz dela
    ("C:/.../forge/references/x.js" -> "references/x.js"); qualquer outro caminho local é erro de geração."""
    if pasta is not None:
        for forma in sorted(formas(pasta), key=len, reverse=True):
            for sep in ("/", "\\", "\\\\"):
                texto = texto.replace(forma + sep + PLANO, PLANO)
            texto = re.sub(re.escape(forma) + r"([^\s\"'`|<>\]]*)",
                           lambda m: PASTA + re.sub(r"[\\/]+", "/", m.group(1)), texto)

    def relativo(m):
        caminho = m.group(0).rstrip(".:!?")  # pontuação no fim é da frase, não do caminho
        partes = re.split(r"[\\/]+", URL_DE_ARQUIVO.sub("", caminho))
        for i in range(1, len(partes)):
            if partes[i] and RAIZ_SKILL.joinpath(*partes[i:]).exists():
                return "/".join(partes[i:]) + m.group(0)[len(caminho):]
        raise RuntimeError(f"caminho local fora da skill: {caminho}")
    return CAMINHO_LOCAL.sub(relativo, texto)


# --------------------------------------------------------------------------- exemplos


def comando_exibido(args):
    partes = ["forge.py"] + [f'"{a}"' if re.search(r"[\s?]", a) or not a else a for a in args]
    return " ".join(partes)


def git(repo, *args):
    subprocess.run(["git", "-c", "core.hooksPath=", "-c", "commit.gpgsign=false", "-C", str(repo), *args],
                   check=True, capture_output=True, env={**os.environ, **GIT_ENV})


def preparar(passo, pasta):
    if passo == "frentes":
        # Frentes não têm comando: entram editando o JSON (references/plano-json.md), depois `md`
        caminho = pasta / PLANO
        plano = json.loads(caminho.read_text(encoding="utf-8"))
        plano["objetivo"] = "Uma rota de saúde para o balanceador saber se a API está de pé."
        plano["frentes"] = [{"id": "A", "nome": "API", "repo": (pasta / "repo").as_posix(), "stack": "Python",
                             "como_testar": "python -m unittest", "proibido": []}]
        caminho.write_text(json.dumps(plano, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif passo == "commit":
        repo = pasta / "repo"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        (repo / "README.md").write_text("# API\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "estado inicial")
        git(repo, "checkout", "-q", "-b", "exemplo")
        (repo / "saude.py").write_text('def saude():\n    return 200, "ok"\n', encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "A1: rota GET /saude")


def executar(args, cwd, registro, forge_py=FORGE_PY, data=None):
    """Roda o forge.py com o FORGE_REGISTRO dado (nunca o de quem roda); com `data`, o dia de hoje é ela."""
    env = {**os.environ, "FORGE_REGISTRO": str(registro), "PYTHONIOENCODING": "utf-8"}
    inicio = [sys.executable, "-c", FIXAR_DATA, data] if data else [sys.executable]
    return subprocess.run([*inicio, str(forge_py), *args], cwd=cwd, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)


def rodar(args, pasta, esperado):
    """Um passo do roteiro: no dia do exemplo, com o registro dentro da pasta temporária."""
    r = executar(args, pasta, pasta / "registro.json", data=DATA_EXEMPLO)
    if r.returncode != esperado:
        raise RuntimeError(f"forge.py {' '.join(args)} saiu com {r.returncode} (esperado {esperado}):\n"
                           f"{r.stdout}{r.stderr}")
    return (r.stdout + r.stderr).rstrip("\n")


def exemplos():
    """{comando: {"comando", "saida"}} do primeiro uso de cada comando no roteiro."""
    saida = {}
    # O TemporaryDirectory também apaga os objetos do git, que ficam só para leitura no Windows
    with tempfile.TemporaryDirectory(prefix="forge-exemplo-") as tmp:
        pasta = Path(tmp).resolve()
        for passo in ROTEIRO:
            if isinstance(passo, str):
                preparar(passo, pasta)
                continue
            args, esperado = passo
            args = [a.replace("{pasta}", pasta.as_posix()) for a in args]
            texto = rodar(args, pasta, esperado)
            if args[0] not in saida:
                saida[args[0]] = {"comando": sem_caminhos_locais(comando_exibido(args), pasta),
                                  "saida": sem_caminhos_locais(texto, pasta)}
    return saida


# --------------------------------------------------------------------------- fluxo

FASE = re.compile(r"Fase (\d+) — (.+)")
# A frase de resumo de uma seção (D13): a primeira linha não vazia abaixo do título, uma linha só, inteira em
# itálico com asteriscos (*...*, não **...**); dentro, só ** de negrito (*a* e *b* não é uma linha em itálico)
RESUMO = re.compile(r"\*(?![*\s])((?:[^*]|\*\*)+?)(?<![*\s])\*")
# Seções `## ` do SKILL.md que são referência, não parte do fluxo, pelo título inteiro em texto puro: não viram
# transversal. Cada uma precisa existir no SKILL.md: renomear uma delas é erro de geração, nunca transversal calada.
REFERENCIA = {"Peças", "Regras que não se negociam", "Hooks (instalados em ~/.claude/settings.json)"}
# A fase em que o fluxo para e espera o dono (pelo ident() do título): a única com "parada": true
APROVACAO = "aprovacao"
MAX_RESUMO = 300
# Como o references/workflow-onda.js encadeia os papéis de cada tarefa (test_extrair_fluxo confere a ordem)
ETAPAS = [
    {"papeis": ["executor"], "condicional": False, "rotulo": None},
    {"papeis": ["revisor-contrato", "revisor-padroes"], "condicional": False, "rotulo": "em paralelo"},
    {"papeis": ["executor"], "condicional": True, "rotulo": "correção, se houver bloqueante"},
    {"papeis": ["testador"], "condicional": False, "rotulo": None},
]


def texto_puro(md):
    """Markdown de uma linha para texto: sem código, ênfase, links nem marcadores de lista."""
    md = re.sub(r"`([^`]*)`", r"\1", md)
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)
    md = re.sub(r"(\*\*|__)(.+?)\1", r"\2", md)
    md = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", md)
    return re.sub(r"\s+", " ", md).strip()


def secoes(markdown):
    """[(título, corpo)] de cada seção `## ` do Markdown, na ordem, ignorando blocos de código."""
    saida, titulo, corpo, em_codigo = [], None, [], False
    for linha in markdown.splitlines():
        if linha.startswith("```"):
            em_codigo = not em_codigo
        if not em_codigo and linha.startswith("## "):
            if titulo is not None:
                saida.append((titulo, "\n".join(corpo)))
            titulo, corpo = linha[3:].strip(), []
        elif titulo is not None:
            corpo.append(linha)
    if titulo is not None:
        saida.append((titulo, "\n".join(corpo)))
    return saida


def limitar(texto, maximo=MAX_RESUMO):
    """Até `maximo` caracteres: corta no fim da última frase que cabe (a que termina no caractere `maximo`
    cabe) ou, sem frase, na última palavra, com "…"."""
    if len(texto) <= maximo:
        return texto
    frases = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", texto[:maximo + 1]) if m.end() <= maximo]
    if frases:
        return texto[:frases[-1]]
    return texto[:maximo - 1].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"


def resumo(titulo, corpo):
    """A frase de resumo da seção (D13): a primeira linha não vazia do corpo, inteira em itálico (`*...*`).
    Sai sem o itálico, em texto puro, sem caminhos locais e com até MAX_RESUMO caracteres.
    Seção sem essa linha é erro de geração."""
    linha = next((linha.strip() for linha in corpo.splitlines() if linha.strip()), "")
    m = RESUMO.fullmatch(linha)
    if not m:
        raise RuntimeError(f"seção {titulo!r} sem a frase de resumo em itálico (*...*) na linha logo abaixo do "
                           f"título; encontrado: {linha[:80]!r}")
    texto = texto_puro(m.group(1)).strip()
    if not texto:
        raise RuntimeError(f"seção {titulo!r}: a frase de resumo fica vazia em texto puro ({linha!r})")
    return limitar(sem_caminhos_locais(texto))


def ident(titulo):
    """A primeira palavra do título que tem letra ou número, minúscula, sem acento e só com [a-z0-9-]:
    "Decisões no meio..." -> "decisoes". Título sem nenhuma é erro (dois deles colidiriam no id vazio)."""
    for palavra in titulo.split():
        sem_acento = unicodedata.normalize("NFKD", palavra).encode("ascii", "ignore").decode()
        saida = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")
        if saida:
            return saida
    raise RuntimeError(f"título sem letra nem número para virar id: {titulo!r}")


def papeis(forge_py=FORGE_PY):
    """Os papéis da onda, do PAPEIS do forge.py (o que monta a tabela da seção 9 e confere o escreve_codigo),
    com o "faz" em texto puro."""
    return [{"id": i, "nome": p["nome"], "faz": texto_puro(p["faz"]), "escreve_codigo": p["escreve_codigo"]}
            for i, p in carregar_forge(forge_py).PAPEIS.items()]


def gerar_fluxo(skill_md=SKILL_MD, forge_py=FORGE_PY):
    todas = secoes(skill_md.read_text(encoding="utf-8"))
    if not any(FASE.fullmatch(titulo) for titulo, _ in todas):
        raise RuntimeError(f"{skill_md.name}: nenhuma seção '## Fase N — ...'")
    # Antes dos resumos: uma referência renomeada é apontada como tal, não como transversal sem resumo
    faltam = sorted(REFERENCIA - {texto_puro(titulo) for titulo, _ in todas})
    if faltam:
        raise RuntimeError(f"{skill_md.name}: seção de referência não encontrada (renomeada?): {faltam}")
    fases, transversais = [], []
    for titulo, corpo in todas:
        m = FASE.fullmatch(titulo)
        if m:
            n, nome = int(m.group(1)), texto_puro(m.group(2))
            fases.append({"id": f"fase-{n}", "n": n, "titulo": nome, "resumo": resumo(titulo, corpo),
                          "parada": ident(nome) == APROVACAO})
            continue
        nome = texto_puro(titulo)
        if nome not in REFERENCIA:  # transversal, em qualquer posição
            transversais.append({"id": ident(nome), "titulo": nome, "resumo": resumo(titulo, corpo)})
    vistos = set()
    for item in fases + transversais:
        if item["id"] in vistos:
            raise RuntimeError(f"{skill_md.name}: id repetido no fluxo: {item['id']!r} ({item['titulo']})")
        vistos.add(item["id"])
    lista = papeis(forge_py)
    ids = {p["id"] for p in lista}
    for etapa in ETAPAS:
        if not set(etapa["papeis"]) <= ids:
            raise RuntimeError(f"etapa com papel desconhecido: {etapa['papeis']}")
    return {"fases": fases, "transversais": transversais,
            "onda": {"papeis": lista, "etapas": copy.deepcopy(ETAPAS)}}


# --------------------------------------------------------------------------- saída

def gerar():
    lista = comandos(carregar_forge().montar_parser())
    exs = exemplos()
    for c in lista:
        c["exemplo"] = exs.get(c["nome"])
    return {"gerado_de": "scripts/forge.py", "comandos": lista}


def gravar(dados, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    for dados, destino in ((gerar(), DESTINO_COMANDOS), (gerar_fluxo(), DESTINO_FLUXO)):
        gravar(dados, destino)
        print(f"gerado: {destino.relative_to(SITE).as_posix()}")


if __name__ == "__main__":
    main()
