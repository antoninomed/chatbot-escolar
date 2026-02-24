from sqlalchemy import create_engine
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    print("Postgres OK")