"""Core DAA data structures & algorithms used by NewsHub.
Tree (categories) | Trie (search index) | Graph + BFS/DFS (news network) | text processing."""
import html, re, time
from collections import Counter, deque

# ---------------------------------------------------------------- TEXT PROCESSING
STOP_WORDS = set("""a about above after again against all also am amid an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had has have having he her here
hers him his how i if in into is it its just me more most my no nor not now of off on once only or other our out over own said
says same she should so some such than that the their them then there these they this those through to too under until up us
very was we were what when where which while who whom why will with would you your new one two three like get got make made may
might many much year years say told including per via according still back first last next since week day today bbc news read
video live watch photos picture image getty reuters ap""".split())

def clean_text(t):
    """Strip HTML tags/entities and collapse whitespace. O(n)."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    return re.sub(r"\s+", " ", t).strip()

def tokenize(t):
    """Lower-case -> regex tokenization -> stop-word removal (hash-set lookup). O(n)."""
    out = []
    for w in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", clean_text(t).lower()):
        w = re.sub(r"'s$", "", w).replace("'", "")
        if len(w) >= 2 and w not in STOP_WORDS and not w.isdigit():
            out.append(w)
    return out

def extract_keywords(title, desc, k=8):
    """Term-frequency keyword extraction; title words weigh 3x. O(n + m log m)."""
    c = Counter()
    for w in tokenize(title): c[w] += 3
    for w in tokenize(desc): c[w] += 1
    return [w for w, _ in c.most_common(k)]

# ---------------------------------------------------------------- TREE
class TreeNode:
    __slots__ = ("name", "children", "count", "total")
    def __init__(self, name):
        self.name, self.children, self.count, self.total = name, {}, 0, 0

class CategoryTree:
    """General tree: root -> category -> subcategory. Used by the Categories page."""
    def __init__(self, hierarchy, root="News"):
        self.root = TreeNode(root)
        for cat, subs in hierarchy.items():
            node = self.root.children.setdefault(cat, TreeNode(cat))
            for s in list(subs) + ["General"]:
                node.children.setdefault(s, TreeNode(s))

    def add(self, cat, sub, n=1):
        """Insert counts at the leaf. O(1) via dict lookups."""
        node = self.root.children.get(cat)
        if node:
            (node.children.get(sub) or node.children["General"]).count += n

    def aggregate(self, node=None):
        """Post-order DFS that rolls leaf counts up to parents. O(N) for N nodes."""
        node = node or self.root
        node.total = node.count + sum(self.aggregate(c) for c in node.children.values())
        return node.total

    def to_dict(self, node=None):
        node = node or self.root
        return {"name": node.name, "count": node.total,
                "children": [self.to_dict(c) for c in node.children.values()]}

# ---------------------------------------------------------------- TRIE
class TrieNode:
    __slots__ = ("ch", "ids", "end")
    def __init__(self):
        self.ch, self.ids, self.end = {}, set(), False

class Trie:
    """Prefix tree; each word node stores the ids of articles containing it (inverted index)."""
    def __init__(self):
        self.root, self.words = TrieNode(), 0

    def insert(self, word, doc_id):
        """O(L) for word length L."""
        n = self.root
        for c in word:
            n = n.ch.setdefault(c, TrieNode())
        if not n.end:
            n.end = True; self.words += 1
        n.ids.add(doc_id)

    def _find(self, prefix):
        n = self.root
        for c in prefix:
            n = n.ch.get(c)
            if n is None: return None
        return n

    def suggest(self, prefix, k=8):
        """Top-k completions by document frequency. O(P + S) for prefix length P and S nodes in subtree."""
        n = self._find(prefix)
        if n is None: return []
        out, stack = [], [(n, prefix)]
        while stack:
            node, w = stack.pop()
            if node.end: out.append((w, len(node.ids)))
            stack.extend((c, w + ch) for ch, c in node.ch.items())
        out.sort(key=lambda x: (-x[1], x[0]))
        return out[:k]

    def doc_ids(self, prefix):
        """Union of article ids under a prefix. O(P + S)."""
        n = self._find(prefix)
        ids, stack = set(), ([n] if n else [])
        while stack:
            node = stack.pop()
            ids |= node.ids
            stack.extend(node.ch.values())
        return ids

# ---------------------------------------------------------------- GRAPH
class Graph:
    """Undirected graph stored as adjacency lists: {node_id: [neighbour_id, ...]}."""
    def __init__(self):
        self.adj, self.nodes, self.edges, self._seen = {}, {}, [], set()

    def add_node(self, nid, **attrs):
        if nid not in self.nodes:
            self.nodes[nid] = attrs; self.adj[nid] = []

    def add_edge(self, u, v, **attrs):
        key = frozenset((u, v))
        if u == v or key in self._seen: return
        self._seen.add(key)
        self.adj[u].append(v); self.adj[v].append(u)
        self.edges.append({"source": u, "target": v, **attrs})

    def finish(self):
        for l in self.adj.values(): l.sort()

    def _result(self, algo, order, parent, depth, t0):
        V, E = len(self.nodes), len(self.edges)
        return {"algo": algo, "order": order, "parent": parent, "depth": depth, "visited": len(order),
                "V": V, "E": E, "time_ms": round((time.perf_counter() - t0) * 1000, 3),
                "complexity": f"Time O(V + E) = O({V} + {E}) = {V + E} steps | Space O(V) = O({V})"}

    def bfs(self, start):
        """Breadth-first search with a FIFO queue; finds shortest hop distance. O(V + E)."""
        t0 = time.perf_counter()
        seen, dq, order = {start}, deque([start]), []
        parent, depth = {start: None}, {start: 0}
        while dq:
            u = dq.popleft(); order.append(u)
            for v in self.adj[u]:
                if v not in seen:
                    seen.add(v); parent[v] = u; depth[v] = depth[u] + 1; dq.append(v)
        return self._result("bfs", order, parent, depth, t0)

    def dfs(self, start):
        """Depth-first search with an explicit LIFO stack (no recursion limit). O(V + E)."""
        t0 = time.perf_counter()
        seen, stack, order = set(), [start], []
        parent, depth = {start: None}, {start: 0}
        while stack:
            u = stack.pop()
            if u in seen: continue
            seen.add(u); order.append(u)
            for v in reversed(self.adj[u]):
                if v not in seen:
                    parent[v] = u; depth[v] = depth[u] + 1; stack.append(v)
        parent = {k: v for k, v in parent.items() if k in seen}
        return self._result("dfs", order, parent, {k: depth[k] for k in seen}, t0)

    def to_json(self):
        return {"nodes": [{"id": i, "degree": len(self.adj[i]), **a} for i, a in self.nodes.items()],
                "edges": self.edges, "V": len(self.nodes), "E": len(self.edges)}

def build_article_graph(articles, max_related=4):
    """Nodes: articles + sources. Edges: article-source, and article-article when they share >=2
    keywords or share a category plus a keyword. Each article keeps its strongest `max_related`
    links so the graph stays readable. Pair scan is O(n^2 * k)."""
    g, kw = Graph(), {}
    for a in articles:
        aid, sid = f"a{a['id']}", f"s{a['source_id']}"
        g.add_node(sid, label=a["source"], type="source")
        g.add_node(aid, label=a["title"], type="article", category=a["category"], url=a["url"], source=a["source"])
        g.add_edge(aid, sid, kind="source", weight=1)
        kw[aid] = set(a["keywords"])
    ids, cand = list(kw), {i: [] for i in kw}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            u, v = ids[i], ids[j]
            shared = kw[u] & kw[v]
            if not shared: continue
            same = g.nodes[u]["category"] == g.nodes[v]["category"]
            if len(shared) >= 2 or same:
                score = len(shared) * 2 + same
                cand[u].append((score, v, shared)); cand[v].append((score, u, shared))
    for u in ids:
        for _, v, shared in sorted(cand[u], key=lambda x: -x[0])[:max_related]:
            g.add_edge(u, v, kind="related", weight=len(shared), shared=sorted(shared))
    g.finish()
    return g
