#!/usr/bin/env python3
"""
Prometheus Memory — Retention & Backup
Roda diariamente via cron: limpa refs/sessoes antigas e faz backup do SQLite.
"""
import os
import shutil
import sqlite3
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
REFS_DIR = MNEMOSYNE_HOME / "refs"
SESSIONS_DIR = MNEMOSYNE_HOME / "sessions"
DB_PATH = Path(os.environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))
BACKUP_DIR = MNEMOSYNE_HOME / "backups"

REFS_MAX_DAYS = 90
SESSIONS_MAX_DAYS = 180
BACKUP_KEEP = 7


def cutoff(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def clean_dated_dirs(base: Path, max_days: int, archive: bool = False) -> int:
    if not base.exists():
        return 0
    removed = 0
    limit = cutoff(max_days)
    for d in base.glob("????-??-??"):
        if d.name < limit:
            if archive:
                out = base / f"{d.name}.tar.gz"
                with tarfile.open(out, "w:gz") as tf:
                    tf.add(d, arcname=d.name)
            shutil.rmtree(d)
            removed += 1
    return removed


def backup_db() -> str:
    if not DB_PATH.exists():
        return ""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"mnemosyne-{ts}.db"
    src = sqlite3.connect(str(DB_PATH), timeout=10)
    dst = sqlite3.connect(str(dest))
    src.backup(dst)
    dst.close()
    src.close()
    backups = sorted(BACKUP_DIR.glob("mnemosyne-*.db"))
    for old in backups[:-BACKUP_KEEP]:
        old.unlink()
    return str(dest)


def vacuum():
    if not DB_PATH.exists():
        return
    con = sqlite3.connect(str(DB_PATH), timeout=30)
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()


if __name__ == "__main__":
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    refs = clean_dated_dirs(REFS_DIR, REFS_MAX_DAYS)
    sessions = clean_dated_dirs(SESSIONS_DIR, SESSIONS_MAX_DAYS, archive=True)
    dest = backup_db()
    vacuum()
    print(f"[{ts}] retention: {refs} refs dirs, {sessions} sessoes arquivadas, backup={dest or 'skip'}")
