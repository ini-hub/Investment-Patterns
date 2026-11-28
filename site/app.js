// Investment Patterns public site. Reads the JSON written by `python -m scanner.publish`.
// Screens (hash routes): #/ scan · #/stock/TICKER results · #/compare/all or #/compare/A,B,C compare ·
// #/roadmap (this browser's year roadmap) or #/roadmap/YEAR/TICKER:key,... (a shared one).

import { PICKABLE, calendarFile, decodePlan, defaultWindows, encodePlan, lastBday, monthBoard, shortDay, trades, wkey } from './roadmap.js'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const RISING = ['Tier 1', 'Tier 2', 'Watch', 'Emerging']
const CARD_LIMIT = 6
const RESEARCH_TIER1 = ['FCMB', 'VITAFOAM', 'ETI', 'IKEJAHOTEL', 'LEARNAFRCA']
const BADGE = {
  'Tier 1': ['#1D4ED8', '#FFFFFF'], 'Tier 2': ['#DBEAFE', '#1E3A8A'], Watch: ['#E5E7EB', '#1F2937'],
  Emerging: ['#F5F3FF', '#4C1D95'], Negative: ['#FFEDD5', '#9A3412'], 'Open now': ['#DCFCE7', '#14532D'],
  Upcoming: ['#F1F3F6', '#374151'], None: ['#FFFFFF', '#4B5160'], 'Insufficient history': ['#FFFFFF', '#4B5160'],
}
const MAP_FILL = { 'Tier 1': '#1D4ED8', 'Tier 2': '#93B4F5', Watch: '#D1D5DB', Negative: '#EA7A3D', '': '#F1F3F6' }
const LABEL = { Negative: 'Exit or avoid' }
const SORTS = {
  'Most Tier 1': (a, b) => b.counts['Tier 1'] - a.counts['Tier 1'] || b.counts['Tier 2'] - a.counts['Tier 2'] || num(b.best?.median) - num(a.best?.median),
  'Best median': (a, b) => num(b.best?.median) - num(a.best?.median),
  'Least likely chance': (a, b) => num(a.chance, 9) - num(b.chance, 9),
  'Most exit windows': (a, b) => b.counts.Negative - a.counts.Negative,
  'Ticker A to Z': (a, b) => a.ticker.localeCompare(b.ticker),
}
const ICON_WARN = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/></svg>'
const ICON_INFO = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/></svg>'
const ICON_X = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>'
const ICON_ARROW = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'

// ------------------------------------------------------------------ state
const app = document.getElementById('app')
const S = {
  index: null, byTicker: new Map(), stocks: new Map(),
  sel: loadJSON('ip.sel', ['FCMB']), mode: loadJSON('ip.mode', 'Compare'), query: '', active: 0,
  tab: 'patterns', heatAll: false, yearWindow: null, filters: new Set(), sort: 'Most Tier 1', cmpAll: false,
  ranked: 'Rising', lastCompare: null, plan: null, flash: '',
}
const today = (() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), d.getDate()) })()

// ------------------------------------------------------------------ helpers
function esc(s) { return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]) }
function num(v, missing = -9) { return v == null || Number.isNaN(v) ? missing : v }
function pct(v, d = 1, sign = true) {
  if (v == null || Number.isNaN(v)) return 'n/a'
  const x = v * 100
  if (Math.abs(x) < 0.5 * 10 ** -d) return (0).toFixed(d) + '%'
  return (sign && x > 0 ? '+' : '') + x.toFixed(d) + '%'
}
function ratio(a, b) { return a == null || b == null || !b ? 'n/a' : `${a} / ${b}` }
function day(d) { return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}` }
function isoDay(s) { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d) }
function badge(k, text) {
  const [bg, fg] = BADGE[k] || BADGE.None
  const outline = bg === '#FFFFFF' ? ';outline:1px solid #E3E6EB' : ''
  return `<span class="badge" style="background:${bg};color:${fg}${outline}">${esc(text ?? LABEL[k] ?? k)}</span>`
}
function callout(kind, html) { return `<div class="callout ${kind}" role="status">${kind === 'warn' ? ICON_WARN : ICON_INFO}<div>${html}</div></div>` }
function loadJSON(key, fallback) { try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback } catch { return fallback } }
function saveJSON(key, v) { try { localStorage.setItem(key, JSON.stringify(v)) } catch { /* private mode: fine */ } }
async function getJSON(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`)
  return r.json()
}
async function stock(t) {
  if (!S.stocks.has(t)) S.stocks.set(t, await getJSON(`data/stocks/${encodeURIComponent(t)}.json`))
  return S.stocks.get(t)
}
function months(start, len) { return Array.from({ length: len }, (_, i) => ((start - 1 + i) % 12) + 1) }

// Next or current occurrence of a window: entry = close of the last business day before it starts.
function nextDates(start, len, asOf = today) {
  for (const y of [asOf.getFullYear() - 1, asOf.getFullYear(), asOf.getFullYear() + 1]) {
    const entry = lastBday(y, start - 2)
    const exit = lastBday(y, start - 1 + len - 1)
    if (asOf <= entry) return { entry, exit, status: 'Upcoming' }
    if (asOf > entry && asOf <= exit) return { entry, exit, status: 'Open now' }
  }
  return null
}
function whenText(w) {
  if (w.length >= 12) return 'Full calendar year'
  const n = nextDates(w.start_month, w.length)
  return n.status === 'Open now' ? `Open now · exit close ${day(n.exit)}` : `Entry close ${day(n.entry)} · exit close ${day(n.exit)}`
}
function calendar(rows) {
  return rows.filter((w) => w.length < 12).map((w) => ({ ...w, ...nextDates(w.start_month, w.length) }))
    .map((c) => ({ ...c, days: Math.max(0, Math.round((c.entry - today) / 864e5)) }))
    .sort((a, b) => (a.status === b.status ? a.days - b.days : a.status === 'Open now' ? -1 : 1))
}
function download(name, text, type = 'text/csv') {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type }))
  a.download = name
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}
function csv(rows, fields) {
  const cell = (v) => (v == null ? '' : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v))
  return [fields.join(','), ...rows.map((r) => fields.map((f) => cell(r[f])).join(','))].join('\n')
}
function setNav(which) {
  document.querySelectorAll('[data-nav]').forEach((a) => {
    if (a.dataset.nav === which) a.setAttribute('aria-current', 'page')
    else a.removeAttribute('aria-current')
  })
  const n = S.plan?.items.length || 0
  document.getElementById('plan-count').textContent = n ? ` (${n})` : ''
}
function takeFlash() { const f = S.flash; S.flash = ''; return f }

// ------------------------------------------------------------------ roadmap plan (this browser)
function defaultYear() { return today.getMonth() >= 9 ? today.getFullYear() + 1 : today.getFullYear() }
function loadPlan() {
  const p = loadJSON('ip.plan', null)
  const items = Array.isArray(p?.items) ? p.items.filter((i) => i && typeof i.t === 'string' && Array.isArray(i.w)) : []
  return { year: Number.isInteger(p?.year) ? p.year : defaultYear(), exits: p?.exits !== false, items }
}
function savePlan() { saveJSON('ip.plan', S.plan); setNav(document.querySelector('[data-nav][aria-current]')?.dataset.nav || '') }
function planItem(t) { return S.plan.items.find((i) => i.t === t) }
// Add stocks with their default (Tier 1 / Tier 2, non-overlapping) windows. In bulk, stocks with none are skipped.
function addToPlan(tickers, bulk = false) {
  let added = 0
  const skipped = []
  for (const t of tickers) {
    const s = S.byTicker.get(t)
    if (!s || planItem(t)) continue
    const w = defaultWindows(s.classified)
    if (bulk && !w.length) { skipped.push(t); continue }
    S.plan.items.push({ t, w })
    added++
  }
  savePlan()
  return { added, skipped }
}
function removeFromPlan(t) { S.plan.items = S.plan.items.filter((i) => i.t !== t); savePlan() }
function toggleWindow(t, key) {
  let item = planItem(t)
  if (!item) { item = { t, w: [] }; S.plan.items.push(item) }
  item.w = item.w.includes(key) ? item.w.filter((k) => k !== key) : [...item.w, key]
  savePlan()
}
function planButton(t) {
  const on = Boolean(planItem(t))
  return `<button class="pill" data-act="plan" data-v="${esc(t)}" aria-pressed="${on}" title="${on ? 'Remove from' : 'Add to'} your year roadmap">${on ? '✓ In roadmap' : '+ Roadmap'}</button>`
}
function addedMessage({ added, skipped }) {
  const parts = [added ? `Added ${added} stock${added === 1 ? '' : 's'} to your <a href="#/roadmap">year roadmap</a>.` : 'Those stocks are already in your <a href="#/roadmap">year roadmap</a>.']
  if (skipped.length) parts.push(`${skipped.length} with no Tier 1 or Tier 2 window ${skipped.length === 1 ? 'was' : 'were'} skipped${skipped.length <= 8 ? `: ${skipped.map(esc).join(', ')}` : ''}.`)
  return callout('info', parts.join(' '))
}

// ------------------------------------------------------------------ routing
async function render() {
  const [, view, arg, arg2] = (location.hash.replace(/^#/, '') || '/').split('/')
  try {
    if (view === 'stock' && arg) { setNav(''); await renderStock(decodeURIComponent(arg).toUpperCase()) }
    else if (view === 'compare') { setNav('compare'); await renderCompare(decodeURIComponent(arg || 'all')) }
    else if (view === 'roadmap') { setNav('roadmap'); renderRoadmap(arg, arg2) }
    else { setNav('scan'); renderScan() }
  } catch (err) {
    app.innerHTML = `<h1>Something went wrong</h1><p class="muted">${esc(err.message)}</p><p><a href="#/">Back to Scan</a></p>`
  }
}

async function boot() {
  S.index = await getJSON('data/index.json')
  for (const s of S.index.stocks) S.byTicker.set(s.ticker, s)
  const snap = isoDay(S.index.snapshot_date)
  document.getElementById('status').innerHTML = `<span class="dot" aria-hidden="true"></span><span>NGX · ${S.index.stocks.length} stocks · to ${day(snap)}</span>`
  document.getElementById('source').textContent = `Data: ${S.index.source}. Last price ${day(snap)}. Benchmark: ${S.index.benchmark}.`
  S.sel = S.sel.filter((t) => S.byTicker.has(t))
  S.plan = loadPlan()
  S.plan.items = S.plan.items.filter((i) => S.byTicker.has(i.t))
  window.addEventListener('hashchange', () => { render(); app.focus({ preventScroll: true }); window.scrollTo(0, 0) })
  await render()
}

// ------------------------------------------------------------------ screen 1: scan
function single() { return S.mode === 'Single report' }
function runHref() {
  if (!S.sel.length) return '#/'
  if (single() || S.sel.length === 1) return `#/stock/${encodeURIComponent(S.sel[0])}`
  return S.sel.length === S.index.stocks.length ? '#/compare/all' : `#/compare/${S.sel.map(encodeURIComponent).join(',')}`
}
function suggestions() {
  const q = S.query.trim().toUpperCase()
  if (!q) return []
  const starts = [], contains = []
  for (const s of S.index.stocks) {
    if (S.sel.includes(s.ticker)) continue
    if (s.ticker.startsWith(q)) starts.push(s)
    else if (s.ticker.includes(q) || s.name.toUpperCase().includes(q)) contains.push(s)
  }
  return [...starts, ...contains].slice(0, 8)
}
function setSel(list, mode) {
  S.sel = [...new Set(list)]
  if (mode) S.mode = mode
  if (single()) S.sel = S.sel.slice(0, 1)
  saveJSON('ip.sel', S.sel); saveJSON('ip.mode', S.mode)
}

function renderScan(focus = false) {
  const n = S.sel.length
  const sug = suggestions()
  S.active = Math.min(S.active, Math.max(sug.length - 1, 0))
  const sectors = {}
  for (const s of S.index.stocks) if (s.sector) (sectors[s.sector] ||= []).push(s.ticker)
  const picks = [
    ...(single() ? [] : [[`All stocks (${S.index.stocks.length})`, S.index.stocks.map((s) => s.ticker)]]),
    [`Research Tier 1 stocks (${RESEARCH_TIER1.length})`, RESEARCH_TIER1],
    ...Object.entries(sectors).filter(([, g]) => g.length >= 2).sort().map(([k, g]) => [`${k} (${g.length})`, g]),
  ]
  const label = single() || n <= 1 ? 'Run scan' : `Compare ${n} stocks`
  const helper = single()
    ? 'Single report: one stock, every window, heatmap, calendar and year-by-year detail.'
    : `${n} selected. Up to ${CARD_LIMIT} line up side by side; more are shown as sortable tables you can filter.`
  const recent = loadJSON('ip.recent', [])
  app.innerHTML = `
    <section><h1>Scan stocks for seasonal patterns</h1>
      <p class="lede">Pick one NGX stock for a full report, or several (up to every stock) to compare. Every month, rolling 2 and 3-month window and the full year is tested against the stock's own trend, the market and chance.</p></section>
    <section class="card">
      <div class="row spread">
        <label for="ticker-input" style="font-size:14px;font-weight:600">Ticker symbols</label>
        <div class="seg" role="group" aria-label="Scan mode">
          ${['Single report', 'Compare'].map((m) => `<button data-act="mode" data-v="${m}" aria-pressed="${S.mode === m}">${m}</button>`).join('')}
        </div>
      </div>
      <div class="row" style="align-items:stretch">
        <div class="picker">
          <div class="chips">
            ${S.sel.length > 40 ? `<span class="chip">${n} stocks selected</span>` : S.sel.map((t) => `<span class="chip">${esc(t)}<button data-act="remove" data-v="${esc(t)}" aria-label="Remove ${esc(t)}">${ICON_X}</button></span>`).join('')}
            <input id="ticker-input" autocomplete="off" role="combobox" aria-expanded="${sug.length > 0}" aria-controls="suggest" aria-autocomplete="list"
              value="${esc(S.query)}" placeholder="${n ? 'Add a ticker or company' : 'Type a ticker, e.g. ETI'}">
          </div>
          ${sug.length ? `<div class="suggest" id="suggest" role="listbox" aria-label="Matching stocks">${sug.map((s, i) => `
            <button role="option" aria-selected="${i === S.active}" class="${i === S.active ? 'active' : ''}" data-act="add" data-v="${esc(s.ticker)}">
              <span class="t">${esc(s.ticker)}</span><span class="n">${esc(s.name || s.sector || '')}</span><span class="muted">${s.years} years</span>
            </button>`).join('')}</div>` : ''}
        </div>
        <a class="btn primary big" href="${runHref()}" data-act="run" aria-disabled="${n === 0}">${esc(label)} ${ICON_ARROW}</a>
      </div>
      <p class="muted">${esc(helper)}</p>
      <div class="row" style="gap:8px">
        <span class="muted">Quick picks:</span>
        ${picks.map(([l], i) => `<button class="pill" data-act="pick" data-v="${i}">${esc(l)}</button>`).join('')}
        ${n > 1 ? '<button class="pill" data-act="clear">Clear</button>' : ''}
      </div>
    </section>
    ${callout('info', `Results use the default settings and closing prices up to <strong>${day(isoDay(S.index.snapshot_date))}</strong>, so 2026 is not included yet. Prices are not adjusted for dividends.`)}
    ${recent.length ? `<section style="display:flex;flex-direction:column;gap:10px"><h2>Recent scans</h2><div class="list">${recent.map((r) => `
      <a href="${esc(r.href)}"><span style="font-weight:600;flex:1 1 260px">${esc(r.label)}</span><span class="muted" style="flex:1 1 200px">${esc(r.summary)}</span><span class="muted">${esc(r.when)}</span></a>`).join('')}</div></section>` : ''}`

  const input = document.getElementById('ticker-input')
  input.addEventListener('input', () => { S.query = input.value; S.active = 0; renderScan(true) })
  input.addEventListener('keydown', (e) => {
    const list = suggestions()
    if (e.key === 'ArrowDown' && list.length) { S.active = (S.active + 1) % list.length; e.preventDefault(); renderScan(true) }
    else if (e.key === 'ArrowUp' && list.length) { S.active = (S.active - 1 + list.length) % list.length; e.preventDefault(); renderScan(true) }
    else if (e.key === 'Enter') {
      e.preventDefault()
      const exact = S.query.trim().toUpperCase()
      if (list.length) addTicker(list[S.active].ticker)
      else if (exact && S.sel.includes(exact)) { S.query = ''; renderScan(true) }
      else if (!exact && S.sel.length) { remember(); location.hash = runHref() }
    } else if (e.key === 'Backspace' && !S.query && S.sel.length) { setSel(S.sel.slice(0, -1)); renderScan(true) }
    else if (e.key === 'Escape') { S.query = ''; renderScan(true) }
  })
  app.querySelectorAll('[data-act]').forEach((el) => el.addEventListener('click', (e) => {
    const { act, v } = el.dataset
    if (act === 'run') { if (!S.sel.length) e.preventDefault(); else remember(); return }
    e.preventDefault()
    if (act === 'mode') setSel(S.sel, v)
    if (act === 'remove') setSel(S.sel.filter((t) => t !== v))
    if (act === 'add') return addTicker(v)
    if (act === 'pick') { const g = picks[Number(v)][1].filter((t) => S.byTicker.has(t)); setSel(g, g.length > 1 ? 'Compare' : S.mode) }
    if (act === 'clear') setSel([])
    renderScan(act === 'remove')
  }))
  if (focus) { input.focus(); input.setSelectionRange(input.value.length, input.value.length) }
}
function addTicker(t) {
  setSel(single() ? [t] : [...S.sel, t])
  S.query = ''; S.active = 0
  renderScan(true)
}
function remember() {
  const label = S.sel.length > 6 ? `${S.sel.length} stocks` : S.sel.join(', ')
  const rows = S.sel.map((t) => S.byTicker.get(t)).filter(Boolean)
  const c = (k) => rows.reduce((a, s) => a + s.counts[k], 0)
  const summary = `${c('Tier 1')} Tier 1 · ${c('Tier 2')} Tier 2 · ${c('Negative')} falling windows`
  const now = new Date()
  const entry = { href: runHref(), label, summary, when: `${day(now)}, ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}` }
  saveJSON('ip.recent', [entry, ...loadJSON('ip.recent', []).filter((r) => r.href !== entry.href)].slice(0, 5))
}

// ------------------------------------------------------------------ screen 2: one stock
function sparkline(rows, name) {
  if (!rows?.length) return ''
  const scale = Math.max(0.05, ...rows.map((r) => Math.abs(r[1] ?? 0)))
  const bars = rows.map(([y, r]) => `<span title="${y}: ${pct(r)}" style="height:${Math.max(3, Math.min(56, (Math.abs(r) / scale) * 56)).toFixed(0)}px;background:${r > 0 ? '#1D4ED8' : '#C2410C'};align-self:${r > 0 ? 'flex-end' : 'flex-start'}"></span>`).join('')
  return `<div class="spark" role="img" aria-label="${esc(`${name} returns by year, ${rows[0][0]} to ${rows.at(-1)[0]}`)}">${bars}</div>`
}
function patternCards(doc, list) {
  if (!list.length) return '<p class="muted">None found with the default settings.</p>'
  return list.map((w) => {
    const cells = [['Years up', ratio(w.up, w.n)], ['Streak', w.streak], ['Median', pct(w.median)], ['Mean', pct(w.mean)],
      ['Min / max', `${pct(w.worst)} / ${pct(w.best)}`], ['Std dev', pct(w.std, 1, false)], ['Beat market', ratio(w.beat_market, w.market_n)],
      ['Beat own avg', ratio(w.beat_own, w.own_n)], ['Median dip', pct(w.median_dip)]]
    const notes = [w.flags, w.note].filter(Boolean).join('; ')
    return `<article class="pcard"><div class="head">${badge(w.class)}<span class="win">${esc(w.window)}</span><span class="muted">${esc(whenText(w))}</span></div>
      <dl>${cells.map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>${sparkline(doc.years[w.window], w.window)}
      ${notes ? `<div class="flags">${esc(notes)}</div>` : ''}</article>`
  }).join('')
}
function heatStyle(v) {
  if (v == null) return 'background:#F6F7F9;color:#8A909C'
  const a = Math.min(Math.abs(v) / 0.5, 1) * 0.85 + 0.08
  return `background:rgba(${v >= 0 ? '29,78,216' : '194,65,12'},${a.toFixed(2)});color:${a > 0.5 ? '#FFFFFF' : '#14171F'}`
}
function heatmap(doc) {
  const rows = [...doc.windows].sort((a, b) => a.length - b.length || a.start_month - b.start_month)
    .filter((w) => S.heatAll || !['None', 'Insufficient history'].includes(w.class))
  if (!rows.length) return '<p class="muted">No classified windows. Show all windows to see every return.</p>'
  const years = [...new Set(Object.values(doc.years).flat().map((r) => r[0]))].sort()
  const cell = (v) => (v == null ? 'n/a' : Math.abs(v) < 0.005 ? '0%' : pct(v, 0))
  return `<div class="scroll"><table class="heat"><thead><tr><th scope="col" style="text-align:left">Window</th>${years.map((y) => `<th scope="col">${y}</th>`).join('')}</tr></thead><tbody>
    ${rows.map((w) => {
      const by = Object.fromEntries((doc.years[w.window] || []).map((r) => [r[0], r[1]]))
      const k = ['None', 'Insufficient history'].includes(w.class) ? '' : ` ${badge(w.class)}`
      return `<tr><th scope="row">${esc(w.window)}${k}</th>${years.map((y) => `<td style="${heatStyle(by[y])}">${cell(by[y])}</td>`).join('')}</tr>`
    }).join('')}</tbody></table></div>
    <p class="muted">Blue: gain, orange: loss; colour saturates at ±50%. Each cell prints its value. Years are labelled by the year the window starts.</p>`
}
function calendarList(rows, showStock) {
  const cal = calendar(rows)
  if (!cal.length) return '<p class="muted">No classified windows.</p>'
  return `<div class="list">${cal.map((c) => `<div>${badge(c.status)}${showStock ? `<a href="#/stock/${esc(c.ticker)}" style="font-weight:600;width:110px">${esc(c.ticker)}</a>` : ''}
    <span style="font-weight:600;width:90px">${esc(c.window)}</span>${badge(c.class)}
    <span style="flex:1 1 260px">Entry close ${day(c.entry)} · exit close ${day(c.exit)}</span>
    <span class="muted">Up ${ratio(c.up, c.n)} · median ${pct(c.median)}</span></div>`).join('')}</div>`
}
function dataTable(cols, rows, { link } = {}) {
  return `<div class="scroll tall"><table class="data"><thead><tr>${cols.map((c) => `<th class="${c.num ? 'num' : ''}" scope="col">${esc(c.label)}</th>`).join('')}</tr></thead>
    <tbody>${rows.map((r) => `<tr${link ? ` class="link" data-href="${esc(link(r))}" tabindex="0"` : ''}>${cols.map((c) => `<td class="${c.num ? 'num' : ''}">${c.html ? c.html(r) : esc(c.get(r))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`
}
function wireRowLinks(root = app) {
  root.querySelectorAll('tr[data-href]').forEach((tr) => {
    tr.addEventListener('click', (e) => { if (!e.target.closest('button, a')) location.hash = tr.dataset.href })
    tr.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target === tr) location.hash = tr.dataset.href })
  })
}

async function renderStock(t) {
  if (!S.byTicker.has(t)) {
    app.innerHTML = `<h1>No price data found for ${esc(t)}</h1><p class="muted">Check the ticker symbol. The dataset covers ${S.index.stocks.length} NGX stocks.</p><p><a href="#/">Back to Scan</a></p>`
    return
  }
  app.innerHTML = '<p class="loading">Loading…</p>'
  const doc = await stock(t)
  const W = doc.windows
  const byClass = (k) => W.filter((w) => w.class === k)
  const names = (k) => { const w = byClass(k).map((x) => x.window); return [String(w.length), w.length ? w.slice(0, 4).join(', ') + (w.length > 4 ? ' …' : '') : 'none'] }
  const perm = doc.permutation
  const pos = W.filter((w) => RISING.includes(w.class)), neg = byClass('Negative')
  const cal = calendar(W.filter((w) => ['Tier 1', 'Tier 2', 'Watch'].includes(w.class)))
  const up = cal.filter((c) => c.status === 'Upcoming'), open = cal.filter((c) => c.status === 'Open now')
  const banner = []
  if (up.length) banner.push(`<strong>Next window:</strong> ${esc(up[0].window)} (${esc(up[0].class)}) opens at the close of ${day(up[0].entry)} and closes ${day(up[0].exit)}. Up ${ratio(up[0].up, up[0].n)} years, median ${pct(up[0].median)}.`)
  if (open.length) banner.push(`<strong>Open now:</strong> ${open.map((c) => `${esc(c.window)} (${esc(c.class)})`).join(', ')}`)
  const q = doc.quality
  const warns = [callout('warn', `<strong>Data ends ${day(isoDay(doc.last_date))}.</strong> 2026 is not included, so these results cannot yet show whether the patterns held this year.`)]
  if (q.frozen) warns.push(callout('warn', `<strong>Frozen price:</strong> ${pct(q.zero_change_share, 0, false)} of month-to-month changes are exactly 0%. Patterns for this stock are unreliable.`))
  if (q.missing_years.length) warns.push(callout('plain', `<strong>No prices at all in:</strong> ${q.missing_years.join(', ')}.`))
  if (q.large_moves.length) warns.push(callout('plain', `<strong>Large single-day moves</strong> (possible dividend, bonus issue or data error): ${q.large_moves.slice(0, 8).map(([d, m]) => `${esc(d)} (${pct(m)})`).join(', ')}${q.large_moves.length > 8 ? ` and ${q.large_moves.length - 8} more` : ''}.`))
  const tabs = [['patterns', `Patterns (${pos.length})`], ['exit', `Exit or avoid (${neg.length})`], ['heat', 'Heatmap'], ['cal', 'Calendar'], ['years', 'Year detail'], ['chance', 'Chance check'], ['all', 'All windows'], ['method', 'Method']]
  if (!tabs.some(([id]) => id === S.tab)) S.tab = 'patterns'
  const ordered = [...W].sort((a, b) => a.length - b.length || a.start_month - b.start_month)
  if (!S.yearWindow || !W.some((w) => w.window === S.yearWindow)) S.yearWindow = (pos[0] || ordered[0]).window
  const panel = {
    patterns: () => patternCards(doc, pos),
    exit: () => `<p class="muted">Windows that fell in most years. Useful for timing exits; retail short selling is not generally available on the NGX.</p>${patternCards(doc, neg)}`,
    heat: () => `<div class="seg" role="group" aria-label="Rows">${['Classified windows', 'All windows'].map((m, i) => `<button data-act="heat" data-v="${i}" aria-pressed="${S.heatAll === Boolean(i)}">${m}</button>`).join('')}</div>${heatmap(doc)}`,
    cal: () => `<p class="muted">Next or current occurrence of each classified window as of ${day(today)}. Dates are the last business day of the month; NGX holidays are not modelled.</p>${calendarList(W.filter((w) => ['Tier 1', 'Tier 2', 'Watch', 'Negative'].includes(w.class)), false)}`,
    years: () => {
      const w = W.find((x) => x.window === S.yearWindow)
      const rows = (doc.years[S.yearWindow] || []).map(([year, ret, dip, market, own]) => ({ year, ret, dip, market, own }))
      return `<div class="row"><label for="yw" class="muted">Window</label><select id="yw">${ordered.map((x) => `<option ${x.window === S.yearWindow ? 'selected' : ''}>${esc(x.window)}</option>`).join('')}</select></div>
        <p><strong>${esc(t)} ${esc(w.window)}</strong>: ${badge(w.class)} Up in ${w.up} of ${w.n} years, median ${pct(w.median)}, mean ${pct(w.mean)}, worst ${pct(w.worst)}, best ${pct(w.best)}.</p>
        ${dataTable([{ label: 'Year', get: (r) => r.year }, { label: 'Return', num: 1, get: (r) => pct(r.ret) }, { label: 'Dip inside window', num: 1, get: (r) => pct(r.dip) },
          { label: 'Market', num: 1, get: (r) => pct(r.market) }, { label: 'Own average', num: 1, get: (r) => pct(r.own) }], rows)}
        <p class="muted">Return: month-end close of the last month over the month-end close before the window starts. Dip: the lowest daily close inside the window against that entry close. Closing prices themselves are not published here.</p>`
    },
    chance: () => perm ? `<p>${esc(describe(perm))}</p><div class="tiles">
        <div class="tile"><span class="k">Patterns found</span><span class="v">${perm.actual}</span><span class="s">windows passing the Tier 1 / Tier 2 filter</span></div>
        <div class="tile"><span class="k">Average by chance</span><span class="v">${perm.null_mean.toFixed(1)}</span><span class="s">${perm.runs} shuffles, seed ${perm.seed}</span></div>
        <div class="tile"><span class="k">95th percentile</span><span class="v">${perm.null_p95}</span><span class="s">count reached by the luckiest 5% of shuffles</span></div>
        <div class="tile"><span class="k">Runs at or above</span><span class="v">${pct(perm.share_at_or_above, 0, false)}</span><span class="s">lower means less likely to be chance</span></div></div>` : '<p class="muted">Not available.</p>',
    all: () => dataTable([
      { label: 'Window', get: (w) => w.window }, { label: 'Class', html: (w) => badge(w.class) }, { label: 'Years up', get: (w) => ratio(w.up, w.n) },
      { label: 'Streak', num: 1, get: (w) => w.streak }, { label: 'Median', num: 1, get: (w) => pct(w.median) }, { label: 'Worst', num: 1, get: (w) => pct(w.worst) },
      { label: 'Best', num: 1, get: (w) => pct(w.best) }, { label: 'Beat market', get: (w) => ratio(w.beat_market, w.market_n) }, { label: 'Beat own avg', get: (w) => ratio(w.beat_own, w.own_n) },
      { label: 'Median dip', num: 1, get: (w) => pct(w.median_dip) }, { label: 'Flags', get: (w) => [w.flags, w.note].filter(Boolean).join('; ') }], ordered),
    method: () => methodHtml() + `<p class="muted">Data hash ${esc(doc.data_hash)}.</p>`,
  }
  const backHref = S.lastCompare && S.lastCompare.includes(t) ? S.lastCompare.href : null
  app.innerHTML = `
    <a class="back no-print" href="${backHref || '#/'}">← ${backHref ? 'Back to comparison' : 'New scan'}</a>
    <section class="row spread" style="align-items:flex-end">
      <h1>${esc(t)} ${doc.name ? `<small>${esc(doc.name)}</small>` : ''}</h1>
      <div class="row no-print" style="gap:8px">
        ${planButton(t).replace('class="pill"', 'class="btn"')}
        <button class="btn" data-act="addcmp">+ Add to comparison</button>
        <button class="btn" data-act="csv">CSV</button>
        <button class="btn primary" data-act="print">Print or save PDF</button>
      </div>
    </section>
    ${takeFlash()}
    <p class="muted">Daily closes ${day(isoDay(doc.first_date))} to ${day(isoDay(doc.last_date))} · ${esc(doc.completeness)} Benchmark: ${esc(S.index.benchmark)}.</p>
    ${warns.join('')}
    <div class="tiles">
      ${[['Tier 1', ...names('Tier 1')], ['Tier 2', ...names('Tier 2')], ['Watch', ...names('Watch')], ['Exit or avoid', ...names('Negative')],
        ['Chance check', perm ? pct(perm.share_at_or_above, 0, false) : 'n/a', perm ? `${perm.actual} found vs ${perm.null_mean.toFixed(1)} by chance` : '']]
        .map(([k, v, s]) => `<div class="tile"><span class="k">${k}</span><span class="v">${esc(v)}</span><span class="s">${esc(s)}</span></div>`).join('')}
    </div>
    ${banner.length ? callout('info', banner.join(' &nbsp;·&nbsp; ')) : ''}
    <div class="tabs" role="tablist" aria-label="Result views">${tabs.map(([id, l]) => `<button role="tab" aria-selected="${S.tab === id}" data-act="tab" data-v="${id}">${esc(l)}</button>`).join('')}</div>
    <section role="tabpanel" style="display:flex;flex-direction:column;gap:12px">${panel[S.tab]()}</section>`

  app.querySelectorAll('[data-act]').forEach((el) => el.addEventListener('click', () => {
    const { act, v } = el.dataset
    if (act === 'tab') S.tab = v
    if (act === 'heat') S.heatAll = v === '1'
    if (act === 'print') return window.print()
    if (act === 'csv') return download(`patterns_${t}.csv`, csv(W, Object.keys(W[0])))
    if (act === 'addcmp') { setSel([...S.sel.filter((x) => x !== t), t], 'Compare'); location.hash = '#/'; return }
    if (act === 'plan') {
      if (planItem(t)) removeFromPlan(t)
      else {
        addToPlan([t])
        S.flash = callout('info', planItem(t).w.length
          ? `Added ${esc(t)} to your <a href="#/roadmap">year roadmap</a> with its Tier 1 and Tier 2 windows. You can change which windows are used there.`
          : `Added ${esc(t)} to your <a href="#/roadmap">year roadmap</a>. It has no Tier 1 or Tier 2 window, so pick its windows there.`)
      }
    }
    renderStock(t)
  }))
  document.getElementById('yw')?.addEventListener('change', (e) => { S.yearWindow = e.target.value; renderStock(t) })
}
function describe(p) {
  const base = `${p.actual} window(s) passed the pattern filter. Shuffled data with the same yearly trends produced ${p.null_mean.toFixed(1)} on average; ${pct(p.share_at_or_above, 0, false)} of ${p.runs} shuffled runs produced as many or more.`
  if (p.share_at_or_above <= 0.05) return base + ' The patterns, as a group, are unlikely to be pure chance.'
  if (p.share_at_or_above <= 0.25) return base + ' As a group this is only modest evidence; trust patterns that also have a clear reason.'
  return base + ' As a group these patterns are consistent with chance; treat them with caution.'
}
function methodHtml() {
  const i = S.index
  const c = i.settings.classification
  return `<h2>Method</h2><ul>${i.method.map((m) => `<li>${esc(m)}</li>`).join('')}</ul>
    <h2>Classes</h2><ul>${i.classes.map((m) => `<li>${esc(m)}</li>`).join('')}</ul>
    <p class="muted">Thresholds: at least ${c.min_years} years; hit rate ${pct(c.candidate_hit_rate, 0, false)}; beat own average ${pct(c.candidate_own_rate, 0, false)}; median ${pct(c.candidate_min_median, 0, false)}; Tier 1 streak ${c.tier1_min_streak} and beat market in two thirds of years.</p>
    <h2>Caveats</h2><ul>${i.caveats.map((m) => `<li>${esc(m)}</li>`).join('')}</ul>
    <p class="muted">Code version ${esc(i.code_version)} · settings hash ${esc(i.settings_hash)} · ${esc(i.source)}.</p>`
}

// ------------------------------------------------------------------ screen 3: compare
function monthClasses(rows) {
  return Array.from({ length: 12 }, (_, i) => {
    const covering = rows.filter((w) => w.length < 12 && months(w.start_month, w.length).includes(i + 1)).map((w) => w.class)
    return ['Tier 1', 'Tier 2', 'Watch'].find((k) => covering.includes(k)) || (covering.includes('Negative') ? 'Negative' : '')
  })
}
function seasonalMap(list) {
  const now = today.getMonth()
  const names = { '': 'No pattern', Negative: 'Exit or avoid' }
  return `<div class="legend">${['Tier 1', 'Tier 2', 'Watch', 'Negative'].map((k) => `<span><i style="background:${MAP_FILL[k]}"></i>${LABEL[k] || k}</span>`).join('')}</div>
    <div style="overflow-x:auto"><div class="map"><span></span>${MONTHS.map((m, i) => `<span class="m${i === now ? ' now' : ''}">${m}</span>`).join('')}
    ${list.map((s) => `<a class="t" href="#/stock/${esc(s.ticker)}">${esc(s.ticker)}</a>${monthClasses(s.classified).map((k, i) => `<span class="c" title="${esc(`${s.ticker} ${MONTHS[i]}: ${names[k] ?? k}`)}" style="background:${MAP_FILL[k]}"></span>`).join('')}`).join('')}
    </div></div>`
}
function asOfNote(list) {
  const rows = list.flatMap((s) => s.classified.map((w) => ({ ...w, ticker: s.ticker })))
  const cal = calendar(rows.filter((w) => ['Tier 1', 'Negative'].includes(w.class)))
  const soon = cal.filter((c) => c.class === 'Tier 1' && (c.status === 'Open now' || c.days <= 31))
  const exits = cal.filter((c) => c.class === 'Negative' && c.days <= 120 && c.status === 'Upcoming')
  const cap = (items, n) => items.slice(0, n).join('; ') + (items.length > n ? `; and ${items.length - n} more` : '')
  const parts = []
  if (soon.length) parts.push('Tier 1 windows open now or opening within a month: ' + cap(soon.map((c) => `${c.ticker} ${c.window} (${c.status === 'Open now' ? 'open now' : 'opens ' + day(c.entry)})`), 12) + '.')
  if (exits.length) {
    const by = {}
    for (const c of exits) (by[c.window] ||= new Set()).add(c.ticker)
    parts.push('Exit or avoid windows in the next four months: ' + cap(Object.entries(by).map(([w, ts]) => `${w} for ${[...ts].join(', ')}`), 6) + '.')
  }
  return parts.length ? callout('info', esc(`As of ${day(today)}: ` + parts.join(' '))) : ''
}

async function renderCompare(arg) {
  const all = arg === 'all'
  const tickers = all ? S.index.stocks.map((s) => s.ticker) : arg.split(',').map((t) => t.trim().toUpperCase()).filter(Boolean)
  const missing = tickers.filter((t) => !S.byTicker.has(t))
  const scanned = tickers.filter((t) => S.byTicker.has(t)).map((t) => S.byTicker.get(t))
  S.lastCompare = { href: location.hash, includes: (t) => scanned.some((s) => s.ticker === t) }
  if (scanned.length < 2) {
    app.innerHTML = `<h1>Compare stocks</h1>${missing.map((t) => callout('warn', `No price data found for ${esc(t)}`)).join('')}<p>Pick two or more tickers on the <a href="#/">Scan</a> screen and choose <strong>Compare</strong>.</p>`
    return
  }
  let view = scanned
  if (S.filters.has('frozen')) view = view.filter((s) => !s.frozen)
  if (S.filters.has('rising')) view = view.filter((s) => s.best)
  view = [...view].sort(SORTS[S.sort])
  const nFrozen = scanned.filter((s) => s.frozen).length
  const few = view.length <= CARD_LIMIT
  let docs = []
  if (few && view.length) docs = await Promise.all(view.map((s) => stock(s.ticker)))

  const head = `
    <section class="row spread" style="align-items:flex-end">
      <div style="display:flex;flex-direction:column;gap:10px">
        <h1>Comparing ${all ? `all ${scanned.length}` : scanned.length} stocks</h1>
        <div class="row" style="gap:8px">${scanned.length <= CARD_LIMIT ? scanned.map((s) => `<a class="btn" href="#/stock/${esc(s.ticker)}" style="min-height:36px">${esc(s.ticker)}</a>`).join('') : ''}<a href="#/" style="font-size:13px">Edit list</a></div>
      </div>
      <div class="row no-print" style="gap:8px">${view.length ? `<button class="btn" data-act="planall" title="Adds each stock's Tier 1 and Tier 2 windows">+ Add ${view.length === scanned.length ? 'all' : 'the'} ${view.length} shown to roadmap</button>` : ''}<button class="btn" data-act="csv">CSV</button><button class="btn primary" data-act="print">Print or save PDF</button></div>
    </section>
    ${takeFlash()}
    ${missing.map((t) => callout('warn', `No price data found for ${esc(t)}`)).join('')}
    <section class="card no-print" style="flex-direction:row;flex-wrap:wrap;align-items:center;gap:12px">
      <button class="pill" data-act="filter" data-v="frozen" aria-pressed="${S.filters.has('frozen')}">Exclude frozen price</button>
      <button class="pill" data-act="filter" data-v="rising" aria-pressed="${S.filters.has('rising')}">Exclude no rising pattern</button>
      <label class="muted" for="sort" style="margin-left:auto">Sort by</label>
      <select id="sort">${Object.keys(SORTS).map((k) => `<option ${k === S.sort ? 'selected' : ''}>${k}</option>`).join('')}</select>
    </section>
    <p class="muted">Showing ${view.length} of ${scanned.length} stocks.${nFrozen && !S.filters.has('frozen') ? ` ${nFrozen} have frozen prices; their patterns are marked unreliable.` : ''} Exports and the chance check cover all ${scanned.length}.</p>`

  let body = ''
  if (!view.length) body = '<p class="muted">No stocks match the filters. Turn a filter off to see them.</p>'
  else if (few) {
    body = `<section class="scards">${view.map((s) => `
      <article class="scard">
        <a class="body" href="#/stock/${esc(s.ticker)}">
          <span class="row spread" style="gap:8px"><span class="tk">${esc(s.ticker)}</span><span class="muted">${s.years} yrs</span></span>
          <span class="pills">${[['Tier 1', 'T1'], ['Tier 2', 'T2'], ['Watch', 'W'], ['Negative', 'Exit']].map(([k, sh]) => badge(k, `${sh} ${s.counts[k]}`)).join('')}</span>
          <span class="muted">Best: <strong style="color:#14171F">${s.best ? `${esc(s.best.window)} ${ratio(s.best.up, s.best.n)}, median ${pct(s.best.median)}` : 'no rising pattern'}</strong></span>
          ${s.frozen ? '<span class="muted" style="color:#9A3412">Frozen price: unreliable</span>' : ''}
        </a>
        <span class="no-print">${planButton(s.ticker)}</span>
      </article>`).join('')}</section>`
  } else {
    body = `<section class="card"><h2>Stocks</h2><p class="muted">Select a row to open that stock's report.</p>${dataTable([
      { label: 'Stock', html: (s) => `<strong>${esc(s.ticker)}</strong>` }, { label: 'Years', num: 1, get: (s) => s.years },
      { label: 'Tier 1', num: 1, get: (s) => s.counts['Tier 1'] }, { label: 'Tier 2', num: 1, get: (s) => s.counts['Tier 2'] },
      { label: 'Watch', num: 1, get: (s) => s.counts.Watch }, { label: 'Emerging', num: 1, get: (s) => s.counts.Emerging },
      { label: 'Exit', num: 1, get: (s) => s.counts.Negative },
      { label: 'Best window', get: (s) => (s.best ? `${s.best.window} (${s.best.class})` : '') }, { label: 'Years up', get: (s) => (s.best ? ratio(s.best.up, s.best.n) : '') },
      { label: 'Best median', num: 1, get: (s) => (s.best ? pct(s.best.median) : '') }, { label: 'Chance check', num: 1, get: (s) => pct(s.chance, 0, false) },
      { label: 'Frozen', get: (s) => (s.frozen ? 'Frozen' : '') }, { label: 'Roadmap', html: (s) => planButton(s.ticker) }], view, { link: (s) => `#/stock/${s.ticker}` })}</section>`
  }

  let windows = ''
  if (view.length && few) {
    const order = [...docs[0].windows].sort((a, b) => a.length - b.length || a.start_month - b.start_month).map((w) => w.window)
    const rows = order.map((w) => {
      const cells = docs.map((d) => d.windows.find((x) => x.window === w))
      const shown = cells.some((c) => c && !['None', 'Insufficient history'].includes(c.class))
      if (!S.cmpAll && !shown) return ''
      return `<tr><th scope="row" style="white-space:nowrap">${esc(w)}</th>${cells.map((c) => {
        if (!c) return '<td></td>'
        const real = !['None', 'Insufficient history'].includes(c.class)
        const [bg, fg] = BADGE[c.class] || BADGE.None
        const style = real ? `background:${bg};color:${fg}` : 'background:#fff;color:#4B5160;outline:1px solid #EEF0F3'
        return `<td style="${style}"><b>${real ? esc(LABEL[c.class] || c.class) : c.class === 'Insufficient history' ? 'Short history' : ''}</b><span>${ratio(c.up, c.n)} · ${pct(c.median)}</span></td>`
      }).join('')}</tr>`
    }).join('')
    windows = `<section class="card"><div class="row spread"><h2>Window by window</h2>
      <div class="seg" role="group" aria-label="Rows to show">${['Patterns only', 'All windows'].map((m, i) => `<button data-act="cmpall" data-v="${i}" aria-pressed="${S.cmpAll === Boolean(i)}">${m}</button>`).join('')}</div></div>
      <div style="overflow-x:auto"><table class="cmp"><thead><tr><th scope="col">Window</th>${view.map((s) => `<th scope="col">${esc(s.ticker)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>
      <p class="muted">Each cell: class, years up, median return.</p></section>`
  } else if (view.length) {
    const classes = S.ranked === 'Exit or avoid' ? ['Negative'] : RISING
    const rows = view.flatMap((s) => s.classified.filter((w) => classes.includes(w.class)).map((w) => ({ ...w, ticker: s.ticker })))
    const order = { 'Tier 1': 0, 'Tier 2': 1, Watch: 2, Emerging: 3, Negative: 4 }
    rows.sort(classes[0] === 'Negative'
      ? (a, b) => a.up / a.n - b.up / b.n || a.median - b.median
      : (a, b) => order[a.class] - order[b.class] || num(b.score) - num(a.score) || b.median - a.median)
    windows = `<section class="card"><div class="row spread"><h2>Ranked patterns</h2>
      <div class="seg" role="group" aria-label="Patterns to show">${['Rising', 'Exit or avoid'].map((m) => `<button data-act="ranked" data-v="${m}" aria-pressed="${S.ranked === m}">${m}</button>`).join('')}</div></div>
      ${rows.length ? dataTable([
        { label: 'Stock', html: (w) => `<strong>${esc(w.ticker)}</strong>` }, { label: 'Window', get: (w) => w.window }, { label: 'Class', html: (w) => badge(w.class) },
        { label: 'Years up', get: (w) => ratio(w.up, w.n) }, { label: 'Streak', num: 1, get: (w) => w.streak }, { label: 'Median', num: 1, get: (w) => pct(w.median) },
        { label: 'Worst year', num: 1, get: (w) => pct(w.worst) }, { label: 'Beat market', get: (w) => ratio(w.beat_market, w.market_n) },
        { label: 'Median dip', num: 1, get: (w) => pct(w.median_dip) }, { label: 'Next entry close', get: (w) => (w.length < 12 ? day(nextDates(w.start_month, w.length).entry) : '') },
        { label: 'Flags', get: (w) => w.flags || '' },
        ...(classes[0] === 'Negative' ? [] : [{ label: 'Roadmap', html: (w) => {
          const on = Boolean(planItem(w.ticker)?.w.includes(wkey(w)))
          return `<button class="pill" data-act="planw" data-v="${esc(w.ticker)}|${wkey(w)}" aria-pressed="${on}" aria-label="${on ? 'Remove' : 'Add'} ${esc(w.ticker)} ${esc(w.window)} ${on ? 'from' : 'to'} roadmap">${on ? '✓ Added' : '+ Add'}</button>`
        } }])], rows, { link: (w) => `#/stock/${w.ticker}` }) : '<p class="muted">None among the stocks shown.</p>'}
      <p class="muted">${rows.length} windows, strongest first. Select a row to open that stock's report.</p></section>`
  }

  const perm = S.index.permutation
  const each = scanned.length <= CARD_LIMIT
    ? `<br><strong>Each stock</strong> (share of shuffles with as many patterns): ${scanned.map((s) => `${esc(s.ticker)} ${pct(s.chance, 0, false)}`).join('; ')}.`
    : '<br>Each stock\'s own figure is in the Chance check column above and on its report.'
  const chance = perm ? callout('plain', `<strong>Chance check, whole market (all ${S.index.stocks.length} stocks):</strong> ${esc(describe(perm))}${each}<br>Picking stocks because they already showed patterns flatters them; the whole-market figure is the fair test.`) : ''

  app.innerHTML = `${head}${body}${view.length ? `<section class="card"><h2>Seasonal map</h2><p class="muted">Strongest class covering each month. Read down a column to see which stocks move together. The dark month is today (${day(today)}).</p>${seasonalMap(view)}${asOfNote(view)}</section>` : ''}${windows}${chance}`

  wireRowLinks()
  app.querySelectorAll('[data-act]').forEach((el) => el.addEventListener('click', () => {
    const { act, v } = el.dataset
    if (act === 'filter') S.filters.has(v) ? S.filters.delete(v) : S.filters.add(v)
    if (act === 'cmpall') S.cmpAll = v === '1'
    if (act === 'ranked') S.ranked = v
    if (act === 'plan') planItem(v) ? removeFromPlan(v) : addToPlan([v])
    if (act === 'planw') { const [t, key] = v.split('|'); toggleWindow(t, key) }
    if (act === 'planall') S.flash = addedMessage(addToPlan(view.map((s) => s.ticker), true))
    if (act === 'print') return window.print()
    if (act === 'csv') {
      const rows = scanned.map((s) => ({ ticker: s.ticker, name: s.name, sector: s.sector, years: s.years, frozen: s.frozen, tier1: s.counts['Tier 1'], tier2: s.counts['Tier 2'],
        watch: s.counts.Watch, emerging: s.counts.Emerging, exit_or_avoid: s.counts.Negative, best_window: s.best?.window, best_class: s.best?.class, best_median: s.best?.median, chance_share: s.chance }))
      return download(`compare_${scanned.length}_stocks.csv`, csv(rows, Object.keys(rows[0])))
    }
    renderCompare(arg)
  }))
  document.getElementById('sort').addEventListener('change', (e) => { S.sort = e.target.value; renderCompare(arg) })
}

// ------------------------------------------------------------------ screen 4: year roadmap
const ROLE = { buy: 'Buy', buysell: 'Buy + sell', hold: 'Hold', sell: 'Sell', avoid: 'Avoid' }
const SHORT = { 'Tier 1': 'T1', 'Tier 2': 'T2', Watch: 'W', Emerging: 'E', Negative: 'Exit' }
const CLASS_RANK = { 'Tier 1': 0, 'Tier 2': 1, Watch: 2, Emerging: 3 }
const isoDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

function avoidText(ws) {
  const falls = ws.map((w) => w.n - w.up)
  const sameN = ws.every((w) => w.n === ws[0].n)
  const lo = Math.min(...falls), hi = Math.max(...falls)
  const fell = sameN ? `fell in ${lo === hi ? lo : `${lo} to ${hi}`} of ${ws[0].n} years` : 'fell in most years'
  return `${ws.map((w) => w.window).join(', ')} · ${fell}`
}
function boardRow(c) {
  const w = c.w
  const stats = `up ${w.up} of ${w.n} years, median ${pct(w.median)}`
  const detail = {
    buy: () => `${w.window} · buy at the close of ${shortDay(c.entry)} · ${stats}`,
    buysell: () => `${w.window} · buy at the close of ${shortDay(c.entry)}, sell ${shortDay(c.exit)} · ${stats}`,
    hold: () => `${w.window} · hold until ${shortDay(c.exit)}`,
    sell: () => `${w.window} · sell at the close of ${shortDay(c.exit)}`,
    avoid: () => avoidText(c.ws),
  }[c.role]()
  return `<li class="r ${c.role}"><span class="tag">${ROLE[c.role]}</span><span class="who"><a href="#/stock/${esc(c.ticker)}">${esc(c.ticker)}</a>${badge(w.class, SHORT[w.class])}${c.frozen ? '<span class="frz" title="Frozen price: this stock\'s patterns are unreliable">frozen</span>' : ''}</span><span class="d">${esc(detail)}</span></li>`
}

function renderRoadmap(yearArg, itemsArg) {
  let shared = yearArg ? decodePlan(yearArg, itemsArg) : null
  if (shared) {
    shared.items = shared.items.filter((i) => S.byTicker.has(i.t))
    if (encodePlan(shared) === encodePlan(S.plan)) { history.replaceState(null, '', '#/roadmap'); shared = null } // it is this browser's own plan
  }
  const plan = shared ? { ...shared, exits: S.plan.exits } : S.plan
  const editable = !shared
  const rerender = () => (shared ? renderRoadmap(yearArg, itemsArg) : renderRoadmap())
  const n = plan.items.length
  const board = monthBoard(plan, S.byTicker)
  const thisYear = today.getFullYear()
  const years = [...new Set([thisYear, thisYear + 1, thisYear + 2, plan.year])].sort()
  const nowM = plan.year === thisYear ? today.getMonth() : -1
  const pastBefore = plan.year < thisYear ? 12 : plan.year === thisYear ? today.getMonth() : 0
  const nWindows = plan.items.reduce((a, i) => a + i.w.length, 0)

  const head = `
    <section class="row spread" style="align-items:flex-end">
      <div style="display:flex;flex-direction:column;gap:6px">
        <h1>Year roadmap <small>${plan.year}</small></h1>
        <p class="lede">When to buy, hold and sell the stocks you picked, from each stock's strongest seasonal windows. Add stocks from <a href="#/compare/all">Compare</a> or from a stock's report.</p>
      </div>
      <div class="row no-print" style="gap:8px">
        <label class="muted" for="plan-year">Year</label>
        <select id="plan-year">${years.map((y) => `<option ${y === plan.year ? 'selected' : ''}>${y}</option>`).join('')}</select>
        ${n ? `<button class="btn" data-act="share">Copy share link</button><button class="btn" data-act="csv">CSV</button>
        <button class="btn" data-act="ics" title="Buy and sell dates as all-day events for Google, Apple or Outlook Calendar">Calendar (.ics)</button>
        <button class="btn primary" data-act="print">Print or save PDF</button>` : ''}
      </div>
    </section>
    ${takeFlash()}
    ${shared ? callout('info', `<strong>This is a shared roadmap</strong> (${n} stock${n === 1 ? '' : 's'}). It is not saved in this browser.
      <span class="row no-print" style="gap:8px;margin-top:8px"><button class="btn" data-act="adopt">Save as my roadmap</button><a href="#/roadmap">Open my roadmap</a></span>`) : ''}`

  if (!n) {
    app.innerHTML = `${head}
      <section class="card"><h2>${shared ? 'This shared roadmap has no stocks' : 'Your roadmap is empty'}</h2>
        <ol class="steps"><li>Open <strong>Compare</strong> and narrow the list with the filters and sorting.</li>
          <li>Choose <strong>+ Roadmap</strong> on the stocks you want, or <strong>+ Add the stocks shown to roadmap</strong>. A stock's report has the same button.</li>
          <li>Come back here to see the months laid out, switch windows on or off, and export the plan.</li></ol>
        <div class="row"><a class="btn primary" href="#/compare/all">Compare all stocks ${ICON_ARROW}</a><a class="btn" href="#/compare/${RESEARCH_TIER1.join(',')}">Compare the research Tier 1 stocks</a></div>
      </section>`
    wireRoadmap()
    return
  }

  const monthsHtml = `<section class="months">${board.map((cells, m) => `
    <article class="mbox${m === nowM ? ' now' : ''}${m < pastBefore ? ' past' : ''}">
      <h3>${MONTHS_LONG[m]}${m === nowM ? ' <span class="badge" style="background:#14171F;color:#fff">This month</span>' : ''}</h3>
      ${cells.length ? `<ul>${cells.map(boardRow).join('')}</ul>` : '<p class="muted">Nothing planned.</p>'}
    </article>`).join('')}</section>`

  const stocks = plan.items.map((i) => {
    const s = S.byTicker.get(i.t)
    const pick = s.classified.filter((w) => PICKABLE.includes(w.class) && w.length < 12)
      .sort((a, b) => CLASS_RANK[a.class] - CLASS_RANK[b.class] || a.start_month - b.start_month || a.length - b.length)
    const exits = s.classified.filter((w) => w.class === 'Negative' && w.length < 12)
    const pill = (w) => {
      const on = i.w.includes(wkey(w))
      const inner = `<b>${SHORT[w.class]}</b> ${esc(w.window)} <span>${ratio(w.up, w.n)} · ${pct(w.median)}</span>`
      return editable
        ? `<button class="pill win" data-act="win" data-v="${esc(i.t)}|${wkey(w)}" aria-pressed="${on}" aria-label="${esc(`${w.window} ${w.class}, up ${w.up} of ${w.n} years`)}">${inner}</button>`
        : on ? `<span class="pill win" aria-pressed="true">${inner}</span>` : ''
    }
    return `<div class="pstock">
      <div class="row spread" style="gap:8px">
        <span><a class="tk" href="#/stock/${esc(i.t)}">${esc(i.t)}</a> <span class="muted">${esc(s.name || s.sector || '')}</span>
          ${s.frozen ? '<span class="frz">Frozen price: unreliable</span>' : ''}</span>
        ${editable ? `<button class="btn small no-print" data-act="remove" data-v="${esc(i.t)}" aria-label="Remove ${esc(i.t)} from roadmap">Remove</button>` : ''}
      </div>
      <div class="row" style="gap:6px">${pick.length ? pick.map(pill).join('') : '<span class="muted">No rising windows.</span>'}
        ${!i.w.length ? '<span class="muted">No windows chosen, so this stock is not on the calendar.</span>' : ''}</div>
      ${exits.length ? `<p class="muted">Exit or avoid: ${exits.map((w) => `${esc(w.window)} (fell in ${w.n - w.up} of ${w.n} years)`).join(', ')}</p>` : ''}
    </div>`
  }).join('')

  app.innerHTML = `${head}
    ${callout('warn', `<strong>A plan from past patterns, not a forecast.</strong> Windows come from closing prices up to ${day(isoDay(S.index.snapshot_date))}; no ${plan.year} prices are in the data. <em>Buy</em> means at the close of the last business day before the window starts, <em>sell</em> at the close of its last month. NGX holidays are not modelled. Not investment advice.`)}
    <section class="row no-print" style="gap:12px">
      <button class="pill" data-act="exits" aria-pressed="${plan.exits}">Show exit or avoid months</button>
      <span class="muted">${n} stock${n === 1 ? '' : 's'} · ${nWindows} window${nWindows === 1 ? '' : 's'} on the calendar</span>
    </section>
    ${nWindows ? '' : callout('info', 'No windows are switched on yet. Pick some under <strong>Stocks in this roadmap</strong> below.')}
    ${monthsHtml}
    <section class="card">
      <div class="row spread"><h2>Stocks in this roadmap (${n})</h2>${editable ? '<button class="btn small no-print" data-act="clear">Clear roadmap</button>' : ''}</div>
      ${editable ? '<p class="muted no-print">Switch windows on or off. A stock starts with its Tier 1 and Tier 2 windows, leaving out any that overlap a stronger one. T1 Tier 1, T2 Tier 2, W Watch, E Emerging; each shows years up and median return.</p>' : ''}
      <div class="plist">${stocks}</div>
    </section>`
  wireRoadmap()

  function wireRoadmap() {
    document.getElementById('plan-year').addEventListener('change', (e) => {
      const y = Number(e.target.value)
      if (editable) { S.plan.year = y; savePlan(); rerender() } else location.hash = `#/roadmap/${encodePlan({ ...plan, year: y })}`
    })
    app.querySelectorAll('[data-act]').forEach((el) => el.addEventListener('click', async () => {
      const { act, v } = el.dataset
      if (act === 'print') return window.print()
      if (act === 'ics') return download(`roadmap_${plan.year}.ics`, calendarFile(plan, S.byTicker), 'text/calendar')
      if (act === 'csv') {
        const rows = trades(plan, S.byTicker).map((r) => ({ type: r.planned ? 'Planned' : 'Exit or avoid', ticker: r.ticker, name: r.name, window: r.w.window,
          class: r.w.class, buy_at_close_of: isoDate(r.entry), sell_at_close_of: isoDate(r.exit), years_up: r.w.up, years: r.w.n, median_return: r.w.median, frozen_price: r.frozen }))
        return download(`roadmap_${plan.year}.csv`, csv(rows, ['type', 'ticker', 'name', 'window', 'class', 'buy_at_close_of', 'sell_at_close_of', 'years_up', 'years', 'median_return', 'frozen_price']))
      }
      if (act === 'share') {
        const url = `${location.origin}${location.pathname}#/roadmap/${encodePlan(plan)}`
        let copied = false
        try { await navigator.clipboard.writeText(url); copied = true } catch { /* not allowed: show the link to copy by hand */ }
        S.flash = callout('info', `${copied ? '<strong>Link copied.</strong>' : '<strong>Copy this link:</strong>'} <input class="linkbox" readonly value="${esc(url)}" aria-label="Share link"> It holds only the year, tickers and windows.`)
      }
      if (act === 'exits') { S.plan.exits = !S.plan.exits; savePlan() }
      if (act === 'win') { const [t, key] = v.split('|'); toggleWindow(t, key) }
      if (act === 'remove') removeFromPlan(v)
      if (act === 'clear' && window.confirm(`Remove all ${n} stocks from your roadmap?`)) { S.plan.items = []; savePlan() }
      if (act === 'adopt') {
        if (S.plan.items.length && !window.confirm(`Replace your roadmap (${S.plan.items.length} stocks) with this one?`)) return
        S.plan = { year: plan.year, exits: S.plan.exits, items: plan.items.map((i) => ({ t: i.t, w: [...i.w] })) }
        savePlan()
        S.flash = callout('info', 'Saved as your roadmap in this browser.')
        location.hash = '#/roadmap'
        return
      }
      rerender()
      if (act === 'share') app.querySelector('.linkbox')?.select()
    }))
  }
}

boot().catch((err) => {
  app.innerHTML = `<h1>Could not load the data</h1><p class="muted">${esc(err.message)}</p>`
})
