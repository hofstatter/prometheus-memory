#!/usr/bin/env python3
"""
Prometheus Memory — Instalador universal (Windows / macOS / Linux / Raspberry Pi).

Uso:
    python setup.py             # interativo
    python setup.py --lang en   # pula a pergunta de idioma
    python setup.py --dry-run   # simula sem alterar nada

Detecta OS/arquitetura, instala dependencias, copia scripts, configura .env
com idioma escolhido e registra o servico da Web UI conforme a plataforma:
  Linux  -> systemd user + cron (se disponiveis)
  macOS  -> launchd plist
  Windows-> instrucoes Task Scheduler
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
INSTALL_DIR = Path.home() / "prometheus-memory"
BIN_DIR = Path.home() / "bin"
LANGS = {
    "en": "Language / Idioma / Idioma / 语言",
    "pt": "Português (Brasil)",
    "es": "Español",
    "zh": "中文",
}
MSG = {
    "en": {"python_ok": "✓ Python {}", "installing": "→ Installing dependencies...", "copying": "→ Copying to {}...", "done": "✅ Prometheus Memory installed! Run: {}", "lang_prompt": "Choose language [en/pt/es/zh] (default en): ", "tess": "⚠ Tesseract not found (optional, for OCR)."},
    "pt": {"python_ok": "✓ Python {}", "installing": "→ Instalando dependências...", "copying": "→ Copiando para {}...", "done": "✅ Prometheus Memory instalado! Rode: {}", "lang_prompt": "Escolha o idioma [en/pt/es/zh] (padrão en): ", "tess": "⚠ Tesseract não encontrado (opcional, p/ OCR)."},
    "es": {"python_ok": "✓ Python {}", "installing": "→ Instalando dependencias...", "copying": "→ Copiando a {}...", "done": "✅ ¡Prometheus Memory instalado! Ejecuta: {}", "lang_prompt": "Elige idioma [en/pt/es/zh] (por defecto en): ", "tess": "⚠ Tesseract no encontrado (opcional, para OCR)."},
    "zh": {"python_ok": "✓ Python {}", "installing": "→ 正在安装依赖...", "copying": "→ 正在复制到 {}...", "done": "✅ Prometheus Memory 安装完成！运行：{}", "lang_prompt": "请选择语言 [en/pt/es/zh]（默认 en）：", "tess": "⚠ 未找到 Tesseract（可选，用于 OCR）。"},
}


def m(lang, key, *args):
    return MSG.get(lang, MSG["en"])[key].format(*args)


def run(cmd, dry):
    print("  $", " ".join(str(c) for c in cmd))
    if not dry:
        subprocess.run(cmd, check=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=list(LANGS), default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    os_name = platform.system()           # Linux | Darwin | Windows
    arch = platform.machine()             # x86_64 | aarch64 | arm64 | AMD64
    print("⚡ Prometheus Memory — Setup")
    print(f"   OS: {os_name} · Arch: {arch}")

    lang = args.lang
    if not lang:
        try:
            ans = input(MSG["en"]["lang_prompt"]).strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = ""
        lang = ans if ans in LANGS else "en"

    py = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ required")
        sys.exit(1)
    print(m(lang, "python_ok", py))

    # 1. Mnemosyne
    if not shutil.which("mnemosyne"):
        run([sys.executable, "-m", "pip", "install", "--user", "mnemosyne-memory[all]>=3.12"], args.dry_run)
    # 2. Deps
    print(m(lang, "installing"))
    run([sys.executable, "-m", "pip", "install", "--user", "-r", str(SCRIPT_DIR / "requirements.txt")], args.dry_run)

    if not shutil.which("tesseract"):
        print(m(lang, "tess"))

    # 3. Copia para INSTALL_DIR
    if SCRIPT_DIR != INSTALL_DIR:
        print(m(lang, "copying", INSTALL_DIR))
        if not args.dry_run:
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            for item in SCRIPT_DIR.iterdir():
                dest = INSTALL_DIR / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)

    # 4. Scripts em ~/bin (Unix) ou %USERPROFILE%\bin (Windows)
    bin_dir = Path.home() / ("bin" if os_name != "Windows" else "bin")
    if not args.dry_run:
        bin_dir.mkdir(exist_ok=True)
        for s in (INSTALL_DIR / "scripts").glob("*.py"):
            shutil.copy2(s, bin_dir / s.name)

    # 5. Skill auto-memory (caminho novo + legado do OpenCode)
    src = INSTALL_DIR / "skills" / "auto-memory"
    if not args.dry_run and src.exists():
        for base in (Path.home() / ".config" / "opencode" / "skills", Path.home() / ".opencode" / "skills"):
            base.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, base / "auto-memory", dirs_exist_ok=True)

    # 6. .env com idioma
    env_file = INSTALL_DIR / ".env"
    if not args.dry_run:
        if not env_file.exists():
            shutil.copy2(INSTALL_DIR / ".env.example", env_file)
        content = env_file.read_text()
        if "PROMETHEUS_LANG=" not in content:
            content += f"\nPROMETHEUS_LANG={lang}\n"
        env_file.write_text(content)

    # 7. Servico por plataforma
    if os_name == "Linux":
        cron = shutil.which("crontab")
        if cron:
            marker = "# prometheus-memory"
            current = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
            if marker not in current and not args.dry_run:
                jobs = (
                    f"{marker}\n"
                    f"0 */6 * * * set -a; . {INSTALL_DIR}/.env; set +a; python3 {bin_dir}/memory_aggregator.py\n"
                    f"0 8 * * 1 set -a; . {INSTALL_DIR}/.env; set +a; python3 {bin_dir}/persona_synthesizer.py\n"
                    f"30 4 * * * set -a; . {INSTALL_DIR}/.env; set +a; python3 {bin_dir}/retention.py\n"
                )
                subprocess.run(["crontab", "-"], input=current + jobs, text=True)
                print("✓ Cron jobs instalados")
        if shutil.which("systemctl"):
            sd = Path.home() / ".config" / "systemd" / "user"
            if not args.dry_run:
                sd.mkdir(parents=True, exist_ok=True)
                shutil.copy2(INSTALL_DIR / "systemd" / "prometheus-web.service", sd)
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
                subprocess.run(["systemctl", "--user", "enable", "--now", "prometheus-web.service"], check=False)
            print("✓ systemd user service (prometheus-web)")
    elif os_name == "Darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / "com.prometheus.memory.plist"
        if not args.dry_run:
            plist.parent.mkdir(parents=True, exist_ok=True)
            plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.prometheus.memory</string>
  <key>ProgramArguments</key><array>
    <string>{sys.executable}</string><string>{INSTALL_DIR}/web/app.py</string>
  </array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
</dict></plist>""")
        print(f"✓ launchd plist: {plist}")
        print(f"  Ativar: launchctl load {plist}")
    elif os_name == "Windows":
        print("ℹ Servico: use o Agendador de Tarefas (Task Scheduler):")
        print(f'  schtasks /create /tn "PrometheusMemory" /tr "{sys.executable} {INSTALL_DIR}\\web\\app.py" /sc onlogon')

    start_cmd = f"python3 {INSTALL_DIR}/web/app.py" if os_name != "Windows" else f"python {INSTALL_DIR}\\web\\app.py"
    print(m(lang, "done", start_cmd))


if __name__ == "__main__":
    main()
