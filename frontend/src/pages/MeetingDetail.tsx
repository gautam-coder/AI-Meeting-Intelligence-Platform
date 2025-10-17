import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import { SectionCard, Pill, Empty } from '../components/ui'
import { LineChart, BarChart, SpeakerTimeline } from '../components/charts'
import type { SearchHit } from '../api/types'

export default function MeetingDetail() {
  const { id } = useParams()
  const [data, setData] = useState<any>(null)
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [jobInfo, setJobInfo] = useState<{id: string, progress: number, status: string, elapsed: number} | null>(null)
  const [summaryExpanded, setSummaryExpanded] = useState(false)

  useEffect(() => {
    api.get(`/api/meetings/${id}`).then(r => setData(r.data))
  }, [id])

  useEffect(() => {
    let t: number | undefined
    async function poll() {
      try {
        const jobs = await api.get(`/api/jobs/meeting/${id}`)
        const latest = jobs.data?.[0]
        if (latest) {
          const s = await api.get(`/api/jobs/${latest.id}`)
          setJobInfo({ id: latest.id, progress: s.data.progress || 0, status: s.data.status, elapsed: s.data.elapsed_seconds || 0 })
          if (s.data.status === 'succeeded' || s.data.status === 'failed') {
            setTimeout(() => api.get(`/api/meetings/${id}`).then(r => setData(r.data)), 500)
            if (t) window.clearInterval(t)
          }
        } else {
          setJobInfo(null)
        }
      } catch {}
    }
    if (id) {
      poll()
      t = window.setInterval(poll, 1500) as unknown as number
    }
    return () => { if (t) window.clearInterval(t) }
  }, [id])

  async function doSearch() {
    const { data } = await api.post('/api/search', { query, top_k: 8 })
    setHits(data)
  }

  const items = useMemo(() => ({
    action_items: safeJsonArray(data?.summary?.action_items),
    decisions: safeJsonArray(data?.summary?.decisions),
    topics: safeJsonArray(data?.summary?.key_topics),
    sentiment: safeJsonObject(data?.summary?.sentiment_overview),
  }), [data])
  const sentimentSeries = useMemo(() => {
    const arr = (data?.sentiments || []) as any[]
    if (!arr.length) return [] as {x:number,y:number}[]
    return arr.map(s => ({ x: (s.start + s.end)/2, y: s.score }))
  }, [data])
  const topicBars = useMemo(() => {
    const arr = safeJsonArray(data?.summary?.key_topics)
    // Map to labels and pseudo confidence if not present
    return arr.slice(0,8).map((t:any) => ({ label: typeof t === 'string' ? t : (t.label || ''), conf: typeof t === 'string' ? 0.8 : (t.confidence ?? 0.8) }))
  }, [data])
  const speakerInfo = useMemo(() => {
    const segs = (data?.segments || []) as any[]
    const counts: Record<string, number> = {}
    segs.forEach(s => { const sp = s.speaker || 'Speaker'; counts[sp] = (counts[sp]||0) + (s.end - s.start) })
    const speakers = Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([label, dur])=>({label, dur}))
    return { speakers, total: speakers.reduce((a,b)=>a+b.dur,0) }
  }, [data])

  if (!data) return <div>Loading...</div>

  return (
    <div className="space-y-6">
      {jobInfo && data?.status !== 'ready' && (
        <SectionCard title="Processing" subtitle="We’re generating transcription, insights, and search index.">
          <div className="flex items-center justify-between">
            <div className="text-sm">{jobInfo.progress}% • {Math.round(jobInfo.elapsed)}s elapsed</div>
            <Pill color="blue">{jobInfo.status}</Pill>
          </div>
          <div className="h-2 bg-blue-100 rounded mt-2">
            <div className="h-2 bg-blue-600 rounded" style={{ width: `${jobInfo.progress}%` }}></div>
          </div>
        </SectionCard>
      )}
      <SectionCard title={data.title} subtitle={`Status: ${data.status}`} dense>
        {data.error && <div className="text-sm text-red-600">Error: {data.error}</div>}
      </SectionCard>
      {data.summary && (
        <div className="grid lg:grid-cols-3 gap-6">
          <SectionCard
            title="Summary"
            subtitle="LLM-generated report"
            right={<button onClick={() => setSummaryExpanded(v => !v)} className="text-xs px-2 py-1 rounded border hover:bg-gray-50">{summaryExpanded ? 'Collapse' : 'Expand'}</button>}
          >
            <div className={`relative ${summaryExpanded ? '' : 'max-h-72 overflow-hidden'}`}>
              <div className="prose prose-sm max-w-none break-words leading-7">{renderMarkdownLite(data.summary.summary)}</div>
              {!summaryExpanded && (
                <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-white to-transparent" />
              )}
            </div>
          </SectionCard>
          <div className="space-y-6">
            <SectionCard title="Topics" subtitle="Auto-tagged meeting themes" dense>
              {items.topics.length === 0 ? (
                <Empty title="No topics" hint="Tags will appear after processing." />
              ) : (
                <div className="flex flex-wrap gap-2">
                  {items.topics.map((t: any, i: number) => (
                    <Pill key={i} color="indigo">{(typeof t === 'string') ? t : t.label}</Pill>
                  ))}
                </div>
              )}
            </SectionCard>
            <SectionCard title="Sentiment" subtitle="Overall vibe and moments" dense>
              <div className="text-sm capitalize font-medium">
                {items.sentiment.label ? (
                  <>
                    {items.sentiment.label} {typeof items.sentiment.score === 'number' ? `(${items.sentiment.score.toFixed(2)})` : ''}
                  </>
                ) : 'N/A'}
              </div>
              {items.sentiment.vibe && (
                <div className="text-xs text-gray-700 mt-1">Vibe: {items.sentiment.vibe}</div>
              )}
              {items.sentiment.rationale && (
                <div className="text-xs text-gray-600 mt-1 whitespace-pre-wrap">{items.sentiment.rationale}</div>
              )}
              {sentimentSeries.length > 0 && (
                <div className="mt-3">
                  <div className="text-xs text-gray-500 mb-1">Sentiment over time</div>
                  <LineChart points={sentimentSeries} />
                </div>
              )}
              {Array.isArray(items.sentiment.highlights) && items.sentiment.highlights.length > 0 && (
                <div className="mt-2">
                  <div className="text-xs font-medium mb-1">Highlights</div>
                  <ul className="text-xs space-y-1">
                    {items.sentiment.highlights.slice(0,8).map((h:any, i:number) => (
                      <li key={i} className="flex items-start gap-2 p-2 rounded bg-gray-50">
                        <span className={badgeClass(h?.polarity)}>{(h?.polarity || '').slice(0,1).toUpperCase()}</span>
                        <span>{formatMMSS(h?.timestamp)} {h?.text}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </SectionCard>
            <SectionCard title="Speakers" subtitle={`${speakerInfo.speakers.length} participants`} dense>
              <div className="text-xs text-gray-500 mb-2">Speaking timeline</div>
              <SpeakerTimeline segments={(data?.segments || []).map((s:any)=>({start:s.start,end:s.end,speaker:s.speaker||'Speaker'}))} />
              <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1">
                {speakerInfo.speakers.map((s,i)=>(
                  <div key={i} className="text-xs text-gray-700 truncate">{s.label} • {Math.round(s.dur)}s</div>
                ))}
              </div>
            </SectionCard>
          </div>
        </div>
      )}
      <div className="grid lg:grid-cols-3 gap-6">
        <SectionCard title="Decisions" subtitle="Concrete approvals and commitments" dense>
          {items.decisions.length === 0 ? (
            <Empty title="No Decisions" hint="LLM will populate once detected." />
          ) : (
            <ul className="space-y-2">
              {items.decisions.map((d: any, i: number) => (
                <li key={i} className="rounded border p-3 bg-white hover:bg-gray-50 transition">
                  <div className="text-sm break-words leading-6">{d?.text || String(d)}</div>
                  {(d?.owner || d?.timestamp || d?.timestamp_hint) && (
                    <div className="text-xs text-gray-500 mt-1">
                      {d?.owner && <span className="mr-2">Owner: {d.owner}</span>}
                      {formatMMSS((typeof d?.timestamp === 'number' ? d.timestamp : (typeof d?.timestamp_hint === 'number' ? d.timestamp_hint : undefined)))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
        <SectionCard title="Action Items" subtitle="Tasks to follow up" dense>
          {items.action_items.length === 0 ? (
            <Empty title="No Action Items" hint="LLM will populate once detected." />
          ) : (
            <ul className="space-y-2">
              {items.action_items.map((a: any, i: number) => (
                <li key={i} className="rounded border p-3 bg-white hover:bg-gray-50 transition">
                  <div className="text-sm break-words leading-6">{a?.text || String(a)}</div>
                  {(a?.owner || a?.due_date || a?.timestamp || a?.timestamp_hint) && (
                    <div className="text-xs text-gray-500 mt-1">
                      {a?.owner && <span className="mr-2">Owner: {a.owner}</span>}
                      {a?.due_date && <span className="mr-2">Due: {a.due_date}</span>}
                      {formatMMSS((typeof a?.timestamp === 'number' ? a.timestamp : (typeof a?.timestamp_hint === 'number' ? a.timestamp_hint : undefined)))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
        <SectionCard title="Search" subtitle="Find any moment in this meeting">
          <div className="flex gap-2">
            <input className="border rounded px-3 py-2 flex-1" value={query} onChange={e => setQuery(e.target.value)} placeholder="Find moments..." />
            <button className="px-3 py-2 bg-black text-white rounded" onClick={doSearch}>Go</button>
          </div>
          <ul className="text-sm mt-3 space-y-2">
            {hits.map(h => (
              <li key={h.segment_id} className="border rounded p-2">
                <div className="text-xs text-gray-500">{h.title} • {h.start.toFixed(1)}s - {h.end.toFixed(1)}s</div>
                <div>{h.text}</div>
              </li>
            ))}
          </ul>
        </SectionCard>
      </div>
      <SectionCard title="Transcript" subtitle="Chronological speaker turns" dense>
        <div className="text-sm max-h-96 overflow-auto rounded border divide-y">
          {(data.segments || []).map((s: any) => (
            <div key={s.id} className="px-3 py-2">
              <span className="text-gray-500">[{s.start.toFixed(1)}s] {s.speaker || 'Speaker'}:</span>{' '}
              <span className="break-words">{s.text}</span>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}

function Card({ title, children }: { title: string, children: any }) {
  return (
    <div className="bg-white rounded p-4 shadow">
      <div className="font-semibold mb-2">{title}</div>
      {children}
    </div>
  )
}

function safeJsonArray(value: any) {
  if (!value) return []
  if (Array.isArray(value)) return value
  try {
    const v = typeof value === 'string' ? JSON.parse(value) : value
    return Array.isArray(v) ? v : []
  } catch { return [] }
}

function safeJsonObject(value: any) {
  if (!value) return {}
  if (typeof value === 'object' && !Array.isArray(value)) return value
  try {
    const v = typeof value === 'string' ? JSON.parse(value) : value
    return v && typeof v === 'object' && !Array.isArray(v) ? v : {}
  } catch { return {} }
}

function renderMarkdownLite(src: string) {
  if (!src) return null
  const lines = src.split(/\r?\n/)
  const out: any[] = []
  let list: string[] = []
  let lastBlockType: 'p'|'h1'|'h2'|'h3'|null = null
  let inListSection: string | null = null
  const listSections = new Set([
    'Executive Summary', 'Key Points', 'Timeline Highlights', 'Decisions', 'Action Items', 'Key Topics', 'Risks'
  ])
  function flushList() {
    if (list.length) {
      out.push(
        <ul className="list-disc ml-5 my-2" key={`ul-${out.length}`}>
          {list.map((it, i) => <li key={i}>{it}</li>)}
        </ul>
      )
      list = []
    }
  }
  for (let idx = 0; idx < lines.length; idx++) {
    const ln = lines[idx]
    const l = ln.trim()
    if (!l) { flushList(); inListSection = null; lastBlockType = null; continue }
    // Setex-style h1/h2: detect when line of === or --- follows previous paragraph
    if ((/^=+$/).test(l) && lastBlockType === 'p') {
      // transform previous paragraph block into h1
      const last = out.pop()
      const text = last?.props?.children || ''
      flushList()
      out.push(<h1 key={`h1-setex-${idx}`} className="text-lg font-bold mt-4 mb-2">{text}</h1>)
      lastBlockType = 'h1'
      continue
    }
    if ((/^-+$/).test(l) && lastBlockType === 'p') {
      const last = out.pop()
      const text = last?.props?.children || ''
      flushList()
      out.push(<h2 key={`h2-setex-${idx}`} className="font-semibold mt-4 mb-2">{text}</h2>)
      lastBlockType = 'h2'
      continue
    }
    if (l.startsWith('### ')) { flushList(); out.push(<h3 key={`h3-${idx}`} className="font-semibold mt-3 mb-1">{l.slice(4)}</h3>); inListSection = null; lastBlockType = 'h3'; continue }
    if (l.startsWith('## ')) { flushList(); out.push(<h2 key={`h2-${idx}`} className="font-semibold mt-4 mb-2">{l.slice(3)}</h2>); inListSection = l.slice(3); lastBlockType = 'h2'; continue }
    if (l.startsWith('# ')) { flushList(); out.push(<h1 key={`h1-${idx}`} className="text-lg font-bold mt-4 mb-2">{l.slice(2)}</h1>); inListSection = l.slice(2); lastBlockType = 'h1'; continue }
    if (l.startsWith('- ')) { list.push(l.slice(2)); lastBlockType = null; continue }
    // If inside a known list section heading, treat any non-empty line as a bullet until blank line or new heading
    if (inListSection && listSections.has(inListSection)) {
      list.push(ln)
      lastBlockType = null
      continue
    }
    // paragraph
    flushList()
    out.push(<p key={`p-${idx}`} className="whitespace-pre-wrap leading-6">{ln}</p>)
    lastBlockType = 'p'
  }
  flushList()
  return <div>{out}</div>
}

function formatMMSS(sec?: number | null) {
  if (typeof sec !== 'number' || !isFinite(sec)) return ''
  const s = Math.max(0, Math.floor(sec))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `[${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}]`
}

function badgeClass(polarity?: string) {
  const base = 'inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-bold text-white'
  switch ((polarity || '').toLowerCase()) {
    case 'positive':
      return base + ' bg-green-600'
    case 'negative':
      return base + ' bg-red-600'
    case 'contentious':
      return base + ' bg-amber-600'
    default:
      return base + ' bg-gray-400'
  }
}
