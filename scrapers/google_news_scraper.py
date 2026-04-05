import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from utils.normalizer import normalize_name, normalize_date, clean_name
from utils.logger import logger

class GoogleNewsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.rss_url = "https://news.google.com/rss/search"

    def search(self, first_name, last_name, city=None, state=None, date_from=None, date_to=None) -> list[dict]:
        """
        AI-Enhanced Search: Performs broad internet queries like a human researcher.
        """
        logger.info(f"Starting AI-Broad Search for {first_name} {last_name}")
        
        # We perform 2 types of broad searches to maximize scope
        queries = [
            f'"{first_name} {last_name}" obituary {city or ""} {state or ""}',
            f'"{first_name} {last_name}" passed away {city or ""} {state or ""}'
        ]
        
        all_found = []
        for q in queries:
            if getattr(self, 'cancel_requested', False): break
            params = {"q": q.strip(), "hl": "en-US", "gl": "US", "ceid": "US:en"}
            try:
                response = self.make_request(self.rss_url, params=params)
                if response and response.text:
                    all_found.extend(self._parse_rss(response.text))
            except Exception as e:
                logger.error(f"Broad search failed for query '{q}': {e}")
                
        return all_found

    def _parse_rss(self, xml_content) -> list[dict]:
        records = []
        try:
            root = ET.fromstring(xml_content.encode('utf-8'))
            items = root.findall('.//item')
            for item in items[:25]:
                try:
                    title_raw = item.find('title').text if item.find('title') is not None else ""
                    link = item.find('link').text if item.find('link') is not None else ""
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    if not title_raw: continue
                
                    name_info = clean_name(title_raw)
                    full_name = name_info['name']
                    
                    source = "Broad Web Search"
                    if " - " in full_name:
                        parts = full_name.rsplit(" - ", 1)
                        full_name = parts[0]
                        source = parts[1]

                    name_parts = normalize_name(full_name)
                    record = self.normalize_record({
                        "full_name": full_name,
                        "first_name": name_parts["first_name"],
                        "last_name": name_parts["last_name"],
                        "date_of_death": normalize_date(pub_date),
                        "city": name_info['city'],
                        "state": name_info['state'],
                        "source": source,
                        "source_url": link,
                        "full_text": title_raw # Snippet
                    })
                    records.append(record)
                except Exception as e:
                    continue
        except Exception as e:
            logger.error(f"Error parsing RSS XML: {e}")
        return records
