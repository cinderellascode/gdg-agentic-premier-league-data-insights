import { useState } from 'react'
import { askQuestion } from '../api'

const SUGGESTIONS = [
  'Who was the best player?',
  'Why did the home team win?',
  'Which team pressed harder?',
]

export default function FanQA({ matchId }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function submit(q) {
    const text = (q ?? question).trim()
    if (!text || loading) return

    setError(null)
    setLoading(true)
    setMessages((prev) => [...prev, { role: 'user', text }])
    setQuestion('')

    try {
      const res = await askQuestion(text, matchId)
      setMessages((prev) => [...prev, { role: 'assistant', text: res.answer }])
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Could not reach the AI. Is the backend running?'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-2xl border border-slate-700/60 bg-pitch-light/60 p-6">
      <h2 className="mb-2 font-display text-xl font-semibold text-white">Ask about this match</h2>
      <p className="mb-4 text-sm text-slate-400">
        Natural-language Q&A powered by your match data and Groq AI.
      </p>

      {messages.length > 0 && (
        <div className="mb-4 max-h-80 space-y-3 overflow-y-auto rounded-xl bg-slate-900/50 p-4">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  m.role === 'user'
                    ? 'rounded-br-md bg-grass/25 text-emerald-100'
                    : 'rounded-bl-md border border-slate-600 bg-slate-800 text-slate-200'
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
          {loading && (
            <p className="text-sm text-slate-500 animate-pulse">Thinking…</p>
          )}
        </div>
      )}

      {error && (
        <p className="mb-3 rounded-lg bg-rose-500/15 px-3 py-2 text-sm text-rose-300">{error}</p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
        className="flex gap-2"
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask anything about this match…"
          className="flex-1 rounded-xl border border-slate-600 bg-slate-900/80 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-grass focus:outline-none focus:ring-1 focus:ring-grass"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="rounded-xl bg-grass px-5 py-3 text-sm font-semibold text-pitch transition hover:bg-grass-dim disabled:opacity-50"
        >
          Ask
        </button>
      </form>

      <div className="mt-3 flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => submit(s)}
            disabled={loading}
            className="rounded-full border border-slate-600 px-3 py-1 text-xs text-slate-400 transition hover:border-grass/50 hover:text-grass"
          >
            {s}
          </button>
        ))}
      </div>
    </section>
  )
}
