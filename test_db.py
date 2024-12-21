from sqlalchemy import create_engine, text

# Database configuration
DATABASE_URI = 'postgresql://postgres:hanoihue@localhost:5432/synergy'

def test_db_connection():
    try:
        # Connect to the database
        engine = create_engine(DATABASE_URI)
        with engine.connect() as connection:
            print("Database connection successful!")

            # Query to insert a new row into the 'users' table
            new_user_query = text("""
                INSERT INTO users (username, password_hash, last_active, verification_status)
                VALUES (:username, :password_hash, NOW(), :verification_status)
            """)
            new_user_data = {
                "username": "user22",
                "password_hash": "$2b$12$examplehashedpasswordvalue",
                "verification_status": False
            }

            # Execute the insert query
            connection.execute(new_user_query, new_user_data)
            print("New user 'user22' added successfully!")

            # Query to fetch all rows from the 'users' table
            fetch_all_query = text("SELECT * FROM users")
            result = connection.execute(fetch_all_query)

            # Print each row
            print("Rows in the 'users' table:")
            for row in result:
                print(row)
    except Exception as e:
        print(f"Database connection failed: {e}")

if __name__ == "__main__":
    test_db_connection()
