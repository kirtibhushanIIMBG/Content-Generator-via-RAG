"""The runtime LinkedIn presets in generate.py must equal the <!-- PRESET --> blocks in the docs.

If this fails, someone edited docs/style-linkedin-*.md (or generate.py) without re-syncing.
Fix: python tools/sync_presets.py
"""
from tools.sync_presets import GEN, build_block, current_block


def test_styles_presets_match_the_docs() -> None:
    src = GEN.read_text(encoding="utf-8")
    assert current_block(src) == build_block(), (
        "generate.py STYLES presets drifted from docs/style-linkedin-*.md — "
        "run `python tools/sync_presets.py`"
    )
