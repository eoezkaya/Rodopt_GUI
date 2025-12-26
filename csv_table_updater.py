# csv_table_updater.py
import csv
import os
from typing import Optional

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from xml_inspector import XMLInspector


class CSVTableUpdater:
    def __init__(self, table: QTableWidget):
        self.table = table
        self._last_mtime = 0.0

    def update(
        self,
        *,
        csv_path: str,
        xml_path: str,
        start_time: float,
        dimension: Optional[int],
        state: str,
    ):
        """Update table from DoE_history.csv if needed."""
        if state != "running" or not start_time:
            return
        if not os.path.isfile(csv_path):
            return

        mtime = os.path.getmtime(csv_path)
        if mtime == self._last_mtime or mtime < start_time:
            return

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        if len(rows) < 2:
            return

        headers = rows[0]
        data = rows[1:]
        n_cols = len(headers)
        dim = dimension or 0
        if dim >= n_cols:
            return

        xml = XMLInspector(xml_path)
        num_objectives = max(xml.num_objectives(), 1)
        num_constraints = xml.num_constraints()

        feas_col = n_cols - 1
        obj_cols = list(range(dim, min(dim + num_objectives, n_cols)))

        pareto_indices, best_idx = self._analyze(data, obj_cols, feas_col)

        self._populate_table(
            headers,
            data,
            pareto_indices,
            best_idx,
            obj_cols,
            feas_col,
            num_objectives,
            num_constraints,
        )

        self._last_mtime = mtime
        self.table.scrollToBottom()

    # ------------------------------------------------------------
    # --- Analysis ---
    # ------------------------------------------------------------
    def _analyze(self, data, obj_cols, feas_col):
        pareto = set()
        best_idx = None

        if len(obj_cols) == 1:
            feasible = [
                (i, float(row[obj_cols[0]]))
                for i, row in enumerate(data)
                if feas_col < len(row) and self._is_float(row[feas_col])
                and float(row[feas_col]) == 1.0
            ]
            if feasible:
                best_idx, _ = min(feasible, key=lambda x: x[1])

        elif len(obj_cols) == 2:
            feasible_points = []
            for i, row in enumerate(data):
                try:
                    if float(row[feas_col]) == 1.0:
                        feasible_points.append((i, [float(row[c]) for c in obj_cols]))
                except Exception:
                    continue

            pareto = self._pareto_indices([v for _, v in feasible_points])
            pareto = {feasible_points[i][0] for i in pareto}

        return pareto, best_idx

    @staticmethod
    def _pareto_indices(values):
        pareto = set()
        for i, vi in enumerate(values):
            dominated = False
            for j, vj in enumerate(values):
                if i == j:
                    continue
                if all(a <= b for a, b in zip(vj, vi)) and any(a < b for a, b in zip(vj, vi)):
                    dominated = True
                    break
            if not dominated:
                pareto.add(i)
        return pareto

    # ------------------------------------------------------------
    # --- UI ---
    # ------------------------------------------------------------
    def _populate_table(
        self,
        headers,
        data,
        pareto_indices,
        best_idx,
        obj_cols,
        feas_col,
        num_objectives,
        num_constraints,
    ):
        self.table.clear()
        self.table.setColumnCount(len(headers) + 1)
        self.table.setRowCount(len(data))
        self.table.setHorizontalHeaderLabels(["ID"] + headers)

        for i, row in enumerate(data):
            id_text = f"★ {i+1}" if i == best_idx or i in pareto_indices else str(i + 1)
            id_item = QTableWidgetItem(id_text)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, id_item)

            for j, val in enumerate(row):
                col = j + 1
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                if j == feas_col:
                    if self._is_float(val) and float(val) == 1.0:
                        item.setText("Yes")
                        item.setForeground(QColor("#2ECC71"))
                    else:
                        item.setText("No")
                        item.setForeground(QColor("#E74C3C"))

                self.table.setItem(i, col, item)

            if i == best_idx or i in pareto_indices:
                for j in range(len(headers) + 1):
                    cell = self.table.item(i, j)
                    if cell:
                        cell.setBackground(QColor("#fff9d6"))

        self._hide_columns(
            len(headers),
            obj_cols,
            feas_col,
            num_objectives,
            num_constraints,
        )

    def _hide_columns(self, n_headers, obj_cols, feas_col, num_objectives, num_constraints):
        keep = {0}
        keep.update(c + 1 for c in obj_cols)
        if num_constraints > 0:
            keep.add(feas_col + 1)

        for j in range(n_headers + 1):
            self.table.setColumnHidden(j, j not in keep)

    @staticmethod
    def _is_float(s: str) -> bool:
        try:
            float(s)
            return True
        except Exception:
            return False
