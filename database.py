import sqlite3
import re

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

def insert(url, title, initial_price, sentiment_rating, price_rating, average_rating, median, lower_bound, upper_bound):
    con = sqlite3.connect('product_database.db')
    cur = con.cursor()

    # Find the ID of the product
    market_id = (re.search(r"\/item\/([0-9]*)", url)).group(1)

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