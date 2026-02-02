from __future__ import annotations

import csv
import os
import xml.etree.ElementTree as ET
from typing import Optional

import matplotlib.pyplot as plt


def _as_bool(s: str) -> bool:
    v = (s or "").strip().lower()
    if v in ("1", "1.0", "true", "yes", "y"):
        return True
    if v in ("0", "0.0", "false", "no", "n"):
        return False
    try:
        return float(v) > 0.5
    except Exception:
        return False


def _find_col(headers: list[str], candidates: tuple[str, ...]) -> int:
    norm = [h.strip().lower() for h in headers]
    for c in candidates:
        if c in norm:
            return norm.index(c)
    return -1


def _read_dimension_from_xml(xml_path: str) -> int:
    if not xml_path or not os.path.isfile(xml_path):
        raise ValueError("Study XML path not set or not found.")
    root = ET.parse(xml_path).getroot()
    dim_el = root.find(".//dimension")
    if dim_el is None or not (dim_el.text or "").strip():
        raise ValueError("Could not find <dimension> in the study XML.")
    d = int(float(dim_el.text.strip()))
    if d <= 0:
        raise ValueError("<dimension> must be a positive integer.")
    return d


def plot_pareto_front(csv_path: str, *, xml_path: str, title: Optional[str] = None) -> None:
    """
    Plot Pareto front from history.csv.

    Parameters
    ----------
    csv_path : str
        Path to history.csv
    xml_path : str
        Path to study XML (used to read <dimension> so objective columns can be located)
    title : Optional[str]
        Plot title
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(csv_path)

    d = _read_dimension_from_xml(xml_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if len(rows) < 2:
        raise ValueError("CSV has no data rows.")

    headers = rows[0]
    data = rows[1:]

    # CHANGED: objective columns are positional: (d+1) and (d+2) in CSV => indices d and d+1
    obj1_col = d
    obj2_col = d + 1
    if obj2_col >= len(headers):
        raise ValueError(
            f"CSV does not have enough columns for 2 objectives at positions d+1 and d+2 (d={d})."
        )

    feas_col = _find_col(headers, ("feasible", "feasibility", "is_feasible", "feas", "feas_flag"))
    if feas_col < 0:
        raise ValueError("Could not find feasibility column for Pareto plot.")

    feasible_points: list[tuple[float, float, int]] = []
    infeasible_points: list[tuple[float, float, int]] = []

    for i, r in enumerate(data):
        if max(obj1_col, obj2_col, feas_col) >= len(r):
            continue

        try:
            x_val = float(r[obj1_col])
            y_val = float(r[obj2_col])
        except ValueError:
            continue

        sid = i + 1  # row number excluding header
        if _as_bool(r[feas_col]):
            feasible_points.append((x_val, y_val, sid))
        else:
            infeasible_points.append((x_val, y_val, sid))

    if not feasible_points and not infeasible_points:
        raise ValueError("No valid points found in CSV.")

    # NEW: decide log-scale if values span several orders of magnitude
    all_pts = feasible_points + infeasible_points
    xs_all = [p[0] for p in all_pts]
    ys_all = [p[1] for p in all_pts]

    def _should_log(vals: list[float], *, decades: float = 3.0) -> bool:
        # require strictly positive for log scale
        vpos = [v for v in vals if v > 0.0]
        if len(vpos) != len(vals) or not vpos:
            return False
        vmin = min(vpos)
        vmax = max(vpos)
        if vmin <= 0.0 or vmax <= 0.0:
            return False
        # log10(vmax/vmin) >= decades  => spans "decades" orders of magnitude
        import math
        return math.log10(vmax / vmin) >= decades

    use_log_x = _should_log(xs_all, decades=3.0)
    use_log_y = _should_log(ys_all, decades=3.0)

    def dominates(a, b) -> bool:
        ax, ay = a[0], a[1]
        bx, by = b[0], b[1]
        return (ax <= bx and ay <= by) and (ax < bx or ay < by)

    pareto_points = []
    for p in feasible_points:
        if not any(dominates(q, p) for q in feasible_points if q != p):
            pareto_points.append(p)
    pareto_points.sort(key=lambda p: p[0])

    plt.figure(figsize=(10, 8))
    ax = plt.gca()

    if infeasible_points:
        x_infeas, y_infeas, _ = zip(*infeasible_points)
        # CHANGED: red dots for unfeasible samples
        plt.scatter(x_infeas, y_infeas, color="red", label="Unfeasible Samples", marker="o")
        for x, y, sid in infeasible_points:
            plt.annotate(str(sid), (x, y), textcoords="offset points", xytext=(4, 2), fontsize=7, color="red")

    if feasible_points:
        x_feas, y_feas, _ = zip(*feasible_points)
        plt.scatter(x_feas, y_feas, color="blue", label="Feasible Samples", marker="o")
        for x, y, sid in feasible_points:
            plt.annotate(str(sid), (x, y), textcoords="offset points", xytext=(4, 2), fontsize=7, color="blue")

    if pareto_points:
        px, py = zip(*[(p[0], p[1]) for p in pareto_points])
        plt.plot(px, py, color="green", marker="o", linewidth=2.5, label="Pareto Front")

    plt.xlabel(headers[obj1_col].strip() or "Objective 1")
    plt.ylabel(headers[obj2_col].strip() or "Objective 2")
    plt.title(title or "Pareto Front")

    # NEW: apply log scales if appropriate
    if use_log_x:
        ax.set_xscale("log")
    if use_log_y:
        ax.set_yscale("log")

    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.show()