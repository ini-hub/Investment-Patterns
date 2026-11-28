// Year roadmap: which months to buy, hold and sell the stocks a visitor has picked.
// Pure functions only (no DOM), shared by app.js and the tests in tests/site/.
//
// A plan is { year, exits, items: [{ t: 'FCMB', w: ['10.3', '1.1'] }] }, where each window key is
// `${start_month}.${length}`. Plans live in the visitor's browser and in share links; they hold
// tickers and window keys only.

export const PLAN_CLASSES = ['Tier 1', 'Tier 2'] // placed automatically when a stock is added
export const PICKABLE = ['Tier 1', 'Tier 2', 'Watch', 'Emerging'] // can be switched on per stock
const RANK = { 'Tier 1': 0, 'Tier 2': 1, Watch: 2, Emerging: 3 }
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export const wkey = (w) => `${w.start_month}.${w.length}`

// Last business day (Mon to Fri) of month m0 (0-based; may be negative or above 11) of year y.
export function lastBday(y, m0) {
  const d = new Date(y, m0 + 1, 0)
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() - 1)
  return d
}

function monthsOf(w) {
  return Array.from({ length: w.length }, (_, i) => (w.start_month - 1 + i) % 12)
}

// Default windows for a newly added stock: its Tier 1 and Tier 2 windows, strongest first, skipping any
// that overlap a month already taken, so one stock never asks you to buy twice for the same months.
export function defaultWindows(classified) {
  const candidates = classified
    .filter((w) => PLAN_CLASSES.includes(w.class) && w.length < 12)
    .sort((a, b) => RANK[a.class] - RANK[b.class] || (b.score ?? -9) - (a.score ?? -9))
  const used = new Set()
  const keys = []
  for (const w of candidates) {
    const ms = monthsOf(w)
    if (ms.some((m) => used.has(m))) continue
    ms.forEach((m) => used.add(m))
    keys.push(wkey(w))
  }
  return keys
}

// Occurrences of window w that touch `year`: one starting the year before (it may run into January)
// and one starting in `year`. Entry is the close of the last business day before the window starts;
// exit is the close of the last business day of its last month. `cells` are the months inside `year`.
export function occurrences(w, year) {
  if (w.length >= 12) return []
  const out = []
  for (const y0 of [year - 1, year]) {
    const cells = []
    for (let i = 0; i < w.length; i++) {
      const abs = w.start_month - 1 + i
      if (y0 + Math.floor(abs / 12) !== year) continue
      const role = w.length === 1 ? 'buysell' : i === 0 ? 'buy' : i === w.length - 1 ? 'sell' : 'hold'
      cells.push({ m0: abs % 12, role })
    }
    if (cells.length) {
      out.push({ startYear: y0, entry: lastBday(y0, w.start_month - 2), exit: lastBday(y0, w.start_month - 2 + w.length), cells })
    }
  }
  return out
}

const ROLE_ORDER = { buy: 0, buysell: 1, sell: 2, hold: 3, avoid: 4 }

// Twelve lists (January to December) of { ticker, w, role, entry, exit, frozen }.
// role: buy, hold, sell, buysell (a one-month window) or avoid. A planned stock's exit-or-avoid windows
// that cover the same month are merged into one avoid entry whose `ws` lists them all; none is shown in a
// month where that stock is already planned.
export function monthBoard(plan, byTicker) {
  const board = Array.from({ length: 12 }, () => [])
  for (const item of plan.items) {
    const s = byTicker.get(item.t)
    if (!s) continue
    const avoid = Array.from({ length: 12 }, () => [])
    for (const w of s.classified) {
      const planned = item.w.includes(wkey(w))
      if (!planned && !(plan.exits && w.class === 'Negative')) continue
      for (const occ of occurrences(w, plan.year)) {
        for (const c of occ.cells) {
          if (planned) board[c.m0].push({ ticker: s.ticker, w, role: c.role, entry: occ.entry, exit: occ.exit, frozen: s.frozen })
          else if (!avoid[c.m0].includes(w)) avoid[c.m0].push(w)
        }
      }
    }
    avoid.forEach((ws, m0) => {
      // Skip months where this stock is already planned: the planned window is the stronger, deliberate choice.
      if (!ws.length || board[m0].some((c) => c.ticker === s.ticker)) return
      ws.sort((a, b) => a.start_month - b.start_month || a.length - b.length)
      board[m0].push({ ticker: s.ticker, w: ws[0], ws, role: 'avoid', frozen: s.frozen })
    })
  }
  for (const cells of board) cells.sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role] || a.ticker.localeCompare(b.ticker))
  return board
}

// One row per occurrence touching the plan year, sorted by entry date: planned windows, then (if
// plan.exits) exit-or-avoid windows. Used for the CSV and the calendar file.
export function trades(plan, byTicker) {
  const rows = []
  for (const item of plan.items) {
    const s = byTicker.get(item.t)
    if (!s) continue
    for (const w of s.classified) {
      const planned = item.w.includes(wkey(w))
      if (!planned && !(plan.exits && w.class === 'Negative')) continue
      for (const occ of occurrences(w, plan.year)) {
        rows.push({ ticker: s.ticker, name: s.name, w, planned, entry: occ.entry, exit: occ.exit, frozen: s.frozen })
      }
    }
  }
  return rows.sort((a, b) => b.planned - a.planned || a.entry - b.entry || a.ticker.localeCompare(b.ticker))
}

// Share links: #/roadmap/<year>/<TICKER>:<key>:<key>,<TICKER>:<key>
export function encodePlan(plan) {
  return `${plan.year}/` + plan.items.map((i) => [encodeURIComponent(i.t), ...i.w].join(':')).join(',')
}
export function decodePlan(yearText, itemsText) {
  const year = Number(yearText)
  if (!Number.isInteger(year) || year < 2000 || year > 2100) return null
  const items = []
  for (const part of String(itemsText || '').split(',')) {
    const [t, ...keys] = part.split(':')
    const ticker = decodeURIComponent(t || '').trim().toUpperCase()
    if (!ticker || items.some((i) => i.t === ticker)) continue
    items.push({ t: ticker, w: [...new Set(keys.filter((k) => /^([1-9]|1[0-2])\.([1-9]|1[0-1])$/.test(k)))] })
  }
  return { year, exits: true, items }
}

// ------------------------------------------------------------------ calendar file (RFC 5545)
const pad = (n) => String(n).padStart(2, '0')
const ymd = (d) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`
const icsText = (s) => String(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\n/g, '\\n')
export const shortDay = (d) => `${d.getDate()} ${MON[d.getMonth()]} ${d.getFullYear()}`
function pctText(v) {
  if (v == null || Number.isNaN(v)) return 'n/a'
  const x = v * 100
  return (x > 0 ? '+' : '') + x.toFixed(1) + '%'
}
function fold(line) {
  // Lines longer than 75 octets continue on the next line after a space. Text here is ASCII.
  if (line.length <= 75) return line
  const parts = [line.slice(0, 75)]
  for (let i = 75; i < line.length; i += 74) parts.push(' ' + line.slice(i, i + 74))
  return parts.join('\r\n')
}

// All-day "Buy" and "Sell" events for every planned window occurrence in the plan year.
export function calendarFile(plan, byTicker, now = new Date()) {
  const stamp = now.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Investment Patterns//Year roadmap//EN', 'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH', `X-WR-CALNAME:${icsText(`Seasonal roadmap ${plan.year}`)}`]
  for (const r of trades(plan, byTicker).filter((x) => x.planned)) {
    const facts = `${r.w.window} window (${r.w.class}): up in ${r.w.up} of ${r.w.n} years, median ${pctText(r.w.median)}. ` +
      `Buy at the close of ${shortDay(r.entry)}, sell at the close of ${shortDay(r.exit)}.` +
      (r.frozen ? ' Frozen price: this stock\'s patterns are unreliable.' : '') +
      ' Past seasonal behaviour does not guarantee future results. Research tool, not investment advice.'
    for (const [kind, date] of [['Buy', r.entry], ['Sell', r.exit]]) {
      const next = new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1)
      lines.push('BEGIN:VEVENT', `UID:${kind.toLowerCase()}-${r.ticker}-${wkey(r.w)}-${ymd(date)}@invest.bolujo.com`, `DTSTAMP:${stamp}`,
        `DTSTART;VALUE=DATE:${ymd(date)}`, `DTEND;VALUE=DATE:${ymd(next)}`,
        `SUMMARY:${icsText(`${kind} ${r.ticker} at the close (${r.w.window}, ${r.w.class})`)}`,
        `DESCRIPTION:${icsText(facts)}`, 'TRANSP:TRANSPARENT', 'END:VEVENT')
    }
  }
  lines.push('END:VCALENDAR')
  return lines.map(fold).join('\r\n') + '\r\n'
}
