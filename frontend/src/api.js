import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const client = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
})

export async function fetchMatches() {
  const { data } = await client.get('/matches')
  return data
}

export async function fetchMatch(matchId) {
  const { data } = await client.get(`/match/${matchId}`)
  return data
}

export async function fetchPlayerInMatch(matchId, playerId) {
  const { data } = await client.get(`/match/${matchId}/player/${playerId}`)
  return data
}

export async function askQuestion(question, matchId) {
  const { data } = await client.post('/ask', { question, match_id: matchId })
  return data
}

export async function fetchTimeline(matchId) {
  const { data } = await client.get(`/match/${matchId}/timeline`)
  return data
}

export async function comparePlayers(matchId, playerAId, playerBId) {
  const { data } = await client.post(`/match/${matchId}/compare`, {
    player_a_id: playerAId,
    player_b_id: playerBId,
  })
  return data
}

export async function explainTimelineEvent(matchId, eventId) {
  const { data } = await client.post(`/match/${matchId}/timeline/explain`, {
    event_id: eventId,
  })
  return data
}
