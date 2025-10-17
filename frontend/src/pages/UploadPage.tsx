import { useState } from 'react'
import { api } from '../api/client'
import { Link } from 'react-router-dom'
import { SectionCard, ProgressBar } from '../components/ui'

export default function UploadPage() {
  const [title, setTitle] = useState('')
  const [meetingId, setMeetingId] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState('')
  const [jobId, setJobId] = useState<string | null>(null)
  const [progress, setProgress] = useState<number>(0)
  const [elapsed, setElapsed] = useState<number>(0)
  const [jobStatus, setJobStatus] = useState<string>('')
  const [jobError, setJobError] = useState<string>('')
  const [pollTimer, setPollTimer] = useState<number | null>(null)

  async function createMeeting() {
    const { data } = await api.post('/api/meetings', { title })
    setMeetingId(data.id)
  }

  async function upload() {
    if (!meetingId || !file) return
    const form = new FormData()
    form.append('upload', file)
    await api.post(`/api/meetings/${meetingId}/upload`, form)
  }

  async function processMeeting() {
    if (!meetingId) return
    const { data } = await api.post(`/api/meetings/${meetingId}/process`)
    setJobId(data.id)
    setStatus(`Started job ${data.id}`)
    startPolling(data.id)
  }

  function startPolling(id: string) {
    if (pollTimer) window.clearInterval(pollTimer)
    const t = window.setInterval(async () => {
      const { data } = await api.get(`/api/jobs/${id}`)
      setProgress(data.progress || 0)
      setElapsed(data.elapsed_seconds || 0)
      setJobStatus(`${data.status}${data.message ? ' - ' + data.message : ''}`)
      setJobError(data.error || '')
      if (data.status === 'succeeded' || data.status === 'failed') {
        window.clearInterval(t)
        setPollTimer(null)
      }
    }, 1500) as unknown as number
    setPollTimer(t)
  }

  return (
    <div className="space-y-6">
      <SectionCard title="Create Meeting" subtitle="Give your recording a short title.">
        <div className="flex gap-2">
          <input className="border rounded-md px-3 py-2 flex-1 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g., Sprint Review – Oct 15" value={title} onChange={e => setTitle(e.target.value)} />
          <button className="px-4 py-2 bg-gray-900 text-white rounded-md" onClick={createMeeting} disabled={!title}>Create</button>
        </div>
        {meetingId && <div className="text-xs text-gray-500 mt-2">Meeting ID: <code>{meetingId}</code></div>}
      </SectionCard>
      <SectionCard title="Upload File" subtitle="Drop an audio/video file (mp3, wav, mp4, m4a, etc.)">
        <div className="grid gap-3">
          <div className="border-2 border-dashed rounded-lg p-6 text-center bg-gray-50">
            <div className="text-sm text-gray-600">Choose a file to upload</div>
            <input type="file" className="mt-3" onChange={e => setFile(e.target.files?.[0] || null)} />
          </div>
          <div className="flex justify-end">
            <button className="px-4 py-2 bg-gray-900 text-white rounded-md disabled:opacity-50" onClick={upload} disabled={!meetingId || !file}>Upload</button>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Process" subtitle="We’ll transcribe, summarize, extract actions/decisions, and run sentiment.">
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-md disabled:opacity-50" onClick={processMeeting} disabled={!meetingId}>Start Processing</button>
          {status && <div className="text-sm text-gray-600">{status}</div>}
        </div>
        {jobId && (
          <div className="space-y-2 mt-3">
            <ProgressBar value={progress} label={`${jobStatus} • ${Math.round(elapsed)}s elapsed`} />
            {jobError && <div className="text-xs text-red-600">Error: {jobError}</div>}
            {!jobError && jobStatus.toLowerCase().includes('succeeded') && meetingId && (
              <div>
                <Link to={`/meetings/${meetingId}`} className="inline-block mt-1 px-3 py-2 bg-green-600 text-white rounded">View Meeting</Link>
              </div>
            )}
          </div>
        )}
      </SectionCard>
    </div>
  )
}
