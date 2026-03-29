from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QRadioButton, QPushButton, 
                             QLabel, QFileDialog, QHBoxLayout, QButtonGroup, QMessageBox)
import os

class ExportDialog(QDialog):
    def __init__(self, records, parent=None):
        super().__init__(parent)
        self.records = records
        self.setWindowTitle("Export Records")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"<b>Records to export:</b> {len(self.records)}"))
        
        self.group = QButtonGroup(self)
        self.rb_new = QRadioButton("Export to New File")
        self.rb_append = QRadioButton("Append to Existing File")
        self.rb_new.setChecked(True)
        
        self.group.addButton(self.rb_new)
        self.group.addButton(self.rb_append)
        
        layout.addWidget(self.rb_new)
        layout.addWidget(self.rb_append)
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Export")
        self.btn_ok.clicked.connect(self.handle_export)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

    def handle_export(self):
        if self.rb_new.isChecked():
            folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if folder:
                from export.excel_exporter import export_to_new_file
                path = export_to_new_file(self.records, folder)
                QMessageBox.information(self, "Success", f"Exported to:\n{path}")
                self.accept()
        else:
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Existing Excel File", "", "Excel Files (*.xlsx)")
            if file_path:
                from export.excel_appender import append_to_existing
                success, result = append_to_existing(self.records, file_path)
                if success:
                    QMessageBox.information(self, "Success", f"Appended {result} new records.")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", f"Failed to append: {result}")
