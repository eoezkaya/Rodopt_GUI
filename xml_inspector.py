# xml_inspector.py
from typing import Optional
import xml.etree.ElementTree as ET


class XMLInspector:
    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.tree = ET.parse(xml_path)
        self.root = self.tree.getroot()

    def general(self) -> Optional[ET.Element]:
        return (
            self.root.find("general_settings")
            or self.root.find("GeneralSettings")
        )

    def name(self) -> str:
        g = self.general()
        return (g.findtext("name") or g.findtext("Name") or "").strip() if g else ""

    def working_directory(self) -> str:
        g = self.general()
        return (
            g.findtext("working_directory")
            or g.findtext("Working_directory")
            or ""
        ).strip() if g else ""

    def dimension(self) -> Optional[int]:
        g = self.general()
        if not g:
            return None
        text = (g.findtext("dimension") or g.findtext("Dimension") or "").strip()
        return int(text) if text.isdigit() else None

    def num_objectives(self) -> int:
        return len(self.root.findall("objective_function"))

    def num_constraints(self) -> int:
        return len(self.root.findall("constraint_function"))
