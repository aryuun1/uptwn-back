from sqlalchemy import text
from app.db.session import engine

def fix_venue_types():
    with engine.connect() as connection:
        # Check current values
        result = connection.execute(text("SELECT DISTINCT type FROM venues"))
        print("Current types:", [row[0] for row in result])

        # Update values
        # Mapping: theater -> Cinema, restaurant -> Restaurant, event_hall -> Hall, outdoor -> Outdoor
        # Note: Enum in Python is strict, but in DB it's just a string (unless using Postgres ENUM type, but SAEnum usually maps to VARCHAR if not using remote Enum)
        # However, if I used SAEnum(VenueType), SQLAlchemy might expect the exact string.
        # Let's normalize to the Enum values.
        
        updates = [
            ("Cinema", "CINEMA"),
            ("Restaurant", "RESTAURANT"),
            ("Hall", "HALL"),
            ("Outdoor", "OUTDOOR"),
            ("Stadium", "STADIUM"),
            # Legacy mixed case cleanup just in case
            ("theater", "CINEMA"),
            ("event_hall", "HALL"),
        ]
        
        for old, new in updates:
            connection.execute(
                text("UPDATE venues SET type = :new WHERE type = :old"),
                {"new": new, "old": old}
            )
            
        connection.commit()
        print("Updated venue types.")
        
        # Verify
        result = connection.execute(text("SELECT DISTINCT type FROM venues"))
        print("New types:", [row[0] for row in result])

    # Now try ORM
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        from app.models.venue import Venue
        v = db.query(Venue).first()
        print(f"ORM loaded venue: {v.name if v else 'None'} Type: {v.type if v else 'None'}")
    except Exception as e:
        print(f"ORM Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_venue_types()
