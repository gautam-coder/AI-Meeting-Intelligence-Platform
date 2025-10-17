import { Link, Outlet, useLocation } from 'react-router-dom'

export default function App() {
  const loc = useLocation()
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <header className="bg-white/80 backdrop-blur sticky top-0 z-10 border-b">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="font-semibold tracking-tight text-gray-900">AI Meeting Intelligence</Link>
          <nav className="flex items-center gap-2">
            <Link to="/" className={linkClass(loc.pathname === '/')}>Dashboard</Link>
            <Link to="/upload" className={linkClass(loc.pathname.startsWith('/upload'))}>Upload</Link>
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        <Outlet />
      </main>
    </div>
  )
}

function linkClass(active: boolean) {
  return `px-3 py-1.5 rounded-md text-sm ${active ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-100'}`
}
