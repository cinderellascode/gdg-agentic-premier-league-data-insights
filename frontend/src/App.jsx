import { BrowserRouter, Route, Routes } from 'react-router-dom'
import FanModeToggle from './components/FanModeToggle'
import { FanModeProvider } from './context/FanModeContext'
import Home from './pages/Home'
import MatchDashboard from './pages/MatchDashboard'

function Layout({ children }) {
  return (
    <div className="min-h-screen">
      <nav className="border-b border-slate-800/80 bg-pitch/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <a href="/" className="font-display text-xl font-bold text-white">
            Stat<span className="text-grass">Sense</span>
          </a>
          <FanModeToggle />
        </div>
      </nav>
      <main>{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <FanModeProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/match/:matchId" element={<MatchDashboard />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </FanModeProvider>
  )
}
