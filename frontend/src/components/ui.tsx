import React from 'react'

export function SectionCard({ title, subtitle, right, children, dense = false }: { title: string, subtitle?: string, right?: React.ReactNode, children: React.ReactNode, dense?: boolean }) {
  return (
    <section className="bg-white rounded-xl shadow-sm ring-1 ring-gray-200/60 overflow-hidden">
      <div className={`px-5 ${dense ? 'py-2' : 'py-3'} border-b flex items-center justify-between`}> 
        <div>
          <h2 className="font-semibold text-gray-900">{title}</h2>
          {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {right}
      </div>
      <div className={`${dense ? 'p-4' : 'p-5'}`}>
        {children}
      </div>
    </section>
  )
}

export function Pill({ children, color = 'gray' }: { children: React.ReactNode, color?: 'gray'|'blue'|'green'|'red'|'amber'|'indigo'|'purple' }) {
  const colorMap: Record<string, string> = {
    gray: 'bg-gray-100 text-gray-800 ring-gray-200',
    blue: 'bg-blue-100 text-blue-800 ring-blue-200',
    green: 'bg-green-100 text-green-800 ring-green-200',
    red: 'bg-red-100 text-red-800 ring-red-200',
    amber: 'bg-amber-100 text-amber-800 ring-amber-200',
    indigo: 'bg-indigo-100 text-indigo-800 ring-indigo-200',
    purple: 'bg-purple-100 text-purple-800 ring-purple-200',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ring-1 ${colorMap[color]}`}>{children}</span>
  )
}

export function Badge({ children, color='gray' }: { children: React.ReactNode, color?: 'gray'|'green'|'red'|'amber'|'blue' }) {
  const map: Record<string,string> = {
    gray:'bg-gray-200 text-gray-800',
    green:'bg-green-600 text-white',
    red:'bg-red-600 text-white',
    amber:'bg-amber-500 text-white',
    blue:'bg-blue-600 text-white',
  }
  return <span className={`inline-flex items-center justify-center text-[10px] font-bold rounded-full px-1.5 h-4 ${map[color]}`}>{children}</span>
}

export function ProgressBar({ value, label }: { value: number, label?: string }) {
  return (
    <div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className="h-2 bg-blue-600 rounded-full transition-all" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
      {label && <div className="text-xs text-gray-500 mt-1">{label}</div>}
    </div>
  )
}

export function Empty({ title='Nothing here yet', hint }: { title?: string, hint?: string }) {
  return (
    <div className="text-center text-sm text-gray-500">
      <div className="font-medium text-gray-600">{title}</div>
      {hint && <div className="mt-1">{hint}</div>}
    </div>
  )
}
