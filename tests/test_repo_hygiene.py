from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_has_no_live_secrets_file_committed():
    assert (ROOT / ".env.example").exists()
    assert not (ROOT / ".env").exists()


def test_gitignore_excludes_env():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text
