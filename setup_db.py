import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Users table
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        mobile TEXT NOT NULL,
        department TEXT NOT NULL,
        employee_id TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
''')

# Bookings table
c.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        seat_no TEXT NOT NULL,
        status TEXT CHECK(status IN ('pending', 'approved', 'rejected', 'blocked', 'expired')) DEFAULT 'pending',
        shift TEXT,
        booking_date DATE,
        timing TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
''')

conn.close()
print("Database and tables created successfully.")
