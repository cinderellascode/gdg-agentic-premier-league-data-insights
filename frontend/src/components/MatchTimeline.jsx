import { useEffect, useState } from 'react'
import { explainTimelineEvent, fetchTimeline } from '../api'

const ICONS = {
  goal: '⚽',
  card: '🟨',
  substitution: '🔄',
}

function eventLabel(ev) {
  if (ev.event_type === 'goal') {
    const assist = ev.related_player ? ` (assist: ${ev.related_player})` : ''
    return `${ev.player_name || 'Goal'}${assist}`
  }
  if (ev.event_type === 'card') {
    return `${ev.player_name || 'Player'} — ${ev.detail || 'Card'}`
  }
  if (ev.event_type === 'substitution') {
    const off = ev.related_player ? ` ↔ ${ev.related_player}` : ''
    return `${ev.player_name || 'Sub'}${off}`
  }
  return ev.detail || ev.event_type
}

export default function MatchTimeline({ matchId }) {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState(null)
  const [insight, setInsight] = useState(null)
  const [explaining, setExplaining] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchTimeline(matchId)
      .then((data) => setEvents(data.events || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false))
  }, [matchId])

  async function onSelect(ev) {
    setSelectedId(ev.event_id)
    setInsight(null)
    setExplaining(true)
    try {
      const res = await explainTimelineEvent(matchId, ev.event_id)
      setInsight(res.insight)
    } catch {
      setInsight('Could not load AI explanation for this moment.')
    } finally {
      setExplaining(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500 animate-pulse">Loading timeline…</p>
  }

  if (events.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No timeline events yet. Run{' '}
        <code className="rounded bg-slate-800 px-1 text-xs">python data_loader.py --backfill-events</code>{' '}
        in the backend.
      </p>
    )
  }

  return (
    <section className="rounded-2xl border border-slate-700/60 bg-pitch-light/60 p-6">
      <h2 className="mb-4 font-display text-xl font-semibold text-white">Match timeline</h2>
      <p className="mb-4 text-sm text-slate-400">Click a moment for an AI take on its impact.</p>

      <div className="relative overflow-x-auto pb-2">
        <div className="flex min-w-max items-start gap-0 px-2">
          <div className="absolute left-4 right-4 top-8 h-0.5 bg-slate-600" aria-hidden />
          {events.map((ev) => {
            const active = selectedId === ev.event_id
            const icon = ICONS[ev.event_type] || '•'
            const isRed =
              ev.event_type === 'card' &&
              String(ev.detail || '').toLowerCase().includes('red')

            return (
              <button
                key={ev.event_id}
                type="button"
                onClick={() => onSelect(ev)}
                className={`relative z-10 flex w-28 flex-col items-center px-2 text-center transition ${
                  active ? 'scale-105' : 'opacity-90 hover:opacity-100'
                }`}
              >
                <span
                  className={`mb-2 flex h-14 w-14 items-center justify-center rounded-full border-2 text-lg ${
                    active
                      ? 'border-grass bg-grass/20'
                      : isRed
                        ? 'border-rose-500/60 bg-rose-500/10'
                        : 'border-slate-600 bg-slate-800'
                  }`}
                >
                  {icon}
                </span>
                <span className="font-display text-sm font-bold text-grass">{ev.minute}&apos;</span>
                <span className="mt-1 line-clamp-2 text-[11px] leading-tight text-slate-300">
                  {eventLabel(ev)}
                </span>
                <span className="text-[10px] text-slate-500">{ev.team}</span>
              </button>
            )
          })}
        </div>
      </div>

      {(explaining || insight) && (
        <div className="mt-6 rounded-xl border border-grass/30 bg-grass/5 p-4">
          {explaining ? (
            <p className="text-sm text-slate-400 animate-pulse">Analyzing this moment…</p>
          ) : (
            <p className="text-sm leading-relaxed text-slate-200">{insight}</p>
          )}
        </div>
      )}
    </section>
  )
}
