
from app.database.connect_db import Base, engine

# Nạp toàn bộ model để đăng ký metadata
import app.models

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Da tao cac bang database thanh cong!")

if __name__ == "__main__":
    create_tables()
