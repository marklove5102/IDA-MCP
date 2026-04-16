"""Code/text viewer with syntax highlighting and markdown preview."""

from __future__ import annotations

from pathlib import Path

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename, ClassNotFound, TextLexer

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
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
_HTML_STYLE_CACHE: str | None = None


def _get_pygments_css() -> str:
    global _HTML_STYLE_CACHE
    if _HTML_STYLE_CACHE is None:
        formatter = HtmlFormatter(style="default", noclasses=True)
        _HTML_STYLE_CACHE = formatter.get_style_defs()
    return _HTML_STYLE_CACHE


def _highlight_code(text: str, filename: str) -> str:
    try:
        lexer = get_lexer_for_filename(filename, text)
    except ClassNotFound:
        lexer = TextLexer()
    formatter = HtmlFormatter(
        style="default", noclasses=True, linenos="table", linespans="line"
    )
    return highlight(text, lexer, formatter)


def _render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["extra", "codehilite", "toc", "tables"],
        extension_configs={
            "codehilite": {"css_class": "highlight", "guess_lang": True}
        },
    )


def _build_html(body: str) -> str:
    css = _get_pygments_css()
    return f"""<html><head><style>
    body {{ font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 13px; margin: 8px; }}
    pre {{ font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 13px; }}
    table {{ border-collapse: collapse; }}
    td.linenos {{ padding-right: 12px; color: #aaa; text-align: right; }}
    {css}
    .highlight pre {{ font-size: 13px; }}
    h1, h2, h3, h4, h5, h6 {{ margin-top: 16px; margin-bottom: 8px; }}
    code {{ font-family: 'Cascadia Code', 'Consolas', monospace; background: #f0f0f0; padding: 1px 4px; border-radius: 3px; }}
    pre code {{ background: none; padding: 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 12px; text-align: left; }}
    th {{ background: #f5f5f5; font-weight: 600; }}
    blockquote {{ border-left: 3px solid #ddd; margin: 8px 0; padding: 4px 12px; color: #555; }}
    a {{ color: #3b82f6; }}
    img {{ max-width: 100%; }}
</style></head><body>{body}</body></html>"""


class CodeViewWidget(QWidget):
    """Code/text viewer with syntax highlighting and markdown preview."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._file_path: str | None = None
        self._text: str = ""
        self._is_markdown: bool = False
        self._showing_markdown: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setObjectName("codeToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(8)

        self._path_label = QLabel("No file opened")
        self._path_label.setObjectName("codePathLabel")

        self._mode_btn = QPushButton("Markdown")
        self._mode_btn.setObjectName("codeModeToggle")
        self._mode_btn.setCheckable(True)
        self._mode_btn.setVisible(False)
        self._mode_btn.clicked.connect(self._on_toggle_mode)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setCheckable(True)
        self._edit_btn.setObjectName("codeEditToggle")
        self._edit_btn.clicked.connect(self._on_toggle_edit)

        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("codeSaveButton")
        self._save_btn.setVisible(False)
        self._save_btn.clicked.connect(self._on_save)

        toolbar_layout.addWidget(self._path_label, 1)
        toolbar_layout.addWidget(self._edit_btn)
        toolbar_layout.addWidget(self._save_btn)
        toolbar_layout.addWidget(self._mode_btn)

        # Stacked: [0] highlighted view, [1] plain text editor
        self._view_stack = QStackedWidget()

        # Highlighted view (read-only HTML)
        self._highlight_view = QTextBrowser()
        self._highlight_view.setObjectName("codeContent")
        self._highlight_view.setOpenExternalLinks(True)
        self._highlight_view.setPlaceholderText(
            "Open a file from the directory tree to view its content."
        )

        # Plain text editor (for editing)
        self._plain_editor = QTextEdit()
        self._plain_editor.setObjectName("codePlainEditor")
        self._plain_editor.setFont(QFont("Cascadia Code", 10))
        self._plain_editor.setLineWrapMode(QTextEdit.NoWrap)
        self._plain_editor.setPlaceholderText("Edit mode")

        self._view_stack.addWidget(self._highlight_view)
        self._view_stack.addWidget(self._plain_editor)

        layout.addWidget(toolbar)
        layout.addWidget(self._view_stack, 1)

    def load_file(self, path: str, *, text: str | None = None) -> None:
        """Load a text file and display with syntax highlighting."""
        self._file_path = str(Path(path).resolve())
        name = Path(path).name
        self._path_label.setText(name)
        self._path_label.setToolTip(self._file_path)

        if text is not None:
            self._text = text
        else:
            try:
                self._text = Path(path).read_text(encoding="utf-8", errors="replace")
            except Exception:
                self._text = Path(path).read_text(encoding="latin-1", errors="replace")

        suffix = Path(path).suffix.lower()
        self._is_markdown = suffix in _MARKDOWN_EXTS
        self._mode_btn.setVisible(self._is_markdown)

        if self._is_markdown:
            self._showing_markdown = True
            self._mode_btn.setChecked(True)
            self._mode_btn.setText("Code")
            self._show_markdown()
        else:
            self._showing_markdown = False
            self._mode_btn.setChecked(False)
            self._show_code()

    def _show_code(self) -> None:
        if not self._file_path:
            return
        html_body = _highlight_code(self._text, Path(self._file_path).name)
        self._highlight_view.setHtml(_build_html(html_body))

    def _show_markdown(self) -> None:
        html_body = _render_markdown(self._text)
        self._highlight_view.setHtml(_build_html(html_body))

    def _on_toggle_mode(self, checked: bool) -> None:
        if checked:
            self._showing_markdown = True
            self._mode_btn.setText("Code")
            self._show_markdown()
        else:
            self._showing_markdown = False
            self._mode_btn.setText("Markdown")
            self._show_code()

    def _on_toggle_edit(self, checked: bool) -> None:
        if checked:
            # Switch to plain text editor
            self._plain_editor.setPlainText(self._text)
            cursor = self._plain_editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self._plain_editor.setTextCursor(cursor)
            self._view_stack.setCurrentIndex(1)
            self._save_btn.setVisible(True)
            self._edit_btn.setText("View")
        else:
            # Switch back to highlighted view
            self._text = self._plain_editor.toPlainText()
            self._view_stack.setCurrentIndex(0)
            self._save_btn.setVisible(False)
            self._edit_btn.setText("Edit")
            if self._is_markdown and self._showing_markdown:
                self._show_markdown()
            else:
                self._show_code()

    def _on_save(self) -> None:
        if not self._file_path:
            return
        self._text = self._plain_editor.toPlainText()
        Path(self._file_path).write_text(self._text, encoding="utf-8")

    def file_path(self) -> str | None:
        return self._file_path
