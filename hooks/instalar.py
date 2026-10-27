#!/usr/bin/env python3
"""Instala (ou remove, com --remover) os hooks do forge em ~/.claude/settings.json.

Idempotente: reconhece as entradas pelo caminho do forge_hook.py. Guarda uma cópia do settings
antes de gravar, em settings.json.bak-forge.
"""
import json
import shutil
import sys
from pathlib import Path

SETTINGS = Path.home() / ".claude" / "settings.json"
HOOK = (Path(__file__).resolve().parent / "forge_hook.py").as_posix()
MARCA = "forge_hook.py"

ENTRADAS = {
    "SessionStart": {"hooks": [{"type": "command", "command": f'python "{HOOK}" session-start', "timeout": 30}]},
    "PreToolUse": {"matcher": "Bash|PowerShell",
                   "hooks": [{"type": "command", "command": f'python "{HOOK}" pre-tool', "timeout": 15}]},
}


def eh_do_forge(grupo):
    return any(MARCA in h.get("command", "") for h in grupo.get("hooks", []))


def main():
    remover = "--remover" in sys.argv
    settings = {}
    if SETTINGS.exists():
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
        shutil.copyfile(SETTINGS, SETTINGS.with_name("settings.json.bak-forge"))
    hooks = settings.setdefault("hooks", {})
    for evento, entrada in ENTRADAS.items():
        grupos = [g for g in hooks.get(evento, []) if not eh_do_forge(g)]
        if not remover:
            grupos.append(entrada)
        if grupos:
            hooks[evento] = grupos
        else:
            hooks.pop(evento, None)
    if not hooks:
        settings.pop("hooks")
    SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(("removidos" if remover else "instalados") + f" os hooks do forge em {SETTINGS}")


if __name__ == "__main__":
    main()
