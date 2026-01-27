import subprocess
import os

def record_stream(url, output_file, duration, resolution="480", multi_audio=False):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", url,
        "-t", str(duration)
    ]

    if resolution == "480":
        cmd += ["-vf", "scale=854:480"]
    elif resolution == "720":
        cmd += ["-vf", "scale=1280:720"]
    elif resolution == "1080":
        cmd += ["-vf", "scale=1920:1080"]

    if not multi_audio:
        cmd += ["-map", "0:v:0", "-map", "0:a:0"]

    cmd += [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        output_file
    ]

    subprocess.run(cmd, check=True)
