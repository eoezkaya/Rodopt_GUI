from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QToolButton, QTextEdit, QMessageBox


class LogDisplayWindow(QDialog):
    def __init__(
        self,
        *,
        file_path: str,
        title: str | None = None,
        icon_dir: str | Path | None = None,
        parent=None,
        min_size: tuple[int, int] = (900, 600),
    ) -> None:
        super().__init__(parent)
        self._file_path = str(file_path)
        self._icon_dir = Path(icon_dir) if icon_dir is not None else (Path(__file__).resolve().parent / "images")

        self.setWindowTitle(title or Path(self._file_path).name)
        self.setMinimumSize(*min_size)

        self._editor = QTextEdit(self)
        self._editor.setReadOnly(True)
        self._editor.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        self._reload_btn = QToolButton(self)
        self._reload_btn.setAutoRaise(True)
        self._reload_btn.setToolTip("Reload")
        self._reload_btn.setIcon(QIcon(str(self._icon_dir / "reload.svg")))
        self._reload_btn.setIconSize(QSize(18, 18))
        self._reload_btn.clicked.connect(lambda: self.reload(scroll_to_end=True))

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch(1)
        top_bar.addWidget(self._reload_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top_bar)
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.reload(scroll_to_end=True)

    def reload(self, *, scroll_to_end: bool = True) -> None:
        try:
            text = Path(self._file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Failed to open file:\n{e}")
            return

        self._editor.setPlainText(text)
        if scroll_to_end:
            self._editor.moveCursor(QTextCursor.MoveOperation.End)
            QTimer.singleShot(
                0,
                lambda: self._editor.verticalScrollBar().setValue(self._editor.verticalScrollBar().maximum()),
            )