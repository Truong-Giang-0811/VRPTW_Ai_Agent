
from sqlalchemy import text
from app.database.connect_db import engine

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT DATABASE()")
        )
        print("Ket noi MySQL thanh cong!")
        print("Database:", result.scalar())

except Exception as e:
    print("Ket noi that bai!")
    print("Loi:", e)
