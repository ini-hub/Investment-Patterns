// Unit tests for site/roadmap.js. Run with: node --test tests/site/
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { calendarFile, decodePlan, defaultWindows, encodePlan, lastBday, monthBoard, occurrences, stockGrid, trades, wkey } from '../../site/roadmap.js'

const w = (window, start_month, length, cls, extra = {}) => ({ window, start_month, length, class: cls, n: 10, up: 9, median: 0.1, score: 0.5, ...extra })
const FCMB = {
  ticker: 'FCMB', name: 'FCMB Group Plc', frozen: false,
  classified: [
    w('Oct-Dec', 10, 3, 'Tier 1', { score: 0.93 }),
    w('Jan', 1, 1, 'Tier 1', { score: 0.84 }),
    w('Dec-Jan', 12, 2, 'Tier 1', { score: 0.8 }),
    w('Nov', 11, 1, 'Watch'),
    w('Aug-Sep', 8, 2, 'Negative', { up: 2 }),
    w('Full year', 1, 12, 'Tier 2'),
  ],
}
const ETI = { ticker: 'ETI', name: '', frozen: true, classified: [w('Nov-Jan', 11, 3, 'Tier 2')] }
const byTicker = new Map([['FCMB', FCMB], ['ETI', ETI]])
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

test('lastBday skips weekends and crosses year ends', () => {
  assert.equal(iso(lastBday(2027, 9)), '2027-10-29') // 31 Oct 2027 is a Sunday
  assert.equal(iso(lastBday(2027, -1)), '2026-12-31') // December of the year before
  assert.equal(iso(lastBday(2027, 12)), '2028-01-31')
})

test('defaultWindows takes Tier 1 and Tier 2, strongest first, without overlapping months', () => {
  assert.deepEqual(defaultWindows(FCMB.classified), ['10.3', '1.1']) // Dec-Jan overlaps both; Watch and Full year are left out
  assert.deepEqual(defaultWindows(ETI.classified), ['11.3'])
  assert.deepEqual(defaultWindows([w('Nov', 11, 1, 'Watch')]), [])
})

test('occurrences: a window that wraps into January shows in both years', () => {
  const occ = occurrences(w('Nov-Jan', 11, 3, 'Tier 2'), 2027)
  assert.equal(occ.length, 2)
  assert.deepEqual(occ[0].cells, [{ m0: 0, role: 'sell' }]) // the Nov 2026 occurrence ends in Jan 2027
  assert.equal(iso(occ[0].exit), '2027-01-29')
  assert.deepEqual(occ[1].cells, [{ m0: 10, role: 'buy' }, { m0: 11, role: 'hold' }])
  assert.equal(iso(occ[1].entry), '2027-10-29')
  assert.equal(iso(occ[1].exit), '2028-01-31')
})

test('occurrences: a one-month January window is bought at the close of the previous December', () => {
  const [occ] = occurrences(w('Jan', 1, 1, 'Tier 1'), 2027)
  assert.deepEqual(occ.cells, [{ m0: 0, role: 'buysell' }])
  assert.equal(iso(occ.entry), '2026-12-31')
  assert.equal(iso(occ.exit), '2027-01-29')
  assert.deepEqual(occurrences(w('Full year', 1, 12, 'Tier 1'), 2027), [])
})

test('monthBoard places planned windows and, optionally, exit-or-avoid markers', () => {
  const plan = { year: 2027, exits: true, items: [{ t: 'FCMB', w: ['10.3', '1.1'] }, { t: 'ETI', w: ['11.3'] }, { t: 'GONE', w: ['1.1'] }] }
  const board = monthBoard(plan, byTicker)
  const at = (m0) => board[m0].map((c) => `${c.role} ${c.ticker} ${c.w.window}`)
  assert.deepEqual(at(0), ['buysell FCMB Jan', 'sell ETI Nov-Jan'])
  assert.deepEqual(at(7), ['avoid FCMB Aug-Sep'])
  assert.deepEqual(at(9), ['buy FCMB Oct-Dec'])
  assert.deepEqual(at(10), ['buy ETI Nov-Jan', 'hold FCMB Oct-Dec'])
  assert.deepEqual(at(11), ['sell FCMB Oct-Dec', 'hold ETI Nov-Jan'])
  assert.deepEqual(monthBoard({ ...plan, exits: false }, byTicker)[7], [])

  // Overlapping exit windows of one stock become a single avoid entry per month
  const many = { ...FCMB, classified: [...FCMB.classified, w('Aug', 8, 1, 'Negative', { up: 1 })] }
  const merged = monthBoard({ year: 2027, exits: true, items: [{ t: 'FCMB', w: [] }] }, new Map([['FCMB', many]]))
  assert.deepEqual(merged[7].map((c) => [c.role, c.ws.map((x) => x.window)]), [['avoid', ['Aug', 'Aug-Sep']]])
  // ...and are not shown in a month where the same stock is planned
  const clash = monthBoard({ year: 2027, exits: true, items: [{ t: 'FCMB', w: ['9.1'] }] },
    new Map([['FCMB', { ...FCMB, classified: [...FCMB.classified, w('Sep', 9, 1, 'Tier 2')] }]]))
  assert.deepEqual(clash[7].map((c) => c.role), ['avoid'])
  assert.deepEqual(clash[8].map((c) => c.role), ['buysell'])
  assert.deepEqual(merged[8].map((c) => c.ws.map((x) => x.window)), [['Aug-Sep']])
})

test('stockGrid gives one code per stock and month, A to Z', () => {
  const plan = { year: 2027, exits: true, items: [{ t: 'FCMB', w: ['10.3', '1.1'] }, { t: 'ETI', w: ['11.3'] }] }
  const grid = stockGrid(plan, monthBoard(plan, byTicker))
  assert.deepEqual(grid.map((r) => r.ticker), ['ETI', 'FCMB'])
  const codes = (t) => grid.find((r) => r.ticker === t).months.map((m) => m.code || '.').join(' ')
  assert.equal(codes('FCMB'), 'buysell . . . . . . avoid avoid buy hold sell')
  assert.equal(codes('ETI'), 'sell . . . . . . . . . buy hold')
  // Selling one window (Oct-Dec) and buying another (Dec-Jan) in the same month is shown as buysell
  const both = { year: 2027, exits: false, items: [{ t: 'FCMB', w: ['10.3', '12.2'] }] }
  assert.equal(stockGrid(both, monthBoard(both, byTicker))[0].months[11].code, 'buysell')
})

test('trades lists planned windows first, by entry date', () => {
  const rows = trades({ year: 2027, exits: true, items: [{ t: 'FCMB', w: ['10.3', '1.1'] }, { t: 'ETI', w: ['11.3'] }] }, byTicker)
  assert.deepEqual(rows.map((r) => `${r.planned ? 'plan' : 'avoid'} ${r.ticker} ${r.w.window} ${iso(r.entry)}`), [
    'plan ETI Nov-Jan 2026-10-30', 'plan FCMB Jan 2026-12-31', 'plan FCMB Oct-Dec 2027-09-30', 'plan ETI Nov-Jan 2027-10-29',
    'avoid FCMB Aug-Sep 2027-07-30',
  ])
})

test('share links round-trip and ignore junk', () => {
  const plan = { year: 2027, exits: true, items: [{ t: 'FCMB', w: ['10.3', '1.1'] }, { t: 'ETI', w: [] }] }
  const [year, items] = encodePlan(plan).split('/')
  assert.deepEqual(decodePlan(year, items), plan)
  assert.equal(decodePlan('abc', 'FCMB:1.1'), null)
  assert.deepEqual(decodePlan('2027', 'fcmb:1.1:99.9:1.1,FCMB:2.2,').items, [{ t: 'FCMB', w: ['1.1'] }])
})

test('calendarFile writes a Buy and a Sell event per planned occurrence', () => {
  const plan = { year: 2027, exits: true, items: [{ t: 'FCMB', w: ['10.3'] }, { t: 'ETI', w: ['11.3'] }] }
  const ics = calendarFile(plan, byTicker, new Date(Date.UTC(2026, 10, 28, 12, 0, 0)))
  assert.ok(ics.startsWith('BEGIN:VCALENDAR\r\nVERSION:2.0\r\n'))
  assert.ok(ics.endsWith('END:VCALENDAR\r\n'))
  assert.equal(ics.match(/BEGIN:VEVENT/g).length, 6) // FCMB Oct-Dec 2027, ETI Nov-Jan from 2026 and from 2027
  assert.ok(ics.includes('DTSTART;VALUE=DATE:20270930\r\nDTEND;VALUE=DATE:20271001'))
  assert.ok(ics.includes('SUMMARY:Buy FCMB at the close (Oct-Dec\\, Tier 1)'))
  const unfolded = ics.replace(/\r\n /g, '')
  assert.ok(unfolded.includes('Frozen price: this stock\'s patterns are unreliable.'))
  assert.ok(!unfolded.includes('Aug-Sep')) // exit-or-avoid windows are not calendar events
  for (const line of ics.split('\r\n')) assert.ok(line.length <= 75, line)
  assert.equal(wkey(FCMB.classified[0]), '10.3')
})
