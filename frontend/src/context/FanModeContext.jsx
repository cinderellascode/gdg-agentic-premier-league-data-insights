import { createContext, useContext, useMemo, useState } from 'react'
import { FAN_MODES } from '../utils/fanMode'

const STORAGE_KEY = 'statsense_fan_mode'

const FanModeContext = createContext(null)

export function FanModeProvider({ children }) {
  const [mode, setModeState] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    return FAN_MODES.includes(saved) ? saved : 'enthusiast'
  })

  const setMode = (next) => {
    if (!FAN_MODES.includes(next)) return
    localStorage.setItem(STORAGE_KEY, next)
    setModeState(next)
  }

  const value = useMemo(() => ({ mode, setMode }), [mode])

  return <FanModeContext.Provider value={value}>{children}</FanModeContext.Provider>
}

export function useFanMode() {
  const ctx = useContext(FanModeContext)
  if (!ctx) throw new Error('useFanMode must be used within FanModeProvider')
  return ctx
}
