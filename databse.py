import sqlite3

class Database:
    def __init__(self, db_path="favorites.db"):
        """Initializes the database connection and ensures tables exist."""
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_table()
        self.ensure_columns_exist()

    def create_table(self):
        """Creates the necessary tables if they do not exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER,
                source TEXT,
                token TEXT,
                PRIMARY KEY (user_id, source, token)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                user_id INTEGER,
                source TEXT,
                token TEXT,
                price REAL,
                PRIMARY KEY (user_id, source, token)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                active_source TEXT DEFAULT 'Binance',
                last_message_id INTEGER DEFAULT NULL
            )
        """)
        self.conn.commit()

    def ensure_columns_exist(self):
        """Adds necessary columns if they are missing."""
        self.cursor.execute("PRAGMA table_info(settings)")
        columns = [row[1] for row in self.cursor.fetchall()]
        
        if "last_message_id" not in columns:
            self.cursor.execute("ALTER TABLE settings ADD COLUMN last_message_id INTEGER DEFAULT NULL")
            self.conn.commit()

    def update_last_source_message(self, user_id, message_id):
        """Updates the last message ID containing sources for a user."""
        self.cursor.execute("""
            INSERT INTO settings (user_id, last_message_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_message_id = excluded.last_message_id
        """, (user_id, message_id))
        self.conn.commit()

    def get_last_source_message(self, user_id):
        """Retrieves the `message_id` of the last message containing sources."""
        self.cursor.execute("SELECT last_message_id FROM settings WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_all_users(self):
        """Retrieves a list of all users who have favorite tokens."""
        self.cursor.execute("SELECT DISTINCT user_id FROM favorites")
        return [row[0] for row in self.cursor.fetchall()]

    def get_last_price(self, user_id, token, source):
        """Retrieves the last stored price for a user's token from a specific source."""
        self.cursor.execute("SELECT price FROM prices WHERE user_id = ? AND token = ? AND source = ?", 
                            (user_id, token, source))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def update_last_price(self, user_id, token, price, source):
        """Updates the last recorded price of a token for a user in the database."""
        self.cursor.execute("""
            INSERT INTO prices (user_id, source, token, price) 
            VALUES (?, ?, ?, ?) 
            ON CONFLICT(user_id, source, token) DO UPDATE SET price = excluded.price
        """, (user_id, source, token, price))
        self.conn.commit()

    def get_active_source(self, user_id):
        """Retrieves the active data source for a user (defaults to Binance)."""
        self.cursor.execute("SELECT active_source FROM settings WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else "Binance"

    def update_active_source(self, user_id, source):
        """Updates the active data source for a user."""
        self.cursor.execute("""
            INSERT INTO settings (user_id, active_source) 
            VALUES (?, ?) 
            ON CONFLICT(user_id) DO UPDATE SET active_source = excluded.active_source
        """, (user_id, source))
        self.conn.commit()

    def get_favorites(self, user_id, source):
        """Retrieves a list of favorite tokens for a user from a specific source."""
        self.cursor.execute("SELECT token FROM favorites WHERE user_id = ? AND source = ?", (user_id, source))
        return [row[0] for row in self.cursor.fetchall()]

    def add_favorite(self, user_id, token, source):
        """Adds a token to the user's favorites list for a specific source."""
        self.cursor.execute("""
            INSERT INTO favorites (user_id, source, token) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, source, token) DO NOTHING
        """, (user_id, source, token))
        self.conn.commit()

    def remove_favorite(self, user_id, token, source):
        """Removes a token from the user's favorites list."""
        self.cursor.execute("DELETE FROM favorites WHERE user_id = ? AND source = ? AND token = ?", 
                            (user_id, source, token))
        self.conn.commit()

if __name__ == "__main__":
    db = Database()
    print("Successfully initialized!")