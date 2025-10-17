from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import SearchQuery, SearchHit
from ..services.embeddings import get_collection


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/", response_model=list[SearchHit])
@router.post("", response_model=list[SearchHit])
def search(q: SearchQuery, db: Session = Depends(get_db)):
    coll = get_collection()
    res = coll.query(query_texts=[q.query], n_results=q.top_k)
    hits: list[SearchHit] = []
    if res and res.get("ids"):
        ids = res["ids"][0]
        documents = res.get("documents", [[]])[0]
        metadatas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0]
        for i in range(len(ids)):
            md = metadatas[i] or {}
            hits.append(SearchHit(
                meeting_id=md.get("meeting_id"),
                segment_id=md.get("segment_id"),
                score=float(distances[i]) if distances else 0.0,
                start=float(md.get("start", 0)),
                end=float(md.get("end", 0)),
                text=documents[i],
                title=md.get("title", ""),
            ))
    return hits
