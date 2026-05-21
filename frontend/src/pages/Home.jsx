import { useEffect, useState } from 'react'
import { fetchMatches } from '../api'
import MatchCard from '../components/MatchCard'

export default function Home() {
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchMatches()
      .then(setMatches)
      .catch((e) => {
        setError(
          e.message ||
            'Could not load matches. Start the backend: uvicorn main:app --reload --port 8000',
        )
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <header className="mb-10 text-center">
        <p className="mb-2 text-sm font-medium uppercase tracking-widest text-grass">
          Fan-friendly analytics
        </p>
        <h1 className="font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
          StatSense
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-slate-400">
          Pick a match to see AI-powered summaries, team stats, and player insights — no
          spreadsheet required.
        </p>
      </header>

      {loading && (
        <p className="text-center text-slate-400 animate-pulse">Loading matches…</p>
      )}

      {error && (
        <div className="mx-auto max-w-md rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-center text-sm text-rose-200">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="grid gap-4 sm:grid-cols-2">
          {matches.map((m) => (
            <MatchCard key={m.match_id} match={m} />
          ))}
        </div>
      )}

      {!loading && !error && matches.length === 0 && (
        <p className="text-center text-slate-400">
          No matches in the database. Run{' '}
          <code className="rounded bg-slate-800 px-2 py-1 text-xs">python data_loader.py</code>{' '}
          in the backend folder.
        </p>
      )}
    </div>
  )
}
