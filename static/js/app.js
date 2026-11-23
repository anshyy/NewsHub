(() => {
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const CATS = window.CATS, PAGE = document.body.dataset.page;
let reload = () => {};
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const BM = '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>';
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

async function api(url, opt = {}) {
  if (opt.body && typeof opt.body !== 'string') { opt.body = JSON.stringify(opt.body); opt.headers = {'Content-Type': 'application/json'}; }
  const r = await fetch(url, opt), d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || r.statusText);
  return d;
}
function ago(iso) {
  const s = (Date.now() - new Date(iso)) / 1000;
  if (s < 60) return 'just now'; if (s < 3600) return Math.floor(s / 60) + ' min ago';
  if (s < 86400) return Math.floor(s / 3600) + ' h ago'; if (s < 604800) return Math.floor(s / 86400) + ' d ago';
  return new Date(iso).toLocaleDateString();
}
function toast(msg, type = '') {
  const t = document.createElement('div'); t.className = 'toast ' + type; t.textContent = msg; $('#toasts').append(t); setTimeout(() => t.remove(), 3500);
}
function hl(text, q) {  // highlight words that start with any query word
  const ws = (String(q || '').toLowerCase().match(/[a-z0-9]+/g) || []);
  if (!ws.length) return esc(text);
  const re = new RegExp('(\\b(?:' + ws.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')[a-z0-9]*)', 'gi');
  return String(text).split(re).map((p, i) => i % 2 ? '<mark>' + esc(p) + '</mark>' : esc(p)).join('');
}
const badge = c => `<span class="badge" style="--c:${CATS[c] || '#64748b'}">${esc(c)}</span>`;
const bmBtn = a => `<button class="icon-btn ${a.bookmarked ? 'on' : ''}" data-bm="${a.id}" title="Bookmark" aria-label="Bookmark">${BM}</button>`;
function card(a, q = '') {
  const c = CATS[a.category] || '#64748b', sub = a.subcategory && a.subcategory !== 'General' ? `<span class="sub">${esc(a.subcategory)}</span>` : '';
  return `<article class="news-card" style="--c:${c}">
    ${a.image ? `<div class="thumb"><img src="${esc(a.image)}" loading="lazy" alt="" onerror="this.parentNode.remove()"></div>` : ''}
    <div class="nc-body"><div class="nc-top">${badge(a.category)}${sub}</div>
    <h3><a href="${esc(a.url)}" target="_blank" rel="noopener">${hl(a.title, q)}</a></h3>
    <p>${hl(a.summary || a.description || '', q)}</p>
    <div class="nc-foot"><span>${esc(a.source)}, ${ago(a.published)}</span>
    <span class="acts"><a class="btn sm ghost" href="${esc(a.url)}" target="_blank" rel="noopener">Read original</a>${bmBtn(a)}</span></div></div></article>`;
}
const EMPTY = '<div class="empty">No articles found. Use “Refresh news” to collect the latest stories, or change your filters.</div>';
function chart(id, cfg) {
  const el = $('#' + id); if (!el) return;
  if (!window.Chart) { el.parentNode.innerHTML = '<div class="empty">Chart.js could not load (check your internet connection).</div>'; return; }
  Chart.getChart(el)?.destroy();
  Chart.defaults.color = css('--muted'); Chart.defaults.borderColor = css('--border'); Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
  new Chart(el, cfg);
}

/* ---------- shell: theme, sidebar, refresh, bookmarks ---------- */
const setTheme = t => { document.documentElement.dataset.theme = t; localStorage.setItem('theme', t); $$('[data-theme-set]').forEach(b => b.classList.toggle('on-theme', b.dataset.themeSet === t)); if (PAGE !== 'settings') reload(); else window.dispatchEvent(new Event('themechange')); };
$('#themeBtn').onclick = () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
$$('[data-theme-set]').forEach(b => { b.onclick = () => setTheme(b.dataset.themeSet); b.classList.toggle('on-theme', b.dataset.themeSet === document.documentElement.dataset.theme); });
$('#collapseBtn').onclick = () => { document.documentElement.classList.remove('pre-collapsed'); const c = document.body.classList.toggle('collapsed'); localStorage.setItem('collapsed', c ? 1 : 0); };
if (localStorage.getItem('collapsed') === '1') document.body.classList.add('collapsed');
$('#menuBtn').onclick = () => document.body.classList.toggle('open'); $('#scrim').onclick = () => document.body.classList.remove('open');
$('#refreshBtn').onclick = async e => {
  const b = e.currentTarget; b.disabled = true; b.classList.add('spin'); toast('Fetching latest news…');
  try {
    const r = await api('/api/refresh', {method: 'POST'});
    toast(r.busy ? 'A refresh is already running' : `${r.new} new articles collected` + (r.failed.length ? `; ${r.failed.length} feed(s) unavailable` : ''), r.failed?.length ? 'err' : '');
    reload();
  } catch (err) { toast(err.message, 'err'); } finally { b.disabled = false; b.classList.remove('spin'); }
};
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-bm]'); if (!b) return;
  const id = b.dataset.bm, on = !b.classList.contains('on');
  try {
    await api('/api/bookmarks/' + id, {method: on ? 'POST' : 'DELETE'});
    $$(`[data-bm="${id}"]`).forEach(x => x.classList.toggle('on', on));
    toast(on ? 'Article bookmarked' : 'Bookmark removed');
    if (!on && PAGE === 'bookmarks') reload();
  } catch (err) { toast(err.message, 'err'); }
});
const debounce = (f, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => f(...a), ms); }; };

/* ---------- dashboard ---------- */
function initDashboard() {
  reload = async () => {
    const d = await api('/api/stats');
    $('#banner').hidden = d.articles > 0;
    if (!d.articles) { const t = setInterval(async () => { const s = await api('/api/status'); if (!s.running && s.articles > 0) { clearInterval(t); reload(); } }, 3000); }
    const st = [['Total articles', d.articles, 'collected from RSS', '#0D9488'], ['Sources', d.sources, d.active_sources + ' online', '#172554'], ['Categories', d.categories, 'of 8 have articles', '#F59E0B'], ['Bookmarks', d.bookmarks, 'saved for later', '#8B5CF6']];
    $('#stats').innerHTML = st.map(s => `<div class="stat" style="--c:${s[3]}"><div class="l">${s[0]}</div><div class="v">${s[1]}</div><div class="s">${s[2]}</div></div>`).join('');
    $('#latest').innerHTML = d.latest.map(a => `<div class="lrow">${a.image ? `<img src="${esc(a.image)}" alt="" loading="lazy" onerror="this.remove()">` : ''}<div style="flex:1;min-width:0">${badge(a.category)}<h3><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a></h3><span class="muted">${esc(a.source)}, ${ago(a.published)}</span></div>${bmBtn(a)}</div>`).join('') || '<div class="empty">No articles yet.</div>';
    $('#trending').innerHTML = d.trending.map(t => { const dl = t.count - t.prev; return `<div class="trend"><i class="dot" style="--c:${CATS[t.name]}"></i><b>${t.name}</b><span>${t.count} new</span><span class="${dl >= 0 ? 'up' : 'down'}">${dl >= 0 ? '▲' : '▼'} ${Math.abs(dl)}</span></div>`; }).join('');
    const mx = Math.max(1, ...d.top_sources.map(s => s.count));
    $('#topSources').innerHTML = d.top_sources.map(s => `<tr><td>${esc(s.name)}</td><td><span class="badge ${s.status}">${s.status}</span></td><td><div class="row"><b>${s.count}</b><div class="bar" style="flex:1"><i style="width:${s.count / mx * 100}%"></i></div></div></td></tr>`).join('');
    $('#recent').innerHTML = d.recent.map(a => `<tr><td class="t"><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a></td><td>${badge(a.category)}</td><td>${esc(a.source)}</td><td>${bmBtn(a)}</td></tr>`).join('') || '<tr><td colspan="4" class="muted">No more articles yet.</td></tr>';
    chart('distChart', {type: 'doughnut', data: {labels: d.distribution.map(x => x.name), datasets: [{data: d.distribution.map(x => x.count), backgroundColor: d.distribution.map(x => CATS[x.name]), borderWidth: 0}]}, options: {maintainAspectRatio: false, cutout: '62%', plugins: {legend: {position: 'right', labels: {boxWidth: 10}}}}});
  };
  reload();
}

/* ---------- all news + bookmarks ---------- */
async function initList(bm) {
  const P = new URLSearchParams(location.search), st = {page: 1, sub: P.get('subcategory') || ''}, $q = $('#q'), $c = $('#fCat'), $s = $('#fSrc'), $o = $('#fSort');
  if ($c) { $c.innerHTML += Object.keys(CATS).map(c => `<option>${c}</option>`).join(''); $c.value = P.get('category') || ''; }
  if ($s) { (await api('/api/sources')).forEach(x => $s.insertAdjacentHTML('beforeend', `<option value="${x.id}">${esc(x.name)}</option>`)); $s.value = P.get('source') || ''; }
  $q.value = P.get('q') || '';
  reload = async () => {
    const p = new URLSearchParams({page: st.page, per_page: 12, q: $q.value, sort: $o.value, category: $c?.value || '', source: $s?.value || '', subcategory: st.sub});
    if (bm) p.set('bookmarked', 1);
    const d = await api('/api/articles?' + p);
    $('#list').innerHTML = d.items.map(a => card(a, $q.value)).join('') || (bm ? '<div class="empty">No bookmarks match. Use the bookmark icon on any article to save it.</div>' : EMPTY);
    $('#count').textContent = `${d.total} article${d.total === 1 ? '' : 's'}`;
    if ($('#chips')) $('#chips').innerHTML = st.sub ? `<button class="chip" id="clrSub">Sub-category: ${esc(st.sub)} ✕</button>` : '';
    $('#pager').innerHTML = d.pages > 1 ? `<button class="btn ghost sm" ${d.page <= 1 ? 'disabled' : ''} data-pg="${d.page - 1}">Previous</button><span class="muted">Page ${d.page} of ${d.pages}</span><button class="btn ghost sm" ${d.page >= d.pages ? 'disabled' : ''} data-pg="${d.page + 1}">Next</button>` : '';
  };
  $('#pager').onclick = e => { const b = e.target.closest('[data-pg]'); if (b) { st.page = +b.dataset.pg; reload(); scrollTo({top: 0}); } };
  document.addEventListener('click', e => { if (e.target.id === 'clrSub') { st.sub = ''; st.page = 1; reload(); } });
  $q.oninput = debounce(() => { st.page = 1; reload(); }, 250);
  [$c, $s, $o].forEach(el => el && (el.onchange = () => { st.page = 1; reload(); }));
  reload();
}

/* ---------- categories (tree) ---------- */
async function initCategories() {
  reload = async () => {
    const d = await api('/api/categories'), cats = d.tree.children;
    $('#catCards').innerHTML = cats.map(c => `<a class="cat-card" href="/news?category=${encodeURIComponent(c.name)}" style="--c:${CATS[c.name]}"><b>${c.name}</b><div class="n">${c.count}</div><div class="s">${c.children.filter(x => x.count).length} active sub-categories</div></a>`).join('');
    const leaf = (n, cat) => `<div class="leaf"><a href="/news?category=${encodeURIComponent(cat)}&subcategory=${encodeURIComponent(n.name)}">${esc(n.name)}</a><span class="cnt">${n.count}</span></div>`;
    const catNode = c => `<details><summary><i class="dot" style="--c:${CATS[c.name]}"></i>${esc(c.name)}<span class="cnt">${c.count}</span><a class="btn sm ghost" href="/news?category=${encodeURIComponent(c.name)}">Browse</a></summary>${c.children.map(x => leaf(x, c.name)).join('')}</details>`;
    $('#tree').innerHTML = `<details open><summary><b>${esc(d.tree.name)}</b><span class="cnt">${d.tree.count}</span></summary>${cats.map(catNode).join('')}</details>`;
  };
  $('#expandAll').onclick = () => $$('#tree details').forEach(x => x.open = true);
  $('#collapseAll').onclick = () => $$('#tree details').forEach((x, i) => x.open = i === 0);
  reload();
}

/* ---------- smart search (Trie) ---------- */
function initSearch() {
  const $i = $('#sq'); $i.value = new URLSearchParams(location.search).get('q') || '';
  reload = async () => {
    const q = $i.value.trim();
    if (!q) { $('#sugg').innerHTML = ''; $('#results').innerHTML = ''; return; }
    const d = await api('/api/search?q=' + encodeURIComponent(q));
    $('#sugg').innerHTML = d.suggestions.map(s => `<button class="chip" data-w="${esc(s.word)}">${esc(s.word)}<small>${s.count}</small></button>`).join('') || '<span class="muted">No keyword starts with that prefix.</span>';
    $('#sstats').textContent = `${d.total} matching article${d.total === 1 ? '' : 's'} in ${d.time_ms} ms. Trie lookup costs O(P + S) per prefix over a vocabulary of ${d.vocabulary} words.`;
    $('#results').innerHTML = d.items.map(a => card(a, q)).join('') || '<div class="empty">No articles match every word you typed. Try a shorter prefix.</div>';
  };
  $i.oninput = debounce(reload, 120);
  $('#sugg').onclick = e => { const b = e.target.closest('[data-w]'); if (!b) return; const p = $i.value.split(/\s+/); p[p.length - 1] = b.dataset.w; $i.value = p.join(' ') + ' '; $i.focus(); reload(); };
  reload();
}

/* ---------- news network (graph + BFS/DFS) ---------- */
function initNetwork() {
  const cv = $('#graph'), ctx = cv.getContext('2d'), tip = $('#gtip');
  let G, P = {}, N = {}, sel = null, vis = new Map(), tree = new Set(), W = 0, H = 0, drag = null, moved = false, timer = null;
  $('#legend').innerHTML = Object.entries(CATS).map(([c, k]) => `<span><i style="--c:${k}"></i>${c}</span>`).join('') + '<span><i class="sq" style="--c:var(--node-src)"></i>Source</span><span><i style="--c:#F59E0B"></i>Visited (number = order)</span>';
  const size = () => { const r = cv.getBoundingClientRect(), d = devicePixelRatio || 1; W = r.width; H = r.height; cv.width = W * d; cv.height = H * d; ctx.setTransform(d, 0, 0, d, 0, 0); };
  function layout() {  // force-directed layout (Fruchterman-Reingold): O(iterations * (V^2 + E))
    const L = G.nodes; P = {}; L.forEach(n => P[n.id] = {x: W / 2 + (Math.random() - .5) * W * .7, y: H / 2 + (Math.random() - .5) * H * .7});
    const k = Math.sqrt(W * H / L.length) * .65;
    for (let it = 0; it < 300; it++) {
      const t = 1 - it / 300, D = {}; L.forEach(n => D[n.id] = {x: 0, y: 0});
      for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) {
        const a = P[L[i].id], b = P[L[j].id]; let dx = a.x - b.x, dy = a.y - b.y; const d = Math.hypot(dx, dy) || .01, f = k * k / d; dx /= d; dy /= d;
        D[L[i].id].x += dx * f; D[L[i].id].y += dy * f; D[L[j].id].x -= dx * f; D[L[j].id].y -= dy * f;
      }
      G.edges.forEach(e => { const a = P[e.source], b = P[e.target]; let dx = a.x - b.x, dy = a.y - b.y; const d = Math.hypot(dx, dy) || .01, f = d * d / k * .6; dx /= d; dy /= d;
        D[e.source].x -= dx * f; D[e.source].y -= dy * f; D[e.target].x += dx * f; D[e.target].y += dy * f; });
      L.forEach(n => { const p = P[n.id], d = D[n.id]; d.x += (W / 2 - p.x) * .06; d.y += (H / 2 - p.y) * .06; const m = Math.hypot(d.x, d.y) || 1, s = Math.min(m, 30 * t + 2);
        p.x = Math.min(W - 18, Math.max(18, p.x + d.x / m * s)); p.y = Math.min(H - 18, Math.max(18, p.y + d.y / m * s)); });
    }
  }
  const rad = n => n.type === 'source' ? 9 : 4.5 + Math.min(n.degree, 6) * .6;
  function draw() {
    ctx.clearRect(0, 0, W, H);
    G.edges.forEach(e => {
      const a = P[e.source], b = P[e.target], te = tree.has(e.source + '|' + e.target) || tree.has(e.target + '|' + e.source);
      ctx.strokeStyle = te ? '#F59E0B' : css('--edge'); ctx.lineWidth = te ? 3 : e.kind === 'related' ? 1.4 : .8; ctx.globalAlpha = te ? 1 : e.kind === 'related' ? .65 : .35;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    });
    ctx.globalAlpha = 1; ctx.font = '600 10px Inter, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    G.nodes.forEach(n => {
      const p = P[n.id], r = rad(n), v = vis.has(n.id), big = v ? r + 4 : r;
      ctx.fillStyle = v ? '#F59E0B' : n.type === 'source' ? css('--node-src') : CATS[n.category];
      ctx.beginPath(); if (n.type === 'source') ctx.rect(p.x - big, p.y - big, big * 2, big * 2); else ctx.arc(p.x, p.y, big, 0, 7); ctx.fill();
      if (n.id === sel) { ctx.strokeStyle = css('--text'); ctx.lineWidth = 3; ctx.stroke(); }
      if (v) { ctx.fillStyle = '#111'; ctx.fillText(vis.get(n.id) + 1, p.x, p.y + .5); }
      else if (n.type === 'source') { ctx.fillStyle = css('--text'); ctx.fillText(n.label, p.x, p.y - 17); }
    });
  }
  const hit = (x, y) => { let best = null, bd = 1e9; G.nodes.forEach(n => { const d = Math.hypot(P[n.id].x - x, P[n.id].y - y); if (d < Math.max(12, rad(n) + 5) && d < bd) { best = n; bd = d; } }); return best; };
  const pos = e => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  cv.onpointerdown = e => { const n = hit(...pos(e)); if (n) { drag = n; moved = false; cv.setPointerCapture(e.pointerId); } };
  cv.onpointermove = e => {
    const [x, y] = pos(e);
    if (drag) { moved = true; P[drag.id].x = x; P[drag.id].y = y; draw(); return; }
    const n = hit(x, y); cv.style.cursor = n ? 'pointer' : 'grab';
    if (n) { tip.hidden = false; tip.textContent = n.type === 'source' ? 'Source: ' + n.label : `${n.category}: ${n.label}`; tip.style.left = Math.min(x + 12, W - 200) + 'px'; tip.style.top = y + 14 + 'px'; } else tip.hidden = true;
  };
  cv.onpointerup = () => { if (drag && !moved) select(drag.id); drag = null; };
  cv.onpointerleave = () => tip.hidden = true;
  function select(id) {
    sel = id; const n = N[id];
    $('#selInfo').innerHTML = `<b>Start node:</b> ${esc(n.label)}<div class="kv"><b>Type</b><span>${n.type}</span><b>Neighbours</b><span>${n.degree}</span>${n.category ? `<b>Category</b><span>${n.category}</span>` : ''}</div>${n.url ? `<p><a href="${esc(n.url)}" target="_blank" rel="noopener">Read original article</a></p>` : ''}`;
    draw();
  }
  function clear() { clearInterval(timer); vis = new Map(); tree = new Set(); }
  async function run(algo) {
    clear(); if (!G) return;
    const d = await api(`/api/traverse?algo=${algo}&limit=${G.limit}` + (sel ? '&start=' + sel : ''));
    if (!sel) select(d.start);
    const lbl = id => esc(N[id].label.length > 70 ? N[id].label.slice(0, 68) + '…' : N[id].label), name = algo.toUpperCase();
    $('#result').innerHTML = `<b>${name}</b> from “${lbl(d.start)}”<div class="kv"><b>Visited</b><span>${d.visited} of ${d.V} nodes</span><b>Edges</b><span>${d.E}</span><b>Run time</b><span>${d.time_ms} ms</span><b>Max depth</b><span>${Math.max(...Object.values(d.depth))}</span></div>
      <p style="margin:10px 0 0;color:var(--text)"><b>${esc(d.complexity)}</b></p>
      <p class="muted" style="margin:6px 0 0">${algo === 'bfs' ? 'BFS uses a queue and visits nodes level by level.' : 'DFS uses a stack and follows one branch as deep as possible before backtracking.'}</p>
      <ol>${d.order.map((id, i) => `<li><em>${i + 1}</em><span class="lv">L${d.depth[id]}</span><span>${lbl(id)}</span></li>`).join('')}</ol>`;
    let i = 0; timer = setInterval(() => {
      if (i >= d.order.length) return clearInterval(timer);
      const id = d.order[i]; vis.set(id, i); if (d.parent[id]) tree.add(d.parent[id] + '|' + id); i++; draw();
    }, Math.max(25, 1800 / d.order.length));
  }
  async function load() {
    clear(); size();
    G = await api('/api/graph?limit=' + $('#limit').value); N = Object.fromEntries(G.nodes.map(n => [n.id, n])); sel = null;
    $('#selInfo').textContent = 'Click a node to choose the start node. Drag nodes to rearrange. Default: the most connected node.';
    $('#result').textContent = 'Run BFS or DFS to see the visit order, depth and time complexity.';
    if (!G.nodes.length) { ctx.clearRect(0, 0, W, H); ctx.fillStyle = css('--muted'); ctx.textAlign = 'center'; ctx.fillText('No articles yet. Click “Refresh news” first.', W / 2, H / 2); return; }
    layout(); draw();
  }
  reload = load; $('#limit').onchange = load; $('#bfsBtn').onclick = () => run('bfs').catch(e => toast(e.message, 'err')); $('#dfsBtn').onclick = () => run('dfs').catch(e => toast(e.message, 'err'));
  $('#resetBtn').onclick = () => { clear(); sel = null; $('#selInfo').textContent = 'Start node cleared. The most connected node is used by default.'; if (G?.nodes.length) draw(); };
  addEventListener('resize', debounce(() => { if (G?.nodes.length) { size(); layout(); draw(); } }, 200));
  load();
}

/* ---------- analytics ---------- */
function initAnalytics() {
  reload = async () => {
    const d = await api('/api/analytics'), grid = css('--border');
    chart('cCat', {type: 'doughnut', data: {labels: d.distribution.map(x => x.name), datasets: [{data: d.distribution.map(x => x.count), backgroundColor: d.distribution.map(x => CATS[x.name]), borderWidth: 0}]}, options: {maintainAspectRatio: false, cutout: '58%', plugins: {legend: {position: 'right'}}}});
    chart('cSrc', {type: 'bar', data: {labels: d.sources.map(x => x.name), datasets: [{label: 'Articles', data: d.sources.map(x => x.count), backgroundColor: '#0D9488', borderRadius: 4}]}, options: {maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {x: {ticks: {maxRotation: 60}, grid: {display: false}}, y: {beginAtZero: true}}}});
    chart('cTrend', {type: 'line', data: {labels: d.trend.days.map(x => x.slice(5)), datasets: [{label: 'Published', data: d.trend.published, borderColor: '#8B5CF6', backgroundColor: '#8B5CF622', fill: true, tension: .3}, {label: 'Collected by NewsHub', data: d.trend.collected, borderColor: '#0D9488', tension: .3}]}, options: {maintainAspectRatio: false, interaction: {mode: 'index', intersect: false}, scales: {y: {beginAtZero: true}}}});
    chart('cKw', {type: 'bar', data: {labels: d.keywords.map(x => x.word), datasets: [{label: 'Articles', data: d.keywords.map(x => x.count), backgroundColor: '#F59E0B', borderRadius: 4}]}, options: {indexAxis: 'y', maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {grid: {display: false}}}, onClick: (e, els, c) => { if (els.length) location.href = '/search?q=' + encodeURIComponent(c.data.labels[els[0].index]); }}});
  };
  reload();
}

/* ---------- sources ---------- */
function initSources() {
  const f = $('#addForm'); f.category_hint.innerHTML += Object.keys(CATS).map(c => `<option>${c}</option>`).join('');
  reload = async () => {
    const d = await api('/api/sources');
    $('#srcBody').innerHTML = d.map(s => `<tr><td><b>${esc(s.name)}</b></td><td><code title="${esc(s.last_error || '')}">${esc(s.feed_url)}</code></td><td>${s.category_hint ? badge(s.category_hint) : '<span class="muted">auto</span>'}</td>
      <td><span class="badge ${s.active ? s.status : 'pending'}" title="${esc(s.last_error || '')}">${s.active ? s.status : 'paused'}</span>${s.last_error ? `<div class="muted" style="font-size:11px;max-width:200px">${esc(s.last_error)}</div>` : ''}</td>
      <td>${s.articles}</td><td>${s.last_fetched ? ago(s.last_fetched) : 'never'}</td>
      <td><div class="row"><button class="btn sm ghost" data-act="refresh" data-id="${s.id}">Refresh</button><button class="btn sm ghost" data-act="toggle" data-id="${s.id}" data-on="${s.active}">${s.active ? 'Pause' : 'Resume'}</button><button class="btn sm danger" data-act="del" data-id="${s.id}">Remove</button></div></td></tr>`).join('');
  };
  $('#srcBody').onclick = async e => {
    const b = e.target.closest('[data-act]'); if (!b) return; const id = b.dataset.id;
    try {
      if (b.dataset.act === 'refresh') { b.disabled = true; b.textContent = 'Fetching…'; const r = await api(`/api/sources/${id}/refresh`, {method: 'POST'}); toast(r.busy ? 'A refresh is already running' : r.failed.length ? 'Feed unavailable: ' + r.failed[0].error : `${r.new} new articles`, r.failed?.length ? 'err' : ''); }
      else if (b.dataset.act === 'toggle') await api('/api/sources/' + id, {method: 'PATCH', body: {active: b.dataset.on !== '1'}});
      else if (confirm('Remove this source and all of its articles and bookmarks?')) { await api('/api/sources/' + id, {method: 'DELETE'}); toast('Source removed'); }
    } catch (err) { toast(err.message, 'err'); }
    reload();
  };
  $('#refreshAll').onclick = e => $('#refreshBtn').click();
  f.onsubmit = async e => {
    e.preventDefault(); const btn = f.querySelector('button'); btn.disabled = true; btn.textContent = 'Checking feed…';
    try { const r = await api('/api/sources', {method: 'POST', body: Object.fromEntries(new FormData(f))}); toast(`Source added, ${r.new} articles collected`); f.reset(); }
    catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; btn.textContent = 'Add source'; reload(); }
  };
  reload();
}

({dashboard: initDashboard, news: () => initList(false), bookmarks: () => initList(true), categories: initCategories, search: initSearch, network: initNetwork, analytics: initAnalytics, sources: initSources, settings: () => {}})[PAGE]?.();
})();
