"""
base_scraper.py
---------------
Abstract base class for all obituary scrapers.

v1.2 FIXES APPLIED:
  - FIX 1: make_request() restored. It was accidentally deleted when nodriver
            was added. GoogleNewsScraper (RSS) depends on it and crashed without it.
  - FIX 2: get_page_with_nodriver() now injects stored login cookies into the
            nodriver browser context BEFORE navigating. Previously, the browser
            launched with a clean profile and never saw the cookies captured in
            Settings > Sources & Credentials — so logged-in scraping never worked.
  - FIX 3: asyncio.new_event_loop() used instead of asyncio.run() to prevent
            RuntimeError on Windows when called from a daemon thread.
"""

import time
import random
import requests
import json
import asyncio
import os
from abc import ABC, abstractmethod
from utils.logger import logger
from utils.normalizer import extract_details_from_text
from credentials.credential_manager import get_credential


class BaseScraper(ABC):

    def __init__(self, source_key=None):
        self.session = requests.Session()
        self.source_key = source_key
        self.is_logged_in = False
        self.cancel_requested = False
        self.current_browser = None
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # CREDENTIALS
    # ─────────────────────────────────────────────────────────────────────────

    def reload_credentials(self):
        """Loads stored cookies into the requests Session (for make_request)."""
        if self.source_key:
            raw_data = get_credential(self.source_key, "cookies")
            if raw_data:
                try:
                    self.session.cookies.clear()
                    cookie_list = json.loads(raw_data)
                    for c in cookie_list:
                        self.session.cookies.set(
                            c["name"], c["value"],
                            domain=c.get("domain", ""),
                            path=c.get("path", "/")
                        )
                    self.is_logged_in = True
                except Exception as e:
                    logger.error(f"reload_credentials failed for {self.source_key}: {e}")
                    self.is_logged_in = False
            else:
                self.is_logged_in = False

    # ─────────────────────────────────────────────────────────────────────────
    # ABSTRACT
    # ─────────────────────────────────────────────────────────────────────────

    @abstractmethod
    def search(
        self,
        first_name: str,
        last_name: str,
        city: str = None,
        state: str = None,
        date_from: str = None,
        date_to: str = None
    ) -> list[dict]:
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # FIX 1 — make_request() RESTORED
    # This was deleted by mistake. GoogleNewsScraper (RSS) needs it.
    # Do NOT remove this method again.
    # ─────────────────────────────────────────────────────────────────────────

    def make_request(self, url: str, params=None, method: str = "GET"):
        """
        Makes a plain HTTP request using the requests library.
        Used by scrapers that do NOT need JavaScript (e.g. Google News RSS).
        Injects stored session cookies automatically.
        Returns the Response object, or None on failure.
        """
        self.reload_credentials()
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        time.sleep(random.uniform(1.0, 2.5))
        try:
            if method == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=25)
            else:
                response = self.session.post(url, data=params, headers=headers, timeout=25)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"make_request failed for {url}: {e}")
            return None

    def get_page_content(self, url: str) -> str:
        """Convenience wrapper: returns page text or empty string."""
        res = self.make_request(url)
        return res.text if res else ""

    # ─────────────────────────────────────────────────────────────────────────
    # FIX 2 + FIX 3 — get_page_with_nodriver() WITH COOKIE INJECTION
    # FIX 2: Cookies from credentials.enc are now injected into the nodriver
    #         browser before navigating. Previously this never happened and
    #         logged-in scraping silently returned zero results every time.
    # FIX 3: Uses asyncio.new_event_loop() instead of asyncio.run() to avoid
    #         RuntimeError on Windows when called from a daemon thread.
    # ─────────────────────────────────────────────────────────────────────────

    def get_page_with_nodriver(
        self,
        url: str,
        wait_for_selector: str = None,
        timeout: int = 30
    ) -> str:
        """
        Retrieves page HTML. Expects to be called from WITHIN an existing 
        async context (e.g. from a scraper's async _run method).
        """
        import asyncio
        import nodriver as uc

        async def _internal_get():
            browser = self.current_browser
            if not browser:
                logger.error(f"{self.source_key}: No persistent browser session found.")
                return ""

            if getattr(self, 'cancel_requested', False): return ""

            try:
                page = await browser.get(url)

                # Wait for content (periodic cancel checks)
                wait_time = 0
                while wait_time < timeout:
                    if getattr(self, 'cancel_requested', False): return ""
                    if wait_for_selector:
                        selectors = [s.strip() for s in wait_for_selector.split(",")]
                        found = False
                        for sel in selectors:
                            try:
                                res = await page.evaluate(f'document.querySelector("{sel}") !== null')
                                if res: found = True; break
                            except: pass
                        if found: break
                    await asyncio.sleep(1.0)
                    wait_time += 1

                await asyncio.sleep(2.0)
                return await page.get_content()
            except Exception as e:
                logger.error(f"Nodriver retrieval error: {e}")
                return ""

        # Check if we're already in a loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We are already in an async context, just return the future
                return _internal_get()
        except:
            pass

        # Fallback for synchronous calls
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(_internal_get())
        finally:
            new_loop.close()

    async def start_browser_session(self):
        """Starts a persistent nodriver session for multi-page scraping."""
        import nodriver as uc
        
        profile_dir = os.path.join(
            os.getenv("APPDATA", os.path.expanduser("~")),
            "KellysCreepyDeathDiggerMachine",
            "profiles",
            self.source_key or "general"
        )
        os.makedirs(profile_dir, exist_ok=True)
        
        browser_args = [
            "--window-size=800,600",
            "--window-position=0,0",
            "--disable-notifications",
            "--disable-popup-blocking"
        ]
        
        try:
            # Check for stored cookies
            stored_cookies = []
            if self.source_key:
                raw_cookies = get_credential(self.source_key, "cookies")
                if raw_cookies:
                    try:
                        cookie_list = json.loads(raw_cookies)
                        for c in cookie_list:
                            if c.get("domain", "").startswith("."):
                                c["domain"] = c["domain"][1:]
                        stored_cookies = cookie_list
                    except: pass

            self.current_browser = await uc.start(user_data_dir=profile_dir, browser_args=browser_args)
            
            if stored_cookies:
                # Set cookies on a blank page first
                tab = await self.current_browser.get("about:blank")
                await asyncio.sleep(0.5)
                for c in stored_cookies:
                    try:
                        await tab.set_cookie(
                            name=c["name"], value=c["value"],
                            domain=c.get("domain", ""), path=c.get("path", "/")
                        )
                    except: pass
                logger.info(f"{self.source_key}: Injected session cookies into persistent browser.")
                
            return self.current_browser
        except Exception as e:
            logger.error(f"Failed to start browser session: {e}")
            return None

    async def stop_browser_session(self):
        """Closes the persistent session."""
        if self.current_browser:
            try:
                await self.current_browser.stop()
            except:
                pass
            self.current_browser = None
        # ─────────────────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────────────────────
    # NORMALIZE
    # ─────────────────────────────────────────────────────────────────────────

    def normalize_record(self, raw_dict: dict) -> dict:
        """Ensures every record has the same set of keys."""
        schema = {
            "first_name": "", "last_name": "", "full_name": "",
            "date_of_birth": None, "date_of_death": None, "age": None,
            "city": "", "state": "", "source": "", "source_url": "",
            "full_text": "", "survivors": "", "photo_url": "",
            "keywords": "", "date_added": None
        }
        normalized = schema.copy()
        for key in raw_dict:
            if key in normalized:
                normalized[key] = raw_dict[key]
        text_to_mine = f"{normalized['full_name']} {normalized['full_text']}"
        normalized = extract_details_from_text(text_to_mine, normalized)
        return normalized
