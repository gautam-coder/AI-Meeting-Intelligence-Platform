import React from 'react'

type SeriesPoint = { x: number; y: number }

export function LineChart({ points, height=120, stroke='#2563eb' }: { points: SeriesPoint[], height?: number, stroke?: string }) {
  if (!points || points.length === 0) return <div className="text-xs text-gray-500">No data</div>
  const minX = Math.min(...points.map(p => p.x))
  const maxX = Math.max(...points.map(p => p.x))
  const minY = Math.min(...points.map(p => p.y))
  const maxY = Math.max(...points.map(p => p.y))
  const pad = 8
  const w = 320
  const h = height
  const sx = (x: number) => pad + (w - pad*2) * ((x - minX) / (maxX - minX || 1))
  const sy = (y: number) => pad + (h - pad*2) * (1 - ((y - minY) / (maxY - minY || 1)))
  const d = points.map((p,i) => `${i===0?'M':'L'} ${sx(p.x).toFixed(2)} ${sy(p.y).toFixed(2)}`).join(' ')
  const area = `M ${sx(points[0].x)} ${sy(points[0].y)} ` + points.slice(1).map(p => `L ${sx(p.x)} ${sy(p.y)}`).join(' ') + ` L ${sx(points[points.length-1].x)} ${h-pad} L ${sx(points[0].x)} ${h-pad} Z`
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
      <rect x={0} y={0} width={w} height={h} fill="#ffffff" />
      <path d={area} fill="#93c5fd" opacity={0.35} />
      <path d={d} stroke={stroke} strokeWidth={2} fill="none" />
    </svg>
  )
}

export function BarChart({ values, labels, height=120, color='#0ea5e9' }: { values: number[], labels?: string[], height?: number, color?: string }) {
  if (!values || values.length === 0) return <div className="text-xs text-gray-500">No data</div>
  const w = 320; const h = height; const pad = 8
  const maxV = Math.max(...values, 1)
  const bw = (w - pad*2) / values.length - 6
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
      <rect x={0} y={0} width={w} height={h} fill="#ffffff" />
      {values.map((v,i) => {
        const bh = (h - pad*2) * (v / maxV)
        const x = pad + i * (bw + 6)
        const y = h - pad - bh
        return <g key={i}>
          <rect x={x} y={y} width={bw} height={bh} fill={color} rx={3} />
        </g>
      })}
    </svg>
  )
}

export function HStackBar({ parts, height=14 }: { parts: { label: string, value: number, color: string }[], height?: number }) {
  const total = parts.reduce((a,b)=>a+b.value, 0) || 1
  let acc = 0
  return (
    <div className="w-full rounded overflow-hidden flex" style={{height}}>
      {parts.map((p,i) => {
        const w = `${(p.value/total)*100}%`
        return <div key={i} title={`${p.label}: ${p.value}`} style={{width:w, backgroundColor:p.color}} />
      })}
    </div>
  )
}

export function SpeakerTimeline({
  segments,
  colors,
  height = 14,
}: {
  segments: { start: number; end: number; speaker: string }[]
  colors?: Record<string, string>
  height?: number
}) {
  if (!segments || segments.length === 0) return <div className="text-xs text-gray-500">No segments</div>
  const total = Math.max(...segments.map(s => s.end)) || 1
  const palette = [
    '#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b',
    '#e377c2','#7f7f7f','#bcbd22','#17becf'
  ]
  const map: Record<string,string> = {}
  let pi = 0
  const items = segments.map(s => {
    const w = ((s.end - s.start) / total) * 100
    if (!map[s.speaker]) map[s.speaker] = colors?.[s.speaker] || palette[pi++ % palette.length]
    return { left: (s.start/total)*100, width: Math.max(0, w), color: map[s.speaker], speaker: s.speaker }
  })
  return (
    <div className="w-full relative rounded overflow-hidden border" style={{height}}>
      {items.map((it,i)=>(
        <div key={i} className="absolute top-0 h-full" title={`${it.speaker}`} style={{ left: `${it.left}%`, width: `${it.width}%`, backgroundColor: it.color }} />
      ))}
    </div>
  )
}
