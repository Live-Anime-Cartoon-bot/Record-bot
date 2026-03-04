import asyncio, datetime, os, re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import 5856009289, 8191916199:AAE-ezyhTkdta-0p8I-lVSsDn8l7UdjhhY0, 100372627111,


@owner_only
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage:\n/record <start_time> <end_time> <M3U8_LINK>"
        )
        return

    start_time, end_time, m3u8_link = context.args[0], context.args[1], context.args[2]

    # Generate filename
    today = datetime.datetime.now().strftime("%d-%m-%Y")
    filename = f"[AnimeCartoon].[{today}].[{start_time}-{end_time}].480p.TPLAY.WEB-DL.HIN.TEL.MAL.ODI.MAR.BEN.ΚΑΝ.ΤΑΜ.H264.mp4"
    out_path = os.path.join(SAVE_DIR, filename)

    msg = await update.message.reply_text(
        f"📥 Recording started...\nFile: {filename}\nStatus: Recording"
    )

    # FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", m3u8_link,
        "-t", "00:02:00",  # 2 minutes demo
        "-map", "0:v", "-map", "0:a",
        "-c:v", "libx264", "-preset", "slow", "-b:v", "700k",
        "-c:a", "aac", "-b:a", "64k",
        "-movflags", "+faststart",
        out_path
    ]

    process = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')
    total_sec = 120  # 2 minutes
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        decoded = line.decode("utf-8")
        match = pattern.search(decoded)
        if match:
            h, m, s = match.groups()
            elapsed = int(h)*3600 + int(m)*60 + int(float(s))
            percent = min(100, (elapsed/total_sec)*100)
            eta = max(0, total_sec - elapsed)
            size_mb = os.path.getsize(out_path)/1024/1024 if os.path.exists(out_path) else 0
            await msg.edit_text(
                f"📥 Recording...\nStatus: Recording\n"
                f"{percent:.1f}%\nSize: {size_mb:.2f}MB\nETA: {eta}s"
            )

    await process.wait()
    await update.message.reply_text(
        f"✅ Recording completed!\nSaved at: {out_path}"
    )
