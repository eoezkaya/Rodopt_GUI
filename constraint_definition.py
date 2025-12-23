# constraint_definition.py
from __future__ import annotations
from typing import Optional
from PyQt6.QtCore import pyqtSignal
from string_field import StringField
import re
from xml.etree import ElementTree as ET


class ConstraintDefinition(StringField):
    """
    A StringField specialized for constraint definitions.

    Adds:
      - Live validation for strings like "> 9.0" or ">= -12,5"
      - Emits validationChanged(bool)
      - Placeholder hint: "e.g., < 0.12 or > -0.78"

    Styling:
      No inline colors are applied. We set a dynamic property on the QLineEdit:
        _edit.setProperty("isValid", True/False)
      You can style it in QSS, e.g.:
        QLineEdit[isValid="true"]  { border: 1px solid #2e7d32; }
        QLineEdit[isValid="false"] { border: 1px solid #c62828; }
    """

    validationChanged = pyqtSignal(bool)

    def __init__(
        self,
        name: str = "Definition",
        default: str = "",
        *,
        label_width: int = 120,
        field_width: int = 300,
        parent: Optional = None,
    ):
        super().__init__(name, default, label_width=label_width, field_width=field_width, parent=parent)

        # Add placeholder hint for the user
        self._edit.setPlaceholderText("e.g., < 0.12 or > -0.78")

        # Identify the line edit for optional QSS targeting
        self._edit.setObjectName("constraintDefinitionEdit")

        # Connect validator to text changes and run once
        self.textChanged.connect(self._validate_definition)
        self._validate_definition(self.text)

    # -------- XML helpers (override to expose operator/value if valid) --------
    def to_xml(self, tag: str | None = None, attr_label: str | None = None) -> ET.Element:
        """
        Return <definition> with operator/value if valid, otherwise raw text.
        """
        text = self.text.strip()
        el = ET.Element(tag or "definition")

        if self.is_valid_definition(text):
            s = text.replace(",", ".")
            pattern = r'^(>=|<=|>|<|==|!=)\s*(-?\d+(\.\d+)?)$'
            m = re.match(pattern, s)
            if m:
                el.set("operator", m.group(1))
                el.set("value", m.group(2))
        else:
            el.text = text

        if attr_label:
            el.set(attr_label, self.name)
        return el

    def from_xml(self, element: ET.Element) -> None:
        """
        Restore definition text from a <definition> element.
        Accepts either operator/value attributes or raw text.
        """
        if element is None:
            return
        if "operator" in element.attrib and "value" in element.attrib:
            self.text = f"{element.attrib['operator']} {element.attrib['value']}"
        elif element.text:
            self.text = element.text.strip()

    # -------- validation helpers --------
    @staticmethod
    def is_valid_definition(s: str) -> bool:
        if not s:
            return False
        s = s.strip().replace(",", ".")
        pattern = r'^(>=|<=|>|<|==|!=)\s*(-?\d+(\.\d+)?)$'
        return bool(re.match(pattern, s))

    def _validate_definition(self, s: str) -> None:
        s = (s or "").strip()
        if not s:
            self._edit.setProperty("isValid", False)
            self._edit.setToolTip("")
            self._refresh_style()
            self.validationChanged.emit(False)
            return

        ok = self.is_valid_definition(s)
        self._edit.setProperty("isValid", ok)
        self._edit.setToolTip("Valid constraint definition" if ok else "Invalid definition. Use e.g. '> 9.0' or '>= -12,5'")
        self._refresh_style()
        self.validationChanged.emit(ok)

    def _refresh_style(self) -> None:
        le = self._edit
        style = le.style()
        style.unpolish(le)
        style.polish(le)
        le.update()


# ----------------------------------------------------------
# Demo
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    w = ConstraintDefinition("Definition", default="", label_width=140, field_width=300)
    w.validationChanged.connect(lambda ok: print("Valid?", ok))
    w.show()

    def _about_to_quit():
        print("XML element:", w.to_xml_string())
        print("Raw text:", w.text)

    app.aboutToQuit.connect(_about_to_quit)
    sys.exit(app.exec())
