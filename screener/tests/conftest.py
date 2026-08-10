"""Builds tiny git repositories with known-answer histories."""
import subprocess
from pathlib import Path

import pytest


def _git(repo, *args, env=None):
    full = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
            "PATH": __import__("os").environ["PATH"]}
    if env:
        full.update(env)
    subprocess.run(["git", *args], cwd=str(repo), check=True,
                   capture_output=True, text=True, env=full)


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Test Human")
    _git(repo, "config", "user.email", "human@example.com")
    return repo


def commit(repo, files, message, author="Test Human <human@example.com>",
           committer=None):
    """files: {relative_path: contents}"""
    for rel, contents in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contents, encoding="utf-8")
    _git(repo, "add", "-A")
    name, email = author.rstrip(">").split(" <")
    cname, cemail = (name, email)
    if committer:
        cname, cemail = committer.rstrip(">").split(" <")
    env = {
        "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": cname, "GIT_COMMITTER_EMAIL": cemail,
    }
    _git(repo, "commit", "-q", "-m", message, env=env)


@pytest.fixture
def repo_factory(tmp_path):
    return lambda: make_repo(tmp_path)
