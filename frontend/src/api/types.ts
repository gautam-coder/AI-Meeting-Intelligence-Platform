export interface Meeting {
  id: string
  title: string
  status: string
  created_at: string
  duration_seconds: number
}

export interface SearchHit {
  meeting_id: string
  segment_id: string
  score: number
  start: number
  end: number
  text: string
  title: string
}

