from bs4 import BeautifulSoup
import json
import re
from scrapers.base_scraper import BaseScraper
from utils.normalizer import normalize_name, normalize_date, normalize_state, clean_name, parse_age, STATE_TO_FULL
from utils.logger import logger

class LegacyScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_key="legacy")
        self.base_search_url = "https://www.legacy.com/obituaries/search"

    def search(self, first_name, last_name, city=None, state=None, 
               date_from=None, date_to=None) -> list[dict]:
        """
        Searches Legacy.com using a persistent Nodriver session.
        """
        logger.info(f"Starting Legacy.com multi-page search for {first_name} {last_name}")
        
        async def _async_search():
            await self.start_browser_session()
            all_found = []
            
            try:
                full_state = STATE_TO_FULL.get(state, state) if state else ""
                import urllib.parse
                
                for page_num in range(1, 11):
                    if getattr(self, 'cancel_requested', False): break
                    
                    params = {
                        "query": f"{first_name} {last_name}",
                        "country": "United States",
                        "state": full_state,
                        "page": str(page_num)
                    }
                    
                    url = f"{self.base_search_url}?{urllib.parse.urlencode(params)}"
                    logger.info(f"Scraping Legacy.com Page {page_num}...")
                    
                    html = await self.get_page_with_nodriver(
                        url, 
                        wait_for_selector='main, #main, .SearchListing, [class*="RecordCard"]',
                        timeout=30
                    )
                    if not html: break
                    
                    page_results = self._parse_results(html)
                    if not page_results: break 
                    
                    all_found.extend(page_results)
                    if len(page_results) < 20: break
                    
            finally:
                await self.stop_browser_session()
            return all_found

        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_async_search())
        finally:
            loop.close()

    def _parse_results(self, html_content) -> list[dict]:
        records = []
        soup = BeautifulSoup(html_content, 'lxml')
        
        # --- METHOD A: JSON-LD (The Gold Standard) ---
        try:
            script = soup.find('script', type='application/ld+json')
            if script:
                data = json.loads(script.string)
                items = data.get('mainEntity', {}).get('itemListElement', [])
                for item in items:
                    name_raw = item.get('name', '').replace(' Obituary', '')
                    url = item.get('url', '')
                    if name_raw: records.append(self._create_record(name_raw, url, "JSON-LD"))
        except: pass

        # --- METHOD B: CSS Selectors (Fallback) ---
        if not records:
            items = soup.select('[class*="RecordCard"]') or soup.select('.SearchListing')
            for item in items:
                try:
                    name_elem = item.select_one('h3') or item.select_one('a[class*="Name"]')
                    if not name_elem: continue
                    name_raw = name_elem.get_text(strip=True)
                    url = name_elem.get('href') if name_elem.name == 'a' else (name_elem.find('a')['href'] if name_elem.find('a') else "")
                    if url and not url.startswith('http'): url = "https://www.legacy.com" + url
                    records.append(self._create_record(name_raw, url, "Selector"))
                except: pass

        # --- METHOD C: Regex Text Scrape (Final Resort) ---
        if not records:
            # Look for ANY link containing "/person/" and a name
            for a in soup.find_all('a', href=re.compile(r'/person/')):
                name_raw = a.get_text(strip=True)
                if len(name_raw.split()) >= 2 and "Obituary" in name_raw:
                    url = a['href']
                    if not url.startswith('http'): url = "https://www.legacy.com" + url
                    records.append(self._create_record(name_raw.replace(" Obituary", ""), url, "Regex"))

        logger.info(f"Legacy.com: Total unique results found: {len(records)}")
        return records

    def _create_record(self, name_raw, url, debug_method):
        name_info = clean_name(name_raw)
        full_name = name_info['name']
        name_parts = normalize_name(full_name)
        return self.normalize_record({
            "full_name": full_name,
            "first_name": name_parts["first_name"],
            "last_name": name_parts["last_name"],
            "city": name_info['city'],
            "state": name_info['state'],
            "source": "Legacy.com",
            "source_url": url,
            "full_text": f"Captured via {debug_method}"
        })
