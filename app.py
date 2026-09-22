import os
import uuid
import shutil
import subprocess
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
app.mount("/videos", StaticFiles(directory=str(RESULT_DIR)), name="videos")


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

    avatar_path = job_dir / (avatar.filename or "avatar.png")
    audio_path = job_dir / (audio.filename or "audio.mp3")

    try:
        with open(avatar_path, "wb") as f:
            shutil.copyfileobj(avatar.file, f)

        with open(audio_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        command = [
            "python",
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

        process = subprocess.run(
            command,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )

        if process.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "SadTalker inference failed",
                    "stdout": process.stdout[-4000:],
                    "stderr": process.stderr[-4000:],
                },
            )

        generated = list(RESULT_DIR.glob("*.mp4"))

        if not generated:
            raise HTTPException(
                status_code=500,
                detail="SadTalker completed but no MP4 was produced.",
            )

        latest = max(generated, key=lambda p: p.stat().st_mtime)

        final_path = RESULT_DIR / f"{job_id}.mp4"
        shutil.move(str(latest), str(final_path))

        return {
            "success": True,
            "job_id": job_id,
            "video": f"/videos/{final_path.name}",
        }

    finally:
        shutil.rmtree(job_dir, ignore_errors=True)

