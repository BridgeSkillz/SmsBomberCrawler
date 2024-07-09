from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker, declarative_base, Session

Base = declarative_base()

class SearchQuery(Base):
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=False)
    query = Column(String, unique=True, nullable=False)
    utilized = Column(Boolean, default=False, nullable=False)
    comment = Column(String, nullable=True)
    created_date = Column(DateTime(timezone=True), default=func.now(), nullable=False)

class SearchEngineResponse(Base):
    __tablename__ = 'searchengineresponse_records'

    id = Column(Integer, primary_key=True, autoincrement=True)

    domain = Column(String, unique=True, nullable=False)

    title = Column(String, nullable=False)
    href = Column(String, nullable=False)
    desc = Column(String, nullable=False)

    visited = Column(Boolean, default=False, nullable=False)

    comment = Column(String, nullable=True)
    created_date = Column(DateTime(timezone=True), default=func.now(), nullable=False)


    def __repr__(self):
        return f"<SearchEngineResponse(id={self.id}, url='{self.href}', visited={self.visited}, created_date={self.created_date})>"
    
class CrawlerDiscovery(Base):
    __tablename__ = 'crawlerdiscovery_records'

    id = Column(Integer, primary_key=True, autoincrement=True)

    domain = Column(String, unique=True, nullable=False)

    visited = Column(Boolean, default=False, nullable=False)

    comment = Column(String, nullable=True)
    created_date = Column(DateTime(timezone=True), default=func.now(), nullable=False)

class SitesWithTelField(Base):
    __tablename__ = 'siteswithtelfield_records'

    id = Column(Integer, primary_key=True, autoincrement=True)

    domain = Column(String, unique=True, nullable=False)

    validated = Column(Boolean, default=False, nullable=False)

    comment = Column(String, nullable=True)
    created_date = Column(DateTime(timezone=True), default=func.now(), nullable=False)

def get_engine(connection_string='sqlite:///mydatabase.sqlite'):
    return create_engine(connection_string, echo=False)

def get_session(engine):
    SessionClass = sessionmaker(bind=engine)
    return SessionClass()

if __name__ == "__main__":
    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
        print("Database setup completed successfully.")
    except Exception as e:
        print(f"Error setting up the database: {e}")
