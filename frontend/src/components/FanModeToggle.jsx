import { useFanMode } from '../context/FanModeContext'
import { FAN_MODES, MODE_DESCRIPTIONS, MODE_LABELS } from '../utils/fanMode'

export default function FanModeToggle() {
  const { mode, setMode } = useFanMode()

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/40 p-1">
      <div className="flex flex-wrap gap-1">
        {FAN_MODES.map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            title={MODE_DESCRIPTIONS[m]}
            className={`rounded-lg px-3 py-2 text-xs font-semibold transition sm:px-4 sm:text-sm ${
              mode === m
                ? 'bg-grass text-pitch shadow'
                : 'text-slate-400 hover:bg-slate-800 hover:text-white'
            }`}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>
      <p className="mt-2 px-2 text-center text-[11px] text-slate-500">
        {MODE_DESCRIPTIONS[mode]}
      </p>
    </div>
  )
}
