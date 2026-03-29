from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QWidget, QFormLayout, QLineEdit, QPushButton, 
                             QLabel, QGroupBox, QMessageBox, QSpinBox, QListWidget, QAbstractItemView, QScrollArea)
from PyQt6.QtCore import Qt
from credentials.credential_manager import get_credential, set_credential, load_credentials, save_credentials
from utils.settings_manager import load_settings, save_settings
from ui.browser_login import BrowserLoginDialog
from utils.logger import logger
import os

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self.setWindowTitle("Settings")
        self.setMinimumSize(750, 650)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # 1. General Tab
        self.general_tab = QWidget()
        gen_layout = QFormLayout(self.general_tab)
        self.export_dir = QLineEdit(self.settings.get("default_export_dir", ""))
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self.browse_folder)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.export_dir)
        dir_layout.addWidget(self.btn_browse)
        self.request_delay = QSpinBox()
        self.request_delay.setRange(1, 15)
        self.request_delay.setSuffix(" seconds")
        self.request_delay.setValue(self.settings.get("request_delay", 2))
        self.sources_list = QListWidget()
        self.sources_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        all_sources = ["Legacy.com", "SSDI (FamilySearch)", "FindAGrave", "Google News"]

        self.sources_list.addItems(all_sources)
        enabled = self.settings.get("enabled_sources", all_sources)
        for i in range(self.sources_list.count()):
            item = self.sources_list.item(i)
            if item.text() in enabled: item.setSelected(True)
        gen_layout.addRow("Default Export Directory:", dir_layout)
        gen_layout.addRow("Request Delay:", self.request_delay)
        gen_layout.addRow("Enabled Search Sources:", self.sources_list)
        self.tabs.addTab(self.general_tab, "General")
        
        # 2. Sources & Credentials Tab
        self.creds_tab = QWidget()
        creds_main_layout = QVBoxLayout(self.creds_tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.creds_layout = QVBoxLayout(scroll_content)
        self.setup_all_source_creds()
        scroll.setWidget(scroll_content)
        creds_main_layout.addWidget(scroll)
        self.tabs.addTab(self.creds_tab, "Sources & Credentials")
        
        layout.addWidget(self.tabs)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.btn_save_all = QPushButton("💾 Save All Settings")
        self.btn_save_all.setStyleSheet("background-color: #27ae60; color: white;")
        self.btn_save_all.clicked.connect(self.save_all)
        self.btn_close = QPushButton("Cancel")
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        btn_layout.addWidget(self.btn_save_all)
        layout.addLayout(btn_layout)

    def browse_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if folder: self.export_dir.setText(folder)

    def create_source_group(self, title, source_key, login_url=None, success_pattern=None, reg_url=None):
        group = QGroupBox(title)
        form = QFormLayout(group)
        widgets = {}
        
        # Username/Pass fields
        user = QLineEdit(get_credential(source_key, "username"))
        pw = QLineEdit(get_credential(source_key, "password"))
        pw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username:", user)
        form.addRow("Password:", pw)
        widgets['username'] = user
        widgets['password'] = pw
        
        # Cookie field
        cookies = QLineEdit(get_credential(source_key, "cookies"))
        cookies.setPlaceholderText("Browser session token (captured automatically)")
        cookies.setReadOnly(True)
        form.addRow("Session Token:", cookies)
        widgets['cookies'] = cookies
            
        action_layout = QHBoxLayout()
        if login_url:
            btn_browser = QPushButton("🔑 Login via Browser")
            btn_browser.setStyleSheet("background-color: #1a2333; color: white;")
            btn_browser.clicked.connect(lambda: self.launch_browser_login(source_key, login_url, success_pattern, cookies))
            action_layout.addWidget(btn_browser)
            
        status = QLabel("✅ Active" if cookies.text() else "⬜ Not Logged In")
        action_layout.addWidget(status)
        action_layout.addStretch()
        
        if reg_url:
            link = QLabel(f'<a href="{reg_url}">Create Account</a>')
            link.setOpenExternalLinks(True)
            link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            action_layout.addWidget(link)
            
        form.addRow("", action_layout)
        self.source_widgets[source_key] = widgets
        return group

    def setup_all_source_creds(self):
        self.source_widgets = {}
        
        # 1. FamilySearch (SSDI)
        self.creds_layout.addWidget(self.create_source_group(
            "FamilySearch (SSDI)", "familysearch", 
            login_url="https://www.familysearch.org/en/home/portal/",
            success_pattern="familysearch.org/discovery/",
            reg_url="https://www.familysearch.org/register/"
        ))
        
        # 2. FindAGrave
        self.creds_layout.addWidget(self.create_source_group(
            "FindAGrave", "findagrave", 
            login_url="https://www.findagrave.com/login",
            success_pattern="findagrave.com/user/profile",
            reg_url="https://www.findagrave.com/register"
        ))
        
        # 3. Legacy.com
        self.creds_layout.addWidget(self.create_source_group(
            "Legacy.com", "legacy", 
            login_url="https://www.legacy.com/auth/login",
            success_pattern="legacy.com/",
            reg_url="https://www.legacy.com/auth/login"
        ))
        
        # Clear All Button
        self.btn_clear_all = QPushButton("🗑 Clear All Stored Credentials")
        self.btn_clear_all.setStyleSheet("background-color: #c0392b; color: white; margin-top: 20px;")
        self.btn_clear_all.clicked.connect(self.clear_all_creds)
        self.creds_layout.addWidget(self.btn_clear_all)
        self.creds_layout.addStretch()

    def launch_browser_login(self, source_key, url, pattern, cookie_widget):
        try:
            # Pass existing username/password for auto-fill
            user = get_credential(source_key, "username")
            pw = get_credential(source_key, "password")
            
            dialog = BrowserLoginDialog(url, pattern, self, username=user, password=pw)
            
            def on_finished(cookies):
                try:
                    cookie_widget.setText(cookies)
                    set_credential(source_key, "cookies", cookies)
                    QMessageBox.information(self, "Success", f"Session token captured for {source_key}!")
                except Exception as e:
                    logger.error(f"Error saving captured cookies: {e}")
                    QMessageBox.critical(self, "Error", f"Failed to save cookies: {e}")
                
            dialog.login_finished.connect(on_finished)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error launching browser login: {e}")
            QMessageBox.critical(self, "Error", f"Could not open login browser: {e}")

    def save_all(self):
        new_settings = {
            "default_export_dir": self.export_dir.text(),
            "request_delay": self.request_delay.value(),
            "enabled_sources": [item.text() for item in self.sources_list.selectedItems()]
        }
        save_settings(new_settings)
        for source_key, widgets in self.source_widgets.items():
            for field, widget in widgets.items():
                set_credential(source_key, field, widget.text())
        QMessageBox.information(self, "Saved", "All settings and credentials have been saved securely.")
        self.accept()

    def clear_all_creds(self):
        reply = QMessageBox.question(self, 'Confirm Clear', "Permanently delete ALL credentials?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            save_credentials({})
            for widgets in self.source_widgets.values():
                for widget in widgets.values(): widget.clear()
            QMessageBox.information(self, "Cleared", "Wiped.")
