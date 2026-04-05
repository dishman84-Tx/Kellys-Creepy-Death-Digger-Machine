import sys
import os
import threading
import traceback
import time
import random
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QStatusBar, QMenuBar, QMenu, QMessageBox,
                             QProgressBar, QLabel)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtGui import QAction, QIcon

from ui.search_panel import SearchPanel
from ui.results_table import ResultsTable
from ui.detail_view import DetailView
from ui.export_dialog import ExportDialog
from ui.settings_dialog import SettingsDialog
from ui.reaper_loader import ReaperLoader

from scrapers.legacy_scraper import LegacyScraper
from scrapers.ssdi_scraper import SsdiScraper
from scrapers.findagrave_scraper import FindAGraveScraper
from scrapers.google_news_scraper import GoogleNewsScraper

from utils.deduplicator import deduplicate
from utils.logger import logger
from utils.settings_manager import load_settings
from utils.normalizer import parse_date

# NICKNAME MAPPING FOR SMART SEARCH
NICKNAMES = {
    "dave": ["david"], "david": ["dave"],
    "fred": ["frederick", "fredrick"], "frederick": ["fred"],
    "tom": ["thomas"], "thomas": ["tom"],
    "mike": ["michael"], "michael": ["mike"],
    "jim": ["james"], "james": ["jim", "jonesey"]
}

class MainWindow(QMainWindow):
    def __init__(self, db_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.current_results = []
        self.settings = load_settings()
        self.cancel_requested = False
        self.scrapers = {
            "Legacy.com": LegacyScraper(), 
            "SSDI (FamilySearch)": SsdiScraper(), "FindAGrave": FindAGraveScraper(),
            "Google News": GoogleNewsScraper()
        }
        self.setWindowTitle("Kelly's Creepy Death Digger Machine")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "assets", "icon.svg")))
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: white; color: #1a2333; }
            QGroupBox { font-weight: bold; border: 1px solid #ddd; margin-top: 10px; padding-top: 10px; }
            QMenuBar { background-color: #1a2333; color: white; padding: 5px; }
            QMenuBar::item:selected { background-color: #b8962e; }
            QMenu { background-color: #1a2333; color: white; border: 1px solid #b8962e; }
            QMenu::item:selected { background-color: #b8962e; }
            QStatusBar { background-color: #f5f5f5; color: #1a2333; border-top: 1px solid #ddd; }
            QPushButton { background-color: #b8962e; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #d4af37; }
            QLineEdit, QComboBox, QDateEdit, QSpinBox { border: 1px solid #ccc; padding: 0px 8px; border-radius: 4px; height: 30px; font-size: 14px; }
            QTableWidget { gridline-color: #ddd; selection-background-color: #b8962e; selection-color: white; }
        """)
        self.init_ui(); self.connect_signals(); self.refresh_search_history()
        sys.excepthook = self.handle_exception

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        try: logger.critical(f"EXCEPTION: {error_msg}")
        except: pass
        QMessageBox.critical(self, "Critical Error", f"Encountered error:\n\n{exc_value}")

    def init_ui(self):
        self.create_menus()
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.search_panel = SearchPanel(); self.results_table = ResultsTable()
        self.reaper_loader = ReaperLoader(self.results_table)
        self.splitter.addWidget(self.search_panel); self.splitter.addWidget(self.results_table)
        self.splitter.setStretchFactor(1, 1); self.main_layout.addWidget(self.splitter)
        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar(); self.progress_bar.setMaximumHeight(15); self.progress_bar.setMaximumWidth(200); self.progress_bar.setVisible(False)
        self.status_label = QLabel("Ready"); self.db_stat_label = QLabel("DB Records: 0")
        self.status_bar.addWidget(self.status_label, 1); self.status_bar.addPermanentWidget(self.progress_bar); self.status_bar.addPermanentWidget(self.db_stat_label)
        self.update_status_bar_info()

    def create_menus(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File"); exit_act = QAction("&Exit", self); exit_act.triggered.connect(self.close); file_menu.addAction(exit_act)
        db_menu = menu_bar.addMenu("&Database"); view_act = QAction("View All", self); view_act.triggered.connect(self.load_all_from_db); db_menu.addAction(view_act)
        export_menu = menu_bar.addMenu("&Export"); exp_act = QAction("Export Results...", self); exp_act.triggered.connect(self.open_export_dialog); export_menu.addAction(exp_act)
        settings_menu = menu_bar.addMenu("&Settings"); pref_act = QAction("Preferences...", self); pref_act.triggered.connect(self.open_settings); settings_menu.addAction(pref_act)

    def connect_signals(self):
        self.search_panel.search_requested.connect(self.run_search)
        self.search_panel.bulk_search_requested.connect(self.run_bulk_search)
        self.search_panel.cancel_requested.connect(self.request_cancel)
        self.search_panel.clear_results_requested.connect(self.clear_all_results)
        self.search_panel.local_search_requested.connect(self.run_local_search)
        self.search_panel.save_to_db_requested.connect(self.save_results_to_db)
        self.results_table.row_double_clicked.connect(self.show_detail); self.results_table.delete_requested.connect(self.delete_record)

    def request_cancel(self):
        self.cancel_requested = True
        for scraper in self.scrapers.values():
            scraper.cancel_requested = True
        self.status_label.setText("Cancelling...")
        self.search_panel.btn_cancel.setEnabled(False)
        self.search_panel.btn_cancel.setText("🛑 CANCELLING...")

    def clear_all_results(self):
        self.results_table.clear_results()
        self.current_results = []
        self.status_label.setText("Cleared")

    def run_search(self, params):
        self.cancel_requested = False
        self.status_label.setText("Searching..."); self.progress_bar.setValue(0); self.progress_bar.setVisible(True); self.results_table.clear_results()
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint); self.show()
        self.reaper_loader.start_loading()
        self.search_panel.btn_search.setVisible(False); self.search_panel.btn_bulk.setVisible(False)
        self.search_panel.btn_cancel.setVisible(True); self.search_panel.btn_cancel.setEnabled(True); self.search_panel.btn_cancel.setText("🛑 CANCEL SEARCH")
        threading.Thread(target=self._search_thread, args=(params,), daemon=True).start()

    def run_bulk_search(self, bulk_params_list):
        self.cancel_requested = False
        self.status_label.setText(f"Bulk Search: 0/{len(bulk_params_list)} people"); self.progress_bar.setValue(0); self.progress_bar.setVisible(True); self.results_table.clear_results()
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint); self.show()
        self.reaper_loader.start_loading()
        self.search_panel.btn_search.setVisible(False); self.search_panel.btn_bulk.setVisible(False)
        self.search_panel.btn_cancel.setVisible(True); self.search_panel.btn_cancel.setEnabled(True); self.search_panel.btn_cancel.setText("🛑 CANCEL SEARCH")
        threading.Thread(target=self._bulk_search_thread, args=(bulk_params_list,), daemon=True).start()

    def _search_thread(self, params):
        try:
            results = self._perform_single_search(params)
            self.current_results = results
        except Exception as e:
            logger.critical(f"SEARCH THREAD ERROR: {e}")
        finally:
            QMetaObject.invokeMethod(self, "_finalize_search", Qt.ConnectionType.QueuedConnection)

    def _bulk_search_thread(self, bulk_params_list):
        try:
            all_bulk_results = []
            total_people = len(bulk_params_list)
            
            for idx, params in enumerate(bulk_params_list):
                if self.cancel_requested: break
                
                QMetaObject.invokeMethod(self.status_label, "setText", Qt.ConnectionType.QueuedConnection, 
                                         Q_ARG(str, f"Searching person {idx+1}/{total_people}: {params['first_name']} {params['last_name']}"))
                
                person_results = self._perform_single_search(params)
                all_bulk_results.extend(person_results)
                
                QMetaObject.invokeMethod(self.progress_bar, "setValue", Qt.ConnectionType.QueuedConnection, 
                                         Q_ARG(int, int(((idx+1)/total_people)*100)))
                
                # Small delay between people to avoid bot detection
                if idx < total_people - 1:
                    time.sleep(2)
            
            self.current_results = deduplicate(all_bulk_results)
            logger.info(f"BULK SEARCH DONE: Found {len(self.current_results)} total unique records.")
            
        except Exception as e:
            logger.critical(f"BULK SEARCH THREAD ERROR: {e}")
        finally:
            QMetaObject.invokeMethod(self, "_finalize_search", Qt.ConnectionType.QueuedConnection)

    def _perform_single_search(self, params):
        all_found = []
        enabled = [s for s in params.get("sources", []) if s in self.settings.get("enabled_sources", [])]
        if not enabled: return []

        # 1. ENSURE GOOGLE SEARCH GOES FIRST (As requested by user)
        # Re-order list so "Google News" is always the first attempt if enabled
        if "Google News" in enabled:
            enabled.remove("Google News")
            enabled.insert(0, "Google News")

        target_first = params['first_name'].lower().strip()
        target_last = params['last_name'].lower().strip()
        target_full = f"{target_first} {target_last}"

        from difflib import SequenceMatcher

        for name in enabled:
            if self.cancel_requested: break
            scraper = self.scrapers.get(name)
            if not scraper: continue
            
            try:
                found = scraper.search(params['first_name'], params['last_name'], params['city'], params['state'], params['date_from'], params['date_to'])
                if not found: continue
                
                # Apply filter to results from this scraper
                filtered_for_this_source = self._apply_relevance_filter(found, params)
                all_found.extend(filtered_for_this_source)
                
                # 2. CHECK FOR 80% PROBABILITY MATCH (EARLY EXIT)
                # If we found matches in this scraper (Google News first), check if any are high-confidence
                for rec in filtered_for_this_source:
                    rec_full_name = rec.get('full_name', '').lower().strip()
                    # Calculate similarity ratio
                    similarity = SequenceMatcher(None, target_full, rec_full_name).ratio()
                    
                    if similarity >= 0.80:
                        logger.info(f"HIGH CONFIDENCE MATCH ({int(similarity*100)}%): Found {rec_full_name} via {name}. Exiting early for this person.")
                        return all_found # Exit search for this person early
                        
            except Exception as e:
                logger.error(f"SCRAPER ERROR: {name}: {e}")
        
        return deduplicate(all_found)

    def _apply_relevance_filter(self, results, params):
        fname = params['first_name'].lower().strip()
        lname = params['last_name'].lower().strip()
        city_filter = params.get('city', '').lower().strip()
        d_from, d_to = params.get('date_from'), params.get('date_to')
        s_filter = params.get('state')
        
        allowed_fnames = [fname] + NICKNAMES.get(fname, [])
        filtered = []
        
        for rec in results:
            full_name = rec.get('full_name', '').lower()
            rd = rec.get('date_of_death')
            rs = rec.get('state', '').upper()
            rc = rec.get('city', '').lower()
            
            if not (any(n in full_name for n in allowed_fnames) and lname in full_name): continue
            
            if rd and (d_from or d_to):
                df_dt = parse_date(d_from) if isinstance(d_from, str) else d_from
                dt_dt = parse_date(d_to) if isinstance(d_to, str) else d_to
                if df_dt and rd < df_dt: continue
                if dt_dt and rd > dt_dt: continue
            
            if s_filter and s_filter != "All" and rs and rs != s_filter.upper(): continue
            if city_filter and rc and city_filter not in rc: continue
            
            filtered.append(rec)
        return filtered

    @pyqtSlot()
    def refresh_search_history(self):
        if self.db_manager: self.search_panel.update_history_dropdown(self.db_manager.get_search_history())

    @pyqtSlot()
    def _finalize_search(self):
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint); self.show()
        self.results_table.load_results(self.current_results)
        self.reaper_loader.stop_loading(); self.progress_bar.setVisible(False)
        self.status_label.setText("Done." if not self.cancel_requested else "Cancelled.")
        self.search_panel.btn_cancel.setVisible(False); self.search_panel.btn_search.setVisible(True); self.search_panel.btn_bulk.setVisible(True)
        if not self.current_results and not self.cancel_requested: 
            QMessageBox.information(self, "No Results", "No matches found.")

    def run_local_search(self, txt):
        if not self.db_manager: return
        results = self.db_manager.search_local({"keyword": txt} if txt else {})
        self.current_results = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in results]
        self.results_table.load_results(self.current_results); self.status_label.setText("Local Search Complete")

    def load_all_from_db(self): self.run_local_search("")

    def save_results_to_db(self):
        if not self.db_manager or not self.current_results: return
        c = self.db_manager.bulk_insert(self.current_results); QMessageBox.information(self, "Saved", f"Saved {c} new records."); self.update_status_bar_info()

    def show_detail(self, rec): DetailView(rec, self).exec()

    def open_export_dialog(self):
        if not self.current_results: QMessageBox.warning(self, "Export", "No results."); return
        ExportDialog(self.current_results, self).exec()

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec(): self.settings = load_settings(); self.update_status_bar_info()

    def delete_record(self, rid):
        if QMessageBox.question(self, 'Delete', "Are you sure?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_record(rid): self.load_all_from_db(); self.update_status_bar_info()

    def update_status_bar_info(self):
        if self.db_manager: self.db_stat_label.setText(f"DB Records: {self.db_manager.get_stats().get('total_count', 0)}")

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    from database.db_manager import DatabaseManager
    app = QApplication(sys.argv); db = DatabaseManager(); db.initialize_db(); window = MainWindow(db); window.show(); sys.exit(app.exec())
