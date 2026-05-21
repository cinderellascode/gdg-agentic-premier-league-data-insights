import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchMatch } from '../api'
import FanQA from '../components/FanQA'
import MatchTimeline from '../components/MatchTimeline'
import PlayerCard from '../components/PlayerCard'
import PlayerComparison from '../components/PlayerComparison'
import TeamStatsBar from '../components/TeamStatsBar'
import { useFanMode } from '../context/FanModeContext'
import {
  formatDate,
  formatScore,
  HIGHLIGHT_LABELS,
} from '../utils/statLabels'
import { showPlayerComparison, showTimeline, topPerformerHighlight } from '../utils/fanMode'

export default function MatchDashboard() {
  const { matchId } = useParams()
  const { mode } = useFanMode()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedPlayer, setSelectedPlayer] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchMatch(matchId)
      .then(setData)
      .catch((e) => setError(e.message || 'Failed to load match'))
      .finally(() => setLoading(false))
  }, [matchId])

  const match = data?.match

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <p className="animate-pulse text-slate-400">Loading match insights…</p>
      </div>
    )
  }

  if (error || !match) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <p className="text-rose-300">{error || 'Match not found'}</p>
        <Link to="/" className="mt-4 inline-block text-grass hover:underline">
          ← Back to matches
        </Link>
      </div>
    )
  }

  const score = formatScore(match.home_score, match.away_score)

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link
        to="/"
        className="mb-6 inline-flex items-center gap-1 text-sm text-slate-400 hover:text-grass"
      >
        ← All matches
      </Link>

      <header className="mb-8 rounded-2xl border border-slate-700/60 bg-gradient-to-br from-pitch-light to-pitch p-6 sm:p-8">
        <p className="text-sm text-slate-400">
          {match.competition} · {formatDate(match.date)}
        </p>
        <h1 className="mt-2 font-display text-3xl font-bold text-white sm:text-4xl">
          {match.home_team}{' '}
          <span className="text-grass">{score}</span> {match.away_team}
        </h1>
      </header>

      {data.summary && (
        <section className="mb-8 rounded-2xl border border-grass/30 bg-grass/5 p-6">
          <h2 className="mb-3 font-display text-lg font-semibold text-grass">Match story</h2>
          <p className="leading-relaxed text-slate-200">{data.summary}</p>
        </section>
      )}

      {mode !== 'casual' && (
        <div className="mb-8">
          <TeamStatsBar teams={data.teams} />
        </div>
      )}

      {showTimeline(mode) && (
        <div className="mb-8">
          <MatchTimeline matchId={Number(matchId)} />
        </div>
      )}

      <section className="mb-8">
        <h2 className="mb-4 font-display text-xl font-semibold text-white">Top performers</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {data.top_performers?.map((p) => {
            const hl = topPerformerHighlight(mode, p)
            const label = HIGHLIGHT_LABELS[hl.stat] || hl.label || hl.stat
            return (
              <button
                key={p.player_id}
                type="button"
                onClick={() =>
                  setSelectedPlayer({
                    id: p.player_id,
                    name: p.player_name,
                  })
                }
                className="rounded-2xl border border-slate-700/60 bg-pitch-light/80 p-5 text-left transition hover:border-grass/50 hover:bg-slate-800/50"
              >
                <p className="font-display text-lg font-semibold text-white">{p.player_name}</p>
                <p className="text-xs text-slate-500">
                  {p.team}
                  {p.position ? ` · ${p.position}` : ''}
                </p>
                <div className="mt-3 flex flex-wrap items-baseline gap-2">
                  <span className="font-display text-2xl font-bold text-grass">{hl.value}</span>
                  <span className="text-sm text-slate-400">{label}</span>
                </div>
                {mode !== 'casual' && p.insight && (
                  <p className="mt-3 line-clamp-3 text-sm leading-snug text-slate-300">
                    {p.insight}
                  </p>
                )}
                <p className="mt-3 text-xs font-medium text-grass">View full card →</p>
              </button>
            )
          })}
        </div>
      </section>

      {showPlayerComparison(mode) && (
        <div className="mb-8">
          <PlayerComparison matchId={Number(matchId)} players={data.players} />
        </div>
      )}

      <FanQA matchId={Number(matchId)} />

      {selectedPlayer && (
        <PlayerCard
          matchId={Number(matchId)}
          playerId={selectedPlayer.id}
          playerName={selectedPlayer.name}
          onClose={() => setSelectedPlayer(null)}
        />
      )}
    </div>
  )
}
