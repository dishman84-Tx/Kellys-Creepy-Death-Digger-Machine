"""
db_manager.py
-------------
SQLAlchemy-based database manager for Kelly's Creepy Death Digger Machine.

BUG FIX (v1.1): Added missing `from utils.logger import logger` import.
Previously, save_search_history() called logger.info() and logger.error()
but logger was never imported, causing a NameError crash the first time
a search was performed.
"""

import os
import json
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from database.models import Base, Obituary, SearchHistory, UserNote
from utils.logger import logger          # ← FIX: was missing, caused NameError

load_dotenv()


class DatabaseManager:
    """Handles all SQLite read/write operations for obituary records."""

    def __init__(self):
        app_data_dir = os.path.join(
            os.getenv("APPDATA", os.path.expanduser("~")),
            "KellysCreepyDeathDiggerMachine"
        )
        os.makedirs(app_data_dir, exist_ok=True)
        db_path = os.path.join(app_data_dir, "obituary_tracker.db")
        
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.engine)

    def initialize_db(self) -> None:
        """Creates all tables if they don't already exist."""
        Base.metadata.create_all(self.engine)

    def insert_obituary(self, record_dict: dict) -> bool:
        """
        Inserts a single obituary record.
        Silently skips duplicates (enforced by the UniqueConstraint on
        full_name + date_of_death + source).

        Returns True if inserted, False if skipped or on error.
        """
        session = self.Session()
        try:
            if "date_added" not in record_dict or not record_dict["date_added"]:
                record_dict["date_added"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_record = Obituary(**record_dict)
            session.add(new_record)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def bulk_insert(self, records_list: list[dict]) -> int:
        """
        Inserts a list of record dicts.
        Returns the count of records actually inserted (duplicates excluded).
        """
        inserted_count = 0
        for record in records_list:
            if self.insert_obituary(record):
                inserted_count += 1
        return inserted_count

    def search_local(self, query_dict: dict) -> list:
        """
        Searches the local database by any combination of:
            first_name, last_name, state, keyword (searches full_text,
            survivors, and keywords columns).

        Returns a list of Obituary ORM objects.
        """
        session = self.Session()
        query = session.query(Obituary)

        if query_dict.get("first_name"):
            query = query.filter(
                Obituary.first_name.ilike(f"%{query_dict['first_name']}%")
            )
        if query_dict.get("last_name"):
            query = query.filter(
                Obituary.last_name.ilike(f"%{query_dict['last_name']}%")
            )
        if query_dict.get("state"):
            query = query.filter(Obituary.state == query_dict["state"])
        if query_dict.get("keyword"):
            kw = f"%{query_dict['keyword']}%"
            query = query.filter(
                or_(
                    Obituary.full_text.ilike(kw),
                    Obituary.survivors.ilike(kw),
                    Obituary.keywords.ilike(kw),
                )
            )

        results = query.all()
        session.close()
        return results

    def get_all(self) -> list:
        """Returns all Obituary records from the database."""
        session = self.Session()
        results = session.query(Obituary).all()
        session.close()
        return results

    def delete_record(self, record_id: int) -> bool:
        """
        Deletes an Obituary record by its integer ID.
        Returns True if deleted, False if not found.
        """
        session = self.Session()
        record = session.query(Obituary).filter(Obituary.id == record_id).first()
        if record:
            session.delete(record)
            session.commit()
            session.close()
            return True
        session.close()
        return False

    def get_stats(self) -> dict:
        """
        Returns a dict with:
            total_count       (int)
            sources_breakdown (dict: source_name -> count)
        """
        session = self.Session()
        total_count = session.query(Obituary).count()
        sources_query = session.query(Obituary.source).distinct().all()
        breakdown = {}
        for (source_name,) in sources_query:
            count = session.query(Obituary).filter(
                Obituary.source == source_name
            ).count()
            breakdown[source_name] = count
        session.close()
        return {
            "total_count": total_count,
            "sources_breakdown": breakdown,
        }

    def save_search_history(self, params_dict: dict, count: int) -> None:
        """
        Saves a search's parameters and result count to the search_history table.
        Skips saving if the most recent entry has identical parameters
        (avoids duplicate consecutive history entries).
        """
        session = self.Session()
        try:
            last_entry = (
                session.query(SearchHistory)
                .order_by(SearchHistory.id.desc())
                .first()
            )
            params_json = json.dumps(params_dict)

            if last_entry and last_entry.search_params == params_json:
                logger.info("Search matches most recent history. Skipping save.")
                return

            history = SearchHistory(
                search_params=params_json,
                result_count=count,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            session.add(history)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save search history: {e}")
        finally:
            session.close()

    def get_search_history(self, limit: int = 20) -> list:
        """Retrieves the most recent search history entries (newest first)."""
        session = self.Session()
        results = (
            session.query(SearchHistory)
            .order_by(SearchHistory.id.desc())
            .limit(limit)
            .all()
        )
        session.close()
        return results


if __name__ == "__main__":
    # Quick smoke test — run this file directly to verify DB setup
    db = DatabaseManager()
    db.initialize_db()

    test_record = {
        "first_name":    "John",
        "last_name":     "Doe",
        "full_name":     "John Doe",
        "date_of_death": "2024-03-27",
        "source":        "Manual Test",
        "city":          "Nashville",
        "state":         "TN",
    }

    inserted = db.insert_obituary(test_record)
    print(f"Insert result: {inserted}")

    all_records = db.get_all()
    print(f"Total records in DB: {len(all_records)}")

    if all_records:
        print(f"First record: {all_records[0].full_name} from {all_records[0].source}")

    stats = db.get_stats()
    print(f"Stats: {stats}")
