import sys
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtCore import QUrl, pyqtSignal, Qt, QTimer
from utils.logger import logger
import json

class BrowserLoginDialog(QDialog):
    login_finished = pyqtSignal(str) 

    def __init__(self, target_url, success_pattern, parent=None, username=None, password=None):
        super().__init__(parent)
        self.target_url = target_url
        self.success_pattern = success_pattern
        self.username = username
        self.password = password
        self.setWindowTitle("Secure Web Login")
        self.setMinimumSize(1000, 850)
        
        self.captured_cookies = [] 
        self.init_ui()
        
        # Auto-fill timer
        if self.username and self.password:
            self.browser.loadFinished.connect(self.attempt_autofill)

    def attempt_autofill(self, success):
        if not success: return
        # JS to find and fill common login fields
        js = f"""
        (function() {{
            const userFields = document.querySelectorAll('input[type="text"], input[type="email"], input[name*="user"], input[name*="login"], input[id*="user"], input[id*="login"]');
            const passFields = document.querySelectorAll('input[type="password"]');
            
            if (userFields.length > 0) userFields[0].value = "{self.username}";
            if (passFields.length > 0) passFields[0].value = "{self.password}";
            
            // Try to find and click the submit button if it's obvious
            const btn = document.querySelector('button[type="submit"], button[id*="login"], input[type="submit"]');
            // We won't auto-click for safety, just fill.
        }})();
        """
        self.browser.page().runJavaScript(js)

    def init_ui(self):
        layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        self.info_label = QLabel("1. Log in. 2. Once you reach your account page, click FINISH.")
        self.info_label.setWordWrap(True)
        self.btn_manual_finish = QPushButton("FINISH / LOGGED IN")
        self.btn_manual_finish.setStyleSheet("background-color: #27ae60; color: white; padding: 12px 30px; font-weight: bold;")
        self.btn_manual_finish.clicked.connect(self.finalize_capture)
        header_layout.addWidget(self.info_label, 1); header_layout.addWidget(self.btn_manual_finish)
        layout.addLayout(header_layout)
        
        self.progress = QProgressBar(); self.progress.setVisible(False); layout.addWidget(self.progress)
        
        self.browser = QWebEngineView()
        self.profile = QWebEngineProfile.defaultProfile()
        
        # Use a very standard, modern User-Agent
        scraper_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.profile.setHttpUserAgent(scraper_ua)
        
        # Enable full browser features to satisfy Google's security checks
        settings = self.profile.settings()
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        
        self.cookie_store = self.profile.cookieStore()
        self.cookie_store.cookieAdded.connect(self.on_cookie_added)
        
        self.web_page = QWebEnginePage(self.profile, self.browser)
        self.browser.setPage(self.web_page)
        self.browser.setUrl(QUrl(self.target_url))
        self.browser.urlChanged.connect(self.check_url)
        layout.addWidget(self.browser)

    def on_cookie_added(self, cookie):
        """Only capture cookies relevant to the target domain."""
        try:
            domain = cookie.domain()
            # ONLY capture cookies for the site we are actually on (ignore 3rd party junk)
            if any(part in domain.lower() for part in ["findagrave", "familysearch", "legacy"]):
                cookie_dict = {
                    'name': cookie.name().data().decode(),
                    'value': cookie.value().data().decode(),
                    'domain': domain,
                    'path': cookie.path()
                }
                self.captured_cookies.append(cookie_dict)
        except: pass

    def check_url(self, url):
        # We detected the success URL, but we won't auto-close anymore.
        # Instead, we'll highlight the FINISH button to let the user know.
        if self.success_pattern.lower() in url.toString().lower():
            self.btn_manual_finish.setText("✅ SUCCESS DETECTED - CLICK TO FINISH")
            self.btn_manual_finish.setStyleSheet("background-color: #2ecc71; color: white; padding: 12px 30px; font-weight: bold; border: 3px solid #ffffff;")
            self.info_label.setText("Login pattern recognized! Wait 2-3 seconds for all tokens to settle, then click FINISH.")

    def finalize_capture(self):
        # Remove duplicates
        unique_cookies = { (c['name'], c['domain']): c for c in self.captured_cookies }.values()
        
        # Return as JSON string
        raw_json = json.dumps(list(unique_cookies))
        logger.info(f"Capture finished. Slimmed down to {len(unique_cookies)} relevant cookies.")
        self.login_finished.emit(raw_json)
        self.accept()
