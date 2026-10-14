from sqlalchemy import text

from app.database.session import engine


def test_connection():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_user")
        )

        database_name, username = result.one()

        print(f"Database: {database_name}")
        print(f"Connected user: {username}")
        print("PostgreSQL connection successful!")


if __name__ == "__main__":
    test_connection()