import sqlite3

def initialize():
    con = sqlite3.connect('product_database.db')
    con.execute("PRAGMA foreign_keys = 2")
    cur = con.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS products
    (id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    initialPrice INTEGER NOT NULL)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS ratings
    (id TEXT NOT NULL,
    sentimentRating REAL PRIMARY KEY,
    priceRating REAL NOT NULL,
    averageRating REAL NOT NULL,
    FOREIGN KEY (id) REFERENCES products (id))''')

    cur.execute('''CREATE TABLE IF NOT EXISTS similar
    (id TEXT NOT NULL,
    median REAL PRIMARY KEY,
    lowerBound REAL NOT NULL,
    upperBound REAL NOT NULL,
    FOREIGN KEY (id) REFERENCES products (id))''')

    con.commit()

def insert(market_id, title, initial_price, sentiment_rating, price_rating, average_rating, median, lower_bound, upper_bound):
    con = sqlite3.connect('product_database.db')
    cur = con.cursor()

    try:
        # Insert the product into the database
        cur.execute("INSERT INTO products VALUES (?, ?, ?)", (market_id, title, initial_price))
        # Insert the rating into the database
        cur.execute("INSERT INTO ratings VALUES (?, ?, ?, ?)", (market_id, sentiment_rating, price_rating, average_rating))
        # Insert the similar products into the database
        cur.execute("INSERT INTO similar VALUES (?, ?, ?, ?)", (market_id, median, lower_bound, upper_bound))
        con.commit()
    except sqlite3.IntegrityError:
        # If the product already exists, do nothing
        pass

def retrieve(market_id):
    con = sqlite3.connect('product_database.db')
    cur = con.cursor()
    
    try:
        # Retrieve all the products from the database
        cur.execute("SELECT id, title, initialPrice, sentimentRating, priceRating, averageRating, median, lowerBound, upperBound FROM(SELECT * FROM products p JOIN ratings r on p.id = r.id JOIN similar s on s.id = p.id) AS t WHERE id = ?", (market_id,))
        records = cur.fetchone()
        assert len(records) == 9 

        # If the product exists, return the product
        return records
    except TypeError:
        return False