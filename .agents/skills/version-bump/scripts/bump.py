#!/usr/bin/env python3
import subprocess
import re
import sys
from pathlib import Path


def run_git(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def get_last_release_commit():
    try:
        logs = run_git(["git", "log", "--grep=release:", "--format=%H %s", "-n", "1"])
        if logs:
            return logs.split()[0]
    except Exception:
        pass
    try:
        tag = run_git(["git", "describe", "--tags", "--abbrev=0"])
        return run_git(["git", "rev-parse", tag])
    except Exception:
        return None


def get_commits_since(commit_hash):
    if commit_hash:
        cmd = ["git", "log", f"{commit_hash}..HEAD", "--format=%s"]
    else:
        cmd = ["git", "log", "--format=%s", "-n", "50"]
    output = run_git(cmd)
    return [line.strip() for line in output.splitlines() if line.strip()]


def determine_bump_type(commits):
    bump_type = "patch"
    for commit in commits:
        if "BREAKING CHANGE" in commit or re.search(r"^[a-zA-Z]+(\(.+?\))?!:", commit):
            return "major"
        if commit.startswith("feat"):
            bump_type = "minor"
    return bump_type


def bump_version_string(current_version, bump_type):
    parts = list(map(int, current_version.split(".")))
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts[0], parts[1], parts[2]
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    return f"{major}.{minor}.{patch}"


def get_next_rc_version(base_version):
    try:
        tags = run_git(["git", "tag", "-l", f"v{base_version}-rc*"]).splitlines()
    except Exception:
        tags = []
    max_n = -1
    for tag in tags:
        tag = tag.strip()
        match = re.search(rf"^v{base_version}-rc(\d+)$", tag)
        if match:
            n = int(match.group(1))
            if n > max_n:
                max_n = n
    return max_n + 1


def read_pyproject_version():
    content = Path("pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise ValueError("Versão não encontrada em pyproject.toml")


def update_pyproject_version(new_version):
    path = Path("pyproject.toml")
    content = path.read_text(encoding="utf-8")
    new_content = re.sub(
        r'^(version\s*=\s*)"[^"]+"', f'\\1"{new_version}"', content, flags=re.MULTILINE
    )
    path.write_text(new_content, encoding="utf-8")


def update_fastapi_version(new_version):
    path = Path("torrent_stats/interfaces/api/main.py")
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    new_content = re.sub(r'(version\s*=\s*)"[^"]+"', f'\\1"{new_version}"', content)
    path.write_text(new_content, encoding="utf-8")


def main():
    print("Analisando commits para version bump...")
    last_commit = get_last_release_commit()
    commits = get_commits_since(last_commit)
    print(f"Total de commits encontrados desde a última release: {len(commits)}")
    for c in commits[:10]:
        print(f" - {c}")

    current_version = read_pyproject_version()
    print(f"Versão atual (pyproject.toml): {current_version}")

    clean_current = current_version.split("-")[0]
    is_rc_current = "-" in current_version

    if is_rc_current:
        base_version = clean_current
        print(f"Versão atual é um release candidate. Base version: {base_version}")
    else:
        bump_type = determine_bump_type(commits)
        print(f"Tipo de bump determinado: {bump_type}")
        base_version = bump_version_string(clean_current, bump_type)

    is_rc = "--rc" in sys.argv or "--release-candidate" in sys.argv
    if is_rc:
        rc_num = get_next_rc_version(base_version)
        new_version = f"{base_version}-rc{rc_num}"
        print(f"Modo Release Candidate ativado. RC número: {rc_num}")
    else:
        new_version = base_version
    print(f"Nova versão calculada: {new_version}")

    if "--dry-run" in sys.argv:
        print("Dry run ativado. Nenhuma alteração aplicada.")
        return

    update_pyproject_version(new_version)
    update_fastapi_version(new_version)
    print(
        "Versões atualizadas em pyproject.toml e torrent_stats/interfaces/api/main.py."
    )

    run_git(["git", "add", "pyproject.toml", "torrent_stats/interfaces/api/main.py"])
    commit_smg = f"release: {new_version}"
    run_git(["git", "commit", "-m", commit_smg])
    print(f"Commit criado: {commit_smg}")

    tag_name = f"v{new_version}"
    run_git(["git", "tag", tag_name])
    print(f"Tag criada: {tag_name}")
    print(f"Sucesso! Projeto versionado para {new_version} (tag {tag_name}).")


if __name__ == "__main__":
    main()
