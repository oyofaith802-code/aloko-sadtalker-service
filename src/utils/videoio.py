
import shutil
import uuid
import os
import subprocess

import cv2


# Known-good FFmpeg installation on this Windows computer
FFMPEG_PATH = (
    r"C:\Users\USER\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.1-full_build-shared\bin\ffmpeg.exe"
)


def load_video_to_cv2(input_path):
    video_stream = cv2.VideoCapture(input_path)

    fps = video_stream.get(cv2.CAP_PROP_FPS)

    full_frames = []

    while True:
        still_reading, frame = video_stream.read()

        if not still_reading:
            video_stream.release()
            break

        full_frames.append(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        )

    return full_frames


def save_video_with_watermark(
    video,
    audio,
    save_path,
    watermark=False
):
    # Check FFmpeg
    if not os.path.exists(FFMPEG_PATH):
        raise FileNotFoundError(
            f"FFmpeg not found at: {FFMPEG_PATH}"
        )

    # Check input video
    if not os.path.exists(video):
        raise FileNotFoundError(
            f"Input video not found: {video}"
        )

    # Check input audio
    if not os.path.exists(audio):
        raise FileNotFoundError(
            f"Input audio not found: {audio}"
        )

    # Create destination directory
    save_dir = os.path.dirname(
        os.path.abspath(save_path)
    )

    os.makedirs(save_dir, exist_ok=True)

    # Temporary output file
    temp_file = os.path.join(
        save_dir,
        f"{uuid.uuid4()}.mp4"
    )

    # Combine video + audio
    #
    # Video:
    #   copied without re-encoding
    #
    # Audio:
    #   encoded to AAC for MP4 compatibility
    #
    command = [
        FFMPEG_PATH,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        video,
        "-i",
        audio,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        temp_file
    ]

    try:
        subprocess.run(
            command,
            check=True
        )

    except subprocess.CalledProcessError as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)

        raise RuntimeError(
            "FFmpeg failed to create the final video file."
        ) from e

    # Verify temporary video exists
    if not os.path.exists(temp_file):
        raise RuntimeError(
            "FFmpeg completed but no video file was created."
        )

    # No watermark
    if watermark is False:

        if os.path.exists(save_path):
            os.remove(save_path)

        shutil.move(
            temp_file,
            save_path
        )

        return save_path

    # -------------------------
    # WATERMARK
    # -------------------------

    try:
        import webui
        from modules import paths

        watermark_path = (
            paths.script_path
            + "/extensions/SadTalker/docs/sadtalker_logo.png"
        )

    except Exception:

        dir_path = os.path.dirname(
            os.path.realpath(__file__)
        )

        watermark_path = os.path.abspath(
            os.path.join(
                dir_path,
                "../../docs/sadtalker_logo.png"
            )
        )

    if not os.path.exists(watermark_path):
        raise FileNotFoundError(
            f"Watermark image not found: {watermark_path}"
        )

    # Temporary watermark output
    watermarked_file = os.path.join(
        save_dir,
        f"{uuid.uuid4()}_watermarked.mp4"
    )

    watermark_command = [
        FFMPEG_PATH,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        temp_file,
        "-i",
        watermark_path,
        "-filter_complex",
        "[1]scale=100:-1[wm];"
        "[0][wm]overlay=(main_w-overlay_w)-10:10",
        watermarked_file
    ]

    try:
        subprocess.run(
            watermark_command,
            check=True
        )

    except subprocess.CalledProcessError as e:

        if os.path.exists(temp_file):
            os.remove(temp_file)

        if os.path.exists(watermarked_file):
            os.remove(watermarked_file)

        raise RuntimeError(
            "FFmpeg failed while adding the watermark."
        ) from e

    # Verify watermark output
    if not os.path.exists(watermarked_file):
        if os.path.exists(temp_file):
            os.remove(temp_file)

        raise RuntimeError(
            "FFmpeg completed but the watermarked video was not created."
        )

    # Remove old final file
    if os.path.exists(save_path):
        os.remove(save_path)

    # Move watermarked video to final location
    shutil.move(
        watermarked_file,
        save_path
    )

    # Remove temporary video
    if os.path.exists(temp_file):
        os.remove(temp_file)

    return save_path
