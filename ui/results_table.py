from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QLabel, QHeaderView, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal

class ResultsTable(QWidget):
    # Signals
    row_double_clicked = pyqtSignal(dict)
    add_to_spreadsheet_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.current_records = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Result count label
        self.count_label = QLabel("Showing: 0 results")
        self.count_label.setStyleSheet("font-weight: bold; color: #1a2333; margin-bottom: 5px;")
        layout.addWidget(self.count_label)
        
        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "#", "Full Name", "Date of Death", "Age", "City", "State", "Source"
        ])
        
        # Table styling
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                selection-background-color: #b8962e;
            }
            QHeaderView::section {
                background-color: #1a2333;
                color: white;
                padding: 4px;
                border: 1px solid #333;
            }
        """)
        
        # Column behavior
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Set some sensible initial widths
        self.table.setColumnWidth(0, 40)   # #
        self.table.setColumnWidth(1, 250)  # Full Name
        self.table.setColumnWidth(2, 120)  # DOD
        self.table.setColumnWidth(3, 50)   # Age
        self.table.setColumnWidth(4, 150)  # City
        self.table.setColumnWidth(5, 60)   # State
        
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Signals
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)

    def load_results(self, records):
        """Populates the table with a list of record dictionaries."""
        self.clear_results()
        self.current_records = records
        self.table.setSortingEnabled(False) # Disable while loading
        
        self.table.setRowCount(len(records))
        for i, rec in enumerate(records):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(rec.get('full_name', '')))
            self.table.setItem(i, 2, QTableWidgetItem(rec.get('date_of_death', '')))
            self.table.setItem(i, 3, QTableWidgetItem(str(rec.get('age', '')) if rec.get('age') else ""))
            self.table.setItem(i, 4, QTableWidgetItem(rec.get('city', '')))
            self.table.setItem(i, 5, QTableWidgetItem(rec.get('state', '')))
            self.table.setItem(i, 6, QTableWidgetItem(rec.get('source', '')))
            
            # Store the record index in the first item's data for retrieval
            self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, i)
            
        self.table.setSortingEnabled(True)
        self.count_label.setText(f"Showing: {len(records)} results")

    def clear_results(self):
        """Empties the table."""
        self.table.setRowCount(0)
        self.current_records = []
        self.count_label.setText("Showing: 0 results")

    def on_cell_double_clicked(self, row, column):
        index = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if index < len(self.current_records):
            self.row_double_clicked.emit(self.current_records[index])

    def show_context_menu(self, pos):
        row = self.table.currentRow()
        if row < 0:
            return
            
        index = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        record = self.current_records[index]
        
        menu = QMenu(self)
        
        view_action = menu.addAction("👁 View Detail")
        copy_name_action = menu.addAction("📋 Copy Name")
        open_url_action = menu.addAction("🌐 Open Source URL")
        add_to_excel_action = menu.addAction("📊 Add to Spreadsheet")
        delete_action = menu.addAction("🗑 Delete from DB")
        
        action = menu.exec(self.table.mapToGlobal(pos))
        
        if action == view_action:
            self.row_double_clicked.emit(record)
        elif action == copy_name_action:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(record.get('full_name', ''))
        elif action == open_url_action:
            import webbrowser
            if record.get('source_url'):
                webbrowser.open(record['source_url'])
        elif action == add_to_excel_action:
            self.add_to_spreadsheet_requested.emit(record)
        elif action == delete_action:
            # We would need the DB ID here, which might not exist if it's a fresh search
            db_id = record.get('id')
            if db_id:
                self.delete_requested.emit(db_id)
            else:
                QMessageBox.information(self, "Info", "This record is not yet saved to the database.")
