# Owner-only decorator
# -----------------------------
def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("❌ Only Owner Can Use This Bot.")
            return
        return await func(update, context)
    return wrapper

# -----------------------------
# User data store
# -----------------------------
user_data_store = {
    OWNER_ID: {
        "title": "",
        "watermark": False,
        "blackbars": False,
        "quality": "480",
        "compress": True,
        "recordings": [],
        "total_minutes": 0
    }
}

MAX_RECORDINGS = 4
MAX_TOTAL_MINUTES = 120  # 2 hours

# -----------------------------
# Progress bar helper
# -----------------------------
def progress_bar(percent):
    filled = int(percent / 10)
    return "█" * filled + "░" * (10 - filled)

# -----------------------------
# /start command
# -----------------------------
@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("360p", callback_data="quality_360"),
         InlineKeyboardButton("480p", callback_data="quality_480")],
        [InlineKeyboardButton("576p", callback_data="quality_576"),
         InlineKeyboardButton("720p", callback_data="quality_720")],
        [InlineKeyboardButton("Compress", callback_data="compress"),
         InlineKeyboardButton("Skip", callback_data="skip")],
        [InlineKeyboardButton("Watermark ON/OFF", callback_data="watermark"),
         InlineKeyboardButton("Black Bars ON/OFF", callback_data="blackbars")],
        [InlineKeyboardButton("Set Title", callback_data="title")],
        [InlineKeyboardButton("Start Recording Queue", callback_data="start_queue")]
    ]
    await update.message.reply_text(
        f"🌇 Good Evening {update.effective_user.first_name} 👋\n"
        "🎥 Owner Control Board\nSelect options and start recording queue:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -----------------------------
# /titleintegrated command
# -----------------------------
@owner_only
async def titleintegrated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/titleintegrated ? – Show current title\n"
            "/titleintegrated <title> – Set new title\n"
            "/titleintegrated cancel – Remove title"
        )
        return
    arg = " ".join(context.args).strip()
    if arg == "?":
        title = user_data_store[OWNER_ID].get("title", "")
        await update.message.reply_text(f"📌 Current Title: {title}" if title else "❌ No title set yet.")
    elif arg.lower() == "cancel":
        user_data_store[OWNER_ID]["title"] = ""
        await update.message.reply_text("❌ Title cancelled.")
    else:
        user_data_store[OWNER_ID]["title"] = arg
        await update.message.reply_text(f"✅ Title saved: {arg}")

# -----------------------------
# /addrecord command
# -----------------------------
@owner_only
async def addrecord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /addrecord <M3U8 link> <duration in minutes>\n"
            "Example: /addrecord https://example.com/stream.m3u8 16"
        )
        return

    link = context.args[0]
    try:
        duration = int(context.args[1])
    except:
        await update.message.reply_text("❌ Duration must be an integer (minutes).")
        return

    data = user_data_store[OWNER_ID]
    if len(data["recordings"]) >= MAX_RECORDINGS:
        await update.message.reply_text("❌ Max 4 recordings reached.")
        return
    if data["total_minutes"] + duration > MAX_TOTAL_MINUTES:
        await update.message.reply_text("❌ Total recording limit 2 hours exceeded.")
        return

    data["recordings"].append({"link": link, "duration": duration})
    data["total_minutes"] += duration
    await update.message.reply_text(f"✅ Recording added: {link} ({duration} min)\n"
                                    f"Total queued: {len(data['recordings'])} recordings, "
                                    f"{data['total_minutes']} minutes.")

# -----------------------------
# Button handler
# -----------------------------
@owner_only
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = user_data_store[OWNER_ID]

    if query.data.startswith("quality_"):
        data["quality"] = query.data.split("_")[1]
        await query.edit_message_text(f"✅ Quality selected: {data['quality']}p")
    elif query.data == "compress":
        data["compress"] = True
        await query.edit_message_text("⚡ Compression enabled")
    elif query.data == "skip":
        data["compress"] = False
        await query.edit_message_text("⚡ Upload original enabled")
    elif query.data == "watermark":
        data["watermark"] = not data["watermark"]
        await query.edit_message_text(f"Watermark: {'ON' if data['watermark'] else 'OFF'}")
    elif query.data == "blackbars":
        data["blackbars"] = not data["blackbars"]
        await query.edit_message_text(f"Black Bars: {'ON' if data['blackbars'] else 'OFF'}")
    elif query.data == "title":
        await update.message.reply_text("📌 Use /titleintegrated <text> to set title")
    elif query.data == "start_queue":
        await start_recording_queue(update, context, data)

# -----------------------------
# Real-time ffmpeg recording queue
# -----------------------------
async def start_recording_queue(update, context, data):
    query = update.callback_query
    if not data["recordings"]:
        await query.edit_message_text("❌ No recordings in queue. Add recordings with /addrecord")
        return

    for idx, rec in enumerate(data["recordings"], start=1):
        link = rec["link"]
        duration = rec["duration"]
        base_file = os.path.join(DOWNLOAD_DIR, f"record_{idx}.mp4")
        final_file = base_file

        msg = await query.edit_message_text(f"📥 Recording {idx}/{len(data['recordings'])}...\n[░░░░░░░░░░] 0%")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", link, "-t", str(duration*60),
            "-progress", "pipe:1", "-c", "copy", base_file
        ]
        proc = await asyncio.create_subprocess_exec(*ffmpeg_cmd,
                                                    stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)
        percent = 0
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line = line.decode().strip()
            if line.startswith("out_time_ms="):
                ms = int(line.split("=")[1])
                percent = min(int(ms / (duration*60*1000) * 100), 100)
                await msg.edit_text(f"📥 Recording {idx}/{len(data['recordings'])}...\n[{progress_bar(percent)}] {percent}%")
        await proc.wait()

        # ---------------- COMPRESSION ----------------
        if data.get("compress", True):
            msg = await query.edit_message_text(f"⚡ Compressing {idx}/{len(data['recordings'])}...\n[░░░░░░░░░░] 0%")
            compressed_file = os.path.join(DOWNLOAD_DIR, f"record_compressed_{idx}.mp4")
            compress_cmd = ["ffmpeg", "-y", "-i", base_file, "-b:v", "1M"]
            if data.get("watermark"):
                compress_cmd += ["-i", "watermark.png", "-filter_complex", "overlay=10:10"]
            if data.get("blackbars"):
                compress_cmd += ["-vf", "pad=iw:ih+100:0:50:black"]
            if data.get("title"):
                compress_cmd += ["-vf", f"drawtext=text='{data['title']}':x=10:y=H-th-10:fontsize=24:fontcolor=white"]
            compress_cmd.append(compressed_file)

            proc2 = await asyncio.create_subprocess_exec(*compress_cmd,
                                                         stdout=asyncio.subprocess.PIPE,
                                                         stderr=asyncio.subprocess.PIPE)
            percent = 0
            while True:
                line = await proc2.stderr.readline()
                if not line:
                    break
                percent = min(percent + 5, 100)
                await msg.edit_text(f"⚡ Compressing {idx}/{len(data['recordings'])}...\n[{progress_bar(percent)}] {percent}%")
            await proc2.wait()
            final_file = compressed_file

        # ---------------- UPLOAD ----------------
        msg = await query.edit_message_text(f"📤 Uploading {idx}/{len(data['recordings'])}...\n[░░░░░░░░░░] 0%")
        percent = 0
        with open(final_file, "rb") as f:
            for i in range(0, 101, 10):
                percent = i
                await msg.edit_text(f"📤 Uploading {idx}/{len(data['recordings'])}...\n[{progress_bar(percent)}] {percent}%")
                await asyncio.sleep(0.5)
            await context.bot.send_video(chat_id=OWNER_ID, video=f, caption=f"✅ Recording {idx} Completed!")

        os.remove(base_file)
        if final_file != base_file:
            os.remove(final_file)

    data["recordings"] = []
    data["total_minutes"] = 0
    await query.edit_message_text("✅ All recordings uploaded. Queue cleared.")

# -----------------------------
# Run Bot
# -----------------------------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("titleintegrated", titleintegrated))
app.add_handler(CommandHandler("addrecord", addrecord))
app.add_handler(CallbackQueryHandler(button_handler))

print("✅ Multi-recording M3U8 Bot (real-time progress) is running...")
app.run_polling()
