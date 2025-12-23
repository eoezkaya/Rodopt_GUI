# string_field.py
from __future__ import annotations
from typing import Optional
from PyQt6.QtWidgets import QWidget, QLabel, QLineEdit, QHBoxLayout, QApplication, QSizePolicy
from PyQt6.QtCore import pyqtSignal
import sys
from xml.etree import ElementTree as ET
import re


class StringField(QWidget):
    """
    Label + QLineEdit with fixed sizes (no expansion, no extra strip).

    Added XML export helpers:
      - to_xml(tag=None, attr_label=None)
      - to_xml_string(...)
    """
    textChanged = pyqtSignal(str)

    def __init__(
        self,
        name: str,
        default: str = "",
        *,
        label_width: int = 120,
        field_width: int = 300,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # Label
        self._label = QLabel(name, self)
        self._label.setFixedWidth(label_width)
        self._label.setFixedHeight(self._label.sizeHint().height())
        self._label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Line edit
        self._edit = QLineEdit(self)
        self._edit.setText(default)
        self._edit.setFixedWidth(field_width)
        self._edit.setFixedHeight(self._edit.sizeHint().height())
        self._edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # set to 0 if you want no gap at all
        layout.addWidget(self._label)
        layout.addWidget(self._edit)
        self.setLayout(layout)

        # Signal
        self._edit.textChanged.connect(self.textChanged.emit)

        # Lock composite size
        self.setFixedSize(self.sizeHint())

    def from_xml(self, element: ET.Element) -> None:
        """
        Restore value from an XML element that was produced by to_xml().
        Example:
            <Name>ObjectiveFunction</Name>
        """
        if element is not None and element.text is not None:
            self.text = element.text.strip()

    # --- public API ---
    @property
    def name(self) -> str:
        return self._label.text()

    @name.setter
    def name(self, text: str) -> None:
        self._label.setText(text)

    @property
    def text(self) -> str:
        return self._edit.text()

    @text.setter
    def text(self, value: str) -> None:
        self._edit.setText(value)

    # --- XML helpers ---
    def to_xml(self, tag: str | None = None, attr_label: str | None = None) -> ET.Element:
        """
        Build an XML element for this field.

        Args:
            tag: Optional custom tag name. If None, a safe tag is derived from the label.
            attr_label: Optional attribute name to store the visible label text, e.g. "label".

        Returns:
            xml.etree.ElementTree.Element with element.text = current field text.
        """
        safe_tag = tag or self._sanitize_tag(self.name)
        el = ET.Element(safe_tag)
        el.text = self.text
        if attr_label:
            el.set(attr_label, self.name)
        return el

    def to_xml_string(self, **kwargs) -> str:
        """
        Returns a UTF-8 XML string of `to_xml(...)`.
        Accepts same kwargs as `to_xml` (e.g., tag="name", attr_label="label").
        """
        el = self.to_xml(**kwargs)
        return ET.tostring(el, encoding="utf-8").decode("utf-8")

    @staticmethod
    def _sanitize_tag(label: str) -> str:
        """
        Create a safe XML tag from a human label:
        - non-alphanumeric -> '_'
        - collapse multiple '_'s
        - ensure it starts with a letter; prefix with 'f_' if needed
        """
        s = re.sub(r"[^0-9A-Za-z]+", "_", label).strip("_")
        s = re.sub(r"_+", "_", s)
        if not s or s[0].isdigit():
            s = "f_" + (s or "field")
        return s


# ----------------------------------------------------------
# Demo
if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = StringField("Study name", default="MyDesignStudy", label_width=140, field_width=300)
    w.textChanged.connect(lambda s: print("Changed to:", s))
    w.show()

    # Print XML snapshot on close
    def _about_to_quit():
        print("XML element:", w.to_xml_string())
        print("XML with attr:", w.to_xml_string(attr_label="label"))

    app.aboutToQuit.connect(_about_to_quit)

    sys.exit(app.exec())
