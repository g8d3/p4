import shutil
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import Config
from .db import JobStore
from .worker import Worker

STATIC_DIR = Path(__file__).parent / "static"


class JobIn(BaseModel):
    url: str


class BatchIn(BaseModel):
    urls: list[str]


class ConfigIn(BaseModel):
    key: str
    value: object


def create_app(config_path: str | Path | None = None) -> FastAPI:
    config_path = Path(config_path or (Path(__file__).parent.parent / "config.json"))
    cfg = Config(config_path)
    store = JobStore(cfg.data_dir / "queue.db")
    worker = Worker(store, cfg, log=lambda *a: print("[worker]", *a))

    async def _shutdown():
        worker.stop()
        from .detector import cleanup_browser
        cleanup_browser()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker.start()
        yield
        await _shutdown()

    app = FastAPI(title="URL Video Queue", lifespan=lifespan)
    app.state.cfg = cfg
    app.state.store = store
    app.state.worker = worker

    origins = cfg.get("allow_origins") or []
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins,
                           allow_methods=["*"], allow_headers=["*"])

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    async def health():
        return {"ok": True, "window_open": cfg.window_open(),
                "chrome": bool(shutil.which("google-chrome") or shutil.which("chromium"))}

    @app.post("/api/jobs", status_code=202)
    async def create_job(body: BatchIn | JobIn):
        urls = body.urls if isinstance(body, BatchIn) else [body.url]
        jobs = []
        for u in urls:
            u = u.strip()
            if not u.startswith(("http://", "https://")):
                raise HTTPException(422, f"invalid url: {u}")
            jobs.append(store.create(u))
        return {"jobs": jobs}

    @app.get("/api/jobs")
    async def list_jobs():
        return {"jobs": store.list()}

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str):
        job = store.get(job_id)
        if not job:
            raise HTTPException(404, "job not found")
        return job

    @app.delete("/api/jobs/{job_id}")
    async def delete_job(job_id: str):
        job = store.get(job_id)
        if not job:
            raise HTTPException(404, "job not found")
        if job["status"] in ("queued", "waiting_window", "detecting",
                             "downloading", "merging"):
            store.update(job_id, status="cancelling")
            return {"id": job_id, "status": "cancelling"}
        store.delete(job_id)
        return {"id": job_id, "status": "deleted"}

    @app.get("/api/jobs/{job_id}/video")
    async def get_video(job_id: str):
        job = store.get(job_id)
        if not job:
            raise HTTPException(404, "job not found")
        if job["status"] != "done" or not job["output_path"]:
            raise HTTPException(409, f"video not ready (status={job['status']})")
        path = Path(job["output_path"])
        if not path.exists():
            raise HTTPException(410, "output file missing")
        return FileResponse(path, media_type="video/mp4", headers={
            "Content-Disposition": f"inline; filename=merged-{job_id}.mp4",
        })

    @app.post("/api/detect")
    async def detect(body: JobIn):
        import threading as _t
        result = {}
        from .detector import detect_videos

        def run():
            result["items"] = detect_videos(body.url, cfg)

        t = _t.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=120)
        if "items" not in result:
            raise HTTPException(504, "detection timed out")
        return {"url": body.url, "videos": result["items"]}

    @app.get("/api/config")
    async def get_config():
        return cfg.data

    @app.put("/api/config")
    async def set_config(body: ConfigIn):
        cfg.set(body.key, body.value)
        cfg.save()
        return cfg.data

    return app


app = create_app()
