import telebot
from telebot import types
import json
import os
import re
from utils.ffmpeg_helper import record_stream

# ==================== CONFIG VARIABLES ====================
BOT_TOKEN = "8365813233:AAHSs86QVjPPB5G_04tAdEzCRXHB_UxLaI4"
API_ID = "29481626"                        # From my.telegram.org
API_HASH = "4892185769903521077c4cea97808b8c"
OWNER_ID = [int(i) for i in os.environ.get("OWNER_ID", "8532720894").split("8532720894")]
AUTH_USERS = [8532720894]                  # Authorized users
TIME_GAP = 0                               # Seconds gap after each request
BOT_USERNAME = "LiveRecording_Bot"         # Bot username without @
API_TOKEN = "65aa5be4d757fb7242fff9dde00f6cd5d4acc977"  # Access token, don't change
SHORTXLINK_URL = "https://shortx.link/abc123"  # Verification link
MAX_DURATION = 300                           # Max recording duration in seconds
# ==========================================================

bot = telebot.TeleBot(BOT_TOKEN)

# Temporary recordings folder
os.makedirs("data/recordings", exist_ok=True)

# Load channels
with open("channels.json", "r") as f:
    CHANNELS = json.load(f)

# ================= /verify =================
VERIFY_TEXT = (
    "✅ Important\n\n"
    "Group users must complete verification before using recording.\n"
    "Use the /verify command to unlock recording access."
)
verify_btn = types.InlineKeyboardMarkup()
verify_btn.add(types.InlineKeyboardButton("🔓 Verify Access", url=SHORTXLINK_URL))

@bot.message_handler(commands=['verify'])
def verify(msg):
    if msg.from_user.id not in AUTH_USERS:
        bot.reply_to(msg, "❌ You are not authorized to use this bot")
        return
    bot.send_message(msg.chat.id, VERIFY_TEXT, reply_markup=verify_btn)

# ================= /help =================
HELP_TEXT = f"""
🎬 How to Record a Stream

Format 1:
http://video_link -d 22-06-2025 -t 10:15 AM -10:19 AM -n 20

Format 2:
/dl -c Sony yay -d 22-06-2025 -t 10:15 AM -10:19 AM -n 20

Note:
• Avoid special characters in filenames (/\:*?"<>|)
• Only non-DRM public streams supported
• If unstable, auto reconnect after 5s (only https URL)
"""
@bot.message_handler(commands=['help', 'start'])
def help_cmd(msg):
    bot.send_message(msg.chat.id, HELP_TEXT)

# ================= /dl -c CHANNEL =================
@bot.message_handler(commands=['dl'])
def dl_handler(msg):
    if msg.from_user.id not in AUTH_USERS:
        bot.reply_to(msg, "❌ You are not authorized to use this bot")
        return

    text = msg.text
    try:
        channel_match = re.search(r"-c (.+?) -d", text)
        time_match = re.search(r"-t (.+?)( -n|$)", text)
        name_match = re.search(r"-n (.+)", text)

        if not channel_match or not time_match:
            bot.reply_to(msg, "❌ Format galat\nUse:\n/dl -c CHANNEL -d DATE -t TIME -n NAME")
            return

        channel_name = channel_match.group(1).strip()
        time_range = time_match.group(1).strip()
        custom_name = name_match.group(1).strip() if name_match else channel_name

        if channel_name not in CHANNELS:
            bot.reply_to(msg, "❌ Channel link mapping nahi mila")
            return

        m3u8_link = CHANNELS[channel_name]
        duration = 30  # demo, parse from -t if needed

        # Resolution + audio buttons
        kb = types.InlineKeyboardMarkup(row_width=2)
        for res in ["480", "720", "1080"]:
            kb.add(
                types.InlineKeyboardButton(f"{res}p Single Audio",
                                           callback_data=f"res_{res}_single|{duration}|{m3u8_link}|{custom_name}"),
                types.InlineKeyboardButton(f"{res}p Multi Audio",
                                           callback_data=f"res_{res}_multi|{duration}|{m3u8_link}|{custom_name}")
            )
        kb.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel"))

        caption = f"📺 Channel: {channel_name}\n⏰ Time: {time_range}\n🎬 Name: {custom_name}\nChoose resolution/audio:"
        bot.send_message(msg.chat.id, caption, reply_markup=kb)

    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {str(e)}")

# ================= Direct M3U8 link handler =================
@bot.message_handler(func=lambda msg: msg.text.startswith("http"))
def link_handler(msg):
    if msg.from_user.id not in AUTH_USERS:
        bot.reply_to(msg, "❌ You are not authorized to use this bot")
        return

    text = msg.text
    try:
        link_match = re.match(r"(http\S+)", text)
        if not link_match:
            bot.reply_to(msg, "❌ Invalid link")
            return

        m3u8_link = link_match.group(1)

        # Optional name
        name_match = re.search(r"-n (.+)", text)
        custom_name = name_match.group(1).strip() if name_match else "Recording"

        duration = 30  # demo, parse from -t if needed

        kb = types.InlineKeyboardMarkup(row_width=2)
        for res in ["480", "720", "1080"]:
            kb.add(
                types.InlineKeyboardButton(f"{res}p Single Audio",
                                           callback_data=f"res_{res}_single|{duration}|{m3u8_link}|{custom_name}"),
                types.InlineKeyboardButton(f"{res}p Multi Audio",
                                           callback_data=f"res_{res}_multi|{duration}|{m3u8_link}|{custom_name}")
            )
        kb.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel"))

        bot.send_message(msg.chat.id, f"📺 Direct Link\n🎬 Name: {custom_name}\nChoose resolution/audio:", reply_markup=kb)

    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {str(e)}")

# ================= Callback Handler =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "cancel":
        bot.edit_message_text("❌ Cancelled", call.message.chat.id, call.message.message_id)
        return

    try:
        res, duration, link, name = call.data.split("|")
        duration = int(duration)
        resolution = res.split("_")[1]
        multi_audio = "multi" in res
        output_file = f"data/recordings/{name.replace(' ','_')}_{resolution}.mp4"

        bot.edit_message_text(f"⏺ Recording {name} at {resolution}p...", call.message.chat.id, call.message.message_id)
        record_stream(link, output_file, duration, resolution, multi_audio)

        with open(output_file, "rb") as f:
            bot.send_video(call.message.chat.id, f)

        os.remove(output_file)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Error: {str(e)}")

# ================= RUN BOT =================
bot.polling()
