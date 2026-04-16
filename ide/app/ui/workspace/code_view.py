"""Text editor with syntax highlighting and markdown preview."""

from __future__ import annotations

from pathlib import Path

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename, ClassNotFound, TextLexer

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


_MARKDOWN_EXTS = {".md", ".markdown", ".mdown", ".mkd"}
_MONO_FONT = QFont("Cascadia Code", 10)


# ---------------------------------------------------------------------------
# Real-time syntax highlighter using Pygments
# ---------------------------------------------------------------------------

# Map Pygments token *suffix* patterns to colours.
# We match against the stringified token like "Token.Keyword.Reserved".
_TOKEN_RULES: list[tuple[str, str, bool]] = [
    # (suffix, colour, bold)
    ("Token.Comment", "#008000", False),
    ("Token.Keyword", "#0000FF", True),
    ("Token.Literal.String", "#A31515", False),
    ("Token.Literal.Number", "#098658", False),
    ("Token.Name.Builtin", "#267F99", False),
    ("Token.Name.Function", "#795E26", False),
    ("Token.Name.Class", "#267F99", True),
    ("Token.Name.Decorator", "#795E26", False),
    ("Token.Name.Attribute", "#E50000", False),
    ("Token.Operator", "#000000", False),
    ("Token.Name.Variable", "#001080", False),
]


class _PygmentsHighlighter(QSyntaxHighlighter):
    """QSyntaxHighlighter backed by a Pygments lexer."""

    def __init__(self, document: QTextDocument, lexer=None) -> None:
        super().__init__(document)
        self._lexer = lexer or TextLexer()

    def set_lexer(self, lexer) -> None:
        self._lexer = lexer or TextLexer()
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        from pygments.token import Token

        for start, tokentype, value in self._lexer.get_tokens_unprocessed(text):
            if tokentype in (Token.Text, Token.Text.Whitespace, Token):
                continue
            token_str = str(tokentype)
            for suffix, color, bold in _TOKEN_RULES:
                if token_str.startswith(suffix):
                    fmt = QTextCharFormat()
                    fmt.setForeground(QColor(color))
                    if bold:
                        fmt.setFontWeight(75)
                    self.setFormat(start, len(value), fmt)
                    break


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["extra", "codehilite", "toc", "tables"],
        extension_configs={
            "codehilite": {"css_class": "highlight", "guess_lang": True},
        },
    )


_MD_HTML_TEMPLATE = """<html><head><style>
body {{ font-family: 'Segoe UI', sans-serif; font-size: 14px; margin: 16px; }}
pre, code {{ font-family: 'Cascadia Code', 'Consolas', monospace; }}
pre {{ font-size: 13px; background: #f6f8fa; padding: 12px; border-radius: 6px; overflow-x: auto; }}
code {{ background: #f0f0f0; padding: 1px 4px; border-radius: 3px; }}
pre code {{ background: none; padding: 0; }}
h1, h2, h3, h4, h5, h6 {{ margin-top: 20px; margin-bottom: 8px; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
th, td {{ border: 1px solid #ddd; padding: 6px 12px; text-align: left; }}
th {{ background: #f5f5f5; font-weight: 600; }}
blockquote {{ border-left: 3px solid #ddd; margin: 8px 0; padding: 4px 12px; color: #555; }}
a {{ color: #3b82f6; }}
img {{ max-width: 100%; }}
</style></head><body>{body}</body></html>"""


# ---------------------------------------------------------------------------
# Syntax-highlighted HTML for the editor gutter (used by non-md files too)
# ---------------------------------------------------------------------------

_PYGMENTS_CSS_CACHE: str | None = None


def _pygments_css() -> str:
    global _PYGMENTS_CSS_CACHE
    if _PYGMENTS_CSS_CACHE is None:
        _PYGMENTS_CSS_CACHE = HtmlFormatter(
            style="default", noclasses=True
        ).get_style_defs()
    return _PYGMENTS_CSS_CACHE


def _highlight_code(text: str, filename: str) -> str:
    try:
        lexer = get_lexer_for_filename(filename, text)
    except ClassNotFound:
        lexer = TextLexer()
    fmt = HtmlFormatter(
        style="default", noclasses=True, linenos="table", linespans="line"
    )
    return highlight(text, lexer, fmt)


_CODE_HTML_TEMPLATE = """<html><head><style>
body {{ font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 13px; margin: 0; }}
pre {{ font-size: 13px; }}
table {{ border-collapse: collapse; }}
td.linenos {{ padding-right: 12px; color: #aaa; text-align: right; vertical-align: top; }}
td.code {{ vertical-align: top; }}
{css}
</style></head><body>{body}</body></html>"""


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------


class CodeViewWidget(QWidget):
    """Text editor with syntax highlighting and markdown preview.

    Non-markdown files: always show an editable QTextEdit.
    Markdown files: toggle between rendered preview (read-only) and
    editable source via the "View Source" / "Preview" button.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._file_path: str | None = None
        self._is_markdown: bool = False
        self._showing_render: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Toolbar ----
        toolbar = QWidget()
        toolbar.setObjectName("codeToolbar")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(8, 6, 8, 6)
        tb.setSpacing(8)

        self._path_label = QLabel("No file opened")
        self._path_label.setObjectName("codePathLabel")

        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("codeSaveButton")
        self._save_btn.clicked.connect(self._on_save)

        self._md_toggle = QPushButton("View Source")
        self._md_toggle.setObjectName("codeMdToggle")
        self._md_toggle.setVisible(False)
        self._md_toggle.clicked.connect(self._on_toggle_md)

        tb.addWidget(self._path_label, 1)
        tb.addWidget(self._save_btn)
        tb.addWidget(self._md_toggle)

        # ---- Stacked: [0] editor  [1] markdown preview ----
        self._stack = QStackedWidget()

        # Page 0: plain-text editor (always editable)
        self._editor = QTextEdit()
        self._editor.setObjectName("codeEditor")
        self._editor.setFont(_MONO_FONT)
        self._editor.setLineWrapMode(QTextEdit.NoWrap)
        self._editor.setPlaceholderText("Open a file from the directory tree…")

        # Syntax highlighter attached to the editor's document
        self._highlighter = _PygmentsHighlighter(self._editor.document())

        # Page 1: rendered markdown (read-only)
        self._preview = QTextBrowser()
        self._preview.setObjectName("codePreview")
        self._preview.setOpenExternalLinks(True)

        self._stack.addWidget(self._editor)
        self._stack.addWidget(self._preview)

        layout.addWidget(toolbar)
        layout.addWidget(self._stack, 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_file(self, path: str, *, text: str | None = None) -> None:
        """Load a text file into the editor."""
        self._file_path = str(Path(path).resolve())
        name = Path(path).name
        self._path_label.setText(name)
        self._path_label.setToolTip(self._file_path)

        if text is not None:
            raw = text
        else:
            try:
                raw = Path(path).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raw = Path(path).read_text(encoding="latin-1", errors="replace")

        self._is_markdown = Path(path).suffix.lower() in _MARKDOWN_EXTS
        self._md_toggle.setVisible(self._is_markdown)

        # Always put source text into editor
        self._editor.setPlainText(raw)
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self._editor.setTextCursor(cursor)

        # Set syntax highlighter lexer based on filename
        try:
            lexer = get_lexer_for_filename(Path(path).name, raw)
        except ClassNotFound:
            lexer = TextLexer()

        # Re-attach highlighter to the current document (setPlainText
        # may have replaced the underlying QTextDocument)
        doc = self._editor.document()
        if self._highlighter.document() is not doc:
            self._highlighter.setDocument(doc)
        self._highlighter.set_lexer(lexer)

        if self._is_markdown:
            # Default: show rendered preview
            self._showing_render = True
            self._md_toggle.setText("View Source")
            self._render_preview()
            self._stack.setCurrentIndex(1)
        else:
            self._showing_render = False
            self._stack.setCurrentIndex(0)

    def file_path(self) -> str | None:
        return self._file_path

    # ------------------------------------------------------------------
    # Markdown toggle
    # ------------------------------------------------------------------

    def _on_toggle_md(self) -> None:
        if self._showing_render:
            # Switch from preview → source editor
            self._showing_render = False
            self._md_toggle.setText("Preview")
            self._stack.setCurrentIndex(0)
        else:
            # Switch from source → preview: sync text first
            self._render_preview()
            self._showing_render = True
            self._md_toggle.setText("View Source")
            self._stack.setCurrentIndex(1)

    def _render_preview(self) -> None:
        html = _render_markdown(self._editor.toPlainText())
        self._preview.setHtml(_MD_HTML_TEMPLATE.format(body=html))

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        if not self._file_path:
            return
        Path(self._file_path).write_text(self._editor.toPlainText(), encoding="utf-8")
