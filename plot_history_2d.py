import csv
import os
from typing import Sequence, Optional

import matplotlib.pyplot as plt


def _find_col(headers: Sequence[str], candidates: Sequence[str]) -> int:
    norm = [h.strip().lower() for h in headers]
    for c in candidates:
        if c.lower() in norm:
            return norm.index(c.lower())
    return -1


def _find_objective_col(headers: Sequence[str]) -> int:
    """
    Find objective column index.
    Tries common names first, then heuristics (obj/objective/f*).
    """
    norm = [h.strip().lower() for h in headers]

    for key in ("objective", "objective_value", "obj", "obj_value", "f", "f0", "f1"):
        if key in norm:
            return norm.index(key)

    for i, h in enumerate(norm):
        if h.startswith("objective") or h.startswith("obj") or h.startswith("f"):
            return i

    return -1


def _find_feas_col(headers: Sequence[str]) -> int:
    """
    Find feasibility column index.
    """
    return _find_col(headers, ("feasible", "feasibility", "is_feasible", "feas", "feas_flag"))


def _is_feasible(v: str) -> bool:
    s = (v or "").strip().lower()
    if s in ("1", "1.0", "true", "yes", "y"):
        return True
    if s in ("0", "0.0", "false", "no", "n"):
        return False
    try:
        return float(s) > 0.5
    except Exception:
        return False


def plot_history_2d(csv_path: str, d: int, *, title: Optional[str] = None) -> None:
    """
    Plot best-feasible objective improvements vs sample ID.

    Objective column rule:
      - if the problem has d input variables, the objective value is in column (d+1),
        i.e. index d (0-based) in the CSV row.

    - x-axis: sample ID (row number, 1-based)
    - y-axis: objective value
    - infeasible samples are ignored
    - a point is plotted ONLY when the best feasible objective improves.
    """
    if d <= 0:
        raise ValueError("d must be a positive integer.")

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if len(rows) < 2:
        raise ValueError("CSV has no data rows.")

    headers = rows[0]
    data = rows[1:]

    obj_col = d  # (d+1)-th column, 0-based index
    feas_col = _find_feas_col(headers)
    if feas_col < 0:
        raise ValueError("Could not find a feasibility column in CSV headers.")

    xs: list[int] = []
    ys: list[float] = []
    best: Optional[float] = None

    for i, r in enumerate(data):
        if max(obj_col, feas_col) >= len(r):
            continue
        if not _is_feasible(r[feas_col]):
            continue

        try:
            val = float(r[obj_col])
        except ValueError:
            continue

        if best is None or val < best:
            best = val
            xs.append(i + 1)  # sample ID
            ys.append(val)

    if not ys:
        raise ValueError("No feasible samples with numeric objective values found.")

    plt.figure(figsize=(10, 8))

    plt.plot(xs, ys, linewidth=2.0, marker="o", markersize=8)

    ax = plt.gca()
    plt.tight_layout()

    # NEW: avoid clutter — if points are too close, annotate only the better (lower y)
    # threshold in pixels
    min_sep_px = 18.0

    last_annot_xy_disp = None
    last_annot = None
    last_annot_y = None

    # need a draw so transforms are valid
    ax.figure.canvas.draw()

    for x, y in zip(xs, ys):
        # display coords (pixels)
        xy_disp = ax.transData.transform((x, y))

        if last_annot_xy_disp is not None:
            dx = xy_disp[0] - last_annot_xy_disp[0]
            dy = xy_disp[1] - last_annot_xy_disp[1]
            dist2 = dx * dx + dy * dy

            if dist2 < (min_sep_px * min_sep_px):
                # points too close: keep only the better (lower objective)
                # since these are improvements, the later point is always <= previous best,
                # but handle defensively anyway.
                if last_annot is not None and last_annot_y is not None and y <= last_annot_y:
                    last_annot.remove()
                    last_annot = None
                    last_annot_xy_disp = None
                    last_annot_y = None
                else:
                    # current is not better -> skip annotating current
                    continue

        last_annot = ax.annotate(
            f"{x}\n{y:.6g}",
            (x, y),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=7,
        )
        last_annot_xy_disp = xy_disp
        last_annot_y = y

    plt.xlabel("Sample ID")
    plt.ylabel(headers[obj_col].strip() if obj_col < len(headers) else "Objective value")
    plt.title(title or "Best feasible objective vs Sample ID")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.show()