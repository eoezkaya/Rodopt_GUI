<!-- filepath: /Users/emreozkaya/Rodopt_GUI/README.md -->

# Rodopt GUI

A PyQt6-based desktop GUI for creating, editing, and running optimization / DoE studies.  
The app lets you configure:

- **General Settings** (problem name, working directory, sampling/optimization mode, etc.)
- **Parameters** (design variables table)
- **Objective Function(s)**
- **Constraint Function(s)**
- **Run / DoE execution** and result inspection (e.g., selecting designs, plotting)

Studies can be exported/imported as **XML**.

---

## Requirements

- macOS
- Python 3.10+ (recommended)
- `pip` (or a virtual environment manager)
- Dependencies:
  - PyQt6
  - numpy
  - matplotlib (if plotting is enabled in the app)

---

## Setup (macOS)

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install PyQt6 numpy matplotlib