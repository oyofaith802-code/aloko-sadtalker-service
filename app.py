import os
import re
import uuid
import shutil
import subprocess
import threading
import sys
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULT_DIR = BASE_DIR / "results"
TEMP_DIR = BASE_DIR / "temp"

RESULT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Aloko SadTalker Service")

app.mount(
    "/videos",
    StaticFiles(directory=str(RESULT_DIR)),
    name="videos",
)

jobs = {}


def update_job(job_id, progress=None, stage=None, status=None, video=None, error=None):
    job = jobs.get(job_id)
    if not job:
        return

    if progress is not None:
        job["progress"] = max(0, min(100, int(progress)))

    if stage is not None:
        job["stage"] = stage

    if status is not None:
        job["status"] = status

    if video is not None:
        job["video"] = video

    if error is not None:
        job["error"] = error


def process_job(job_id, avatar_path, audio_path):
    try:
        update_job(
            job_id,
            progress=5,
            stage="Preparing avatar and audio",
            status="processing",
        )

        command = [
            sys.executable,
            str(BASE_DIR / "inference.py"),
            "--source_image",
            str(avatar_path),
            "--driven_audio",
            str(audio_path),
            "--checkpoint_dir",
            str(CHECKPOINT_DIR),
            "--result_dir",
            str(RESULT_DIR),
            "--size",
            "256",
            "--preprocess",
            "crop",
            "--cpu",
        ]

        process = subprocess.Popen(
            command,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        face_current = 0
        face_total = 1

        for line in process.stdout:
            line = line.strip()

            if not line:
                continue

            print(f"[{job_id}] {line}", flush=True)

            if "3DMM Extraction for source image" in line:
                update_job(
                    job_id,
                    progress=10,
                    stage="Extracting facial landmarks",
                )

            elif "3DMM Extraction In Video" in line:
                update_job(
                    job_id,
                    progress=20,
                    stage="Extracting facial motion",
                )

            elif "mel::" in line:
                update_job(
                    job_id,
                    progress=30,
                    stage="Processing audio",
                )

            elif "audio2exp::" in line:
                update_job(
                    job_id,
                    progress=40,
                    stage="Generating facial expressions",
                )

            elif "Face Renderer::" in line:
                match = re.search(r"(\d+)/(\d+)", line)

                if match:
                    face_current = int(match.group(1))
                    face_total = max(1, int(match.group(2)))

                    renderer_progress = (
                        face_current / face_total
                    )

                    progress = 45 + int(renderer_progress * 40)

                    update_job(
                        job_id,
                        progress=progress,
                        stage=f"Animating avatar ({face_current}/{face_total})",
                    )

            elif "The generated video is named" in line:
                update_job(
                    job_id,
                    progress=90,
                    stage="Finalizing video",
                )

        return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(
                f"SadTalker exited with code {return_code}"
            )

        generated = list(RESULT_DIR.glob("*.mp4"))

        if not generated:
            raise RuntimeError(
                "SadTalker completed but no MP4 was produced."
            )

        latest = max(
            generated,
            key=lambda p: p.stat().st_mtime,
        )

        final_path = RESULT_DIR / f"{job_id}.mp4"

        if latest.resolve() != final_path.resolve():
            shutil.move(str(latest), str(final_path))

        update_job(
            job_id,
            progress=100,
            stage="Video ready",
            status="completed",
            video=f"/videos/{final_path.name}",
        )

    except Exception as exc:
        print(f"[{job_id}] ERROR: {exc}", flush=True)

        update_job(
            job_id,
            status="failed",
            stage="Generation failed",
            error=str(exc),
        )

    finally:
        shutil.rmtree(
            avatar_path.parent,
            ignore_errors=True,
        )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "sadtalker",
        "checkpoints": CHECKPOINT_DIR.exists(),
    }


@app.post("/generate")
async def generate(
    avatar: UploadFile = File(...),
    audio: UploadFile = File(...),
):
    job_id = uuid.uuid4().hex

    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    avatar_path = job_dir / (
        avatar.filename or "avatar.png"
    )

    audio_path = job_dir / (
        audio.filename or "audio.mp3"
    )

    with open(avatar_path, "wb") as f:
        shutil.copyfileobj(avatar.file, f)

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "stage": "Queued",
        "video": None,
        "error": None,
    }

    thread = threading.Thread(
        target=process_job,
        args=(job_id, avatar_path, audio_path),
        daemon=True,
    )

    thread.start()

    return {
        "success": True,
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Generation job not found",
        )

    return job

