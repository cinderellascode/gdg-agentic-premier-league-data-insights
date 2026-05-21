import { STAT_TOOLTIPS } from '../utils/statLabels'

export default function StatTooltip({ statKey, label, children }) {
  const tip = STAT_TOOLTIPS[statKey]

  return (
    <span className="group relative inline-flex cursor-help items-center gap-1">
      {children ?? <span className="border-b border-dotted border-slate-500">{label}</span>}
      {tip && (
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 hidden w-56 -translate-x-1/2 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-left text-xs font-normal leading-snug text-slate-200 shadow-xl group-hover:block"
        >
          {tip}
        </span>
      )}
    </span>
  )
}
