from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from ytmusicapi import YTMusic
import requests

app = FastAPI()
yt = YTMusic()

#Pydantic (DTO)
class Track(BaseModel):
    youtubeTrackId: str
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None

class WebhookPayload(BaseModel):
    jobId: str
    sourcePlaylistId: str
    status: str
    tracks: List[Track]

class FetchRequest(BaseModel):
    jobId: str
    playlistId: str

def fetch_and_forward_playlist(job_id: str, playlist_id: str):
    try:
        playlist_data =  yt.get_playlist(playlist_id, limit=None)
        tracks = []

        for item in playlist_data.get('tracks', []):
            if not item.get('videoId'):
                continue #Skip non playable tracks

            artists = ", ".join([a['name'] for a in item.get('artists', [])]) if item.get('artists') else None
            album = item.get('album', {}).get('name') if item.get('album') else None

            tracks.append(Track(
                youtubeTrackId=item['videoId'],
                title=item['title'],
                artist=artists,
                album=album
            ))

        payload = WebhookPayload(
            jobId=job_id,
            sourcePlaylistId=playlist_id,
            status="FETCH_SUCCESS",
            tracks=tracks
        )

    except Exception as e:
        print(f"Error fetching playlist: {e}")
        payload = WebhookPayload(
            jobId=job_id,
            sourcePlaylistId=playlist_id,
            status="FETCH_FAILED",
            tracks=[]
        )

    try:
        requests.post(
            "http://localhost:8080/api/webhooks/youtube",
            json=payload.model_dump()
        )
        print(f"Successfully forwarded job {job_id} to Java.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to reach Java backend: {e}")

@app.post("/api/worker/fetch")
async def trigger_fetch(request: FetchRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(fetch_and_forward_playlist, request.jobId, request.playlistId)

    return {"message": "Fetch job accepted and running in background"}

