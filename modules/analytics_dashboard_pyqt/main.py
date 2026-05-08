# main.py
# Run this file to launch the Module 7 Analytics Dashboard (PyQt5 version)

import sys
from PyQt5.QtWidgets import QApplication
from dashboard_app import AnalyticsDashboard


if __name__ == "__main__":
    app    = QApplication(sys.argv)
    window = AnalyticsDashboard()
    window.show()
    sys.exit(app.exec_())
