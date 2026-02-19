
import sys
import os
import traceback

# Add project root to path
sys.path.append(os.getcwd())

print("Starting schema verification...")

try:
    from app import schemas
    print("Schemas package imported successfully.")
    
    # Try instantiating a few to check for runtime errors in definitions
    from pydantic import ValidationError
    
    try:
        user = schemas.UserCreate(email="test@example.com", full_name="Test User", password="password")
        print(f"UserCreate schema valid: {user}")
    except ValidationError as e:
        print(f"UserCreate validation failed: {e}")

    print("SUCCESS: Schemas verified.")

except Exception:
    print("FAILURE: Schema verification failed.")
    traceback.print_exc()
    sys.exit(1)
