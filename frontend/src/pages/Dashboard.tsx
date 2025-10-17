import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Meeting, SearchHit } from '../api/types'
import { SectionCard, Pill, Empty } from '../components/ui'
import { HStackBar, BarChart } from '../components/charts'

export default function Dashboard() {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const statusParts = (() => {
    const m: Record<string, number> = {}
    meetings.forEach(x => m[x.status] = (m[x.status]||0)+1)
    const colors: Record<string,string> = { ready:'#16a34a', uploaded:'#f59e0b', created:'#64748b', error:'#ef4444' }
    return Object.entries(m).map(([label,value])=>({label, value, color: colors[label] || '#94a3b8'}))
  })()
  const durationValues = meetings.map(m => Math.max(1, Math.round(m.duration_seconds/60)))

  useEffect(() => {
    api.get('/api/meetings').then(r => setMeetings(r.data))
  }, [])

  async function doSearch(e?: React.FormEvent) {
    e?.preventDefault()
    if (!query.trim()) { setHits([]); return }
    const { data } = await api.post('/api/search', { query, top_k: 12 })
    setHits(data)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Meetings</h1>
          <p className="text-sm text-gray-500">Search, browse, and review insights.</p>
        </div>
        <Link to="/upload" className="px-4 py-2 rounded-md bg-gray-900 text-white hover:bg-black transition">New Upload</Link>
      </div>
      <SectionCard title="Search" subtitle="Find moments across all meetings.">
        <form onSubmit={doSearch} className="flex gap-2 items-center">
          <input className="border rounded-md px-3 py-2 flex-1 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Search across all meetings..." value={query} onChange={e => setQuery(e.target.value)} />
          <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md">Search</button>
        </form>
        {hits.length > 0 ? (
          <ul className="mt-4 grid gap-2">
            {hits.map(h => (
              <li key={`${h.segment_id}`} className="rounded-md border p-3 hover:bg-gray-50">
                <div className="text-xs text-gray-500 mb-1">{h.title} • {h.start.toFixed(1)}s - {h.end.toFixed(1)}s</div>
                <Link to={`/meetings/${h.meeting_id}`} className="hover:underline">{h.text}</Link>
              </li>
            ))}
          </ul>
        ) : (
          <div className="mt-3"><Empty hint="Try a keyword like ‘budget’, ‘timeline’, or ‘risk’." /></div>
        )}
      </SectionCard>
      <SectionCard title="Overview" subtitle="Status and duration distribution" >
        <div className="grid md:grid-cols-3 gap-4 items-center">
          <div className="col-span-2">
            <div className="text-xs text-gray-500 mb-1">By status</div>
            <HStackBar parts={statusParts} />
            <div className="mt-2 flex gap-3 flex-wrap">
              {statusParts.map((p,i)=>(
                <div key={i} className="text-xs text-gray-600 flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{background:p.color}} /> {p.label}: {p.value}</div>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">Durations (min)</div>
            <BarChart values={durationValues.slice(0,12)} />
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Recent Meetings" subtitle="Latest processed recordings.">
        {meetings.length === 0 ? (
          <Empty title="No meetings yet" hint="Upload your first recording to get started." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {meetings.map(m => (
              <Link key={m.id} to={`/meetings/${m.id}`} className="rounded-lg border p-4 hover:shadow-sm transition bg-white">
                <div className="flex items-start justify-between">
                  <div className="font-medium text-gray-900 truncate pr-3">{m.title}</div>
                  <Pill color={m.status === 'ready' ? 'green' : m.status === 'error' ? 'red' : 'amber'}>{m.status}</Pill>
                </div>
                <div className="text-xs text-gray-500 mt-2">{Math.max(1, Math.round(m.duration_seconds/60))} min</div>
              </Link>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  )
}
