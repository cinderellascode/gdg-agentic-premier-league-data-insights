const BADGE_STYLES = {
  above: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
  below: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
  average: 'bg-amber-500/20 text-amber-200 border-amber-500/40',
}

const BADGE_LABELS = {
  above: 'Above average',
  below: 'Below average',
  average: 'Near average',
}

export default function InsightBadge({ badge, size = 'sm' }) {
  const level = badge || 'average'
  const sizeClass = size === 'lg' ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-xs'

  return (
    <span
      className={`inline-flex items-center rounded-full border font-medium ${sizeClass} ${BADGE_STYLES[level]}`}
    >
      {BADGE_LABELS[level]}
    </span>
  )
}
