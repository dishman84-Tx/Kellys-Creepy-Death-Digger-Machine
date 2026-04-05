from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                             QComboBox, QDateEdit, QGroupBox, QCheckBox, 
                             QPushButton, QLabel, QFrame, QScrollArea)
from PyQt6.QtCore import pyqtSignal, QDate, Qt

class SearchPanel(QWidget):
    # Signals
    search_requested = pyqtSignal(dict)
    bulk_search_requested = pyqtSignal(list)
    cancel_requested = pyqtSignal()
    clear_results_requested = pyqtSignal()
    local_search_requested = pyqtSignal(str)
    save_to_db_requested = pyqtSignal()
    history_item_selected = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # MAIN LAYOUT
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. SCROLLABLE AREA (Criteria & Sources)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 0. History Group
        history_group = QGroupBox("Recent Searches")
        hist_layout = QVBoxLayout(history_group)
        self.combo_history = QComboBox()
        self.combo_history.addItem("Select from history...")
        self.combo_history.currentIndexChanged.connect(self.on_history_changed)
        hist_layout.addWidget(self.combo_history)
        layout.addWidget(history_group)

        # 1. Search Fields Group
        search_group = QGroupBox("Search Criteria")
        form_layout = QFormLayout(search_group)
        
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.city = QLineEdit()
        
        self.state = QComboBox()
        states = ["All", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
                  "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
                  "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
                  "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
                  "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]
        self.state.addItems(states)
        
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate(1900, 1, 1))
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        
        self.keywords = QLineEdit()
        self.keywords.setPlaceholderText("e.g. Navy, Teacher")

        form_layout.addRow("First Name:", self.first_name)
        form_layout.addRow("Last Name:", self.last_name)
        form_layout.addRow("City:", self.city)
        form_layout.addRow("State:", self.state)
        form_layout.addRow("Date From:", self.date_from)
        form_layout.addRow("Date To:", self.date_to)
        form_layout.addRow("Keywords:", self.keywords)
        
        layout.addWidget(search_group)

        # 2. Sources Group
        sources_group = QGroupBox("Sources")
        sources_layout = QVBoxLayout(sources_group)
        self.sources = [
            QCheckBox("Legacy.com"), 
            QCheckBox("SSDI (FamilySearch)"), QCheckBox("FindAGrave"), 
            QCheckBox("Google News")
        ]
        for s in self.sources:
            s.setChecked(True)
            sources_layout.addWidget(s)
        layout.addWidget(sources_group)

        # 5. Local DB Search
        local_group = QGroupBox("Local DB Search")
        local_layout = QVBoxLayout(local_group)
        self.local_query = QLineEdit(); self.local_query.setPlaceholderText("Search saved records...")
        self.btn_local_search = QPushButton("🔍 Search Local DB")
        self.btn_local_search.setStyleSheet("background-color: #1a2333; color: white;")
        self.btn_local_search.clicked.connect(self.on_local_search_clicked)
        local_layout.addWidget(self.local_query)
        local_layout.addWidget(self.btn_local_search)
        layout.addWidget(local_group)
        layout.addStretch()
        
        scroll.setWidget(content_widget)
        self.main_layout.addWidget(scroll)

        # 2. FIXED BUTTON CONTAINER (Always visible at bottom)
        self.button_container = QWidget()
        btn_layout = QVBoxLayout(self.button_container)
        btn_layout.setContentsMargins(10, 10, 10, 10)
        btn_layout.setSpacing(8)

        self.btn_search = QPushButton("🔍 SEARCH ALL")
        self.btn_search.setMinimumHeight(45)
        self.btn_search.clicked.connect(self.on_search_clicked)

        self.btn_bulk = QPushButton("📂 BULK SEARCH (CSV/XLSX)")
        self.btn_bulk.setMinimumHeight(45)
        self.btn_bulk.setStyleSheet("background-color: #2980b9; color: white;")
        self.btn_bulk.clicked.connect(self.on_bulk_clicked)
        
        self.btn_cancel = QPushButton("🛑 CANCEL SEARCH")
        self.btn_cancel.setMinimumHeight(45)
        self.btn_cancel.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        self.btn_cancel.setVisible(False)
        
        self.btn_clear = QPushButton("🗑 CLEAR FIELDS")
        self.btn_clear.setStyleSheet("background-color: #7f8c8d; color: white;")
        self.btn_clear.clicked.connect(self.clear_fields)
        
        self.btn_save = QPushButton("📥 SAVE RESULTS TO DB")
        self.btn_save.setStyleSheet("background-color: #2c3e50; color: white;")
        self.btn_save.clicked.connect(self.save_to_db_requested.emit)
        
        btn_layout.addWidget(self.btn_search)
        btn_layout.addWidget(self.btn_bulk)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_save)
        
        self.main_layout.addWidget(self.button_container)

    def on_bulk_clicked(self):
        from ui.bulk_import_dialog import BulkImportDialog
        dialog = BulkImportDialog(self)
        if dialog.exec():
            # Add common search params (sources, dates) to each person
            bulk_data = []
            sources = [s.text() for s in self.sources if s.isChecked()]
            date_f = self.date_from.date().toString(Qt.DateFormat.ISODate)
            date_t = self.date_to.date().toString(Qt.DateFormat.ISODate)
            
            for person in dialog.people_data:
                p = person.copy()
                p.update({
                    "sources": sources,
                    "date_from": date_f,
                    "date_to": date_t,
                    "keywords": self.keywords.text()
                })
                bulk_data.append(p)
            
            self.bulk_search_requested.emit(bulk_data)

    def on_history_changed(self, index):
        if index <= 0: return
        data = self.combo_history.itemData(index)
        if data:
            self.first_name.setText(data.get("first_name", ""))
            self.last_name.setText(data.get("last_name", ""))
            self.city.setText(data.get("city", ""))
            idx = self.state.findText(data.get("state", "All") or "All")
            if idx >= 0: self.state.setCurrentIndex(idx)
            if data.get("date_from"): self.date_from.setDate(QDate.fromString(data["date_from"], Qt.DateFormat.ISODate))
            if data.get("date_to"): self.date_to.setDate(QDate.fromString(data["date_to"], Qt.DateFormat.ISODate))
            self.keywords.setText(data.get("keywords", ""))
            enabled = data.get("sources", [])
            for s in self.sources: s.setChecked(s.text() in enabled)

    def update_history_dropdown(self, history_records):
        self.combo_history.blockSignals(True); self.combo_history.clear(); self.combo_history.addItem("Select from history...")
        import json
        for h in history_records:
            try:
                params = json.loads(h.search_params)
                self.combo_history.addItem(f"{params.get('first_name','')} {params.get('last_name','')} ({h.timestamp})", params)
            except: continue
        self.combo_history.blockSignals(False)

    def on_search_clicked(self):
        params = {
            "first_name": self.first_name.text(),
            "last_name": self.last_name.text(),
            "city": self.city.text(),
            "state": self.state.currentText() if self.state.currentText() != "All" else None,
            "date_from": self.date_from.date().toString(Qt.DateFormat.ISODate),
            "date_to": self.date_to.date().toString(Qt.DateFormat.ISODate),
            "keywords": self.keywords.text(),
            "sources": [s.text() for s in self.sources if s.isChecked()]
        }
        self.search_requested.emit(params)

    def on_local_search_clicked(self): self.local_search_requested.emit(self.local_query.text())

    def clear_fields(self):
        self.first_name.clear(); self.last_name.clear(); self.city.clear(); self.state.setCurrentIndex(0)
        self.date_from.setDate(QDate(1900, 1, 1)); self.date_to.setDate(QDate.currentDate())
        self.keywords.clear(); self.local_query.clear()
        for s in self.sources: s.setChecked(True)
        self.clear_results_requested.emit()
