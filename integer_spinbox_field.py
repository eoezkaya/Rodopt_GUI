# integer_spinbox_field.py
from __future__ import annotations
from typing import Optional
from PyQt6.QtWidgets import QWidget, QLabel, QSpinBox, QHBoxLayout, QApplication, QSizePolicy
from PyQt6.QtCore import pyqtSignal
from xml.etree import ElementTree as ET
import sys
import re


class IntegerSpinBoxField(QWidget):
    """
    Fixed-size label + QSpinBox.

    Properties:
        name (str)          : label text
        value (int)         : current value
        minimum (int)       : lower bound
        maximum (int)       : upper bound
        label_width (int)   : fixed label width (0 = auto reset)
        field_width (int)   : fixed spinbox width (0 = auto reset)

    XML helpers:
        to_xml(tag=None, attr_label=None) -> ET.Element
        to_xml_string(**kwargs) -> str
    """
    valueChanged = pyqtSignal(int)

    def __init__(
        self,
        name: str,
        value: int = 0,
        minimum: int = -10_000,
        maximum: int = 10_000,
        label_width: int = 120,
        field_width: int = 80,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        # --- Label ---
        self._label = QLabel(name, self)
        if label_width > 0:
            self._label.setFixedWidth(label_width)
        self._label.setFixedHeight(self._label.sizeHint().height())
        self._label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # --- SpinBox ---
        self._spin = QSpinBox(self)
        self._spin.setRange(minimum, maximum)
        self._spin.setValue(value)
        if field_width > 0:
            self._spin.setFixedWidth(field_width)
        self._spin.setFixedHeight(self._spin.sizeHint().height())
        self._spin.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # --- Layout (no stretching) ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._label)     # no stretch factors
        layout.addWidget(self._spin)
        self.setLayout(layout)

        # signal
        self._spin.valueChanged.connect(self.valueChanged.emit)

        # lock composite size
        self.setFixedSize(self.sizeHint())

    def from_xml(self, element: ET.Element) -> None:
        """
        Restore value from an XML element produced by to_xml().
        Example:
            <Iterations>42</Iterations>
        """
        if element is not None and element.text is not None:
            try:
                self.value = int(element.text.strip())
            except ValueError:
                # Ignore invalid text; keep previous value
                pass

        # optional: restore bounds if you later decide to save them
        if element is not None:
            if "min" in element.attrib:
                try:
                    self.minimum = int(element.get("min"))
                except ValueError:
                    pass
            if "max" in element.attrib:
                try:
                    self.maximum = int(element.get("max"))
                except ValueError:
                    pass

    # --- properties ---
    @property
    def name(self) -> str:
        return self._label.text()

    @name.setter
    def name(self, text: str) -> None:
        self._label.setText(text)

    @property
    def value(self) -> int:
        return self._spin.value()

    @value.setter
    def value(self, v: int) -> None:
        self._spin.setValue(v)

    @property
    def minimum(self) -> int:
        return self._spin.minimum()

    @minimum.setter
    def minimum(self, v: int) -> None:
        self._spin.setMinimum(v)

    @property
    def maximum(self) -> int:
        return self._spin.maximum()

    @maximum.setter
    def maximum(self, v: int) -> None:
        self._spin.setMaximum(v)

    # --- width controls ---
    @property
    def label_width(self) -> int:
        return self._label.width()

    @label_width.setter
    def label_width(self, w: int) -> None:
        if w > 0:
            self._label.setFixedWidth(w)
        else:
            self._label.setMaximumWidth(16777215)  # reset to auto

        self.setFixedSize(self.sizeHint())

    @property
    def field_width(self) -> int:
        return self._spin.width()

    @field_width.setter
    def field_width(self, w: int) -> None:
        if w > 0:
            self._spin.setFixedWidth(w)
        else:
            self._spin.setMaximumWidth(16777215)  # reset to auto

        self.setFixedSize(self.sizeHint())

    # --- XML helpers ---
    def to_xml(self, tag: str | None = None, attr_label: str | None = None) -> ET.Element:
        """
        Build an XML element for this integer field.
        element.text holds the integer value as string.

        Args:
            tag: custom tag; if None, a safe tag is derived from the label text.
            attr_label: optional attribute name to store the human label, e.g. "label".
        """
        safe_tag = tag or self._sanitize_tag(self.name)
        el = ET.Element(safe_tag)
        el.text = str(self.value)
        if attr_label:
            el.set(attr_label, self.name)
        # If you later want bounds in XML, uncomment:
        # el.set("min", str(self.minimum))
        # el.set("max", str(self.maximum))
        return el

    def to_xml_string(self, **kwargs) -> str:
        """UTF-8 XML string for the element returned by to_xml(...)."""
        el = self.to_xml(**kwargs)
        return ET.tostring(el, encoding="utf-8").decode("utf-8")

    @staticmethod
    def _sanitize_tag(label: str) -> str:
        s = re.sub(r"[^0-9A-Za-z]+", "_", label).strip("_")
        s = re.sub(r"_+", "_", s)
        if not s or s[0].isdigit():
            s = "f_" + (s or "field")
        return s


# ----------------------------------------------------------
# Run standalone for quick demo
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Label width = 200, spinbox width = 80; fixed sizes
    widget = IntegerSpinBoxField(
        "Iterations", value=5, minimum=0, maximum=50,
        label_width=200, field_width=80
    )
    widget.valueChanged.connect(lambda v: print("Value changed to:", v))
    widget.show()

    # Print XML on close
    def _about_to_quit():
        print("XML:", widget.to_xml_string())
        print("XML with attr:", widget.to_xml_string(attr_label="label"))

    app.aboutToQuit.connect(_about_to_quit)
    sys.exit(app.exec())
