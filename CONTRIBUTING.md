# Contributing to Smart Cardiology Document Processing

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Smart-Cardiology-Document-Processing.git
   cd Smart-Cardiology-Document-Processing
   ```
3. **Create a virtual environment** and install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   pip install -r requirements.txt
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Project Architecture

- **Entry Point:** `main_app.py` — Central launcher for all 8 modules
- **Shared Layer:** `shared/database.py` — All database tables and CRUD helpers
- **Modules:** `modules/<module_name>/` — Each module is an independent package

## Module Development Rules

When adding or modifying a module, follow these rules:

| Rule | Details |
|------|---------|
| **No cross-imports** | Never import another module's code. Use the shared database for data exchange. |
| **Use shared DB layer** | All database operations go through `shared/database.py`. Don't create private tables. |
| **Patient ID format** | `P-XXXX` (e.g., `P-0001`) |
| **Center IDs** | `CEN-001` through `CEN-006` |
| **Timestamps** | Use `now_text()` from `shared/database.py` |
| **UI pattern** | Use `Toplevel(parent)`, not standalone `Tk()` |
| **Entry point** | Export `launch(parent)` in your module's `__init__.py` |

## Adding a New Module

1. Create `modules/your_module/` with these files:
   ```
   modules/your_module/
   ├── __init__.py       # from .ui import launch
   ├── ui.py             # Tkinter UI with launch(parent) function
   ├── main.py           # Standalone test entry point
   └── database.py       # Import from shared/database.py
   ```
2. Register it in `main_app.py`'s `MODULES` list

## Commit Messages

Use clear, descriptive commit messages:
```
feat: add blood pressure tracking to Module 2
fix: resolve patient ID collision in OCR module
docs: update README with new module instructions
```

## Pull Request Process

1. Ensure your code runs without errors (`python main_app.py`)
2. Update documentation if you changed any public API
3. Submit a PR against the `main` branch with a clear description
