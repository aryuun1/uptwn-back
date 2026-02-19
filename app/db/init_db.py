
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database():
    """Create database if it doesn't exist."""
    try:
        # Connect to default 'postgres' database to check/create target DB
        con = psycopg2.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            dbname="postgres"
        )
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        
        # Check if DB exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{settings.POSTGRES_DB}'")
        exists = cur.fetchone()
        
        if not exists:
            logger.info(f"Database {settings.POSTGRES_DB} does not exist. Creating...")
            cur.execute(f"CREATE DATABASE {settings.POSTGRES_DB}")
            logger.info(f"Database {settings.POSTGRES_DB} created successfully.")
        else:
            logger.info(f"Database {settings.POSTGRES_DB} already exists.")
            
        cur.close()
        con.close()
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        # Proceeding anyway, maybe it exists or connection params are for the target DB directly

if __name__ == "__main__":
    create_database()
