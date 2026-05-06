import os
import sys
import tkinter as tk


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ecg_analysis.ui import launch  # noqa: E402


def main():
    root = tk.Tk()
    root.withdraw()
    app = launch(root)
    app.root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
