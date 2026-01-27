import subprocess

def record_stream(url, output_file, duration=30, resolution="480", multi_audio=False):
    """
    Record m3u8 stream using FFmpeg
    :param url: m3u8 link
    :param output_file: path to save mp4
    :param duration: duration in seconds
    :param resolution: 480, 720, 1080
    :param multi_audio: True if multi audio, False for single audio
    """
    try:
        # Base FFmpeg command
        cmd = [
            "ffmpeg",
            "-y",           # overwrite output file if exists
            "-i", url,      # input stream URL
            "-t", str(duration)  # recording duration
        ]

        # Set resolution
        if resolution == "480":
            cmd += ["-s", "854x480"]
        elif resolution == "720":
            cmd += ["-s", "1280x720"]
        elif resolution == "1080":
            cmd += ["-s", "1920x1080"]

        # Audio mapping
        if not multi_audio:
            cmd += ["-map", "0:v:0", "-map", "0:a:0"]

        # Output file
        cmd += [output_file]

        print(f"Running FFmpeg: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed: {e}")
    except Exception as e:
        print(f"Error: {e}")
