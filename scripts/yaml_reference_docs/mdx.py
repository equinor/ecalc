"""
Text utilities for MDX output: escaping, keyword detection, file I/O.
"""

import re
from pathlib import Path

_yaml_keyword_re = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_module_path_re = re.compile(r"\b[a-z_][a-z0-9_.]*\.([A-Z]\w*)")
_kw_placeholder_re = re.compile(r"\$ECALC_DOCS_KEYWORDS_URL/\S*")


def mdx_escape(text: str) -> str:
    """Escape characters that MDX interprets as JSX/expressions."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("{", "&#123;")
        .replace("}", "&#125;")
    )


def mdx_code(text: str) -> str:
    """Wrap text in an HTML <code> tag, escaping MDX-unsafe characters."""
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("{", "&#123;")
        .replace("}", "&#125;")
        .replace("|", "&#124;")
    )
    return f"<code>{safe}</code>"


def clean_description(desc: str) -> str:
    """Remove $ECALC_DOCS_KEYWORDS_URL/... placeholders from descriptions."""
    if not desc:
        return ""
    return _kw_placeholder_re.sub("", desc).strip()


def is_yaml_keyword(keyword: str) -> bool:
    """Check if a string looks like a YAML keyword (e.g. TIME_SERIES, NAME)."""
    if not keyword:
        return False
    return bool(_yaml_keyword_re.match(keyword))


def strip_module_paths(text: str) -> str:
    """Remove Python module paths, keeping only class names.

    'libecalc.foo.bar.MyClass' → 'MyClass'
    """
    return _module_path_re.sub(r"\1", text)


def write_text_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
