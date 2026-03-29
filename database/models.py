from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Obituary(Base):
    __tablename__ = 'obituaries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String)
    last_name = Column(String)
    full_name = Column(String)
    date_of_birth = Column(String)
    date_of_death = Column(String)
    age = Column(Integer)
    city = Column(String)
    state = Column(String)
    country = Column(String, default='US')
    source = Column(String)
    source_url = Column(String)
    full_text = Column(Text)
    survivors = Column(Text)
    photo_url = Column(String)
    keywords = Column(Text)
    date_added = Column(String)
    
    # User notes relationship
    notes = relationship("UserNote", back_populates="obituary", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('full_name', 'date_of_death', 'source', name='_name_dod_source_uc'),
    )

class SearchHistory(Base):
    __tablename__ = 'search_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_params = Column(Text)
    result_count = Column(Integer)
    timestamp = Column(String)

class UserNote(Base):
    __tablename__ = 'user_notes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    obituary_id = Column(Integer, ForeignKey('obituaries.id'))
    note = Column(Text)
    tag = Column(String)
    created_at = Column(String)
    
    obituary = relationship("Obituary", back_populates="notes")
