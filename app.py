"""NewsHub - Smart News Aggregator and Categorizer (Flask). Run: python3 app.py"""
import platform, sqlite3, threading, time
from collections import Counter
from datetime import datetime, timedelta, timezone
import flask
from flask import Flask, jsonify, render_template, request
import database as D
import news_fetcher as NF
from algorithms import CategoryTree, Trie, build_article_graph, tokenize
from categorizer import CATEGORY_COLORS, HIERARCHY

app = Flask(__name__)
PAGES = {"dashboard": ("/", "Dashboard", "grid"), "news": ("/news", "All News", "news"),
         "categories": ("/categories", "Categories", "layers"), "search": ("/search", "Smart Search", "search"),
         "network": ("/network", "News Network", "share"), "bookmarks": ("/bookmarks", "Bookmarks", "bookmark"),
         "analytics": ("/analytics", "Analytics", "chart"), "sources": ("/sources", "Sources", "rss"),
         "settings": ("/settings", "Settings", "sliders")}

def iso(dt): return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
def counts():
    return D.q("SELECT (SELECT COUNT(*) FROM articles) articles,(SELECT COUNT(*) FROM sources) sources,"
               "(SELECT COUNT(*) FROM bookmarks) bookmarks", one=True)

@app.context_processor
def inject(): return {"NAV": PAGES, "CATS": CATEGORY_COLORS}

def _page(name):
    def view():
        extra = {}
        if name == "settings":
            extra["info"] = {"Python": platform.python_version(), "Flask": flask.__version__, "SQLite": sqlite3.sqlite_version,
                             "Database": D.DB_PATH, **{k.title(): v for k, v in counts().items()}}
        return render_template(f"{name}.html", page=name, title=PAGES[name][1], **extra)
    app.add_url_rule(PAGES[name][0], "page_" + name, view)
for _n in PAGES: _page(_n)

# ------------------------------------------------------------------ articles
SEL = ("SELECT a.id,a.title,a.url,a.description,a.summary,a.image,a.category,a.subcategory,a.keywords,a.published,"
       "s.id source_id,s.name source,(b.id IS NOT NULL) bookmarked FROM articles a JOIN sources s ON s.id=a.source_id "
       "LEFT JOIN bookmarks b ON b.article_id=a.id ")
FROM = "FROM articles a JOIN sources s ON s.id=a.source_id LEFT JOIN bookmarks b ON b.article_id=a.id "
SORTS = {"newest": "a.published DESC", "oldest": "a.published ASC", "title": "a.title COLLATE NOCASE ASC",
         "source": "s.name COLLATE NOCASE ASC, a.published DESC"}

def fix(r):
    r["bookmarked"] = bool(r["bookmarked"]); r["keywords"] = r["keywords"].split(",") if r["keywords"] else []
    return r

def latest(limit, offset=0):
    return [fix(r) for r in D.q(SEL + "ORDER BY a.published DESC LIMIT ? OFFSET ?", (limit, offset))]

@app.get("/api/articles")
def articles():
    g, w, args = request.args.get, [], []
    if g("q"):
        like = "%" + g("q").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        w.append("(a.title LIKE ? ESCAPE '\\' OR a.description LIKE ? ESCAPE '\\')"); args += [like, like]
    for key, col in (("category", "a.category"), ("subcategory", "a.subcategory"), ("source", "s.id")):
        if g(key): w.append(f"{col}=?"); args.append(g(key))
    if g("bookmarked"): w.append("b.id IS NOT NULL")
    where = ("WHERE " + " AND ".join(w) + " ") if w else ""
    per = min(max(int(g("per_page", 12)), 1), 60); page = max(int(g("page", 1)), 1)
    total = D.q("SELECT COUNT(*) c " + FROM + where, args, one=True)["c"]
    rows = D.q(SEL + where + "ORDER BY " + SORTS.get(g("sort"), SORTS["newest"]) + " LIMIT ? OFFSET ?", args + [per, (page - 1) * per])
    return jsonify(items=[fix(r) for r in rows], total=total, page=page, pages=max(1, -(-total // per)))

@app.route("/api/bookmarks/<int:aid>", methods=["POST", "DELETE"])
def bookmark(aid):
    if request.method == "POST":
        if not D.q("SELECT 1 FROM articles WHERE id=?", (aid,), one=True): return jsonify(error="Article not found"), 404
        D.run("INSERT OR IGNORE INTO bookmarks(article_id) VALUES(?)", (aid,))
    else:
        D.run("DELETE FROM bookmarks WHERE article_id=?", (aid,))
    return jsonify(ok=True, bookmarked=request.method == "POST")

# ------------------------------------------------------------------ dashboard / categories
@app.get("/api/stats")
def stats():
    now = datetime.now(timezone.utc); t24, t48 = iso(now - timedelta(hours=24)), iso(now - timedelta(hours=48))
    cur = {r["category"]: r["c"] for r in D.q("SELECT category,COUNT(*) c FROM articles WHERE published>=? GROUP BY category", (t24,))}
    prev = {r["category"]: r["c"] for r in D.q("SELECT category,COUNT(*) c FROM articles WHERE published>=? AND published<? GROUP BY category", (t48, t24))}
    dist = D.q("SELECT category name,COUNT(*) count FROM articles GROUP BY category ORDER BY count DESC")
    trending = sorted([{"name": c, "count": cur.get(c, 0), "prev": prev.get(c, 0)} for c in CATEGORY_COLORS], key=lambda x: (-x["count"], x["name"]))[:5]
    srcs = D.q("SELECT s.id,s.name,s.status,COUNT(a.id) count FROM sources s LEFT JOIN articles a ON a.source_id=s.id GROUP BY s.id ORDER BY count DESC LIMIT 6")
    c = counts()
    return jsonify(articles=c["articles"], sources=c["sources"], bookmarks=c["bookmarks"], categories=len(dist),
                   active_sources=D.q("SELECT COUNT(*) c FROM sources WHERE status='online'", one=True)["c"],
                   latest=latest(5), recent=latest(10, 5), trending=trending, top_sources=srcs, distribution=dist)

@app.get("/api/categories")
def categories():
    tree = CategoryTree(HIERARCHY)
    for r in D.q("SELECT category,subcategory,COUNT(*) c FROM articles GROUP BY category,subcategory"):
        tree.add(r["category"], r["subcategory"], r["c"])
    tree.aggregate()
    return jsonify(tree=tree.to_dict(), colors=CATEGORY_COLORS)

# ------------------------------------------------------------------ smart search (Trie)
CACHE = {"trie_stamp": None, "trie": None, "graphs": {}}

def get_trie():
    stamp = D.q("SELECT COUNT(*) c,COALESCE(MAX(id),0) m FROM articles", one=True)
    if CACHE["trie_stamp"] != stamp:
        t = Trie()
        for a in D.q("SELECT id,title,description FROM articles"):
            for w in set(tokenize(a["title"] + " " + (a["description"] or ""))): t.insert(w, a["id"])
        CACHE.update(trie=t, trie_stamp=stamp, graphs={})
    return CACHE["trie"]

@app.get("/api/search")
def search():
    t0, qs = time.perf_counter(), request.args.get("q", "").lower()
    words = [w for w in qs.replace("'", "").split() if w]
    words = ["".join(ch for ch in w if ch.isalnum()) for w in words]; words = [w for w in words if w]
    if not words: return jsonify(suggestions=[], items=[], total=0, time_ms=0)
    trie = get_trie()
    sugg = trie.suggest(words[-1], 8)
    ids = None
    for w in words:  # AND semantics: intersect id-sets of every typed prefix
        s = trie.doc_ids(w); ids = s if ids is None else ids & s
    items = []
    if ids:
        marks = ",".join("?" * min(len(ids), 500))
        items = [fix(r) for r in D.q(SEL + f"WHERE a.id IN ({marks}) ORDER BY a.published DESC LIMIT 30", sorted(ids)[-500:])]
    return jsonify(suggestions=[{"word": w, "count": c} for w, c in sugg], items=items, total=len(ids or ()),
                   time_ms=round((time.perf_counter() - t0) * 1000, 3), vocabulary=trie.words)

# ------------------------------------------------------------------ graph / traversal
def get_graph(limit):
    get_trie()  # refreshes CACHE if the DB changed
    if limit not in CACHE["graphs"]:
        CACHE["graphs"][limit] = build_article_graph(latest(limit))
    return CACHE["graphs"][limit]

def _limit(): return min(max(request.args.get("limit", 50, type=int), 10), 120)

@app.get("/api/graph")
def graph():
    lim = _limit(); d = get_graph(lim).to_json(); d["limit"] = lim
    return jsonify(d)

@app.get("/api/traverse")
def traverse():
    g = get_graph(_limit()); start = request.args.get("start")
    if start not in g.nodes:
        if not g.nodes: return jsonify(error="No articles yet - refresh news first"), 400
        start = max(g.adj, key=lambda n: len(g.adj[n]))
    algo = request.args.get("algo", "bfs")
    return jsonify(start=start, **(g.dfs(start) if algo == "dfs" else g.bfs(start)))

# ------------------------------------------------------------------ analytics
@app.get("/api/analytics")
def analytics():
    kw = Counter(k for r in D.q("SELECT keywords FROM articles WHERE keywords<>''") for k in r["keywords"].split(","))
    day = (datetime.now(timezone.utc) - timedelta(days=13)).strftime("%Y-%m-%d")
    pub = {r["d"]: r["c"] for r in D.q("SELECT substr(published,1,10) d,COUNT(*) c FROM articles WHERE substr(published,1,10)>=? GROUP BY d", (day,))}
    col = {r["d"]: r["c"] for r in D.q("SELECT substr(fetched_at,1,10) d,COUNT(*) c FROM articles WHERE substr(fetched_at,1,10)>=? GROUP BY d", (day,))}
    days = [(datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
    return jsonify(distribution=D.q("SELECT category name,COUNT(*) count FROM articles GROUP BY category ORDER BY count DESC"),
                   sources=D.q("SELECT s.name,s.status,COUNT(a.id) count FROM sources s LEFT JOIN articles a ON a.source_id=s.id GROUP BY s.id ORDER BY count DESC"),
                   trend={"days": days, "published": [pub.get(d, 0) for d in days], "collected": [col.get(d, 0) for d in days]},
                   keywords=[{"word": w, "count": c} for w, c in kw.most_common(15)], colors=CATEGORY_COLORS)

# ------------------------------------------------------------------ sources
SRC_SQL = "SELECT s.*,COUNT(a.id) articles FROM sources s LEFT JOIN articles a ON a.source_id=s.id "

@app.get("/api/sources")
def sources(): return jsonify(D.q(SRC_SQL + "GROUP BY s.id ORDER BY s.name"))

@app.post("/api/sources")
def add_source():
    d = request.get_json(silent=True) or {}
    name, url, hint = (d.get("name") or "").strip(), (d.get("feed_url") or "").strip(), d.get("category_hint") or None
    if not name or not url.startswith(("http://", "https://")): return jsonify(error="Enter a name and a valid http(s) feed URL"), 400
    if hint and hint not in CATEGORY_COLORS: hint = None
    if D.q("SELECT 1 FROM sources WHERE feed_url=?", (url,), one=True): return jsonify(error="This feed is already added"), 409
    sid, _ = D.run("INSERT INTO sources(name,feed_url,category_hint) VALUES(?,?,?)", (name, url, hint))
    res = NF.refresh(sid); row = D.q(SRC_SQL + "WHERE s.id=? GROUP BY s.id", (sid,), one=True)
    if row["status"] == "offline":
        D.run("DELETE FROM sources WHERE id=?", (sid,))
        return jsonify(error="Could not read feed: " + (row["last_error"] or "unknown error")), 400
    return jsonify(source=row, new=res["new"]), 201

@app.patch("/api/sources/<int:sid>")
def toggle_source(sid):
    D.run("UPDATE sources SET active=? WHERE id=?", (1 if (request.get_json(silent=True) or {}).get("active") else 0, sid))
    return jsonify(ok=True)

@app.delete("/api/sources/<int:sid>")
def delete_source(sid):
    D.run("DELETE FROM sources WHERE id=?", (sid,)); return jsonify(ok=True)

@app.post("/api/sources/<int:sid>/refresh")
def refresh_one(sid): return jsonify(NF.refresh(sid))

@app.post("/api/refresh")
def refresh_all(): return jsonify(NF.refresh())

@app.get("/api/status")
def status(): return jsonify(running=NF.STATE["running"], **counts())

if __name__ == "__main__":
    D.init_db()
    if counts()["articles"] == 0:  # first launch: collect news in the background
        threading.Thread(target=NF.refresh, daemon=True).start()
    print("NewsHub running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
