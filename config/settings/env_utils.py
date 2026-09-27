"""Minimal project-root.env loader for split settings - no extra dependency.

Shared by the dev settings and the cognito overlay. setdefault keeps
explicit shell exports authoritative over file values, so export VAR=... still
wins over what a file declares.
"""

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_env_file(filename: str) -> None:
    """Load KEY=VALUE lines from a project-root file into os.environ.

    A missing file is a no-op. Existing environment variables are never
    overwritten (setdefault), so shell exports take precedence over the file.
    """
    env_path = _PROJECT_ROOT / filename
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
