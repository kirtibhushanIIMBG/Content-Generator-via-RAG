"""Scaffold verification. Run: python tests/test_scaffold.py

Checks structure and CONFIG KEY NAMES only — never reads or prints secret values.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# CLAUDE.md §5
REQUIRED_VARS = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "QDRANT_URL",
    "QDRANT_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGSMITH_TRACING",
    "N8N_WEBHOOK_URL",
}


def _keys(path: Path) -> set[str]:
    """Key names on the left of '=' — values are never read."""
    return {
        m.group(1)
        for m in re.finditer(
            r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", path.read_text(encoding="utf-8"), re.M
        )
    }


def _value(path: Path, key: str) -> str:
    """Whether a key has a non-empty value. Returns the value's LENGTH-BEARING form only for
    the caller's truthiness test — callers must never print it."""
    m = re.search(rf"^\s*{re.escape(key)}\s*=\s*(.*)$", path.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip().strip("\"'") if m else ""


def test_folders() -> None:
    for d in (
        "src/ingest",
        "src/retrieval",
        "src/generation",
        "src/graph",
        "data/raw",
        "data/processed",
        "tests",
        ".streamlit",
    ):
        assert (ROOT / d).is_dir(), f"missing folder: {d}"


def test_source_pdfs_present() -> None:
    # Build-time inputs (CLAUDE.md §4). Exact filenames, no substitutes.
    for pdf in ("DPDP_Act_2023.pdf", "DPDP_Rules_2025.pdf"):
        p = ROOT / "data" / "raw" / pdf
        assert p.is_file(), f"missing source PDF: data/raw/{pdf}"
        assert p.stat().st_size > 0, f"empty source PDF: {pdf}"


def test_env_has_required_var_names() -> None:
    env = ROOT / ".env"
    assert env.is_file(), ".env not found — copy the 7 keys from CLAUDE.md §5"
    missing = REQUIRED_VARS - _keys(env)
    assert not missing, f".env missing var names: {sorted(missing)}"

    # A PRESENT-BUT-BLANK key is the failure mode this project has actually hit (see the
    # blank-secret eviction in app.py): every consumer here treats "" as unset, so the name
    # being there proves nothing. Reports only the NAME of an empty var — never a value.
    blank = sorted(k for k in REQUIRED_VARS & _keys(env) if not _value(env, k))
    assert not blank, f".env has these keys but they are EMPTY: {blank}"


def test_secrets_template_mirrors_env() -> None:
    # The .example is committed and must always exist; secrets.toml is gitignored,
    # so it is only checked when the developer has actually created it.
    example = ROOT / ".streamlit" / "secrets.toml.example"
    assert example.is_file(), ".streamlit/secrets.toml.example not found"
    missing = REQUIRED_VARS - _keys(example)
    assert not missing, f"secrets.toml.example missing var names: {sorted(missing)}"

    local = ROOT / ".streamlit" / "secrets.toml"
    if local.is_file():
        missing = REQUIRED_VARS - _keys(local)
        assert not missing, f"secrets.toml missing var names: {sorted(missing)}"


def test_build_deps_never_leak_into_the_runtime_requirements() -> None:
    """Streamlit Cloud installs requirements.txt on a ~2.7 GB free tier. Ingestion-only
    libraries must stay in requirements-build.txt (CLAUDE.md §3: nothing at runtime may
    depend on the build machine). `unstructured` was dropped at Phase 2 -- it was never
    imported, and it pulls spacy/nltk/numba/llvmlite."""
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    build = ROOT / "requirements-build.txt"
    assert build.is_file(), "requirements-build.txt not found"

    # Compare DISTRIBUTION NAMES, not whole lines. requirements.txt is unpinned today, and
    # its own header says to pin it before deploying — at which point "pypdf==5.1.0" is not
    # equal to "pypdf", every banned check passes vacuously, and pypdf ships to the free tier:
    # the precise failure this test exists to prevent, arriving via the step the file tells
    # you to take. Strip version specifiers, extras and markers.
    pkgs = {
        re.split(r"[=<>~!\[;\s]", ln.split("#")[0].strip().lower())[0]
        for ln in runtime.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }
    for banned in ("pdfminer.six", "pypdf", "unstructured", "ragas"):
        assert banned not in pkgs, f"{banned} is build-time only -- move it out of requirements.txt"

    for needed in ("pdfminer.six", "pypdf"):
        assert needed in build.read_text(encoding="utf-8"), f"{needed} missing from build deps"


def test_gitignore_covers_secrets() -> None:
    lines = {
        ln.strip().rstrip("/")
        for ln in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    # data/raw/ and venv/ are committed on purpose; only the secrets must stay out.
    for pattern in (".env", ".streamlit/secrets.toml"):
        assert pattern in lines, f".gitignore missing: {pattern}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
