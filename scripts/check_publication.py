"""Check candidate Git files for common private data (not a full security audit)."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIPPED_LOCAL_DIRS = {'.venv', 'venv', '__pycache__', '.git', 'backups', 'RESPALDOS_NEXOMERC', 'photos', 'data', 'tools', 'patch_backups'}
FORBIDDEN_SUFFIXES = {'.sqlite', '.sqlite3', '.db', '.pem', '.key', '.p12', '.pfx', '.pyc', '.log', '.bak', '.env'}
FORBIDDEN_FILES = {'reset_admin_password.py', '.env', 'id_rsa', 'id_ed25519'}
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    'GitHub token': re.compile(r'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}'),
    'AWS key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    'Slack token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{18,}'),
    'specific Windows user path': re.compile(r'[A-Za-z]:\\Users\\[^\\\s\'\"<>]+\\', re.IGNORECASE),
}
SCAN_SUFFIXES = {'.py', '.json', '.md', '.txt', '.qss', '.bat', '.yml', '.yaml', '.toml', '.ini', '.cfg'}


def candidate_files():
    """If available, audit the actual Git index, not ignored runtime folders."""
    if (ROOT / '.git').exists():
        try:
            listing = subprocess.check_output(
                ['git', '-C', str(ROOT), 'ls-files', '--cached', '-z'],
                stderr=subprocess.DEVNULL,
            )
            if listing:
                print('Audit scope: Git index (tracked/staged files)')
                return [ROOT / x.decode('utf-8', 'surrogateescape') for x in listing.split(b'\0') if x]
        except (OSError, subprocess.CalledProcessError):
            pass
    print('Audit scope: unpacked source, excluding local runtime folders')
    return [p for p in ROOT.rglob('*') if p.is_file() and not any(x in SKIPPED_LOCAL_DIRS for x in p.relative_to(ROOT).parts[:-1])]


def main() -> int:
    issues = []
    items = candidate_files()
    for item in items:
        rel = item.relative_to(ROOT)
        if any(x in SKIPPED_LOCAL_DIRS for x in rel.parts[:-1]):
            issues.append(f'Forbidden tracked directory: {rel}')
            continue
        if item.name in FORBIDDEN_FILES or item.suffix.lower() in FORBIDDEN_SUFFIXES or item.name.endswith(('-wal', '-shm')):
            issues.append(f'Forbidden file: {rel}')
        if not item.is_file() or item.suffix.lower() not in SCAN_SUFFIXES:
            continue
        try:
            content = item.read_text(encoding='utf-8')
        except (UnicodeError, OSError):
            continue
        for desc, pattern in PATTERNS.items():
            if pattern.search(content):
                issues.append(f'Sensitive pattern [{desc}]: {rel}')
    print(f'Checked {len(items)} candidate files')
    if issues:
        for issue in issues:
            print('WARNING:', issue)
        print('NOT READY for public release until every issue is reviewed.')
        return 1
    print('Static sanitation checks OK. Manual audit and Windows GUI verification are still required.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
