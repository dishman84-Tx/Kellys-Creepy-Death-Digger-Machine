from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QLabel, 
                             QFileDialog, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QComboBox, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt
import pandas as pd
import os

class BulkImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Import People")
        self.setMinimumSize(800, 600)
        self.people_data = []
        self.df = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. File Selection
        file_layout = QHBoxLayout()
        self.lbl_file = QLabel("No file selected")
        btn_browse = QPushButton("📁 Load CSV/XLSX")
        btn_browse.clicked.connect(self.load_file)
        file_layout.addWidget(self.lbl_file, 1)
        file_layout.addWidget(btn_browse)
        layout.addLayout(file_layout)
        
        layout.addWidget(QLabel("<b>Map Columns:</b>"))
        
        # 2. Mapping Form
        mapping_layout = QHBoxLayout()
        self.map_first = QComboBox(); self.map_last = QComboBox()
        self.map_city = QComboBox(); self.map_state = QComboBox()
        
        for combo, label in [(self.map_first, "First Name*"), (self.map_last, "Last Name*"), 
                             (self.map_city, "City"), (self.map_state, "State")]:
            v_box = QVBoxLayout()
            v_box.addWidget(QLabel(label))
            combo.addItem("-- Skip --")
            v_box.addWidget(combo)
            mapping_layout.addLayout(v_box)
        
        layout.addLayout(mapping_layout)
        
        # 3. Preview Table
        layout.addWidget(QLabel("<b>Data Preview (Top 50 rows):</b>"))
        self.table = QTableWidget()
        layout.addWidget(self.table)
        
        # 4. Buttons
        btn_layout = QHBoxLayout()
        self.btn_import = QPushButton("🚀 Start Bulk Search")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self.handle_import)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_import)
        layout.addLayout(btn_layout)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select People List", "", "Data Files (*.csv *.xlsx *.xls)"
        )
        if not file_path: return
        
        try:
            if file_path.endswith('.csv'):
                self.df = pd.read_csv(file_path).head(50)
            else:
                self.df = pd.read_excel(file_path).head(50)
            
            self.lbl_file.setText(os.path.basename(file_path))
            cols = self.df.columns.tolist()
            
            for combo in [self.map_first, self.map_last, self.map_city, self.map_state]:
                combo.clear()
                combo.addItem("-- Skip --")
                combo.addItems(cols)
                
                # Auto-guessing
                text = combo.parent().findChild(QLabel).text().lower()
                for c in cols:
                    c_low = c.lower()
                    if "first" in text and "first" in c_low: combo.setCurrentText(c)
                    elif "last" in text and "last" in c_low: combo.setCurrentText(c)
                    elif "city" in text and "city" in c_low: combo.setCurrentText(c)
                    elif "state" in text and "state" in c_low: combo.setCurrentText(c)

            self.update_preview()
            self.btn_import.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def update_preview(self):
        if self.df is None: return
        self.table.setColumnCount(len(self.df.columns))
        self.table.setRowCount(len(self.df))
        self.table.setHorizontalHeaderLabels(self.df.columns)
        
        for i in range(len(self.df)):
            for j in range(len(self.df.columns)):
                self.table.setItem(i, j, QTableWidgetItem(str(self.df.iloc[i, j])))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def handle_import(self):
        if self.map_first.currentText() == "-- Skip --" or self.map_last.currentText() == "-- Skip --":
            QMessageBox.warning(self, "Mapping Error", "First Name and Last Name columns are required.")
            return
            
        self.people_data = []
        for _, row in self.df.iterrows():
            person = {
                "first_name": str(row[self.map_first.currentText()]) if self.map_first.currentText() != "-- Skip --" else "",
                "last_name": str(row[self.map_last.currentText()]) if self.map_last.currentText() != "-- Skip --" else "",
                "city": str(row[self.map_city.currentText()]) if self.map_city.currentText() != "-- Skip --" else "",
                "state": str(row[self.map_state.currentText()]) if self.map_state.currentText() != "-- Skip --" else ""
            }
            if person["first_name"] and person["last_name"]:
                self.people_data.append(person)
        
        if not self.people_data:
            QMessageBox.warning(self, "No Data", "No valid people records found to import.")
            return
            
        self.accept()
