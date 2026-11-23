"""SQLite layer: schema, auto-initialisation and tiny parameterized-query helpers."""
import os, sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "newshub.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  feed_url TEXT NOT NULL UNIQUE,
  category_hint TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'pending',
  last_error TEXT,
  last_fetched TEXT
);
CREATE TABLE IF NOT EXISTS articles(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  title_hash TEXT NOT NULL UNIQUE,      -- duplicate guard (same story, different feed)
  url TEXT NOT NULL UNIQUE,             -- duplicate guard (same link)
  description TEXT, summary TEXT, image TEXT,
  category TEXT NOT NULL, subcategory TEXT, keywords TEXT,
  published TEXT NOT NULL, fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_art_pub ON articles(published DESC);
CREATE INDEX IF NOT EXISTS idx_art_cat ON articles(category);
CREATE TABLE IF NOT EXISTS bookmarks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULT_SOURCES = [
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "World"),
    ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml", "Technology"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", "Business"),
    ("BBC Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "Science"),
    ("BBC Health", "https://feeds.bbci.co.uk/news/health/rss.xml", "Health"),
    ("BBC Entertainment", "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "Entertainment"),
    ("BBC Politics", "https://feeds.bbci.co.uk/news/politics/rss.xml", "Politics"),
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml", "Sports"),
    ("The Guardian World", "https://www.theguardian.com/world/rss", "World"),
    ("NPR News", "https://feeds.npr.org/1001/rss.xml", "World"),
    ("TechCrunch", "https://techcrunch.com/feed/", "Technology"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "Technology"),
    ("The Hindu National", "https://www.thehindu.com/news/national/feeder/default.rss", "Politics"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "World"),
]

def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def q(sql, args=(), one=False):
    """SELECT helper (always parameterized). Returns dict / list of dicts."""
    c = connect()
    try:
        cur = c.execute(sql, args)
        if one:
            r = cur.fetchone()
            return dict(r) if r else None
        return [dict(r) for r in cur.fetchall()]
    finally:
        c.close()

def run(sql, args=()):
    """INSERT/UPDATE/DELETE helper. Returns (lastrowid, rowcount)."""
    c = connect()
    try:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid, cur.rowcount
    finally:
        c.close()

def init_db():
    c = connect()
    try:
        c.executescript(SCHEMA)
        if c.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0:
            c.executemany("INSERT OR IGNORE INTO sources(name,feed_url,category_hint) VALUES(?,?,?)", DEFAULT_SOURCES)
        c.commit()
    finally:
        c.close()
