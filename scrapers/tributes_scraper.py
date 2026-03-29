"""
tributes_scraper.py
-------------------
Scrapes obituary search results from Tributes.com.

BUG FIX (v1.1): clean_name() returns a dict, not a string.
Previously the code did:
    full_name = clean_name(raw_name)          # dict assigned to full_name
    name_parts = normalize_name(full_name)    # dict passed where string expected → CRASH

Fixed by assigning the dict to name_info first, then extracting name_info['name'].
"""

import re
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from utils.normalizer import normalize_name, normalize_date, normalize_state, clean_name, parse_age
from utils.logger import logger


class TributesScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.tributes.com/search/obituaries"

    def search(self, first_name, last_name, city=None, state=None, 
               date_from=None, date_to=None) -> list[dict]:
        """
        Searches Tributes.com using Nodriver (superior anti-bot bypass).
        """
        logger.info(f"Starting Tributes.com search for {first_name} {last_name}")
        
        url = f"{self.base_url}/{last_name}-{first_name}"
        
        try:
            html = self.get_page_with_nodriver(
                url,
                wait_for_selector='.obituary_result, .search-result',
                timeout=25
            )
            
            if not html:
                logger.warning("Tributes.com: Nodriver returned empty content.")
                return []
            
            return self._parse_results(html)
            
        except Exception as e:
            logger.error(f"Tributes.com search failed: {e}")
            return []

    def _parse_results(self, html_content: str) -> list[dict]:
        """Parses the Tributes.com search results page HTML."""
        soup = BeautifulSoup(html_content, "lxml")
        records = []

        result_items = (
            soup.select(".obituary_result")
            or soup.select(".search-result")
        )

        for item in result_items:
            try:
                name_elem = item.select_one(".name") or item.select_one("h2")
                if not name_elem:
                    continue

                raw_name = name_elem.get_text(strip=True)

                # ── FIX: clean_name() returns a DICT, not a string ──────────
                # Old (broken): full_name = clean_name(raw_name)
                # New (fixed):
                name_info = clean_name(raw_name)
                full_name = name_info["name"]           # extract the string
                # ────────────────────────────────────────────────────────────

                # Source URL
                url_elem = (
                    name_elem.find("a")
                    if name_elem.name != "a"
                    else name_elem
                )
                url = url_elem.get("href", "") if url_elem else ""
                if url and not url.startswith("http"):
                    url = "https://www.tributes.com" + url

                info_text = item.get_text(separator=" ", strip=True)

                # Parse age
                age = parse_age(info_text)

                # Parse date of death
                dod = ""
                dod_match = re.search(
                    r"Died:\s*([A-Za-z]+\s+\d+,\s+\d{4})", info_text
                )
                if dod_match:
                    dod = normalize_date(dod_match.group(1))

                # Parse city/state from text
                city_val  = name_info.get("city", "")
                state_val = name_info.get("state", "")

                if not city_val:
                    loc_match = re.search(
                        r"in\s+([^,]+),\s*([A-Z]{2}|[A-Za-z\s]+)", info_text
                    )
                    if loc_match:
                        city_val  = loc_match.group(1).strip()
                        state_val = normalize_state(loc_match.group(2).strip())

                # normalize_name now receives a proper string
                name_parts = normalize_name(full_name)

                record = self.normalize_record({
                    "first_name":    name_parts["first_name"],
                    "last_name":     name_parts["last_name"],
                    "full_name":     full_name,
                    "date_of_death": dod,
                    "age":           age,
                    "city":          city_val,
                    "state":         state_val,
                    "source":        "Tributes.com",
                    "source_url":    url,
                })

                records.append(record)

            except Exception as e:
                logger.error(f"Error parsing Tributes.com item: {e}")
                continue

        return records


if __name__ == "__main__":
    scraper = TributesScraper()
    test_results = scraper.search("John", "Smith")
    print(f"Found {len(test_results)} results for John Smith on Tributes.com")
