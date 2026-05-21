import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fetchPlayerInMatch } from '../api'
import { useFanMode } from '../context/FanModeContext'
import { filterInsightCards, PLAYER_GRID_BY_MODE } from '../utils/fanMode'
import InsightBadge from './InsightBadge'
import StatTooltip from './StatTooltip'

function chartData(comparison, gridStats) {
  if (!comparison) return []
  return gridStats.filter((k) => comparison[k]?.player != null).map((key) => ({
    stat: key.replace(/_/g, ' '),
    player: Number(comparison[key].player) || 0,
    team: Number(comparison[key].team_average) || 0,
  }))
}

export default function PlayerCard({ matchId, playerId, playerName, onClose }) {
  const { mode } = useFanMode()
  const gridStats = PLAYER_GRID_BY_MODE[mode] || PLAYER_GRID_BY_MODE.enthusiast
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!matchId || !playerId) return
    setLoading(true)
    setError(null)
    fetchPlayerInMatch(matchId, playerId)
      .then(setData)
      .catch((e) => setError(e.message || 'Failed to load player'))
      .finally(() => setLoading(false))
  }, [matchId, playerId])

  const player = data?.player
  const cards = filterInsightCards(data?.insight_cards || [], mode)
  const comparison = data?.comparison
  const bars = mode !== 'casual' ? chartData(comparison, gridStats) : []

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <aside
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-lg flex-col border-l border-slate-700 bg-pitch shadow-2xl"
        role="dialog"
        aria-labelledby="player-card-title"
      >
        <header className="flex items-start justify-between border-b border-slate-700 p-5">
          <div>
            <h2 id="player-card-title" className="font-display text-2xl font-bold text-white">
              {player?.player_name || playerName || 'Player'}
            </h2>
            {player && (
              <p className="mt-1 text-sm text-slate-400">
                {player.team}
                {player.position ? ` · ${player.position}` : ''}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
            aria-label="Close"
          >
            ✕
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-5">
          {loading && (
            <p className="animate-pulse text-slate-400">Loading player insights…</p>
          )}
          {error && <p className="text-rose-400">{error}</p>}

          {!loading && !error && player && (
            <>
              <div
                className={`mb-6 grid gap-3 ${
                  gridStats.length <= 2
                    ? 'grid-cols-2'
                    : 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4'
                }`}
              >
                {gridStats.map((key) => {
                  const val = player[key]
                  if (val == null) return null
                  const card = cards.find((c) => c.stat === key)
                  return (
                    <div
                      key={key}
                      className="rounded-xl border border-slate-700 bg-slate-900/50 p-3 text-center"
                    >
                      <p className="font-display text-2xl font-bold text-white">{val}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        <StatTooltip statKey={key} label={card?.label || key} />
                      </p>
                      {card && (
                        <div className="mt-2 flex justify-center">
                          <InsightBadge badge={card.badge} />
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {mode !== 'casual' && bars.length > 0 && (
                <div className="mb-6 h-48 rounded-xl border border-slate-700 bg-slate-900/40 p-3">
                  <p className="mb-2 text-center text-xs text-slate-400">
                    Player vs team average
                  </p>
                  <ResponsiveContainer width="100%" height="90%">
                    <BarChart data={bars} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="stat" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} width={28} />
                      <Tooltip
                        contentStyle={{
                          background: '#0f172a',
                          border: '1px solid #475569',
                          borderRadius: 8,
                        }}
                      />
                      <Bar dataKey="player" name="Player" fill="#22c55e" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="team" name="Team avg" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {cards.length > 0 && (
                <>
              <h3 className="mb-3 font-display text-lg font-semibold text-white">
                {mode === 'casual' ? 'Quick take' : 'AI insights'}
              </h3>
              <div className="space-y-3">
                {cards.map((card) => (
                  <div
                    key={card.stat}
                    className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-4"
                  >
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <StatTooltip
                        statKey={card.stat}
                        label={
                          <span className="font-medium text-slate-200">{card.label}</span>
                        }
                      />
                      <div className="flex items-center gap-2">
                        <span className="font-display text-lg font-bold text-white">
                          {card.value}
                        </span>
                        <InsightBadge badge={card.badge} />
                      </div>
                    </div>
                    <p className="text-sm leading-relaxed text-slate-300">{card.insight}</p>
                  </div>
                ))}
              </div>
                </>
              )}
            </>
          )}
        </div>
      </aside>
    </>
  )
}
