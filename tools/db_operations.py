#!/usr/bin/env python3
"""Safe SQLite backup/verification/restore primitives for CBEOS.

Backups are created with SQLite's online backup API (WAL-safe), validated with
integrity_check and foreign_key_check, and accompanied by a SHA-256 manifest.
Restore never overwrites an existing target unless --replace is explicitly set.
This is an operational tool, not a substitute for encrypted off-site backups.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate_database(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f'Database missing or empty: {path}')
    con = sqlite3.connect(f'file:{path.resolve()}?mode=ro', uri=True)
    try:
        integrity = [r[0] for r in con.execute('PRAGMA integrity_check')]
        fk = [tuple(r) for r in con.execute('PRAGMA foreign_key_check')]
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        if integrity != ['ok']:
            raise ValueError(f'SQLite integrity_check failed: {integrity[:10]}')
        if fk:
            raise ValueError(f'SQLite foreign_key_check failed: {fk[:10]}')
        return {'integrity_check': 'ok', 'foreign_key_violations': 0, 'table_count': len(tables), 'tables': tables}
    finally:
        con.close()


def backup_database(source: Path, destination: Path) -> dict:
    source, destination = source.resolve(), destination.resolve()
    if source == destination:
        raise ValueError('Backup destination must differ from source')
    if not source.is_file():
        raise ValueError(f'Source database does not exist: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f'Backup destination already exists: {destination}')
    # Build in same directory then atomically publish only after verification.
    fd, tmp_name = tempfile.mkstemp(prefix=f'.{destination.name}.', suffix='.tmp', dir=destination.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        src = sqlite3.connect(f'file:{source}?mode=ro', uri=True)
        dst = sqlite3.connect(tmp)
        try:
            src.backup(dst, pages=256, sleep=0.05)
            dst.commit()
        finally:
            dst.close(); src.close()
        validation = validate_database(tmp)
        digest = sha256_file(tmp)
        os.replace(tmp, destination)
        manifest = {
            'format_version': 1,
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'source_path_basename': source.name,
            'backup_path_basename': destination.name,
            'sha256': digest,
            'bytes': destination.stat().st_size,
            'validation': validation,
            'status': 'BACKUP_VERIFIED',
            'limits': ['Local backup only; copy to encrypted off-site storage separately.', 'Restore should be tested on an isolated target before operational use.'],
        }
        manifest_path = destination.with_suffix(destination.suffix + '.manifest.json')
        if manifest_path.exists():
            destination.unlink()
            raise FileExistsError(f'Manifest destination already exists: {manifest_path}')
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        return manifest
    finally:
        if tmp.exists(): tmp.unlink()


def restore_database(backup: Path, destination: Path, replace: bool = False) -> dict:
    backup, destination = backup.resolve(), destination.resolve()
    validate_database(backup)
    if destination.exists() and not replace:
        raise FileExistsError(f'Restore target exists; refusing to overwrite: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if backup == destination:
        raise ValueError('Restore source and destination must differ')
    fd, tmp_name = tempfile.mkstemp(prefix=f'.{destination.name}.', suffix='.restore', dir=destination.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        src = sqlite3.connect(f'file:{backup}?mode=ro', uri=True)
        dst = sqlite3.connect(tmp)
        try:
            src.backup(dst, pages=256, sleep=0.05)
            dst.commit()
        finally:
            dst.close(); src.close()
        validation = validate_database(tmp)
        digest = sha256_file(tmp)
        os.replace(tmp, destination)
        return {'status': 'RESTORE_VERIFIED', 'destination': str(destination), 'sha256': digest, 'bytes': destination.stat().st_size, 'validation': validation}
    finally:
        if tmp.exists(): tmp.unlink()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('backup'); b.add_argument('source', type=Path); b.add_argument('destination', type=Path)
    v = sub.add_parser('verify'); v.add_argument('database', type=Path)
    r = sub.add_parser('restore'); r.add_argument('backup', type=Path); r.add_argument('destination', type=Path); r.add_argument('--replace', action='store_true')
    args = p.parse_args(argv)
    try:
        if args.command == 'backup': result = backup_database(args.source, args.destination)
        elif args.command == 'verify': result = {'status': 'DATABASE_VERIFIED', **validate_database(args.database), 'sha256': sha256_file(args.database)}
        else: result = restore_database(args.backup, args.destination, args.replace)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({'status': 'FAILED', 'error': f'{type(exc).__name__}: {exc}'}), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
