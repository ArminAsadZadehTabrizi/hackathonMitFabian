"""
Datenbank-Service für SQLite mit SQLModel
Integriert von Partner 2's Backend
"""
from sqlmodel import SQLModel, Session, create_engine
from typing import Generator

# SQLite database URL
DATABASE_URL = "sqlite:///./receipts.db"

# Create engine with check_same_thread=False for SQLite
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    connect_args={"check_same_thread": False}
)


def init_db() -> None:
    """Initialize database and create all tables."""
    SQLModel.metadata.create_all(engine)
    print("✅ Datenbank initialisiert")


def get_session() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Usage in FastAPI:
        @app.get("/example")
        def example(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session

