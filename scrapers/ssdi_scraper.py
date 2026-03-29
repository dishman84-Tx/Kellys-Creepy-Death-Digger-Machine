import json
import requests
import re
import urllib.parse
import asyncio
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from utils.normalizer import normalize_name, STATE_TO_FULL
from utils.logger import logger
from credentials.credential_manager import get_credential

class SsdiScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_key="familysearch")
        self.api_url = "https://api.familysearch.org/platform/records/personas"
        self.search_url = "https://www.familysearch.org/en/search/all-collections/results"

    def search(self, first_name, last_name, city=None, state=None, 
               date_from=None, date_to=None) -> list[dict]:
        """
        Searches FamilySearch. Tries official API first, falls back to nodriver.
        """
        self.reload_credentials()
        
        if not self.is_logged_in:
            logger.warning("SSDI (FamilySearch) requires a session token. Please login in Settings.")
            return []
            
        # 1. Try Official API (GEDCOM X Atom JSON)
        token = self.session.cookies.get("fssessionid")
        if token:
            results = self._search_via_api(token, first_name, last_name, state, date_from, date_to)
            if results:
                logger.info(f"FamilySearch API: Successfully returned {len(results)} results.")
                return results
            else:
                logger.info("FamilySearch API returned 0 results or failed. Falling back to nodriver...")
        else:
            logger.warning("FamilySearch: fssessionid cookie not found. Falling back to nodriver...")

        # 2. Fallback to Nodriver (Web Scraping)
        async def _async_fallback():
            await self.start_browser_session()
            try:
                return await self._search_via_nodriver(first_name, last_name, state)
            finally:
                await self.stop_browser_session()

        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_async_fallback())
        finally:
            loop.close()

    def _search_via_api(self, token, first_name, last_name, state, date_from, date_to):
        """Hits the official FamilySearch Records API using targeted death parameters."""
        full_state = STATE_TO_FULL.get(state, state) if state else ""
        
        # Base parameters
        params = {
            "q.givenName": first_name,
            "q.surname": last_name,
            "count": 200
        }
        
        # Use q.deathLikePlace instead of q.birthLikePlace to find deaths/obituaries
        if full_state:
            params["q.deathLikePlace"] = full_state
            
        # Add date range directly to the API query
        # API format: q.deathLikeDate.from=YYYY and q.deathLikeDate.to=YYYY
        from utils.normalizer import parse_date
        df_dt = parse_date(date_from) if isinstance(date_from, str) else date_from
        dt_dt = parse_date(date_to) if isinstance(date_to, str) else date_to
        
        if df_dt:
            params["q.deathLikeDate.from"] = df_dt.year
        if dt_dt:
            params["q.deathLikeDate.to"] = dt_dt.year
            
        headers = {
            "Accept": "application/x-gedcomx-atom+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": self.user_agent
        }
        
        try:
            # Note: api.familysearch.org might require fssessionid in header too
            response = requests.get(self.api_url, params=params, headers=headers, timeout=20)
            if response.status_code != 200:
                logger.error(f"FamilySearch API returned status {response.status_code}")
                return None
            
            data = response.json()
            entries = data.get("entries", [])
            results = []
            
            for entry in entries:
                try:
                    content = entry.get("content", {})
                    gx = content.get("gedcomx", {})
                    # The record person is usually the first person in the list
                    person = gx.get("persons", [{}])[0]
                    
                    # Extract name more robustly
                    full_name = entry.get("title", "Unknown")
                    names = person.get("names", [])
                    if names:
                        forms = names[0].get("nameForms", [])
                        if forms:
                            full_name = forms[0].get("fullText", full_name)
                    
                    # Extract facts (death, birth)
                    facts = person.get("facts", [])
                    d_date = None
                    d_city = ""
                    d_state = ""
                    is_death_record = False
                    
                    for f in facts:
                        f_type = f.get("type", "")
                        # Strictly look for Death, Burial, or Obituary fact types
                        if any(kw in f_type for kw in ["Death", "Burial", "Obituary"]):
                            is_death_record = True
                            d_date_str = f.get("date", {}).get("original", "")
                            if not d_date_str:
                                d_date_str = f.get("date", {}).get("formal", "").replace("+", "")
                            
                            from utils.normalizer import parse_date
                            d_date = parse_date(d_date_str)
                            d_city = f.get("place", {}).get("original", "")
                    
                    # DISCARD if it's not a death record or has no date
                    if not is_death_record or not d_date:
                        continue

                    # Extract record URL (ARK) - Try multiple possible link keys
                    source_url = ""
                    links = entry.get("links", {})
                    if "alternate" in links:
                        source_url = links["alternate"].get("href", "")
                    
                    # If constructed from ID, it's usually a Persona ID for historical records (ARK)
                    if not source_url and entry.get("id"):
                        raw_id = entry.get("id").split("/")[-1] # Get just the ID part
                        source_url = f"https://www.familysearch.org/ark:/61903/1:1:{raw_id}"
                    
                    # Safety check for absolute URLs
                    if source_url and not source_url.startswith("http"):
                        if not source_url.startswith("/"):
                            source_url = "/" + source_url
                        source_url = "https://www.familysearch.org" + source_url

                    results.append(self.normalize_record({
                        "full_name": full_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "date_of_death": d_date,
                        "city": d_city,
                        "state": d_state,
                        "source": "FamilySearch (API)",
                        "source_url": source_url,
                        "full_text": f"Death Record: {full_name}. Location: {d_city}"
                    }))
                except Exception as e:
                    logger.debug(f"Error parsing individual API entry: {e}")
                    continue
            return results
        except Exception as e:
            logger.error(f"FamilySearch API call failed: {e}")
            return None

    def _search_via_nodriver(self, first_name, last_name, state):
        """Existing nodriver-based web scraper with automated login support."""
        full_state = STATE_TO_FULL.get(state, state) if state else ""
        params = {
            "q.surname": last_name,
            "q.givenName": first_name,
            "q.birthLikePlace": full_state
        }
        url = f"{self.search_url}?{urllib.parse.urlencode(params)}"
        
        async def _run_with_login():
            browser = self.current_browser
            if not browser: return []
            
            page = await browser.get(url)
            await asyncio.sleep(2)
            
            # CHECK IF WE ARE AT LOGIN PAGE
            current_url = page.url
            if "login" in current_url.lower() or "auth" in current_url.lower():
                logger.info("FamilySearch: Not logged in. Attempting automated login...")
                user = get_credential("familysearch", "username")
                pw = get_credential("familysearch", "password")
                
                if user and pw:
                    # Fill login fields via JS
                    login_js = f"""
                    (function() {{
                        const u = document.querySelector('input[name*="user"], input[id*="user"], input[type="text"]');
                        const p = document.querySelector('input[name*="pass"], input[id*="pass"], input[type="password"]');
                        if (u) {{
                            u.value = "{user}";
                            u.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            u.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        if (p) {{
                            p.value = "{pw}";
                            p.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            p.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        const b = document.querySelector('button[type="submit"], button[id*="login"]');
                        if (b) b.click();
                    }})();
                    """
                    await page.evaluate(login_js)
                    await asyncio.sleep(5) # Wait for login to process
                    # Re-navigate to search
                    page = await browser.get(url)
                else:
                    logger.warning("FamilySearch: Login required but no credentials found in Settings.")
                    return []

            # SCRAPE RESULTS
            html = await self.get_page_with_nodriver(url, wait_for_selector='table, tr, article')
            if not html: return []
            
            soup = BeautifulSoup(html, "lxml")
            records = []
            rows = soup.find_all('tr')
            if not rows:
                rows = soup.find_all(['article', 'div'], class_=re.compile(r'result|card', re.I))

            for row in rows:
                try:
                    link = row.find('a', href=True)
                    if not link: continue
                    full_name = link.get_text(strip=True)
                    if len(full_name.split()) < 2: continue
                    r_url = link['href']
                    if not r_url.startswith("http"):
                        r_url = "https://www.familysearch.org" + r_url
                    row_text = row.get_text(separator=" ", strip=True)
                    name_parts = normalize_name(full_name)
                    records.append(self.normalize_record({
                        "full_name":  full_name,
                        "first_name": name_parts["first_name"],
                        "last_name":  name_parts["last_name"],
                        "source":     "FamilySearch (Web)",
                        "source_url": r_url,
                        "full_text":  row_text,
                    }))
                except: continue
            return records

        return _run_with_login()
