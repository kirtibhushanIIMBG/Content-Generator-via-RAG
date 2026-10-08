"""Keep generate.py's STYLES presets in sync with the <!-- PRESET:* --> blocks in the style docs.

    python tools/sync_presets.py           # regenerate generate.py's _SYNCED_PRESETS from the docs
    python tools/sync_presets.py --check   # exit 1 if generate.py is out of sync (CI / pre-commit)

The root *_Instructions.md guides (Newsletter_Instructions.md, LinkedIn_Article_Long_Instructions.md,
LinkedIn_Article_Short_Instructions.md) plus docs/style-blog.md are the SINGLE SOURCE OF TRUTH for the
presets; the block in generate.py is generated from their <!-- PRESET:* --> blocks.
Editing a .md doc's PRESET block is what changes the live LinkedIn preset — run this so generate.py
follows, then deploy
generate.py (GitHub -> Render + Streamlit). Whitespace/line-wrapping inside a PRESET block is
normalised to single spaces on sync (the preset is one flowing instruction to the model), so you
can wrap the doc block however reads best.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "src" / "generation" / "generate.py"
DOCS = {
    "blog": ROOT / "docs" / "style-blog.md",
    # newsletter, linkedin_article and linkedin_article_short are each sourced from their root
    # *_Instructions.md reference guide, which carries the human how-to AND its <!-- PRESET:* -->
    # block (§9). newsletter moved here from docs/style-newsletter.md on 2026-07-23 (evidence-based
    # rewrite from Newsletter_AI_Training_Corpus_Certinal.md); linkedin_article moved off
    # docs/style-linkedin-article.md the same day. Both docs/style-newsletter.md and
    # docs/style-linkedin-article.md are now orphaned dead source-of-truth docs — delete them on
    # GitHub, as was done for style-linkedin-post.md.
    "newsletter": ROOT / "Newsletter_Instructions.md",
    "linkedin_article": ROOT / "LinkedIn_Article_Long_Instructions.md",
    "linkedin_article_short": ROOT / "LinkedIn_Article_Short_Instructions.md",
}
ORDER = ["blog", "newsletter", "linkedin_article", "linkedin_article_short"]  # order written in the block
START = "# >>> SYNCED-PRESETS-START <<<"
END = "# >>> SYNCED-PRESETS-END <<<"


def preset_from_doc(key: str) -> str:
    """The text inside a doc's <!-- PRESET:key --> block, whitespace-normalised to one line."""
    doc = DOCS[key].read_text(encoding="utf-8")
    m = re.search(rf"<!--\s*PRESET:{re.escape(key)}\s*-->(.*?)<!--\s*/PRESET\s*-->", doc, re.S)
    if not m:
        sys.exit(f"ERROR: no <!-- PRESET:{key} --> ... <!-- /PRESET --> block in {DOCS[key]}")
    text = " ".join(m.group(1).split())
    if not text:
        sys.exit(f"ERROR: the PRESET:{key} block in {DOCS[key]} is empty")
    return text


def build_block() -> str:
    """What generate.py's _SYNCED_PRESETS block SHOULD be, derived from the docs."""
    lines = ["_SYNCED_PRESETS: dict[str, str] = {"]
    for k in ORDER:
        lines.append(f'    "{k}": {json.dumps(preset_from_doc(k), ensure_ascii=False)},')
    lines.append("}")
    return "\n".join(lines)


def current_block(src: str) -> str:
    """The _SYNCED_PRESETS block that is currently in generate.py."""
    m = re.search(rf"{re.escape(START)}\n(.*?)\n{re.escape(END)}", src, re.S)
    if not m:
        sys.exit(f"ERROR: {START} / {END} markers not found in {GEN}")
    return m.group(1)


def main() -> int:
    check = "--check" in sys.argv
    src = GEN.read_text(encoding="utf-8")
    want, have = build_block(), current_block(src)
    if have == want:
        print("presets in sync with the docs  OK")
        return 0
    if check:
        print("DRIFT: generate.py presets do not match the docs.  Fix: python tools/sync_presets.py")
        return 1
    new = re.sub(
        rf"({re.escape(START)}\n).*?(\n{re.escape(END)})",
        lambda m: m.group(1) + want + m.group(2),
        src,
        flags=re.S,
    )
    GEN.write_text(new, encoding="utf-8")
    print(f"regenerated generate.py _SYNCED_PRESETS from the docs ({', '.join(ORDER)})  OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
