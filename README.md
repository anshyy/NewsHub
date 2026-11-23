# NewsHub – Smart News Aggregator and Categorizer (DAA project)

Flask + SQLite + feedparser + vanilla JS + Chart.js. Collects real RSS news, categorizes it automatically and exposes the DAA algorithms through the UI.

## Run on macOS
```bash
cd newshub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```
Open http://127.0.0.1:5000 . On first launch the app creates `instance/newshub.db` and fetches news in the background (about 10–20 s). Use **Refresh news** any time. Internet access is needed for RSS and for the Chart.js CDN.

## Where each algorithm is used
| Algorithm | File | Used by |
|---|---|---|
| Tree (`CategoryTree`) | algorithms.py | Categories page tree, rolled-up counts |
| Trie | algorithms.py | Smart Search suggestions + article lookup |
| Graph (adjacency lists) | algorithms.py | News Network |
| BFS / DFS | algorithms.py | News Network buttons (`/api/traverse`) |
| Text processing | algorithms.py | Every fetched article, keywords, Trie index |
| Keyword categorizer | categorizer.py | Category + sub-category on fetch |
| Extractive summarizer | summarizer.py | Card summaries on fetch |

## Structure
`app.py` routes/APIs · `database.py` SQLite · `news_fetcher.py` RSS · `templates/` · `static/css|js` · `instance/` database.
Duplicates are blocked by UNIQUE `url` and `title_hash`. Unreachable feeds are marked *offline* with the error shown on the Sources page.
