import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# retry logic to wait for Postgres readiness
retries = 5
for i in range(retries):
    try:
        engine = create_engine(DATABASE_URL)
        # test connection
        conn = engine.connect()
        conn.close()
        break
    except Exception:
        if i < retries - 1:
            time.sleep(2)
        else:
            raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()