#!/usr/bin/env python3
"""forge — plano de trabalho vivo para projetos divididos em frentes e tocados por agentes.

O estado mora em forge-<slug>.json. O forge-<slug>.md ao lado é GERADO a partir dele a cada
alteração — não se edita o .md à mão. Rode `python forge.py -h` para ver os comandos.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

VERSAO = 1
RAIZ_SKILL = Path(__file__).resolve().parent.parent
REFERENCIAS = RAIZ_SKILL / "references"
REGISTRO = Path(os.environ.get("FORGE_REGISTRO") or Path.home() / ".claude" / "forge" / "registro.json")

FASES = ["requisitos", "aguardando-aprovacao", "aprovado", "em-execucao", "fechado"]
ESTADOS = {"pendente": "☐", "feito": "✔", "revisar": "⟳"}
PAPEIS = ["executor", "revisor-contrato", "revisor-padroes", "testador"]

# Modelo e esforço de cada papel por complexidade da tarefa. O plano pode sobrepor qualquer célula em
# agentes.modelos; o Opus fica só onde errar custa caro (código difícil e furo de contrato).
COMPLEXIDADES = ["baixa", "media", "alta"]
MODELOS = ["haiku", "sonnet", "opus"]
ESFORCOS = ["low", "medium", "high", "xhigh", "max"]
MODELOS_PADRAO = {
    "executor":         {"baixa": ("sonnet", "medium"), "media": ("sonnet", "high"),  "alta": ("opus", "high")},
    "revisor-contrato": {"baixa": ("sonnet", "low"),    "media": ("sonnet", "high"),  "alta": ("opus", "high")},
    "revisor-padroes":  {"baixa": ("haiku", "medium"),  "media": ("sonnet", "medium"), "alta": ("sonnet", "high")},
    "testador":         {"baixa": ("haiku", "medium"),  "media": ("sonnet", "medium"), "alta": ("sonnet", "high")},
}
# D, Q e R já numeram decisões, dúvidas e requisitos — uma frente com essas letras confundiria os IDs
FRENTES_RESERVADAS = {"D", "Q", "R"}

REGRAS_PADRAO = [
    "Contrato não se muda de um lado só. Quem esbarrar num problema com um contrato **para e reporta** — não adapta do seu lado.",
    "Uma tarefa faz uma coisa só, termina e é testada sozinha. Quando depende de outra, a dependência está escrita nela.",
    "Um commit por tarefa (ou mais, nunca menos), com a mensagem começando pelo ID: `A3: ...`.",
    "Só a sessão principal altera o plano, e sempre pelo `forge.py`. Agentes reportam; quem integra marca o ✔.",
    "Se o repositório e o plano discordarem, o repositório tem razão — corrija o plano.",
    "Decisão nova é linha nova. As antigas não são apagadas: são revogadas e viram histórico.",
    "Nada de conectar em banco nem executar SQL (regra da organização), exceto banco local `torge_*`. Migration e DAO se escrevem e se revisam; quem roda é o dono do projeto.",
    "Restrição escrita no plano envelhece: confira com um teste de um minuto antes de repassar para um agente.",
]


# --------------------------------------------------------------------------- utilidades

def hoje():
    return datetime.date.today().isoformat()


def normalizar(caminho):
    return os.path.normcase(os.path.realpath(str(caminho)))


def dentro_de(caminho, pasta):
    c, p = normalizar(caminho), normalizar(pasta)
    return c == p or c.startswith(p.rstrip("\\/") + os.sep)


def erro(msg, codigo=2):
    print(f"forge: {msg}", file=sys.stderr)
    sys.exit(codigo)


def celula(texto):
    return str(texto or "").replace("|", "\\|").replace("\n", "<br>")


def configurar_saida():
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


# --------------------------------------------------------------------------- plano em disco

def caminho_md(caminho_json):
    return Path(caminho_json).with_suffix(".md")


def carregar(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        erro(f"plano não encontrado: {caminho}")
    with open(caminho, encoding="utf-8") as f:
        plano = json.load(f)
    if plano.get("forge") != VERSAO:
        erro(f"{caminho} não é um plano forge v{VERSAO}")
    return plano


def salvar(caminho, plano):
    """Valida, carimba a data, grava o JSON e regenera o Markdown. Plano inválido não é gravado."""
    problemas = validar(plano)
    if problemas:
        erro("plano inválido, nada foi gravado:\n  - " + "\n  - ".join(problemas))
    plano["atualizado"] = hoje()
    texto_md = gerar_md(plano, caminho)
    plano["md_sha"] = hashlib.sha256(texto_md.encode("utf-8")).hexdigest()[:16]
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        json.dump(plano, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(caminho_md(caminho), "w", encoding="utf-8", newline="\n") as f:
        f.write(texto_md)


def plano_vazio(slug, titulo, dono, branch, base):
    return {
        "forge": VERSAO,
        "slug": slug,
        "titulo": titulo,
        "dono": dono,
        "criado": hoje(),
        "atualizado": hoje(),
        "fase": "requisitos",
        "aprovado_em": None,
        "branch": branch or slug,
        "base": base,
        "objetivo": "",
        "requisitos": [],
        "regras": list(REGRAS_PADRAO),
        "frentes": [],
        "decisoes": [],
        "apurado": [],
        "duvidas": [],
        "contratos": [],
        "tarefas": [],
        "rodadas": [],
        "agentes": {"push": False, "licoes": []},
        "pendencias_dono": [],
    }


def validar(plano):
    problemas = []
    if plano.get("fase") not in FASES:
        problemas.append(f"fase inválida: {plano.get('fase')} (use {', '.join(FASES)})")

    frentes = {}
    for f in plano.get("frentes", []):
        fid = f.get("id", "")
        if not re.fullmatch(r"[A-Z]{1,3}", fid):
            problemas.append(f"frente com id inválido: {fid!r} (1 a 3 letras maiúsculas)")
        elif fid in FRENTES_RESERVADAS:
            problemas.append(f"frente {fid}: as letras D, Q e R são reservadas")
        if fid in frentes:
            problemas.append(f"frente {fid} repetida")
        if not f.get("repo"):
            problemas.append(f"frente {fid} sem repo")
        frentes[fid] = f

    ids = {}
    for t in plano.get("tarefas", []):
        tid = t.get("id", "")
        if tid in ids:
            problemas.append(f"tarefa {tid} repetida")
        ids[tid] = t
        if t.get("frente") not in frentes:
            problemas.append(f"tarefa {tid}: frente {t.get('frente')!r} não existe")
        elif not re.fullmatch(re.escape(t["frente"]) + r"\d+", tid):
            problemas.append(f"tarefa {tid}: o ID deve ser a letra da frente seguida de número ({t['frente']}N)")
        if t.get("estado") not in ESTADOS:
            problemas.append(f"tarefa {tid}: estado inválido {t.get('estado')!r}")
        if not t.get("como_testar"):
            problemas.append(f"tarefa {tid}: falta 'como_testar' — toda tarefa precisa provar que funciona sozinha")
        if t.get("complexidade", "media") not in COMPLEXIDADES:
            problemas.append(f"tarefa {tid}: complexidade inválida {t.get('complexidade')!r} (use {', '.join(COMPLEXIDADES)})")
    for papel, niveis_ in (plano.get("agentes", {}).get("modelos") or {}).items():
        if papel not in MODELOS_PADRAO:
            problemas.append(f"agentes.modelos: papel {papel!r} não existe")
            continue
        for nivel, escolha in niveis_.items():
            if nivel not in COMPLEXIDADES:
                problemas.append(f"agentes.modelos.{papel}: complexidade {nivel!r} não existe")
            elif (escolha.get("modelo") not in MODELOS) or (escolha.get("esforco") not in ESFORCOS):
                problemas.append(f"agentes.modelos.{papel}.{nivel}: modelo em {MODELOS} e esforco em {ESFORCOS}")
    for t in plano.get("tarefas", []):
        for d in t.get("depende", []):
            if d not in ids:
                problemas.append(f"tarefa {t['id']}: depende de {d}, que não existe")
    if not problemas:
        try:
            niveis(plano)
        except ValueError as e:
            problemas.append(str(e))

    decisoes = {d.get("id") for d in plano.get("decisoes", [])}
    for d in plano.get("decisoes", []):
        if d.get("revoga") and d["revoga"] not in decisoes:
            problemas.append(f"{d['id']} revoga {d['revoga']}, que não existe")
        for a in d.get("afeta", []):
            if a not in ids:
                problemas.append(f"{d['id']} afeta {a}, que não existe")
        contratos = {c.get("id") for c in plano.get("contratos", [])}
        for c in d.get("contratos", []):
            if c not in contratos:
                problemas.append(f"{d['id']} altera o contrato {c}, que não existe")
    for c in plano.get("contratos", []):
        for fid in c.get("entre", []):
            if fid not in frentes:
                problemas.append(f"contrato {c.get('id')}: frente {fid} não existe")
    return problemas


def niveis(plano):
    """Nível de cada tarefa no grafo de dependências (0 = não depende de nada). Erra em ciclo."""
    por_id = {t["id"]: t for t in plano["tarefas"]}
    nivel, visitando = {}, set()

    def calcular(tid):
        if tid in nivel:
            return nivel[tid]
        if tid in visitando:
            raise ValueError(f"dependência circular passando por {tid}")
        visitando.add(tid)
        deps = por_id[tid].get("depende", [])
        nivel[tid] = 1 + max((calcular(d) for d in deps), default=-1)
        visitando.discard(tid)
        return nivel[tid]

    for tid in por_id:
        calcular(tid)
    return nivel


def proximo_id(prefixo, existentes):
    numeros = [int(m.group(1)) for e in existentes if (m := re.fullmatch(re.escape(prefixo) + r"(\d+)", e))]
    return f"{prefixo}{max(numeros, default=0) + 1}"


def frente(plano, fid):
    for f in plano["frentes"]:
        if f["id"] == fid:
            return f
    erro(f"frente {fid} não existe")


def tarefa(plano, tid):
    for t in plano["tarefas"]:
        if t["id"] == tid:
            return t
    erro(f"tarefa {tid} não existe")


def modelos_efetivos(plano):
    """{papel: {complexidade: {modelo, esforco}}}: o padrão com as células que o plano sobrepõe."""
    sobrepostos = plano.get("agentes", {}).get("modelos") or {}
    return {papel: {nivel: dict({"modelo": modelo, "esforco": esforco}, **sobrepostos.get(papel, {}).get(nivel, {}))
                    for nivel, (modelo, esforco) in por_nivel.items()}
            for papel, por_nivel in MODELOS_PADRAO.items()}


def decisoes_em_vigor(plano):
    revogadas = {d["revoga"] for d in plano["decisoes"] if d.get("revoga")}
    return [d for d in plano["decisoes"] if d["id"] not in revogadas]


def bloqueio(plano, t):
    """Lista das dependências ainda não feitas."""
    estado = {x["id"]: x["estado"] for x in plano["tarefas"]}
    return [d for d in t.get("depende", []) if estado.get(d) != "feito"]


# --------------------------------------------------------------------------- git

def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def existe_ref(repo, ref):
    return git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}") is not None


def ref_base(repo, base):
    for ref in (base, f"origin/{base}"):
        if base and existe_ref(repo, ref):
            return ref
    return None


def ids_do_assunto(assunto):
    """IDs de tarefa no começo da mensagem: 'A3: x', 'A3, A4: x', 'A27 (T9): x', 'B2 e C4: x'."""
    m = re.match(r"\s*([A-Z]{1,3}\d+(?:\s*(?:,|/|\+|\be\b)\s*[A-Z]{1,3}\d+)*)\b", assunto)
    return re.findall(r"[A-Z]{1,3}\d+", m.group(1)) if m else []


def commits_da_frente(plano, f):
    """Commits da branch do plano que ainda não estão na base, do mais novo para o mais antigo."""
    repo, branch = f["repo"], f.get("branch") or plano["branch"]
    if not Path(repo).exists() or not existe_ref(repo, branch):
        return None
    base = ref_base(repo, f.get("base") or plano.get("base"))
    intervalo = f"{base}..{branch}" if base else branch
    saida = git(repo, "log", "--no-merges", "--format=%H%x09%cI%x09%s", "-n", "500", intervalo) or ""
    commits = []
    for linha in saida.splitlines():
        sha, data, assunto = (linha.split("\t", 2) + ["", ""])[:3]
        commits.append({"sha": sha, "data": data[:10], "assunto": assunto, "ids": ids_do_assunto(assunto)})
    return commits


def commits_por_tarefa(plano):
    """{tid: [commits]} e {frente: lista de commits ou None se a branch não existe}."""
    por_tarefa, por_frente, vistos = {}, {}, set()
    for f in plano["frentes"]:
        commits = commits_da_frente(plano, f)
        por_frente[f["id"]] = commits
        for c in commits or []:
            # frentes no mesmo repositório leem o mesmo git log: cada commit conta uma vez só
            if c["sha"] in vistos:
                continue
            vistos.add(c["sha"])
            for tid in c["ids"]:
                por_tarefa.setdefault(tid, []).append(c)
    return por_tarefa, por_frente


# --------------------------------------------------------------------------- Markdown

def gerar_md(plano, caminho_json):
    nome_json = Path(caminho_json).name
    tarefas = plano["tarefas"]
    feitas = sum(1 for t in tarefas if t["estado"] == "feito")
    revisar = [t["id"] for t in tarefas if t["estado"] == "revisar"]
    livres = [t["id"] for t in tarefas if t["estado"] != "feito" and not bloqueio(plano, t)]
    abertas = [q for q in plano["duvidas"] if not q.get("resposta")]
    pend_dono = [p for p in plano["pendencias_dono"] if not p.get("feito")]
    l = []
    a = l.append

    a(f"# {plano['titulo']} — plano de trabalho\n")
    a(f"*Documento vivo, **gerado** de `{nome_json}` pelo `forge.py` — não edite este arquivo à mão: "
      "a próxima geração apaga a edição. Ele é a fonte da verdade do trabalho, não o histórico da conversa.*\n")
    a("---\n")

    a("## 0. Estado atual — comece por aqui\n")
    a("| | |\n|---|---|")
    a(f"| Fase | **{plano['fase']}**" + (f" (aprovado em {plano['aprovado_em']})" if plano.get("aprovado_em") else "") + " |")
    a(f"| Última atualização | {plano['atualizado']} |")
    a(f"| Dono | {celula(plano['dono'])} |")
    a(f"| Branch | `{plano['branch']}` sobre `{plano.get('base') or '—'}` em todos os repositórios |")
    a(f"| Tarefas | **{feitas} de {len(tarefas)}** feitas" + (f" · a revisar: {', '.join(revisar)}" if revisar else "") + " |")
    for f in plano["frentes"]:
        ts = [t for t in tarefas if t["frente"] == f["id"]]
        a(f"| Frente {f['id']} · {celula(f['nome'])} | {sum(1 for t in ts if t['estado'] == 'feito')} de {len(ts)} |")
    a(f"| Próximas desbloqueadas | {', '.join(livres) or '—'} |")
    a(f"| Dúvidas em aberto | {', '.join(q['id'] for q in abertas) or 'nenhuma'} |")
    a(f"| Pendências do dono | {len(pend_dono)} (seção 11) |")
    a("")
    a("**Como retomar numa sessão nova:** chame `/forge` (ou rode `forge.py status` e `forge.py drift`). "
      "O que vale é o que está commitado nas branches; se o plano discordar do `git log`, o repositório "
      "tem razão. Agente não sobrevive à troca de sessão — o que sobrevive é o commit e o ✔.\n")

    a("## 1. Objetivo e requisitos\n")
    a((plano.get("objetivo") or "*(a preencher)*") + "\n")
    if plano["requisitos"]:
        a("| # | Requisito | Fonte |\n|---|---|---|")
        for r in plano["requisitos"]:
            a(f"| {r['id']} | {celula(r['texto'])} | {celula(r.get('fonte'))} |")
        a("")

    a("## 2. Como vamos trabalhar\n")
    a(f"O trabalho está dividido em **{len(plano['frentes'])} frente(s)**, cada uma no seu repositório e na branch `{plano['branch']}`:\n")
    if plano["frentes"]:
        a("| Frente | Repositório | Stack | Como testar a frente | Restrições |\n|---|---|---|---|---|")
        for f in plano["frentes"]:
            a(f"| **{f['id']} · {celula(f['nome'])}** | `{celula(f['repo'])}` | {celula(f.get('stack'))} | "
              f"{celula(f.get('como_testar'))} | {celula('; '.join(f.get('proibido', [])))} |")
        a("")
    a("Regras do jogo:\n")
    for r in plano["regras"]:
        a(f"- {r}")
    a("")

    a("## 3. Decisões já tomadas\n")
    if plano["decisoes"]:
        revogadas = {d["revoga"]: d["id"] for d in plano["decisoes"] if d.get("revoga")}
        a("| # | Data | Assunto | Decisão |\n|---|---|---|---|")
        for d in plano["decisoes"]:
            texto = celula(d["texto"])
            if d["id"] in revogadas:
                texto = f"~~{texto}~~ — revogada pela {revogadas[d['id']]}"
            extra = f" *(afeta {', '.join(d['afeta'])})*" if d.get("afeta") else ""
            a(f"| {d['id']} | {d.get('data', '')} | {celula(d.get('assunto'))} | {texto}{extra} |")
        a("")
    else:
        a("*(nenhuma ainda)*\n")

    a("## 4. O que foi apurado no código\n")
    a("Fatos lidos nos repositórios, não suposições — para ninguém precisar redescobrir.\n")
    for item in plano["apurado"]:
        a(f"### {item['area']}\n\n{item['texto']}\n")
    if not plano["apurado"]:
        a("*(a levantar)*\n")

    a("## 5. Dúvidas\n")
    if plano["duvidas"]:
        a("| # | Dúvida | Resposta | Virou |\n|---|---|---|---|")
        for q in plano["duvidas"]:
            a(f"| {q['id']} | {celula(q['texto'])} | {celula(q.get('resposta') or '**em aberto**')} | {q.get('decisao') or '—'} |")
        a("")
    else:
        a("*(nenhuma)*\n")

    a("## 6. Contratos entre as frentes\n")
    a("> **Regra:** contrato não se muda sozinho. Quem esbarrar num problema com o que está escrito aqui "
      "**para e reporta** — não adapta do seu lado. Uma frente que adapta em silêncio quebra as outras, "
      "e o erro só aparece na integração.\n")
    for c in plano["contratos"]:
        a(f"### {c['id']} {c['titulo']}\n")
        alterado = [d["id"] for d in plano["decisoes"] if c["id"] in d.get("contratos", [])]
        a(f"*Entre as frentes {', '.join(c.get('entre', []))}."
          + (f" Alterado pela(s) {', '.join(alterado)}." if alterado else "") + "*\n")
        a(c["texto"] + "\n")
    if not plano["contratos"]:
        a("*(nenhum — as frentes não conversam entre si)*\n")

    a("## 7. Tarefas\n")
    for f in plano["frentes"]:
        a(f"### Frente {f['id']} · {f['nome']} (`{f['repo']}`)\n")
        a("| ✔ | # | Tarefa | Como testar | Depende de | Complexidade | Commit |\n|---|---|---|---|---|---|---|")
        for t in tarefas:
            if t["frente"] != f["id"]:
                continue
            commit = ", ".join(f"`{s[:8]}`" for s in t.get("commits", [])) or "—"
            a(f"| {ESTADOS[t['estado']]} | {t['id']} | {celula(t['titulo'])} | {celula(t['como_testar'])} | "
              f"{', '.join(t.get('depende', [])) or '—'} | {t.get('complexidade', 'media')} | {commit} |")
        a("")
    a("`☐` não começada · `✔` feita, testada e commitada · `⟳` feita, mas uma decisão posterior pede revisão.\n")

    a("## 8. Ordem e dependências\n")
    if tarefas:
        nivel = niveis(plano)
        for n in range(max(nivel.values()) + 1):
            a(f"- **Onda {n + 1}:** " + ", ".join(
                f"{t['id']}{'' if t['estado'] != 'feito' else ' ✔'}" for t in tarefas if nivel[t["id"]] == n))
        a("\nTarefas da mesma onda podem andar em paralelo, desde que estejam em repositórios diferentes.\n")

    a("## 9. Tocar o trabalho com agentes\n")
    a("Cada tarefa passa por quatro papéis, numa onda executada pelo `references/workflow-onda.js` da skill:\n")
    a("| Papel | O que faz | Escreve código? |\n|---|---|---|")
    a("| **Executor** | Faz a tarefa, testa e commita com o ID na mensagem. | sim |")
    a("| **Revisor de contrato** | Adversarial: procura onde a mudança contraria uma decisão, quebra um contrato ou outra frente. | não |")
    a("| **Revisor de padrões** | Padrões do repositório (CLAUDE.md, README, lint, skills de padrões da stack) e simplicidade; sempre procura uma forma mais simples, reutilizável ou genérica de fazer o mesmo. | não |")
    a("| **Testador** | Independente: confere o *como testar*, escreve o teste que falta e roda. Não corrige código de produção. | só testes |")
    a("")
    a(f"Push ao terminar: **{'sim' if plano['agentes'].get('push') else 'não — só commit local'}**.\n")
    a("Modelo e esforço de cada papel, pela complexidade da tarefa (coluna da seção 7; `agentes.modelos` no "
      "JSON sobrepõe o padrão):\n")
    a("| Papel | " + " | ".join(COMPLEXIDADES) + " |\n|---|" + "---|" * len(COMPLEXIDADES))
    efetivos = modelos_efetivos(plano)
    for papel in MODELOS_PADRAO:
        a(f"| {papel} | " + " | ".join("{modelo} · {esforco}".format(**efetivos[papel][n]) for n in COMPLEXIDADES) + " |")
    a("")
    if plano["agentes"].get("licoes"):
        a("O que as rodadas anteriores ensinaram:\n")
        for li in plano["agentes"]["licoes"]:
            a(f"- {li}")
        a("")

    a("## 10. Rodadas\n")
    for r in plano["rodadas"]:
        a(f"### Rodada {r['n']} — {r['titulo']} ({r['data']})\n")
        a(r["registro"] + "\n")
    if not plano["rodadas"]:
        a("*(nenhuma ainda)*\n")

    a("## 11. O que fica com o dono\n")
    a("Coisas que só o dono do projeto pode fazer (rodar contra banco, subir em servidor, decidir).\n")
    for i, p in enumerate(plano["pendencias_dono"], 1):
        a(f"{i}. {'~~' + p['texto'] + '~~ feito' if p.get('feito') else p['texto']}")
    if not plano["pendencias_dono"]:
        a("*(nada)*")
    return "\n".join(l).rstrip() + "\n"


# --------------------------------------------------------------------------- registro de planos

def ler_registro():
    try:
        with open(REGISTRO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"planos": []}


def registrar(caminho):
    reg = ler_registro()
    alvo = str(Path(caminho).resolve())
    if normalizar(alvo) not in {normalizar(p) for p in reg["planos"]}:
        reg["planos"].append(alvo)
        REGISTRO.parent.mkdir(parents=True, exist_ok=True)
        with open(REGISTRO, "w", encoding="utf-8") as f:
            json.dump(reg, f, ensure_ascii=False, indent=2)


def planos_registrados():
    """(caminho, plano) de cada plano registrado que ainda existe e é legível."""
    saida = []
    for p in ler_registro()["planos"]:
        try:
            with open(p, encoding="utf-8") as f:
                plano = json.load(f)
            if plano.get("forge") == VERSAO:
                saida.append((Path(p), plano))
        except (OSError, ValueError):
            continue
    return saida


def planos_do_diretorio(cwd):
    """Planos que interessam a quem abriu uma sessão em `cwd`: o da pasta do plano ou de uma frente."""
    saida = []
    for caminho, plano in planos_registrados():
        pastas = [caminho.parent] + [f["repo"] for f in plano.get("frentes", [])]
        if any(dentro_de(cwd, p) for p in pastas):
            saida.append((caminho, plano))
    return saida


# --------------------------------------------------------------------------- status e drift

def texto_status(caminho, plano, com_git=True):
    por_tarefa = commits_por_tarefa(plano)[0] if com_git else {}
    tarefas = plano["tarefas"]
    feitas = sum(1 for t in tarefas if t["estado"] == "feito")
    l = [f"{Path(caminho).name} — {plano['titulo']} · fase {plano['fase']} · atualizado {plano['atualizado']}",
         f"Tarefas: {feitas}/{len(tarefas)} ✔"]
    for f in plano["frentes"]:
        ts = [t for t in tarefas if t["frente"] == f["id"]]
        l.append(f"  {f['id']} · {f['nome']} — {sum(1 for t in ts if t['estado'] == 'feito')}/{len(ts)}  "
                 f"[{f['repo']} @ {f.get('branch') or plano['branch']}]")
        for t in ts:
            falta = bloqueio(plano, t)
            if t["estado"] == "feito":
                info = ", ".join(s[:8] for s in t.get("commits", [])) or "sem commit registrado"
            elif falta:
                info = "espera " + ", ".join(falta)
            else:
                info = "desbloqueada"
            if t["estado"] != "feito" and t["id"] in por_tarefa:
                info += f" · já tem commit ({por_tarefa[t['id']][0]['sha'][:8]}) — marcar?"
            l.append(f"    {ESTADOS[t['estado']]} {t['id']} {t['titulo']} — {info}")
    abertas = [q["id"] for q in plano["duvidas"] if not q.get("resposta")]
    if abertas:
        l.append("Dúvidas em aberto: " + ", ".join(abertas))
    dono = [p["texto"] for p in plano["pendencias_dono"] if not p.get("feito")]
    if dono:
        l.append(f"Pendências do dono: {len(dono)}")
    livres = [t["id"] for t in tarefas if t["estado"] != "feito" and not bloqueio(plano, t)]
    l.append("Próximas: " + (", ".join(livres) or "nenhuma"))
    return "\n".join(l)


def achar_drift(caminho, plano):
    """Divergências entre o plano e os repositórios. Cada item: (tipo, mensagem)."""
    achados = []
    por_tarefa, por_frente = commits_por_tarefa(plano)
    ids = {t["id"]: t for t in plano["tarefas"]}
    vistos = set()

    for f in plano["frentes"]:
        commits = por_frente[f["id"]]
        branch = f.get("branch") or plano["branch"]
        if not Path(f["repo"]).exists():
            achados.append(("repo", f"frente {f['id']}: repositório {f['repo']} não existe"))
            continue
        if commits is None:
            if plano["fase"] in ("em-execucao", "fechado") or any(
                    t["estado"] == "feito" for t in plano["tarefas"] if t["frente"] == f["id"]):
                achados.append(("branch", f"frente {f['id']}: branch {branch} não existe em {f['repo']}"))
            continue
        for c in commits:
            if c["sha"] in vistos:
                continue
            vistos.add(c["sha"])
            if not c["ids"]:
                achados.append(("sem-tarefa", f"{f['id']} {c['sha'][:8]} sem ID de tarefa: {c['assunto']}"))
            for tid in c["ids"]:
                if tid not in ids:
                    achados.append(("tarefa-inexistente", f"{f['id']} {c['sha'][:8]} cita {tid}, que não está no plano"))

    for t in plano["tarefas"]:
        commits = por_tarefa.get(t["id"], [])
        if t["estado"] == "feito" and not commits and not t.get("commits"):
            achados.append(("feito-sem-commit", f"{t['id']} está ✔ mas nenhum commit cita esse ID"))
        if t["estado"] == "pendente" and commits:
            achados.append(("commit-sem-feito", f"{t['id']} tem commit ({commits[0]['sha'][:8]}) mas está ☐ — rode `marcar {t['id']}`"))

    for d in decisoes_em_vigor(plano):
        for tid in d.get("afeta", []):
            t = ids.get(tid)
            if not t or t["estado"] != "feito":
                continue
            datas = [c["data"] for c in por_tarefa.get(tid, [])]
            if datas and max(datas) < d.get("data", ""):
                achados.append(("decisao-posterior", f"{tid} foi feita em {max(datas)}, antes da {d['id']} ({d['data']}) que a afeta — revisar"))

    md = caminho_md(caminho)
    if md.exists():
        atual = hashlib.sha256(md.read_text(encoding="utf-8").encode("utf-8")).hexdigest()[:16]
        if plano.get("md_sha") and atual != plano["md_sha"]:
            achados.append(("md-editado", f"{md.name} foi editado à mão — passe a mudança para o JSON e rode `md`"))
    else:
        achados.append(("md-ausente", f"{md.name} não existe — rode `md`"))
    return achados


# --------------------------------------------------------------------------- briefings e ondas

def lista_md(itens, vazio="*(nenhum)*"):
    return "\n".join(itens) if itens else vazio


def montar_briefing(caminho, plano, t, papel):
    f = frente(plano, t["frente"])
    modelo = (REFERENCIAS / f"briefing-{papel}.md").read_text(encoding="utf-8")
    deps = t.get("depende", [])
    contratos = [f"### {c['id']} {c['titulo']}\n\n{c['texto']}" for c in plano["contratos"] if f["id"] in c.get("entre", [])]
    decisoes = [f"- **{d['id']}** ({d.get('assunto', '')}): {d['texto']}" for d in decisoes_em_vigor(plano)]
    push = plano["agentes"].get("push")
    notas = t.get("notas") or ""
    if t["estado"] == "revisar":
        motivos = [d for d in decisoes_em_vigor(plano) if t["id"] in d.get("afeta", [])]
        notas = (f"**Esta tarefa já foi feita** (commits {', '.join(s[:8] for s in t.get('commits', [])) or '—'}) "
                 "e voltou por causa de decisão tomada depois: "
                 + "; ".join(f"**{d['id']}** — {d['texto']}" for d in motivos)
                 + ". Ajuste o que já existe para cumprir a decisão; não refaça do zero.\n\n" + notas)
    valores = {
        "titulo_projeto": plano["titulo"],
        "plano_md": str(caminho_md(caminho).resolve()),
        "repo": f["repo"],
        "branch": f.get("branch") or plano["branch"],
        "base": f.get("base") or plano.get("base") or "—",
        "frente": f"{f['id']} · {f['nome']}",
        "tarefa_id": t["id"],
        "tarefa_titulo": t["titulo"],
        "como_testar": t["como_testar"],
        "depende": ", ".join(f"{d} ({tarefa(plano, d)['titulo']})" for d in deps) or "nada",
        "notas": notas,
        "contratos": lista_md(contratos, "*(nenhum contrato envolve esta frente)*"),
        "decisoes": lista_md(decisoes, "*(nenhuma)*"),
        "regras": lista_md([f"- {r}" for r in plano["regras"]]),
        "teste_frente": f.get("como_testar") or "*(não definido — descubra no README/CLAUDE.md e diga no relatório)*",
        "proibido": lista_md([f"- {p}" for p in f.get("proibido", [])], "*(nenhuma além das regras)*"),
        "push": "Faça **push** da branch ao terminar." if push else "**Não faça push** — só commit local.",
    }
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(valores.get(m.group(1), m.group(0))), modelo)


def montar_onda(caminho, plano, maximo):
    """Escolhe as tarefas da próxima onda, grava os briefings em disco e devolve o `args` do workflow.

    Entra a tarefa não feita cujas dependências estão feitas ou vêm antes dela na mesma fila (mesmo
    repositório, executadas em sequência). Frentes no mesmo repositório viram uma fila só.
    """
    pasta = Path(caminho).parent / f"forge-{plano['slug']}.briefings"
    pasta.mkdir(exist_ok=True)
    filas, escolhidas, fora = {}, set(), []
    nivel = niveis(plano)
    candidatas = sorted((t for t in plano["tarefas"] if t["estado"] != "feito"),
                        key=lambda t: (nivel[t["id"]], plano["tarefas"].index(t)))
    for t in candidatas:
        repo = normalizar(frente(plano, t["frente"])["repo"])
        fila = filas.setdefault(repo, {"repo": frente(plano, t["frente"])["repo"], "frentes": [], "tarefas": []})
        na_fila = {x["id"] for x in fila["tarefas"]}
        if not all(d in na_fila or tarefa(plano, d)["estado"] == "feito" for d in t.get("depende", [])):
            continue
        if len(escolhidas) >= maximo:
            fora.append(t["id"])
            continue
        briefings = {}
        for papel in PAPEIS:
            arq = pasta / f"{t['id']}-{papel}.md"
            arq.write_text(montar_briefing(caminho, plano, t, papel), encoding="utf-8", newline="\n")
            briefings[papel.replace("-", "_")] = str(arq.resolve())
        nivel_t = t.get("complexidade", "media")
        modelos = {papel.replace("-", "_"): {"model": escolha[nivel_t]["modelo"], "effort": escolha[nivel_t]["esforco"]}
                   for papel, escolha in modelos_efetivos(plano).items()}
        fila["tarefas"].append({"id": t["id"], "titulo": t["titulo"], "complexidade": nivel_t,
                                "briefings": briefings, "modelos": modelos})
        if t["frente"] not in fila["frentes"]:
            fila["frentes"].append(t["frente"])
        escolhidas.add(t["id"])
    return {
        "plano": str(Path(caminho).resolve()),
        "filas": [{"id": "+".join(q["frentes"]), "repo": q["repo"], "tarefas": q["tarefas"]}
                  for q in filas.values() if q["tarefas"]],
        "fora": fora,
    }


# --------------------------------------------------------------------------- comandos

def cmd_novo(a):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", a.slug):
        erro("slug: só minúsculas, números e hífen")
    caminho = Path(a.dir).resolve() / f"forge-{a.slug}.json"
    if caminho.exists():
        erro(f"{caminho} já existe")
    salvar(caminho, plano_vazio(a.slug, a.titulo, a.dono, a.branch, a.base))
    registrar(caminho)
    print(caminho)


def cmd_registrar(a):
    carregar(a.plano)
    registrar(a.plano)
    print(f"registrado: {Path(a.plano).resolve()}")


def cmd_lista(a):
    for caminho, plano in planos_registrados():
        feitas = sum(1 for t in plano["tarefas"] if t["estado"] == "feito")
        print(f"{plano['fase']:<22} {feitas}/{len(plano['tarefas'])}  {caminho}")


def cmd_md(a):
    plano = carregar(a.plano)
    salvar(a.plano, plano)
    print(f"gerado: {caminho_md(a.plano)}")


def cmd_validar(a):
    problemas = validar(carregar(a.plano))
    for p in problemas:
        print(f"- {p}")
    print("ok" if not problemas else f"{len(problemas)} problema(s)")
    sys.exit(1 if problemas else 0)


def cmd_status(a):
    plano = carregar(a.plano)
    if a.json:
        print(json.dumps({t["id"]: {"estado": t["estado"], "espera": bloqueio(plano, t)} for t in plano["tarefas"]},
                         ensure_ascii=False, indent=2))
        return
    print(texto_status(a.plano, plano, com_git=not a.sem_git))
    if not a.sem_git:
        achados = achar_drift(a.plano, plano)
        if achados:
            print(f"Drift: {len(achados)} divergência(s) — rode `drift` para ver")


def cmd_drift(a):
    achados = achar_drift(a.plano, carregar(a.plano))
    for tipo, msg in achados:
        print(f"[{tipo}] {msg}")
    print("sem divergências" if not achados else f"{len(achados)} divergência(s)")
    sys.exit(1 if achados else 0)


def cmd_marcar(a):
    plano = carregar(a.plano)
    t = tarefa(plano, a.id)
    if a.pendente or a.revisar:
        t["estado"] = "pendente" if a.pendente else "revisar"
    else:
        commits = a.commit or [c["sha"] for c in commits_por_tarefa(plano)[0].get(a.id, [])]
        if not commits and not a.forcar:
            erro(f"nenhum commit cita {a.id} na branch — passe --commit SHA ou --forcar")
        t["estado"] = "feito"
        anteriores = t.get("commits", [])
        t["commits"] = anteriores + [c for c in commits if c not in anteriores]
    salvar(a.plano, plano)
    print(f"{ESTADOS[t['estado']]} {t['id']} {t['titulo']}")


def cmd_tarefa(a):
    plano = carregar(a.plano)
    frente(plano, a.frente)
    tid = proximo_id(a.frente, [t["id"] for t in plano["tarefas"]])
    plano["tarefas"].append({"id": tid, "frente": a.frente, "titulo": a.titulo, "como_testar": a.testar,
                             "depende": a.depende or [], "estado": "pendente", "commits": [],
                             "complexidade": a.complexidade, "rodada": len(plano["rodadas"]) + 1,
                             "notas": a.notas or ""})
    salvar(a.plano, plano)
    print(tid)


def cmd_complexidade(a):
    plano = carregar(a.plano)
    for tid in a.ids:
        tarefa(plano, tid)["complexidade"] = a.nivel
    salvar(a.plano, plano)
    print(f"{', '.join(a.ids)}: {a.nivel}")


def cmd_decisao(a):
    plano = carregar(a.plano)
    did = proximo_id("D", [d["id"] for d in plano["decisoes"]])
    plano["decisoes"].append({"id": did, "data": a.data or hoje(), "assunto": a.assunto, "texto": a.texto,
                              "afeta": a.afeta or [], "revoga": a.revoga, "contratos": a.contrato or []})
    if a.duvida:
        for q in plano["duvidas"]:
            if q["id"] == a.duvida:
                q["decisao"] = did
    # Tarefa feita que a decisão afeta volta para a fila como ⟳ — a próxima onda a pega com o motivo no briefing
    reabertas = []
    for tid in a.afeta or []:
        t = next((x for x in plano["tarefas"] if x["id"] == tid), None)
        if t and t["estado"] == "feito":
            t["estado"] = "revisar"
            reabertas.append(tid)
    salvar(a.plano, plano)
    print(did)
    if reabertas:
        print(f"reabertas para revisão (⟳): {', '.join(reabertas)}")
    if a.contrato:
        frentes = sorted({f for c in plano["contratos"] if c["id"] in a.contrato for f in c.get("entre", [])})
        print(f"contrato alterado: edite o texto de {', '.join(a.contrato)} no JSON e rode `md`; "
              f"confira as tarefas das frentes {', '.join(frentes)} que já usam esse contrato e passe-as em --afeta")


def cmd_duvida(a):
    plano = carregar(a.plano)
    qid = proximo_id("Q", [q["id"] for q in plano["duvidas"]])
    plano["duvidas"].append({"id": qid, "texto": a.texto, "resposta": None, "decisao": None})
    salvar(a.plano, plano)
    print(qid)


def cmd_responder(a):
    plano = carregar(a.plano)
    for q in plano["duvidas"]:
        if q["id"] == a.id:
            q["resposta"] = a.resposta
            salvar(a.plano, plano)
            print(f"{a.id} respondida — se mudou algo, registre a decisão com `decisao --duvida {a.id}`")
            return
    erro(f"dúvida {a.id} não existe")


def cmd_rodada(a):
    plano = carregar(a.plano)
    registro = Path(a.arquivo).read_text(encoding="utf-8") if a.arquivo else a.registro
    if not registro:
        erro("passe --registro TEXTO ou --arquivo CAMINHO")
    n = len(plano["rodadas"]) + 1
    plano["rodadas"].append({"n": n, "data": hoje(), "titulo": a.titulo, "registro": registro.strip()})
    for texto in a.dono or []:
        plano["pendencias_dono"].append({"texto": texto, "feito": False, "rodada": n})
    for texto in a.licao or []:
        plano["agentes"]["licoes"].append(texto)
    salvar(a.plano, plano)
    print(f"rodada {n} registrada")


def cmd_dono(a):
    plano = carregar(a.plano)
    if a.add:
        plano["pendencias_dono"].append({"texto": a.add, "feito": False, "rodada": len(plano["rodadas"])})
    if a.feito:
        plano["pendencias_dono"][a.feito - 1]["feito"] = True
    salvar(a.plano, plano)
    for i, p in enumerate(plano["pendencias_dono"], 1):
        print(f"{i}. [{'x' if p.get('feito') else ' '}] {p['texto']}")


def cmd_fase(a):
    plano = carregar(a.plano)
    if a.fase in ("aprovado", "em-execucao") and not plano["tarefas"]:
        erro("plano sem tarefas não pode ser aprovado")
    plano["fase"] = a.fase
    if a.fase == "aprovado" and not plano.get("aprovado_em"):
        plano["aprovado_em"] = hoje()
    salvar(a.plano, plano)
    print(f"fase: {a.fase}")


def cmd_briefing(a):
    plano = carregar(a.plano)
    print(montar_briefing(a.plano, plano, tarefa(plano, a.id), a.papel))


def cmd_onda(a):
    plano = carregar(a.plano)
    if plano["fase"] not in ("aprovado", "em-execucao"):
        erro(f"fase {plano['fase']}: o plano precisa ser aprovado antes de executar (`fase aprovado`)")
    args = montar_onda(a.plano, plano, a.max)
    texto = json.dumps(args, ensure_ascii=False, indent=2)
    if a.saida:
        Path(a.saida).write_text(texto, encoding="utf-8")
    print(texto)


def cmd_branches(a):
    plano = carregar(a.plano)
    for f in plano["frentes"]:
        repo, branch = f["repo"], f.get("branch") or plano["branch"]
        if not Path(repo).exists():
            print(f"{f['id']}  {repo}: não existe")
            continue
        atual = (git(repo, "branch", "--show-current") or "?").strip()
        sujos = len((git(repo, "status", "--porcelain") or "").splitlines())
        if not existe_ref(repo, branch):
            print(f"{f['id']}  {repo}: branch {branch} não existe (atual: {atual}, {sujos} arquivo(s) alterado(s))")
            continue
        base = ref_base(repo, f.get("base") or plano.get("base"))
        conta = "base não encontrada"
        if base:
            atras, frente_ = (git(repo, "rev-list", "--left-right", "--count", f"{base}...{branch}") or "? ?").split()
            conta = f"{frente_} à frente, {atras} atrás de {base}"
        remoto = "publicada" if existe_ref(repo, f"origin/{branch}") else "só local"
        print(f"{f['id']}  {repo} @ {branch}: {conta} · {remoto} · atual: {atual} · {sujos} arquivo(s) alterado(s)")


def cmd_ponteiros(a):
    plano = carregar(a.plano)
    md = caminho_md(a.plano).resolve()
    for f in plano["frentes"]:
        ts = [t for t in plano["tarefas"] if t["frente"] == f["id"]]
        texto = [f"# Frente {f['id']} · {f['nome']}\n",
                 f"Este repositório é uma das frentes de **{plano['titulo']}**.\n",
                 f"**O plano completo fica fora daqui:** `{md}` — decisões, contratos entre as frentes e o "
                 "estado de todas as tarefas. **Leia antes de escrever qualquer código**, principalmente as "
                 "seções 3 (decisões), 6 (contratos) e 7 (tarefas).\n",
                 "| ✔ | # | Tarefa |\n|---|---|---|"]
        texto += [f"| {ESTADOS[t['estado']]} | {t['id']} | {celula(t['titulo'])} |" for t in ts]
        texto.append("\nEsta tabela é uma cópia: o estado que vale é o do plano. Ao terminar uma tarefa, "
                     f"comite com a mensagem começando pelo ID (`{f['id']}1: ...`).\n")
        destino = Path(f["repo"]) / "FORGE.md"
        destino.write_text("\n".join(texto), encoding="utf-8", newline="\n")
        print(f"escrito: {destino}")


def cmd_contexto(a):
    """Resumo dos planos que interessam a uma pasta — usado pelo hook de SessionStart."""
    for caminho, plano in planos_do_diretorio(a.cwd or os.getcwd()):
        if plano.get("fase") != "fechado":
            print(texto_status(caminho, plano))
            print()


def main():
    configurar_saida()
    p = argparse.ArgumentParser(prog="forge.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)

    def comando(nome, func, ajuda, plano=True):
        s = sub.add_parser(nome, help=ajuda, description=ajuda)
        if plano:
            s.add_argument("plano", help="caminho do forge-<slug>.json")
        s.set_defaults(func=func)
        return s

    s = comando("novo", cmd_novo, "cria forge-<slug>.json e .md e registra o plano", plano=False)
    s.add_argument("slug")
    s.add_argument("--titulo", required=True)
    s.add_argument("--dono", required=True)
    s.add_argument("--dir", default=".", help="pasta onde o plano mora (fora dos repositórios)")
    s.add_argument("--branch", help="branch de trabalho em todos os repositórios (padrão: o slug)")
    s.add_argument("--base", default="teste", help="branch de onde as branches saem (padrão: teste)")

    comando("registrar", cmd_registrar, "registra um plano existente para os hooks o acharem")
    comando("lista", cmd_lista, "lista os planos registrados", plano=False)
    comando("md", cmd_md, "valida o JSON e regenera o Markdown (rode depois de editar o JSON à mão)")
    comando("validar", cmd_validar, "valida o JSON sem gravar nada")

    s = comando("status", cmd_status, "estado das tarefas, com os commits de cada uma")
    s.add_argument("--sem-git", action="store_true")
    s.add_argument("--json", action="store_true")

    comando("drift", cmd_drift, "divergências entre o plano e os repositórios (sai com 1 se houver)")

    s = comando("marcar", cmd_marcar, "marca a tarefa como feita (acha os commits pelo ID), pendente ou a revisar")
    s.add_argument("id")
    s.add_argument("--commit", nargs="+")
    s.add_argument("--forcar", action="store_true", help="marca feita mesmo sem commit")
    s.add_argument("--pendente", action="store_true")
    s.add_argument("--revisar", action="store_true")

    s = comando("tarefa", cmd_tarefa, "acrescenta uma tarefa à frente, com o próximo ID")
    s.add_argument("--frente", required=True)
    s.add_argument("--titulo", required=True)
    s.add_argument("--testar", required=True, help="como provar que a tarefa funciona sozinha")
    s.add_argument("--depende", nargs="*")
    s.add_argument("--notas")
    s.add_argument("--complexidade", choices=COMPLEXIDADES, default="media",
                   help="escolhe o modelo e o esforço dos agentes da tarefa (padrão: media)")

    s = comando("complexidade", cmd_complexidade, "reclassifica a complexidade de uma ou mais tarefas")
    s.add_argument("nivel", choices=COMPLEXIDADES)
    s.add_argument("ids", nargs="+")

    s = comando("decisao", cmd_decisao, "registra a próxima decisão (D<n>)")
    s.add_argument("--assunto", required=True)
    s.add_argument("--texto", required=True)
    s.add_argument("--afeta", nargs="*", help="tarefas que esta decisão obriga a revisar (as feitas voltam como ⟳)")
    s.add_argument("--contrato", nargs="*", help="contratos que esta decisão altera")
    s.add_argument("--revoga", help="decisão que esta substitui")
    s.add_argument("--duvida", help="dúvida que esta decisão responde")
    s.add_argument("--data")

    s = comando("duvida", cmd_duvida, "registra uma dúvida em aberto (Q<n>)")
    s.add_argument("texto")

    s = comando("responder", cmd_responder, "responde uma dúvida")
    s.add_argument("id")
    s.add_argument("resposta")

    s = comando("rodada", cmd_rodada, "registra o fechamento de uma rodada")
    s.add_argument("--titulo", required=True)
    s.add_argument("--registro")
    s.add_argument("--arquivo")
    s.add_argument("--dono", nargs="*", help="pendências que ficam com o dono")
    s.add_argument("--licao", nargs="*", help="lições sobre os agentes")

    s = comando("dono", cmd_dono, "lista, acrescenta ou fecha pendências do dono")
    s.add_argument("--add")
    s.add_argument("--feito", type=int)

    s = comando("fase", cmd_fase, "muda a fase do plano")
    s.add_argument("fase", choices=FASES)

    s = comando("briefing", cmd_briefing, "mostra o briefing de um papel para uma tarefa")
    s.add_argument("id")
    s.add_argument("--papel", choices=PAPEIS, default="executor")

    s = comando("onda", cmd_onda, "escolhe a próxima onda, grava os briefings e imprime o args do workflow")
    s.add_argument("--max", type=int, default=3, help="máximo de tarefas na onda (padrão 3)")
    s.add_argument("--saida")

    comando("branches", cmd_branches, "situação da branch de trabalho em cada repositório")
    comando("ponteiros", cmd_ponteiros, "escreve um FORGE.md em cada repositório apontando para o plano")

    s = comando("contexto", cmd_contexto, "resumo dos planos que interessam a uma pasta", plano=False)
    s.add_argument("--cwd")

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
