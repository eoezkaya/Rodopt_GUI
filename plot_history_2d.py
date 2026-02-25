import csv
import os
from typing import Sequence, Optional

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


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


def plot_history_2d(csv_path: str, d: int, *, title: Optional[str] = None, num_doe_samples: int = 0) -> None:

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

    # NEW: anchor at num_doe_samples with best value up to that point (display only)
    try:
        nds = int(num_doe_samples)
    except Exception:
        nds = 0
    if nds < 0:
        nds = 0

    if nds > 0:
        # find y corresponding to the best improvement point with x <= nds
        anchor_y: Optional[float] = None
        for x, y in zip(xs, ys):
            if x <= nds:
                anchor_y = y
            else:
                break

        # If we have any feasible best up to nds, start plot at (nds, anchor_y)
        if anchor_y is not None:
            # only add anchor if it isn't already exactly at x=nds
            if not xs or xs[0] != nds or ys[0] != anchor_y:
                xs_plot = [nds] + [x for x in xs if x >= nds]
                ys_plot = [anchor_y] + [y for x, y in zip(xs, ys) if x >= nds]
            else:
                xs_plot = xs
                ys_plot = ys
        else:
            # no feasible improvements before/at nds -> just show points >= nds
            xs_plot = [x for x in xs if x >= nds]
            ys_plot = [y for x, y in zip(xs, ys) if x >= nds]
    else:
        xs_plot = xs
        ys_plot = ys

    if not ys_plot:
        raise ValueError("No points to plot in the selected x-range.")

    plt.figure(figsize=(10, 8))
    plt.plot(xs_plot, ys_plot, linewidth=2.0, marker="o", markersize=8)

    ax = plt.gca()
    plt.tight_layout()

    # --- existing annotation logic, but use xs_plot/ys_plot ---
    min_sep_px = 18.0
    last_annot_xy_disp = None
    last_annot = None
    last_annot_y = None

    ax.figure.canvas.draw()

    for idx, (x, y) in enumerate(zip(xs_plot, ys_plot)):
        xy_disp = ax.transData.transform((x, y))

        if last_annot_xy_disp is not None:
            dx = xy_disp[0] - last_annot_xy_disp[0]
            dy = xy_disp[1] - last_annot_xy_disp[1]
            dist2 = dx * dx + dy * dy

            if dist2 < (min_sep_px * min_sep_px):
                if last_annot is not None and last_annot_y is not None and y <= last_annot_y:
                    last_annot.remove()
                    last_annot = None
                    last_annot_xy_disp = None
                    last_annot_y = None
                else:
                    continue

        x_label = "DoE best" if (idx == 0 and nds > 0 and x == nds) else str(int(x))

        last_annot = ax.annotate(
            f"{x_label}\n{y:.6g}",
            (x, y),
            textcoords="offset points",
            xytext=(4, 4),   # top-right of the marker
            ha="left",
            va="bottom",
            fontsize=7,
        )
        last_annot_xy_disp = xy_disp
        last_annot_y = y

    plt.xlabel("Sample ID")
    plt.ylabel(headers[obj_col].strip() if obj_col < len(headers) else "Objective value")
    plt.title(title or "Best feasible objective vs Sample ID")
    plt.grid(True, linestyle="--", alpha=0.4)

    # NEW: view window starts at num_doe_samples when provided
    if nds > 0:
        right = max(xs_plot) if xs_plot else nds + 1
        if right <= nds:
            right = nds + 1
        ax.set_xlim(nds, right)

    # Force integer x-axis ticks/labels (no 100.0, 101.0, ...)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    # Show x-axis with a small buffer around plotted points
    if xs_plot:
        left = max(0, int(min(xs_plot)) - 1)
        right = int(max(xs_plot)) + 1
        if right <= left:
            right = left + 1
        ax.set_xlim(left, right)

    plt.tight_layout()
    plt.show()