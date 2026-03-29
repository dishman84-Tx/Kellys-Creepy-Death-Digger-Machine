"""
findagrave_scraper.py
---------------------
Scrapes FindAGrave search results using nodriver (headless browser).
Supports persistent sessions for multi-page scraping.
"""

from bs4 import BeautifulSoup
import re
import urllib.parse
import asyncio
from scrapers.base_scraper import BaseScraper
from utils.normalizer import (
    normalize_name, normalize_date, normalize_state,
    clean_name, parse_age, STATE_TO_FULL
)
from utils.logger import logger

# Full 50-state FindAGrave location ID map
FINDAGRAVE_STATE_IDS = {
    "AL": "state_1",  "AK": "state_2",  "AZ": "state_3",  "AR": "state_4",
    "CA": "state_5",  "CO": "state_6",  "CT": "state_7",  "DE": "state_8",
    "FL": "state_9",  "GA": "state_10", "HI": "state_11", "ID": "state_12",
    "IL": "state_13", "IN": "state_14", "IA": "state_15", "KS": "state_16",
    "KY": "state_17", "LA": "state_18", "ME": "state_19", "MD": "state_20",
    "MA": "state_21", "MI": "state_22", "MN": "state_23", "MS": "state_24",
    "MO": "state_25", "MT": "state_26", "NE": "state_27", "NV": "state_28",
    "NH": "state_29", "NJ": "state_30", "NM": "state_31", "NY": "state_32",
    "NC": "state_33", "ND": "state_34", "OH": "state_35", "OK": "state_36",
    "OR": "state_37", "PA": "state_38", "RI": "state_39", "SC": "state_40",
    "SD": "state_41", "TN": "state_45", "TX": "state_46", "UT": "state_47",
    "VT": "state_48", "VA": "state_49", "WA": "state_50", "WV": "state_51",
    "WI": "state_52", "WY": "state_53",
}


class FindAGraveScraper(BaseScraper):

    def __init__(self):
        super().__init__(source_key="findagrave")
        self.base_search_url = "https://www.findagrave.com/memorial/search"

    def search(
        self,
        first_name: str,
        last_name: str,
        city: str = None,
        state: str = None,
        date_from: str = None,
        date_to: str = None
    ) -> list[dict]:
        """Searches FindAGrave using a persistent nodriver session."""
        logger.info(f"Starting FindAGrave multi-page search for {first_name} {last_name}")

        async def _async_search():
            await self.start_browser_session()
            all_found = []
            
            try:
                full_state = STATE_TO_FULL.get(state, state) if state else ""
                full_location = f"{full_state}, United States of America" if full_state else ""
                loc_id = FINDAGRAVE_STATE_IDS.get(state, "") if state else ""

                # Scrape up to 10 pages (~200 results)
                for page_num in range(1, 11):
                    if getattr(self, 'cancel_requested', False): break
                    
                    params = {
                        "firstname":       first_name,
                        "middlename":      "",
                        "lastname":        last_name,
                        "birthyear":       "",
                        "birthyearfilter": "",
                        "deathyearfilter": "",
                        "location":        full_location,
                        "locationId":      loc_id,
                        "page":            str(page_num),
                    }

                    url = f"{self.base_search_url}?{urllib.parse.urlencode(params)}"
                    logger.info(f"Scraping FindAGrave Page {page_num}...")

                    html = await self.get_page_with_nodriver(
                        url,
                        wait_for_selector=".memorial-item, .no-results",
                        timeout=30
                    )
                    if not html: break
                    
                    page_results = self._parse_results(html)
                    if not page_results: break
                    
                    all_found.extend(page_results)
                    if len(page_results) < 15: break 
                    
            finally:
                await self.stop_browser_session()
            return all_found

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_async_search())
        finally:
            loop.close()

    def _parse_results(self, html_content: str) -> list[dict]:
        soup = BeautifulSoup(html_content, "lxml")
        records = []
        result_items = soup.select(".memorial-item") or soup.select("div[class*='memorial-item']")

        for item in result_items:
            try:
                name_anchor = item.select_one('a[href*="/memorial/"]')
                if not name_anchor: continue

                name_info = clean_name(name_anchor.get_text(strip=True))
                full_name = name_info["name"]
                url = name_anchor.get("href", "")
                if url and not url.startswith("http"):
                    url = "https://www.findagrave.com" + url

                card_text  = item.get_text(separator=" ", strip=True)
                name_parts = normalize_name(full_name)

                record = self.normalize_record({
                    "full_name":  full_name,
                    "first_name": name_parts["first_name"],
                    "last_name":  name_parts["last_name"],
                    "city":       name_info["city"],
                    "state":      normalize_state(name_info["state"]),
                    "source":     "FindAGrave",
                    "source_url": url,
                    "full_text":  card_text,
                })
                records.append(record)
            except Exception as e:
                logger.error(f"Error parsing FindAGrave item: {e}")

        return records
