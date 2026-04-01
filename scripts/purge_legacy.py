from sqlmodel import Session, select, delete
from init_db import Mill, engine

def purge_legacy_mills():
    with Session(engine) as session:
        # Delete any mill ID that doesn't start with '37'
        statement = delete(Mill).where(Mill.id.notlike("37%"))
        session.exec(statement)
        session.commit()
    print("🧹 Legacy/Internal IDs purged. Only hardware-verified meters remain.")

if __name__ == "__main__":
    purge_legacy_mills()