#!/usr/bin/env python3
"""Hooks globais do forge.

  forge_hook.py session-start   (SessionStart)  injeta o estado dos planos que interessam à pasta
  forge_hook.py pre-tool        (PreToolUse, Bash|PowerShell)  trava de banco e ID de tarefa no commit

Qualquer erro inesperado libera a ação (fail-open): um hook quebrado não pode travar o trabalho.
A regra de banco continua valendo mesmo quando o hook não pega o comando.
"""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import forge  # noqa: E402

CLIENTES_BANCO = {"psql", "pgcli", "pg_dump", "pg_dumpall", "pg_restore", "mysql", "mysqldump", "mariadb",
                  "sqlcmd", "osql", "isql", "sqlite3", "mongo", "mongosh", "redis-cli", "clickhouse-client"}
SO_LEITURA = {"grep", "rg", "cat", "head", "tail", "less", "echo", "printf", "git", "sed", "awk", "find",
              "ls", "select-string", "get-content", "findstr", "type", "write-output", "write-host"}
HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1", "[::1]"}
# A regra padrão é só banco local. Quem precisa de mais (uma organização com bancos que ninguém pode abrir,
# ou só os de um prefixo) aperta por variável de ambiente, sem mexer no código da skill.
VAR_PREFIXO = "FORGE_BANCO_PREFIXO"
VAR_PROIBIDOS = "FORGE_BANCOS_PROIBIDOS"
URL_BANCO = re.compile(r"(?:jdbc:)?(postgres(?:ql)?|mysql|mariadb|sqlserver|mongodb(?:\+srv)?)://"
                       r"(?:[^@/\s'\"]*@)?(\[[^\]]+\]|[^/\s:;?'\"]+)(?::\d+)?/([\w\-]+)", re.I)


def ler_entrada():
    dados = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    return json.loads(dados) if dados.strip() else {}


# --------------------------------------------------------------------------- SessionStart

def session_start(entrada):
    cwd = entrada.get("cwd") or os.getcwd()
    partes = []
    for caminho, plano in forge.planos_do_diretorio(cwd):
        if plano.get("fase") == "fechado":
            continue
        try:
            partes.append(forge.texto_status(caminho, plano))
        except Exception as e:  # um plano quebrado não esconde os outros
            partes.append(f"{caminho}: não foi possível ler o estado ({e})")
    if not partes:
        return
    texto = ("[forge] Plano(s) ativo(s) para esta pasta. Para retomar, use a skill /forge "
             "(rode `drift` antes de qualquer onda).\n\n" + "\n\n".join(partes))
    if len(texto) > 6000:
        texto = texto[:6000] + "\n… (cortado — rode `forge.py status`)"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": texto}},
                     ensure_ascii=False))


# --------------------------------------------------------------------------- PreToolUse

def tokens(segmento):
    try:
        brutos = shlex.split(segmento, posix=False)
    except ValueError:
        brutos = segmento.split()
    saida = []
    for t in brutos:
        if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
            t = t[1:-1]
        saida.append(t)
    while saida and (re.fullmatch(r"\w+=.*", saida[0]) or saida[0] in ("sudo", "&", "env", "exec", "time")):
        saida.pop(0)
    return saida


def nome_programa(token):
    nome = re.split(r"[\\/]", token)[-1].lower()
    return nome[:-4] if nome.endswith(".exe") else nome


def segmentos(comando):
    return [s.strip() for s in re.split(r"\r?\n|;|&&|\|\||\|", comando) if s.strip()]


def regra_local():
    """(prefixo, proibidos) das variáveis de ambiente; vazios quando não configuradas."""
    prefixo = os.environ.get(VAR_PREFIXO, "").strip().lower()
    proibidos = {b.strip().lower() for b in os.environ.get(VAR_PROIBIDOS, "").split(",") if b.strip()}
    return prefixo, proibidos


def banco_permitido(host, banco):
    """(permitido, motivo). Só banco local (sem host vale como local), apertado pela regra_local()."""
    prefixo, proibidos = regra_local()
    if banco and banco.lower() in proibidos:
        return False, f"o banco '{banco}' está em {VAR_PROIBIDOS}"
    if host and host.lower() not in HOSTS_LOCAIS:
        return False, f"o host '{host}' não é local"
    if prefixo and not (banco or "").lower().startswith(prefixo):
        return False, f"o banco '{banco or '?'}' não começa com {prefixo} ({VAR_PREFIXO})"
    return True, ""


def alvo_cliente(args):
    """Host e banco de uma linha de cliente de banco (psql, mysql, sqlcmd...)."""
    host = banco = None
    posicionais = []
    i = 0
    while i < len(args):
        a = args[i]
        prox = args[i + 1] if i + 1 < len(args) else None
        m = URL_BANCO.search(a)
        if m:
            return m.group(2).strip("[]") if m.group(2).startswith("[") else m.group(2), m.group(3)
        if re.match(r"(host|dbname)=", a):
            for chave, valor in re.findall(r"(host|dbname)=(\S+)", " ".join(args[i:])):
                host = valor if chave == "host" else host
                banco = valor if chave == "dbname" else banco
            break
        for curtas, longa, campo in (("-h", "--host", "host"), ("-S", "--server", "host"),
                                     ("-d", "--dbname", "banco"), ("-D", "--database", "banco")):
            valor = None
            if a in (curtas, longa) and prox:
                valor, i = prox, i + 1
            elif a.startswith(longa + "="):
                valor = a.split("=", 1)[1]
            elif a.startswith(curtas) and len(a) > 2 and not a.startswith("--"):
                valor = a[2:]
            if valor is not None:
                if campo == "host":
                    host = valor.split(",")[0].split("\\")[0]
                else:
                    banco = valor
                break
        else:
            if not a.startswith("-"):
                posicionais.append(a)
        i += 1
    if banco is None and posicionais:
        banco = posicionais[0]
    if banco and banco.lower().endswith((".db", ".sqlite", ".sqlite3")):
        banco = Path(banco).stem
    return host, banco


def checar_banco(comando):
    for seg in segmentos(comando):
        ts = tokens(seg)
        if not ts:
            continue
        programa = nome_programa(ts[0])
        if programa in CLIENTES_BANCO:
            host, banco = alvo_cliente(ts[1:])
            ok, motivo = banco_permitido(host, banco)
            if not ok:
                return f"`{programa}` bloqueado: {motivo}"
        elif programa not in SO_LEITURA:
            for m in URL_BANCO.finditer(seg):
                host = m.group(2).strip("[]")
                ok, motivo = banco_permitido(host, m.group(3))
                if not ok:
                    return f"conexão `{m.group(0)}` bloqueada: {motivo}"
    return None


def mensagem_do_commit(comando):
    m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)\n\s*\1\b", comando, re.S)
    if m:
        return m.group(2)
    m = re.search(r"@'\s*\r?\n(.*?)\r?\n'@", comando, re.S) or re.search(r'@"\s*\r?\n(.*?)\r?\n"@', comando, re.S)
    if m:
        return m.group(1)
    m = re.search(r"(?:\s-m|\s--message)(?:=|\s+)(\"(?:[^\"\\]|\\.)*\"|'[^']*'|\S+)", comando)
    if m:
        valor = m.group(1)
        return valor[1:-1] if valor[:1] in "\"'" else valor
    return None


def pasta_do_commit(comando, cwd):
    pasta = Path(cwd)
    antes = comando.split("commit", 1)[0]
    for m in re.finditer(r"(?:^|[;&|\n]\s*)(?:cd|Set-Location|pushd)\s+(\"[^\"]+\"|'[^']+'|\S+)", antes):
        pasta = pasta / m.group(1).strip("\"'")
    m = re.search(r"git\s+-C\s+(\"[^\"]+\"|'[^']+'|\S+)\s+commit", comando)
    if m:
        pasta = pasta / m.group(1).strip("\"'")
    return pasta


def checar_commit(comando, cwd):
    if not re.search(r"\bgit\b(?:\s+-C\s+(?:\"[^\"]+\"|'[^']+'|\S+))?\s+commit\b", comando):
        return None
    mensagem = mensagem_do_commit(comando)
    if mensagem is None:
        return None  # -F arquivo, editor, --no-edit: não dá para conferir aqui
    pasta = pasta_do_commit(comando, cwd)

    def g(*args):
        r = subprocess.run(["git", "-C", str(pasta), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None

    topo, branch = g("rev-parse", "--show-toplevel"), g("branch", "--show-current")
    if not topo or not branch:
        return None
    for _, plano in forge.planos_registrados():
        if plano.get("fase") == "fechado":
            continue
        for f in plano.get("frentes", []):
            if forge.normalizar(f["repo"]) != forge.normalizar(topo) or branch != (f.get("branch") or plano["branch"]):
                continue
            existentes = {t["id"] for t in plano.get("tarefas", [])}
            primeira = mensagem.strip().splitlines()[0] if mensagem.strip() else ""
            if any(i in existentes for i in forge.ids_do_assunto(primeira)):
                return None
            pendentes = [t["id"] for t in plano["tarefas"] if t["frente"] == f["id"] and t["estado"] != "feito"]
            return (f"commit recusado: este repositório é a frente {f['id']} do plano forge '{plano['slug']}' "
                    f"(branch {branch}), e a mensagem precisa começar pelo ID de uma tarefa do plano "
                    f"(ex.: `{(pendentes or [f['id'] + '1'])[0]}: ...`). Pendentes desta frente: "
                    f"{', '.join(pendentes) or 'nenhuma'}. Trabalho fora do plano vira tarefa antes "
                    f"(`forge.py tarefa`).")
    return None


def pre_tool(entrada):
    comando = (entrada.get("tool_input") or {}).get("command") or ""
    if not comando:
        return
    motivo = checar_banco(comando) or checar_commit(comando, entrada.get("cwd") or os.getcwd())
    if motivo:
        if "commit recusado" not in motivo:
            motivo += " — o forge só libera banco local (localhost, 127.0.0.1 ou ::1)."
        print(f"[forge] {motivo}", file=sys.stderr)
        sys.exit(2)


def main():
    forge.configurar_saida()
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        entrada = ler_entrada()
        if modo == "session-start":
            session_start(entrada)
        elif modo == "pre-tool":
            pre_tool(entrada)
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
