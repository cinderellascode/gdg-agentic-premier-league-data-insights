import { useFanMode } from '../context/FanModeContext'
import { TEAM_METRICS_BY_MODE } from '../utils/fanMode'
import StatTooltip from './StatTooltip'

function barWidth(value, otherValue) {
  const v = Number(value) || 0
  const o = Number(otherValue) || 0
  const total = v + o || 1
  return `${Math.round((v / total) * 100)}%`
}

export default function TeamStatsBar({ teams }) {
  const { mode } = useFanMode()
  const metrics = TEAM_METRICS_BY_MODE[mode] || TEAM_METRICS_BY_MODE.enthusiast

  if (!teams?.length || teams.length < 2) return null

  const [home, away] = teams
  const homeName = home.team
  const awayName = away.team

  return (
    <section className="rounded-2xl border border-slate-700/60 bg-pitch-light/60 p-6">
      <h2 className="mb-6 font-display text-xl font-semibold text-white">Team comparison</h2>

      <div className="mb-6 flex justify-between text-sm font-medium">
        <span className="text-grass">{homeName}</span>
        <span className="text-slate-400">vs</span>
        <span className="text-sky-300">{awayName}</span>
      </div>

      <div className="space-y-6">
        {metrics.map(({ key, label, suffix }) => {
          const hv = home.stats?.[key]
          const av = away.stats?.[key]
          if (hv == null && av == null) return null

          return (
            <div key={key}>
              <div className="mb-2 flex justify-center">
                <StatTooltip statKey={key} label={label} />
              </div>
              <div className="flex h-10 overflow-hidden rounded-lg bg-slate-900/80">
                <div
                  className="flex items-center justify-end bg-grass/80 pr-2 text-xs font-semibold text-pitch transition-all"
                  style={{ width: barWidth(hv, av) }}
                >
                  {hv != null && (
                    <span>
                      {hv}
                      {suffix}
                    </span>
                  )}
                </div>
                <div
                  className="flex flex-1 items-center justify-start bg-sky-500/70 pl-2 text-xs font-semibold text-pitch"
                  style={{ minWidth: barWidth(av, hv) }}
                >
                  {av != null && (
                    <span>
                      {av}
                      {suffix}
                    </span>
                  )}
                </div>
              </div>
              <div className="mt-1 flex justify-between text-xs text-slate-500">
                <span>{homeName}</span>
                <span>{awayName}</span>
              </div>
              {mode === 'analyst' && home.benchmarks?.[key] && (
                <p className="mt-1 text-center text-[10px] text-slate-500">
                  League avg ~{home.benchmarks[key].league_average}
                  {' · '}
                  <span
                    className={
                      home.benchmarks[key].badge === 'above'
                        ? 'text-emerald-400'
                        : home.benchmarks[key].badge === 'below'
                          ? 'text-rose-400'
                          : 'text-amber-400'
                    }
                  >
                    {home.team} {home.benchmarks[key].badge}
                  </span>
                </p>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
