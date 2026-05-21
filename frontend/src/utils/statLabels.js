export const STAT_TOOLTIPS = {
  xg: 'Expected Goals: the probability this player should have scored from their chances.',
  xa: 'Expected Assists: the quality of chances created for teammates.',
  ppda: 'Passes Per Defensive Action — lower means more intense pressing.',
  xg_for: 'Expected goals created by this team\'s attacks.',
  xg_against: 'Expected goals conceded — lower is better for the defense.',
  pass_accuracy_pct: 'Share of passes that reached a teammate.',
  duels_won_pct: 'Share of one-on-one battles won.',
  conversion_rate_pct: 'Goals scored per shot taken.',
  shot_accuracy_pct: 'Shots on target as a share of all shots.',
  progressive_passes: 'Passes that move the ball significantly toward goal.',
  key_passes: 'Passes that directly set up a shot.',
  pressing_intensity: 'How aggressively the team tried to win the ball back.',
  possession_pct: 'Share of time the team had the ball.',
}

export const HIGHLIGHT_LABELS = {
  goals: 'Goals',
  assists: 'Assists',
  xg: 'Expected Goals',
  xa: 'Expected Assists',
}

export function formatScore(home, away) {
  if (home == null || away == null) return '—'
  return `${home} – ${away}`
}

export function formatDate(dateStr) {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}
