import { useState } from 'react'
import { comparePlayers } from '../api'
import { useFanMode } from '../context/FanModeContext'
import StatTooltip from './StatTooltip'

export default function PlayerComparison({ matchId, players = [] }) {
  const { mode } = useFanMode()
  const [playerA, setPlayerA] = useState('')
  const [playerB, setPlayerB] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const sorted = [...players].sort((a, b) =>
    (a.player_name || '').localeCompare(b.player_name || ''),
  )

  async function runCompare() {
    if (!playerA || !playerB || playerA === playerB) {
      setError('Pick two different players.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const data = await comparePlayers(matchId, Number(playerA), Number(playerB))
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Comparison failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-2xl border border-slate-700/60 bg-pitch-light/60 p-6">
      <h2 className="mb-2 font-display text-xl font-semibold text-white">Compare players</h2>
      <p className="mb-4 text-sm text-slate-400">
        Side-by-side stats with an AI verdict for this match.
        {mode === 'analyst' && ' Raw numbers shown for every metric.'}
      </p>

      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <select
          value={playerA}
          onChange={(e) => setPlayerA(e.target.value)}
          className="rounded-xl border border-slate-600 bg-slate-900/80 px-3 py-2 text-sm text-white"
        >
          <option value="">Player A</option>
          {sorted.map((p) => (
            <option key={p.player_id} value={p.player_id}>
              {p.player_name} ({p.team})
            </option>
          ))}
        </select>
        <select
          value={playerB}
          onChange={(e) => setPlayerB(e.target.value)}
          className="rounded-xl border border-slate-600 bg-slate-900/80 px-3 py-2 text-sm text-white"
        >
          <option value="">Player B</option>
          {sorted.map((p) => (
            <option key={p.player_id} value={p.player_id}>
              {p.player_name} ({p.team})
            </option>
          ))}
        </select>
      </div>

      <button
        type="button"
        onClick={runCompare}
        disabled={loading}
        className="mb-4 rounded-xl bg-grass px-5 py-2 text-sm font-semibold text-pitch hover:bg-grass-dim disabled:opacity-50"
      >
        {loading ? 'Comparing…' : 'Compare'}
      </button>

      {error && <p className="mb-3 text-sm text-rose-300">{error}</p>}

      {result && (
        <>
          <div className="mb-4 overflow-x-auto rounded-xl border border-slate-700">
            <table className="w-full min-w-[320px] text-sm">
              <thead>
                <tr className="border-b border-slate-700 bg-slate-900/60 text-left text-slate-400">
                  <th className="p-3">Stat</th>
                  <th className="p-3 text-grass">{result.player_a.player_name}</th>
                  <th className="p-3 text-sky-300">{result.player_b.player_name}</th>
                </tr>
              </thead>
              <tbody>
                {result.stats.map((row) => (
                  <tr key={row.stat} className="border-b border-slate-800/80">
                    <td className="p-3 text-slate-400">
                      <StatTooltip statKey={row.stat} label={row.label} />
                    </td>
                    <td
                      className={`p-3 font-semibold tabular-nums ${
                        row.leader === 'a' ? 'text-grass' : 'text-white'
                      }`}
                    >
                      {row.player_a ?? '—'}
                    </td>
                    <td
                      className={`p-3 font-semibold tabular-nums ${
                        row.leader === 'b' ? 'text-sky-300' : 'text-white'
                      }`}
                    >
                      {row.player_b ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-xl border border-grass/30 bg-grass/5 p-4">
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-grass">
              AI verdict
            </p>
            <p className="leading-relaxed text-slate-200">{result.verdict}</p>
          </div>
        </>
      )}
    </section>
  )
}
