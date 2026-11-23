"""RSS collection: parallel download -> parse -> clean -> categorize -> summarize -> INSERT OR IGNORE
(UNIQUE url/title_hash gives duplicate prevention). Unreachable feeds are recorded, never crash the app."""
import calendar, concurrent.futures as cf, hashlib, re, threading, urllib.request
from datetime import datetime, timezone
import database as D
from algorithms import clean_text, extract_keywords
from categorizer import classify
from summarizer import summarize

UA = {"User-Agent": "Mozilla/5.0 (NewsHub college DAA project)"}
_lock = threading.Lock()
STATE = {"running": False}

def now_iso(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def download(url, timeout=10):
    import feedparser  # imported lazily so the app still boots if it is missing
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return feedparser.parse(r.read())

def find_image(e):
    for m in (e.get("media_thumbnail") or []) + (e.get("media_content") or []):
        if m.get("url") and m.get("medium", "image") != "video" and "video" not in m.get("type", ""):
            return m["url"]
    for l in (e.get("enclosures") or []) + (e.get("links") or []):
        if str(l.get("type", "")).startswith("image") and l.get("href"): return l["href"]
    h = (e.get("summary") or "") + "".join(c.get("value", "") for c in (e.get("content") or []))
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', h)
    return m.group(1) if m else None

def published(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    ts = calendar.timegm(t) if t else datetime.now(timezone.utc).timestamp()
    return datetime.fromtimestamp(min(ts, datetime.now(timezone.utc).timestamp()), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_one(src):
    """Returns (source_id, rows, error). Runs in a worker thread (network + CPU only, no DB writes)."""
    try:
        feed = download(src["feed_url"])
        entries = feed.get("entries") or []
        if not entries:
            raise ValueError(str(feed.get("bozo_exception") or "Feed contains no articles"))
        rows = []
        for e in entries[:40]:
            title, link = clean_text(e.get("title")), (e.get("link") or "").strip()
            if not title or not link.startswith("http"): continue
            desc = clean_text(e.get("summary") or e.get("description"))[:600]
            cat, sub = classify(title, desc, src["category_hint"])
            img = find_image(e)
            rows.append((src["id"], title, hashlib.md5(re.sub(r"\W+", "", title.lower()).encode()).hexdigest(), link, desc,
                         summarize(desc, 2), img if img and img.startswith("http") else None, cat, sub,
                         ",".join(extract_keywords(title, desc)), published(e), now_iso()))
        return src["id"], rows, None
    except Exception as ex:
        return src["id"], [], (str(ex) or ex.__class__.__name__)[:200]

def refresh(source_id=None):
    """Fetch all active sources (or one). Returns a summary dict."""
    if not _lock.acquire(blocking=False):
        return {"busy": True, "new": 0, "failed": []}
    STATE["running"] = True
    try:
        srcs = D.q("SELECT * FROM sources WHERE id=?", (source_id,)) if source_id else D.q("SELECT * FROM sources WHERE active=1")
        with cf.ThreadPoolExecutor(8) as ex:
            results = list(ex.map(fetch_one, srcs))
        names, new, failed = {s["id"]: s["name"] for s in srcs}, 0, []
        con = D.connect()
        try:
            for sid, rows, err in results:
                for r in rows:
                    new += con.execute("INSERT OR IGNORE INTO articles(source_id,title,title_hash,url,description,summary,image,category,subcategory,keywords,published,fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", r).rowcount
                con.execute("UPDATE sources SET status=?, last_error=?, last_fetched=? WHERE id=?",
                            ("offline" if err else "online", err, now_iso(), sid))
                if err: failed.append({"name": names[sid], "error": err})
            con.commit()
        finally:
            con.close()
        return {"busy": False, "new": new, "sources": len(srcs), "failed": failed}
    finally:
        STATE["running"] = False
        _lock.release()
