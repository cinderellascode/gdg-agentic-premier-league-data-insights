import { Link } from 'react-router-dom'
import { formatDate, formatScore } from '../utils/statLabels'

export default function MatchCard({ match }) {
  const score = formatScore(match.home_score, match.away_score)

  return (
    <Link
      to={`/match/${match.match_id}`}
      className="group block rounded-2xl border border-slate-700/60 bg-pitch-light/80 p-5 shadow-lg transition hover:border-grass/50 hover:shadow-grass/10 hover:shadow-xl"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-medium text-slate-300">
          {match.competition}
        </span>
        <span className="text-xs text-slate-500">{formatDate(match.date)}</span>
      </div>

      <div className="mb-2 flex items-center justify-between gap-4">
        <div className="min-w-0 flex-1 text-left">
          <p className="truncate font-display text-lg font-semibold text-white group-hover:text-grass">
            {match.home_team}
          </p>
          <p className="truncate text-sm text-slate-400">vs</p>
          <p className="truncate font-display text-lg font-semibold text-white group-hover:text-grass">
            {match.away_team}
          </p>
        </div>
        <div className="shrink-0 rounded-xl bg-slate-900/80 px-4 py-3 text-center">
          <p className="font-display text-2xl font-bold tracking-tight text-white">{score}</p>
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Full time</p>
        </div>
      </div>

      {match.season && (
        <p className="text-left text-xs text-slate-500">{match.season}</p>
      )}

      <p className="mt-4 text-left text-sm font-medium text-grass opacity-0 transition group-hover:opacity-100">
        View match insights →
      </p>
    </Link>
  )
}
