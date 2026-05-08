# main.py
# Run this file to launch the Module 7 Analytics Dashboard
# No model training needed - this module just shows data

import tkinter as tk
from dashboard_app import AnalyticsDashboard


if __name__ == "__main__":
    root = tk.Tk()
    app  = AnalyticsDashboard(root)
    root.mainloop()
