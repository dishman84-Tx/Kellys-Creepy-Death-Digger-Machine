import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from database.db_manager import DatabaseManager

def main():
    # Keep system certificate and revocation verification enabled.
    # Resolve certificate problems through trusted OS/CA configuration rather than a global bypass.
    # Initialize application
    app = QApplication(sys.argv)
    
    # Initialize database
    db_manager = DatabaseManager()
    db_manager.initialize_db()
    
    # Initialize main window
    window = MainWindow(db_manager)
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
