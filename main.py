import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from database.db_manager import DatabaseManager

def main():
    # Fix for SSL handshake errors and potential crashes in WebEngine
    os.environ["QTWEBENGINE_DISABLE_SSL_REVOCATION"] = "1"
    sys.argv.append("--ignore-certificate-errors")
    
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
