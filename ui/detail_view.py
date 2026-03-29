from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, 
                             QTextEdit, QPushButton, QHBoxLayout, QScrollArea, QFrame, QWidget)
from PyQt6.QtCore import Qt

class DetailView(QDialog):
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.setWindowTitle(f"Record Detail: {record.get('full_name', 'Unknown')}")
        self.setMinimumSize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)
        
        # Display fields
        fields = [
            ("Full Name", "full_name"),
            ("Date of Birth", "date_of_birth"),
            ("Date of Death", "date_of_death"),
            ("Age", "age"),
            ("City", "city"),
            ("State", "state"),
            ("Source", "source"),
            ("Source URL", "source_url")
        ]
        
        for label_text, key in fields:
            val = str(self.record.get(key, ""))
            label = QLabel(val)
            if key == "source_url" and val:
                label.setText(f'<a href="{val}" style="color: #b8962e;">{val}</a>')
                label.setOpenExternalLinks(True)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            else:
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            
            form_layout.addRow(f"<b>{label_text}:</b>", label)
            
        # Survivors and Full Text
        self.survivors_view = QTextEdit()
        self.survivors_view.setReadOnly(True)
        self.survivors_view.setPlainText(self.record.get("survivors", ""))
        form_layout.addRow("<b>Survivors:</b>", self.survivors_view)
        
        self.full_text_view = QTextEdit()
        self.full_text_view.setReadOnly(True)
        self.full_text_view.setPlainText(self.record.get("full_text", ""))
        form_layout.addRow("<b>Full Obituary:</b>", self.full_text_view)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_copy = QPushButton("📋 Copy All")
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    def copy_to_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        text = "\n".join([f"{k}: {v}" for k, v in self.record.items()])
        QApplication.clipboard().setText(text)
