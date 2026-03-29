def deduplicate(records_list: list) -> list:
    """Removes records with same full_name + date_of_death."""
    seen = set()
    unique_records = []
    
    for record in records_list:
        # Create a unique key
        name = record.get('full_name', '').strip().lower()
        dod = record.get('date_of_death', '') or ''
        key = f"{name}|{dod}"
        
        if key not in seen:
            seen.add(key)
            unique_records.append(record)
            
    return unique_records
