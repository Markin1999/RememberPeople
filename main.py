import sys
import os

# Ensure the project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow
import db


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RememberPeople")
    app.setOrganizationName("Personal")

    # Test DB connection
    try:
        db.init_db()
    except Exception as e:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Errore connessione database")
        msg.setText(
            "Impossibile connettersi al database PostgreSQL.\n\n"
            f"Errore: {e}\n\n"
            "Assicurati che Docker sia in esecuzione e il container 'mypeople-db' sia attivo:\n"
            "  docker start mypeople-db"
        )
        msg.exec()
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
