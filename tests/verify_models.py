
import sys
import os
import traceback

# Add project root to path
sys.path.append(os.getcwd())

print("Starting verification...")

try:
    from app.core import config
    print("Config imported.")
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import configure_mappers
    
    # Import Base last (and all models)
    from app.db.base import Base
    print("Base imported. Models loaded.")

    print("Checking ORM mappings...")
    configure_mappers()
    print("SUCCESS: ORM mappings are valid.")
    
    # Optional: We could try to compile DDL to print it, but it requires a postgres dialect instance
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable
    
    # Just defining the engine doesn't mean we can connect, but we can mock it
    # But strictly speaking, configure_mappers() covers most "invalid model definition" errors (bad relationships, etc).
    
except Exception:
    print("FAILURE: Model verification failed.")
    traceback.print_exc()
    sys.exit(1)
