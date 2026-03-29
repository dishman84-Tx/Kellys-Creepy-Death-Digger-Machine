import re
from datetime import datetime

STATES = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

STATE_TO_FULL = {v: k for k, v in STATES.items()}

def clean_name(name_str: str) -> dict:
    if not name_str: return {"name": "", "city": "", "state": ""}
    city, state = "", ""
    # Capture Location from Title: "Name Obituary - City, ST"
    loc_match = re.search(r'Obituary\s*-\s*([A-Za-z\s]+),\s*([A-Z]{2})', name_str, re.IGNORECASE)
    if loc_match:
        city = loc_match.group(1).strip()
        state = loc_match.group(2).strip()
    
    name_str = re.sub(r'Obituary\s*-.*$', '', name_str, flags=re.IGNORECASE)
    noise = ["Recently Deceased", "Obituary", "Death Notice", "Grave Photo", "No grave photo", "Memorial", "In Loving Memory"]
    for word in noise: name_str = re.sub(re.escape(word), ' ', name_str, flags=re.IGNORECASE)
    name_str = re.sub(r'\d{1,2}\s+[A-Za-z]{3}\s+\d{4}', ' ', name_str)
    name_str = re.sub(r'[–-]', ' ', name_str)
    name_str = re.sub(r'\d{4}', ' ', name_str)
    name_str = re.sub(r'[•\*\(\)\[\]]', ' ', name_str)
    return {"name": " ".join(name_str.split()).strip(), "city": city, "state": state}

def normalize_name(name_str: str) -> dict:
    parts = name_str.strip().split()
    if not parts: return {"first_name": "", "last_name": ""}
    return {"first_name": parts[0], "last_name": " ".join(parts[1:]) if len(parts) > 1 else ""}

def parse_age(text: str) -> int:
    if not text: return None
    # Matches: "89 years old", "age 89", "89, of Ransom Canyon"
    match = re.search(r'(?:age|aged)?\s*(\d{1,3})\s*(?:years\s+old|of|,\s+of)?', text, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        if 1 < val < 120: return val
    return None

def parse_date(date_str: str):
    if not date_str: return None
    # Clean noise: "13 Apr 1954 (aged 8)" -> "13 Apr 1954"
    date_str = re.sub(r'\s*\(aged\s+\d+\)', '', date_str, flags=re.I).strip()
    # Clean day names: "Tuesday, September 6, 2022" -> "September 6, 2022"
    date_str = re.sub(r'^[A-Za-z]+,\s*', '', date_str).strip()
    
    formats = ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%d %b %Y", "%Y"]
    for fmt in formats:
        try: return datetime.strptime(date_str, fmt)
        except: continue
    return None

def normalize_date(date_str: str) -> str:
    dt = parse_date(date_str)
    return dt.strftime("%Y-%m-%d") if dt else None

def normalize_state(state_str: str) -> str:
    if not state_str: return ""
    state_str = state_str.strip().title()
    return STATES.get(state_str, state_str.upper() if len(state_str)==2 else state_str)

def extract_details_from_text(text: str, current_record: dict) -> dict:
    if not text: return current_record
    
    # 1. Improved DOD (e.g. "passed from this life Tuesday, September 6, 2022")
    if not current_record.get('date_of_death'):
        dod_pats = [
            r'(?:passed from this life|passed away|died|death|deceased)\s+(?:on\s+)?(?:[A-Za-z]+,\s+)?([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(?:passed from this life|passed away|died|death|deceased)\s+(?:on\s+)?(\d{1,2}/\d{1,2}/\d{4})'
        ]
        for pat in dod_pats:
            m = re.search(pat, text, re.IGNORECASE)
            if m: current_record['date_of_death'] = normalize_date(m.group(1)); break

    # 2. Improved Age (e.g. "Fred Jones, 89, of Ransom Canyon")
    if not current_record.get('age'):
        current_record['age'] = parse_age(text)

    # 3. Improved Location (e.g. "of Ransom Canyon", "in San Antonio, Texas")
    if not current_record.get('city'):
        loc_pats = [
            r'(?:resident of|in|at|of)\s+([A-Za-z\s]+),\s*([A-Za-z\s]{2,})', # City, State
            r'(?:resident of|in|at|of)\s+([A-Za-z\s]{3,})' # Just City
        ]
        for pat in loc_pats:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                city = m.group(1).strip()
                if city.lower() in ['his', 'her', 'the', 'death', 'life', 'this', 'our']: continue
                current_record['city'] = city
                if len(m.groups()) > 1: current_record['state'] = normalize_state(m.group(2))
                break

    return current_record
