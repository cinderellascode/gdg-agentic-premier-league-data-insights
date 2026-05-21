export const FAN_MODES = ['casual', 'enthusiast', 'analyst']

export const MODE_LABELS = {
  casual: 'Casual',
  enthusiast: 'Enthusiast',
  analyst: 'Analyst',
}

export const MODE_DESCRIPTIONS = {
  casual: 'Goals, assists & the big story',
  enthusiast: 'Adds xG, passing & key moments',
  analyst: 'Full stats and raw numbers',
}

export const PLAYER_GRID_BY_MODE = {
  casual: ['goals', 'assists'],
  enthusiast: ['goals', 'assists', 'xg', 'pass_accuracy_pct', 'key_passes'],
  analyst: [
    'goals',
    'assists',
    'xg',
    'xa',
    'pass_accuracy_pct',
    'key_passes',
    'progressive_passes',
    'duels_won_pct',
    'shot_accuracy_pct',
    'conversion_rate_pct',
  ],
}

export const TEAM_METRICS_BY_MODE = {
  casual: [{ key: 'possession_pct', label: 'Possession', suffix: '%' }],
  enthusiast: [
    { key: 'possession_pct', label: 'Possession', suffix: '%' },
    { key: 'shots_on_target', label: 'Shots on target', suffix: '' },
    { key: 'xg_for', label: 'Expected goals', suffix: '' },
  ],
  analyst: [
    { key: 'possession_pct', label: 'Possession', suffix: '%' },
    { key: 'shots_on_target', label: 'Shots on target', suffix: '' },
    { key: 'xg_for', label: 'Expected goals', suffix: '' },
    { key: 'ppda', label: 'Pressing (PPDA)', suffix: '' },
    { key: 'pressing_intensity', label: 'Pressing intensity', suffix: '' },
  ],
}

export function showTimeline(mode) {
  return mode === 'enthusiast' || mode === 'analyst'
}

export function showPlayerComparison(mode) {
  return mode !== 'casual'
}

export function filterInsightCards(cards, mode) {
  if (!cards?.length) return []
  if (mode === 'analyst') return cards
  const allowed = new Set(PLAYER_GRID_BY_MODE[mode] || PLAYER_GRID_BY_MODE.enthusiast)
  return cards.filter((c) => allowed.has(c.stat))
}

export function topPerformerHighlight(mode, performer) {
  if (mode === 'casual') {
    if ((performer.goals || 0) > 0) {
      return { stat: 'goals', value: performer.goals, label: 'Goals' }
    }
    if ((performer.assists || 0) > 0) {
      return { stat: 'assists', value: performer.assists, label: 'Assists' }
    }
  }
  return {
    stat: performer.highlight_stat,
    value: performer.highlight_value,
    label: performer.highlight_stat,
  }
}
