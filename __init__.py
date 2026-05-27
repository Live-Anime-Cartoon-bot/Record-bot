"""
OTT Recorder Bot — all modules combined.
Files: main.py · config.py · handlers/__init__.py  (this file)
"""

# ── Standard library ──────────────────────────────────────────────────────────
import asyncio
import json
import logging
import os
import re
import random
import secrets
import shlex
import shutil
import time
import types
from collections import Counter
from datetime import datetime, timedelta
from os.path import join
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import psutil

# ── Third-party ───────────────────────────────────────────────────────────────
import aiohttp
import pytz
import requests as _req_lib

from pyrogram import Client, enums, filters
from pyrogram.types import (
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

import config


# ═════════════════════════════════════════════════════════════════════════════
#  CONSTANTS  (was constants.py)
# ═════════════════════════════════════════════════════════════════════════════

MAX_CONCURRENT = 3

PROGRESS_FILLED = '<emoji id="5915540975987462465">▰</emoji>'
PROGRESS_EMPTY  = '<emoji id="6217587660634989068">▱</emoji>'

LANG_MAP: Dict[str, str] = {
    "hin": "HIN", "hi": "HIN",
    "kan": "KAN", "kn": "KAN",
    "tel": "TEL", "te": "TEL",
    "tam": "TAM", "ta": "TAM",
    "mal": "MAL", "ml": "MAL",
    "ben": "BEN", "bn": "BEN",
    "mar": "MAR", "mr": "MAR",
    "eng": "ENG", "en": "ENG",
    "pun": "PUN", "pa": "PUN",
    "guj": "GUJ", "gu": "GUJ",
    "ori": "ORI", "or": "ORI",
    "urd": "URD", "ur": "URD",
}

LANG_FULL: Dict[str, str] = {
    "hin": "Hindi",     "hi":  "Hindi",
    "kan": "Kannada",   "kn":  "Kannada",
    "tel": "Telugu",    "te":  "Telugu",
    "tam": "Tamil",     "ta":  "Tamil",
    "mal": "Malayalam", "ml":  "Malayalam",
    "ben": "Bengali",   "bn":  "Bengali",
    "mar": "Marathi",   "mr":  "Marathi",
    "eng": "English",   "en":  "English",
    "pun": "Punjabi",   "pa":  "Punjabi",
    "guj": "Gujarati",  "gu":  "Gujarati",
    "ori": "Odia",      "or":  "Odia",
    "urd": "Urdu",      "ur":  "Urdu",
}

WM_POSITIONS: Dict[str, tuple] = {
    "top_left":     ("10", "10"),
    "top_right":    ("w-tw-10", "10"),
    "center":       ("(w-tw)/2", "(h-th)/2"),
    "bottom_left":  ("10", "h-th-10"),
    "bottom_right": ("w-tw-10", "h-th-10"),
}

WM_LABEL: Dict[str, str] = {
    "top_left":     "↖ Top-Left",
    "top_right":    "↗ Top-Right",
    "center":       "⊙ Center",
    "bottom_left":  "↙ Bottom-Left",
    "bottom_right": "↘ Bottom-Right",
}

WM_LABEL_TO_KEY: Dict[str, str] = {v: k for k, v in WM_LABEL.items()}

VIDEO_SIZES: Dict[str, dict] = {
    "size1": {
        "label": "📺 Size 1 — 720×396",
        "desc":  "16:9 Widescreen",
        "vf":    "scale=720:396:force_original_aspect_ratio=decrease,pad=720:396:(ow-iw)/2:(oh-ih)/2",
    },
    "size2": {
        "label": "📺 Size 2 — 720×540",
        "desc":  "4:3 Black bars",
        "vf":    "scale=720:540:force_original_aspect_ratio=decrease,pad=720:540:(ow-iw)/2:(oh-ih)/2",
    },
    "size3": {
        "label": "📺 Size 3 — 720×405",
        "desc":  "16:9 Border all sides",
        "vf":    "scale=700:394:force_original_aspect_ratio=decrease,pad=720:405:10:5",
    },
    "bars_169": {
        "label": "◼ 16:9 Bars — 720×576",
        "desc":  "Letterbox",
        "vf":    "scale=720:576:force_original_aspect_ratio=decrease,pad=720:576:(ow-iw)/2:(oh-ih)/2",
    },
    "bars_43": {
        "label": "◼ 4:3 Bars — 720×540",
        "desc":  "Pillarbox",
        "vf":    "scale=-2:540:force_original_aspect_ratio=decrease,pad=720:540:(ow-iw)/2:(oh-ih)/2",
    },
    "480p": {
        "label": "📺 480p — 854×480",
        "desc":  "Standard 480p (channel default)",
        "vf":    "scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2:black",
    },
    "original": {
        "label": "🔓 Original Size",
        "desc":  "No scaling",
        "vf":    None,
    },
}

SIZE_LABEL_TO_KEY: Dict[str, str] = {v["label"]: k for k, v in VIDEO_SIZES.items()}

SLOT_EMOJI = ["1️⃣", "2️⃣", "3️⃣"]

COMPRESS_PRESETS: Dict[str, tuple] = {
    "🔵 High Quality":   ("-c:v libx264 -crf 23 -preset fast -c:a aac -b:a 128k", "High (good quality, moderate size)"),
    "🟡 Medium Quality": ("-c:v libx264 -crf 28 -preset fast -c:a aac -b:a 96k",  "Medium (balanced)"),
    "🔴 Low (Smallest)": ("-c:v libx264 -crf 32 -preset fast -c:a aac -b:a 64k",  "Low (small size, lower quality)"),
}

OTT_RES_LABEL_TO_FMT: Dict[str, str] = {}

OTT_AUDIO_LANGS: Dict[str, Optional[str]] = {"🌐 Multi": None}

_HEIGHT_LABEL: Dict[int, str] = {
    144: "📺 140p",  240: "📺 240p",  360: "📺 360p",
    480: "📺 480p",  576: "📺 576p",  640: "📺 640p",
    720: "📺 720p",  1080: "🔵 1080p", 1440: "🔶 2K",
    2160: "🔶 4K",
}

_HEIGHT_FMT: Dict[int, str] = {
    h: f"bestvideo[height<={h}]+bestaudio/best[height<={h}]"
    for h in [144, 240, 360, 480, 576, 640, 720, 1080, 1440, 2160]
}

_LANG_CODE_TO_LABEL: Dict[str, str] = {
    "hin": "🇮🇳 Hindi",    "tam": "🎬 Tamil",
    "tel": "🎭 Telugu",    "mal": "🌴 Malayalam",
    "kan": "🌸 Kannada",   "mar": "🎪 Marathi",
    "ben": "🇧🇩 Bengali",  "pun": "🎵 Punjabi",
    "eng": "🇬🇧 English",  "urd": "🕌 Urdu",
    "guj": "🎶 Gujarati",  "ori": "🌸 Odia",
}

MAX_HISTORY = 500


# ═════════════════════════════════════════════════════════════════════════════
#  VERIFY  (was verify.py)
# ═════════════════════════════════════════════════════════════════════════════

VERIFY_HOURS = 4
verified_users: Dict[int, float] = {}
pending_tokens: Dict[int, str]   = {}


def is_verified(user_id: int, owner_ids: list, auth_users: list) -> bool:
    if user_id in owner_ids or user_id in auth_users:
        return True
    if user_id in verified_users:
        if time.time() < verified_users[user_id]:
            return True
        else:
            del verified_users[user_id]
    return False


def create_token(user_id: int) -> str:
    token = secrets.token_hex(16)
    pending_tokens[user_id] = token
    return token


def confirm_token(user_id: int, token: str) -> bool:
    if user_id in pending_tokens and pending_tokens[user_id] == token:
        expiry = time.time() + (VERIFY_HOURS * 3600)
        verified_users[user_id] = expiry
        del pending_tokens[user_id]
        return True
    return False


def add_validity(user_id: int, seconds: int):
    current = verified_users.get(user_id, time.time())
    if current < time.time():
        current = time.time()
    verified_users[user_id] = current + seconds


def time_remaining(user_id: int) -> str:
    if user_id not in verified_users:
        return "0h 0m"
    remaining = int(verified_users[user_id] - time.time())
    if remaining <= 0:
        return "0h 0m"
    h = remaining // 3600
    m = (remaining % 3600) // 60
    return f"{h}h {m}m"


# ═════════════════════════════════════════════════════════════════════════════
#  LANG  (was lang.py)
# ═════════════════════════════════════════════════════════════════════════════

user_lang: Dict[int, str] = {}


def get_lang(uid) -> str:
    return user_lang.get(uid, "en")


def set_lang(uid, lang: str):
    user_lang[uid] = lang


STRINGS: Dict[str, Dict[str, str]] = {
    "btn_record":       {"en": "🎥 Record",          "hi": "🎥 रिकॉर्ड"},
    "btn_download":     {"en": "📥 Download",         "hi": "📥 डाउनलोड"},
    "btn_ott":          {"en": "🌐 OTT Download",     "hi": "🌐 OTT डाउनलोड"},
    "btn_status":       {"en": "📊 Status",           "hi": "📊 स्टेटस"},
    "btn_compress":     {"en": "🗜 Compress",          "hi": "🗜 कंप्रेस"},
    "btn_screenshot":   {"en": "📸 Screenshot",       "hi": "📸 स्क्रीनशॉट"},
    "btn_cookies":      {"en": "🍪 Cookies",          "hi": "🍪 कुकीज़"},
    "btn_help":         {"en": "📖 Help",              "hi": "📖 मदद"},
    "btn_select_all":   {"en": "🔁 Select All Tracks",  "hi": "🔁 सभी ट्रैक चुनें"},
    "btn_back":         {"en": "◀️ Back",               "hi": "◀️ वापस"},
    "btn_next_wm":      {"en": "✅ Next: Watermark",    "hi": "✅ आगे: वॉटरमार्क"},
    "btn_cancel_setup": {"en": "❌ Cancel Setup",        "hi": "❌ सेटअप रद्द"},
    "btn_wm_off":       {"en": "🚫 Watermark OFF",           "hi": "🚫 वॉटरमार्क बंद"},
    "btn_wm_text":      {"en": "✏️ Change Watermark Text",   "hi": "✏️ वॉटरमार्क टेक्स्ट बदलें"},
    "btn_auto_mode":    {"en": "⏱️ Auto: First+Last 1min",   "hi": "⏱️ ऑटो: पहले+आखिरी 1min"},
    "btn_next_size":    {"en": "📐 Next: Video Size →",      "hi": "📐 आगे: वीडियो साइज →"},
    "btn_start_dl":     {"en": "📥 START DOWNLOAD",          "hi": "📥 डाउनलोड शुरू"},
    "btn_cancel":       {"en": "❌ Cancel",                   "hi": "❌ रद्द करें"},
    "wm_top_left":      {"en": "↖ Top-Left",     "hi": "↖ ऊपर-बाएं"},
    "wm_top_right":     {"en": "↗ Top-Right",    "hi": "↗ ऊपर-दाएं"},
    "wm_center":        {"en": "⊙ Center",        "hi": "⊙ बीच में"},
    "wm_bottom_left":   {"en": "↙ Bottom-Left",  "hi": "↙ नीचे-बाएं"},
    "wm_bottom_right":  {"en": "↘ Bottom-Right", "hi": "↘ नीचे-दाएं"},
    "btn_back_wm":      {"en": "◀️ Back to Watermark",  "hi": "◀️ वॉटरमार्क पर वापस"},
    "btn_start_rec":    {"en": "▶️ Start Recording",    "hi": "▶️ रिकॉर्डिंग शुरू"},
    "btn_cancel_all":   {"en": "❌ Cancel ALL",    "hi": "❌ सब रद्द करें"},
    "btn_close_menu":   {"en": "◀️ Close Menu",    "hi": "◀️ मेनू बंद"},
    "btn_cmp_high":     {"en": "🔵 High Quality",   "hi": "🔵 उच्च गुणवत्ता"},
    "btn_cmp_med":      {"en": "🟡 Medium Quality", "hi": "🟡 मध्यम गुणवत्ता"},
    "btn_cmp_low":      {"en": "🔴 Low (Smallest)", "hi": "🔴 कम (सबसे छोटा)"},
    "btn_cmp_cancel":   {"en": "❌ Cancel Compress", "hi": "❌ कंप्रेस रद्द"},
    "btn_ott_cancel":   {"en": "❌ Cancel OTT",          "hi": "❌ OTT रद्द"},
    "btn_back_res":     {"en": "◀️ Back to Resolution",  "hi": "◀️ रिज़ॉल्यूशन पर वापस"},
    "msg_setup_cancelled": {
        "en": "❌ Setup cancelled.",
        "hi": "❌ सेटअप रद्द कर दिया गया।",
    },
    "msg_cancel_cancelled": {
        "en": "❌ Cancelled.",
        "hi": "❌ रद्द कर दिया गया।",
    },
    "hint_record": {
        "en": "📌 Usage:\n`/rec http://link 00:00:00 Filename`",
        "hi": "📌 तरीका:\n`/rec http://link 00:00:00 Filename`",
    },
    "hint_download": {
        "en": "📌 Usage:\n`/download http://link Filename`",
        "hi": "📌 तरीका:\n`/download http://link Filename`",
    },
    "hint_ott": {
        "en": "📌 Usage:\n`/ott_download https://youtube.com/... Filename`",
        "hi": "📌 तरीका:\n`/ott_download https://youtube.com/... Filename`",
    },
    "hint_compress": {
        "en": "📌 Reply to a video and send `/compress`",
        "hi": "📌 किसी वीडियो को reply करके `/compress` भेजें",
    },
    "hint_screenshot": {
        "en": "📌 Reply to a video and send `/screenshot [1-30]`",
        "hi": "📌 किसी वीडियो को reply करके `/screenshot [1-30]` भेजें",
    },
    "hint_cookies": {
        "en": "📌 Use `/cookies_add` to upload, `/cookies_status` to check, `/del_cookies` to remove",
        "hi": "📌 `/cookies_add` से upload करें, `/cookies_status` से check करें, `/del_cookies` से हटाएं",
    },
    "msg_no_active": {
        "en": "❌ **No active recording to cancel!**",
        "hi": "❌ **कोई active recording नहीं है रद्द करने के लिए!**",
    },
    "msg_all_cancelled": {
        "en": "✅ **All recordings cancelled.**",
        "hi": "✅ **सभी रिकॉर्डिंग रद्द कर दी गई।**",
    },
    "msg_menu_closed": {
        "en": "↩️ Menu closed.",
        "hi": "↩️ मेनू बंद कर दिया।",
    },
    "msg_wm_text_prompt": {
        "en": "✏️ **Type the new watermark text and send it:**",
        "hi": "✏️ **नया वॉटरमार्क टेक्स्ट टाइप करके भेजें:**",
    },
    "msg_lang_set_en": {
        "en": "🇬🇧 **Language changed to English!**\n\nAll buttons and messages are now in English.",
        "hi": "🇬🇧 **भाषा अंग्रेज़ी में बदल दी गई!**\n\nसभी बटन और संदेश अब अंग्रेज़ी में हैं।",
    },
    "msg_lang_set_hi": {
        "en": "🇮🇳 **Language changed to Hindi!**\n\nसभी बटन और संदेश अब हिंदी में हैं।",
        "hi": "🇮🇳 **भाषा हिंदी में बदल दी गई!**\n\nसभी बटन और संदेश अब हिंदी में हैं।",
    },
    "msg_lang_choose": {
        "en": "🌐 **Choose Language / भाषा चुनें:**",
        "hi": "🌐 **भाषा चुनें / Choose Language:**",
    },
}


def t(uid, key: str) -> str:
    lang  = get_lang(uid)
    entry = STRINGS.get(key, {})
    return entry.get(lang) or entry.get("en") or key


_CANONICAL: Dict[str, str] = {}
for _key, _langs in STRINGS.items():
    _en_val = _langs.get("en", "")
    for _lang_val in _langs.values():
        if _lang_val:
            _CANONICAL[_lang_val] = _en_val


def to_canonical(text: str) -> str:
    if text in _CANONICAL:
        return _CANONICAL[text]
    stripped = text.lstrip("✅ ")
    return _CANONICAL.get(stripped, text)


WM_LABEL_BILINGUAL: Dict[str, str] = {}
_WM_KEYS = {
    "wm_top_left":     "top_left",
    "wm_top_right":    "top_right",
    "wm_center":       "center",
    "wm_bottom_left":  "bottom_left",
    "wm_bottom_right": "bottom_right",
}
for _str_key, _pos_key in _WM_KEYS.items():
    for _lv in STRINGS[_str_key].values():
        WM_LABEL_BILINGUAL[_lv] = _pos_key


# ═════════════════════════════════════════════════════════════════════════════
#  LIMIT SYSTEM  (was limit_system.py)
# ═════════════════════════════════════════════════════════════════════════════

LIMIT_FILE = "user_limits.json"

DEFAULT_REC_LIMIT   = 1
DEFAULT_VERIFY_LEFT = 3
LUCKY_RATIO         = 5.8
REFRESH_SECONDS     = 12 * 3600

VERIFY_STEPS = [
    {"rec_delta": +5, "result_rec": None,  "msg": "Aapko milenge +Rec 5"},
    {"rec_delta": -2, "result_rec": 4,     "msg": "Aapki limit ghatkar hogi: Rec 4"},
    {"rec_delta": -1, "result_rec": 3,     "msg": "Aapki limit aur ghatkar hogi: Rec 3"},
]

NEW_USER_WELCOME = (
    "👋 **Welcome to the Bot!**\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "🚀 बोट में आपका स्वागत है! आपका अकाउंट सफ़लपूर्वक एक्टिवेट कर दिया गया है।\n\n"
    f"🎁 नए यूज़र के तौर पर आपको **Rec {DEFAULT_REC_LIMIT}** का ट्रायल बैलेंस "
    f"और **{DEFAULT_VERIFY_LEFT} Verification** चांस मिले हैं।\n\n"
    "📊 अपनी पूरी लिमिट देखने के लिए अभी टाइप करें: /limit\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━"
)


def is_new_user(user_id: int) -> bool:
    data = _ls_load()
    return str(user_id) not in data


def _ls_load() -> dict:
    try:
        with open(LIMIT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _ls_save(data: dict):
    with open(LIMIT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _new_user_record() -> dict:
    is_lucky = random.random() < (1.0 / LUCKY_RATIO)
    return {
        "rec_limit":    DEFAULT_REC_LIMIT,
        "verify_left":  DEFAULT_VERIFY_LEFT,
        "verify_done":  0,
        "is_lucky":     is_lucky,
        "last_refresh": time.time(),
        "first_time":   True,
    }


def get_user(user_id: int) -> dict:
    data = _ls_load()
    uid  = str(user_id)
    if uid not in data:
        data[uid] = _new_user_record()
        _ls_save(data)
    return data[uid]


def mark_seen(user_id: int):
    data = _ls_load()
    uid  = str(user_id)
    if uid in data:
        data[uid]["first_time"] = False
        _ls_save(data)


def is_unlimited(user_id: int, owner_ids: list = None, auth_users: list = None) -> bool:
    if owner_ids and user_id in owner_ids:
        return True
    if auth_users and user_id in auth_users:
        return True
    return False


def use_rec(user_id: int, unlimited: bool = False) -> tuple:
    if unlimited:
        return True, "✅ Unlimited access."
    data = _ls_load()
    uid  = str(user_id)
    if uid not in data:
        data[uid] = _new_user_record()
    user = data[uid]
    if user["rec_limit"] <= 0:
        return False, "❌ Rec limit khatam ho gayi! /limit check karein ya verify karein."
    user["rec_limit"] -= 1
    user["first_time"] = False
    data[uid] = user
    _ls_save(data)
    return True, f"✅ 1 Rec use hua. Bacha: Rec {user['rec_limit']}"


def apply_verify_bonus(user_id: int) -> tuple:
    data = _ls_load()
    uid  = str(user_id)
    if uid not in data:
        data[uid] = _new_user_record()
    user = data[uid]
    if user["verify_left"] <= 0:
        return False, "🚫 Aaj ke liye sab verifications lock ho gaye! Kal tak wait karein."
    step_idx = user["verify_done"]
    if step_idx >= len(VERIFY_STEPS):
        return False, "🚫 Verify limit expire ho gayi!"
    step = VERIFY_STEPS[step_idx]
    if step["result_rec"] is not None:
        user["rec_limit"] = step["result_rec"]
    else:
        user["rec_limit"] = max(0, user["rec_limit"] + step["rec_delta"])
    user["verify_left"]  = max(0, user["verify_left"] - 1)
    user["verify_done"] += 1
    user["first_time"]   = False
    data[uid] = user
    _ls_save(data)
    return True, step["msg"]


def daily_refresh_all():
    data = _ls_load()
    now  = time.time()
    for uid, user in data.items():
        if user.get("is_lucky"):
            user["rec_limit"] = 3
        else:
            user["rec_limit"] = 0
        user["verify_left"]  = DEFAULT_VERIFY_LEFT
        user["verify_done"]  = 0
        user["last_refresh"] = now
    _ls_save(data)


def set_rec(user_id: int, count: int):
    data = _ls_load()
    uid  = str(user_id)
    if uid not in data:
        data[uid] = _new_user_record()
    data[uid]["rec_limit"] = count
    data[uid]["first_time"] = False
    _ls_save(data)


def add_rec(user_id: int, count: int):
    data = _ls_load()
    uid  = str(user_id)
    if uid not in data:
        data[uid] = _new_user_record()
    data[uid]["rec_limit"] = max(0, data[uid]["rec_limit"] + count)
    data[uid]["first_time"] = False
    _ls_save(data)


def format_limit_message(user_id: int) -> str:
    user     = get_user(user_id)
    rec      = user["rec_limit"]
    v_left   = user["verify_left"]
    v_done   = user["verify_done"]
    is_lucky = user.get("is_lucky", False)
    is_first = user.get("first_time", False)
    is_locked = v_left <= 0

    last_refresh = user.get("last_refresh", time.time())
    elapsed      = time.time() - last_refresh
    remaining_s  = max(REFRESH_SECONDS - elapsed, 0)
    rh = int(remaining_s // 3600)
    rm = int((remaining_s % 3600) // 60)
    refresh_str  = f"{rh}h {rm}m" if remaining_s > 0 else "Abhi refresh hoga!"

    if is_locked:
        verify_line = "⚠️ VERIFY NO USE (यह लिमिट अभी लॉक है)"
    elif is_first:
        verify_line = "👉 Pehli baar verify karne par aapka quota unlock ho jayega!"
    else:
        verify_line = "👉 Verify karein aur aur Rec paaein!"

    lucky_line = ""
    if is_lucky:
        lucky_line = "⭐ **Lucky User:** Refresh ke baad Rec 3 milega!\n"

    step_labels = [
        ("1️⃣", "First Use  ➔ Verify 2", "(Aapko milenge +Rec 5)"),
        ("2️⃣", "Second Use ➔ Verify 1", "(Aapki limit ghatkar hogi: Rec 4)"),
        ("3️⃣", "Dobara Use ➔ Verify 1", "(Aapki limit aur ghatkar hogi: Rec 3)"),
        ("4️⃣", "Third Use  ➔ Verify 0", "(Lock 🚫 Today Limit Expired)"),
    ]

    flow_lines = []
    for i, (num, action, reward) in enumerate(step_labels):
        if i < v_done:
            prefix = "✅"
        elif i == v_done and not is_locked:
            prefix = "▶️"
        else:
            prefix = num
        flow_lines.append(f"{prefix} {action} {reward}")

    flow_text = "\n".join(flow_lines)

    return (
        "📊 **BOT VERIFICATION STATUS** 📊\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Your Current Limit:** Rec {rec}\n"
        "Aap iska use kar sakte hain:\n"
        "👉 `/REC LINK 00:00:30 Filename`\n"
        f"🆓 **Remaining Verify Limit:** {v_left} Verification\n"
        f"{verify_line}\n"
        f"{lucky_line}"
        "🔢 **Countdown Flow & Rewards:**\n"
        f"{flow_text}\n\n"
        "🌅 **SURPRISE GIFT (Lucky User):**\n"
        "Every 5.8 users mein se 1 lucky user ko extra badal-badal kar rewards milenge!\n\n"
        f"⏱️ **Daily Refresh Timer:** {refresh_str}\n"
        "🔄 Har 12 ghante me system fresh ho jayega. "
        "Normal users ka Rec 0 hoga, par Lucky User ka balance Rec 3 rahega!"
    )


# ═════════════════════════════════════════════════════════════════════════════
#  SHORTENER  (was shortener.py)
# ═════════════════════════════════════════════════════════════════════════════

_SHORTX_API   = "65aa5be4d757fb7242fff9dde00f6cd5d4acc977"
_SHRINKME_API = "9503d9bf87c90aa9e0aab35d4dec7d1ce24c0a23"


def shrink(long_url: str) -> Optional[str]:
    try:
        resp   = _req_lib.get(
            f"https://shortxlinks.in/api?api={_SHORTX_API}&url={long_url}",
            timeout=10,
        )
        result = resp.json()
        if result.get("status") == "success":
            short = result.get("shortenedUrl", "")
            if short:
                return short
    except Exception:
        pass
    return None


def shrink2(long_url: str) -> Optional[str]:
    try:
        resp   = _req_lib.get(
            f"https://shrinkme.io/api?api={_SHRINKME_API}&url={long_url}",
            timeout=10,
        )
        result = resp.json()
        if result.get("status") == "success":
            short = result.get("shortenedUrl", "")
            if short:
                return short
    except Exception:
        pass
    return None


# ═════════════════════════════════════════════════════════════════════════════
#  PLAYLIST MANAGER  (was playlist_manager.py)
# ═════════════════════════════════════════════════════════════════════════════

PLAYLIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_playlists.json")

_playlist_cache: Dict[int, Dict[int, List[dict]]] = {}


def _pm_load() -> dict:
    if os.path.exists(PLAYLIST_FILE):
        try:
            with open(PLAYLIST_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _pm_save(data: dict):
    with open(PLAYLIST_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_playlists(user_id: int) -> List[dict]:
    data = _pm_load()
    return data.get(str(user_id), [])


def add_playlist(user_id: int, name: str, url: str) -> Tuple[bool, str]:
    data = _pm_load()
    key  = str(user_id)
    playlists = data.get(key, [])
    if len(playlists) >= 10:
        return False, "Maximum 10 playlists allowed per user."
    for p in playlists:
        if p["name"].lower() == name.lower():
            return False, f"Playlist **{name}** already exists. Use a different name."
    playlists.append({"name": name, "url": url})
    data[key] = playlists
    _pm_save(data)
    return True, f"✅ Playlist **{name}** saved!"


def delete_playlist(user_id: int, name: str) -> Tuple[bool, str]:
    data     = _pm_load()
    key      = str(user_id)
    playlists = data.get(key, [])
    new_list  = [p for p in playlists if p["name"].lower() != name.lower()]
    if len(new_list) == len(playlists):
        return False, f"No playlist named **{name}** found."
    data[key] = new_list
    _pm_save(data)
    _playlist_cache.pop(user_id, None)
    return True, f"🗑 Playlist **{name}** deleted."


async def fetch_and_parse(url: str) -> Tuple[bool, str, List[dict]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15),
                                   allow_redirects=True) as resp:
                if resp.status != 200:
                    return False, f"HTTP {resp.status} from playlist URL.", []
                text = await resp.text(errors="replace")
    except asyncio.TimeoutError:
        return False, "Timeout fetching playlist URL.", []
    except Exception as e:
        return False, f"Network error: {e}", []

    channels = _parse_m3u(text)
    if not channels:
        return False, "No channels found. Make sure the URL returns a valid M3U8 playlist.", []
    return True, "", channels


def _parse_m3u(text: str) -> List[dict]:
    channels = []
    lines    = text.splitlines()
    i        = 0
    current_info = None
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            logo  = ""
            group = "General"
            name  = ""
            logo_match  = re.search(r'tvg-logo="([^"]*)"', line)
            group_match = re.search(r'group-title="([^"]*)"', line)
            name_match  = re.search(r',(.+)$', line)
            if logo_match:
                logo  = logo_match.group(1).strip()
            if group_match:
                group = group_match.group(1).strip() or "General"
            if name_match:
                name  = name_match.group(1).strip()
            current_info = {"name": name, "group": group, "logo": logo}
        elif line and not line.startswith("#") and current_info:
            current_info["url"] = line
            channels.append(current_info)
            current_info = None
        i += 1
    return channels


def get_groups(channels: List[dict]) -> List[str]:
    seen = {}
    for ch in channels:
        g = ch.get("group", "General")
        seen[g] = True
    return list(seen.keys())


def channels_in_group(channels: List[dict], group: str) -> List[dict]:
    return [c for c in channels if c.get("group", "General") == group]


def cache_set(user_id: int, pl_idx: int, channels: List[dict]):
    if user_id not in _playlist_cache:
        _playlist_cache[user_id] = {}
    _playlist_cache[user_id][pl_idx] = channels


def cache_get(user_id: int, pl_idx: int) -> Optional[List[dict]]:
    return _playlist_cache.get(user_id, {}).get(pl_idx)


# ═════════════════════════════════════════════════════════════════════════════
#  STATE  (was state.py)
# ═════════════════════════════════════════════════════════════════════════════

tz = pytz.timezone(config.TIMEZONE)


def _tz_time(*args):
    return datetime.now(tz).timetuple()


logging.Formatter.converter = _tz_time
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d-%m-%Y %I:%M:%S %p " + tz.tzname(datetime.now()),
)
LOG = logging.getLogger("ott_bot")

app = Client(
    "recorder",
    bot_token=config.BOT_TOKEN,
    api_id=config.API_ID,
    api_hash=config.API_HASH,
)

_orig_reply_text = Message.reply_text


async def _reply_no_quote(self, text, quote: bool = False, **kw):
    return await _orig_reply_text(self, text, quote=quote, **kw)


Message.reply_text = _reply_no_quote  # type: ignore[method-assign]


def _is_allowed(_, __, message) -> bool:
    uid = message.from_user.id if message.from_user else None
    if uid is None:
        return False
    if uid in config.OWNER_ID or uid in config.AUTH_USERS:
        return True
    if is_verified(uid, config.OWNER_ID, config.AUTH_USERS):
        return True
    try:
        user_data = get_user(uid)
        if user_data.get("rec_limit", 0) > 0:
            return True
    except Exception:
        pass
    return False


allowed = filters.create(_is_allowed)

user_tasks:       Dict[int, Dict[str, float]] = {}
user_status:      Dict[int, Dict[str, dict]]  = {}
user_ffmpeg_pids: Dict[int, Dict[str, int]]   = {}
progress_tasks:   Dict[int, Dict[str, object]] = {}
cancelled_jobs:   set = set()
scheduled_jobs:   Dict[int, Dict[str, dict]]  = {}
_sch_counter:     Dict[int, int]              = {}
history_log:      List[dict]                  = []
user_setup:       Dict[int, dict]             = {}
compress_pending: Dict[int, int]              = {}
recording_cache:  Dict[int, dict]             = {}


# ═════════════════════════════════════════════════════════════════════════════
#  KEYBOARDS  (was keyboards.py)
# ═════════════════════════════════════════════════════════════════════════════

def build_main_keyboard(uid=None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t(uid, "btn_record")),     KeyboardButton(t(uid, "btn_download"))],
            [KeyboardButton(t(uid, "btn_ott")),        KeyboardButton(t(uid, "btn_status"))],
            [KeyboardButton(t(uid, "btn_compress")),   KeyboardButton(t(uid, "btn_screenshot"))],
            [KeyboardButton(t(uid, "btn_cookies")),    KeyboardButton(t(uid, "btn_help"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_audio_keyboard(tracks: List[dict], selected: set, uid=None) -> ReplyKeyboardMarkup:
    rows = []
    for i in range(0, len(tracks), 2):
        row = []
        for track in tracks[i: i + 2]:
            check = "✅" if track["index"] in selected else "❌"
            row.append(KeyboardButton(f"{check} {track['label']}"))
        rows.append(row)
    rows.append([KeyboardButton(t(uid, "btn_select_all"))])
    rows.append([KeyboardButton(t(uid, "btn_back")), KeyboardButton(t(uid, "btn_next_wm"))])
    rows.append([KeyboardButton(t(uid, "btn_cancel_setup"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def _wm_label(key: str, uid=None) -> str:
    str_key_map = {
        "top_left":     "wm_top_left",
        "top_right":    "wm_top_right",
        "center":       "wm_center",
        "bottom_left":  "wm_bottom_left",
        "bottom_right": "wm_bottom_right",
    }
    return t(uid, str_key_map[key])


def build_watermark_keyboard(setup: dict, uid=None) -> ReplyKeyboardMarkup:
    pos  = setup.get("watermark_pos")
    auto = setup.get("auto_mode", False)
    mode = setup.get("mode", "record")

    def lbl(key):
        base = _wm_label(key, uid)
        return ("✅ " if pos == key else "") + base

    wm_off_text = ("✅ " if pos is None else "") + t(uid, "btn_wm_off")
    auto_text   = ("✅ " if auto else "") + t(uid, "btn_auto_mode")

    rows = [
        [KeyboardButton(lbl("top_left")),    KeyboardButton(lbl("top_right"))],
        [KeyboardButton(lbl("center"))],
        [KeyboardButton(lbl("bottom_left")), KeyboardButton(lbl("bottom_right"))],
        [KeyboardButton(wm_off_text)],
        [KeyboardButton(t(uid, "btn_wm_text"))],
    ]
    if mode == "record":
        rows.append([KeyboardButton(auto_text)])
    if mode == "download":
        rows.append([KeyboardButton(t(uid, "btn_start_dl"))])
    else:
        rows.append([KeyboardButton(t(uid, "btn_next_size"))])
    rows.append([KeyboardButton(t(uid, "btn_cancel"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_size_keyboard(selected: str = "original", uid=None) -> ReplyKeyboardMarkup:
    rows = []
    for key, val in VIDEO_SIZES.items():
        check = "✅ " if selected == key else ""
        rows.append([KeyboardButton(f"{check}{val['label']}")])
    rows.append([KeyboardButton(t(uid, "btn_back_wm"))])
    rows.append([KeyboardButton(t(uid, "btn_start_rec")), KeyboardButton(t(uid, "btn_cancel"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_cancel_keyboard(user_id: int, uid=None) -> ReplyKeyboardMarkup:
    uid  = uid or user_id
    jobs = user_status.get(user_id, {})
    rows = []
    for job_id, info in sorted(jobs.items()):
        n     = slot_number(job_id)
        emoji = SLOT_EMOJI[n - 1]
        rows.append([KeyboardButton(f"{emoji} Cancel Slot {n}: {info['filename']}")])
    rows.append([KeyboardButton(t(uid, "btn_cancel_all"))])
    rows.append([KeyboardButton(t(uid, "btn_close_menu"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_compress_keyboard(uid=None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t(uid, "btn_cmp_high"))],
            [KeyboardButton(t(uid, "btn_cmp_med"))],
            [KeyboardButton(t(uid, "btn_cmp_low"))],
            [KeyboardButton(t(uid, "btn_cmp_cancel"))],
        ],
        resize_keyboard=True,
    )


def build_ott_resolution_keyboard_dynamic(res_map: dict, selected: str = "", uid=None) -> ReplyKeyboardMarkup:
    labels = list(res_map.keys())
    rows   = []
    for i in range(0, len(labels), 3):
        row = []
        for lbl in labels[i: i + 3]:
            check = "✅ " if selected == lbl else ""
            row.append(KeyboardButton(f"{check}{lbl}"))
        rows.append(row)
    rows.append([KeyboardButton(t(uid, "btn_ott_cancel"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_ott_audio_keyboard_dynamic(audio_map: dict, selected: str = "", uid=None) -> ReplyKeyboardMarkup:
    rows = []
    for lbl in audio_map:
        check = "✅ " if selected == lbl else ""
        rows.append([KeyboardButton(f"{check}{lbl}")])
    rows.append([KeyboardButton(t(uid, "btn_back_res"))])
    rows.append([KeyboardButton(t(uid, "btn_ott_cancel"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def setup_summary_text(setup: dict) -> str:
    tracks   = setup.get("tracks", [])
    selected = setup.get("selected_tracks", set())
    sel_labels = [tr["label"] for tr in tracks if tr["index"] in selected] or ["All"]
    pos      = setup.get("watermark_pos")
    wm_text  = setup.get("watermark_text", config.DEFAULT_FILENAME)
    auto     = setup.get("auto_mode", False)
    mode     = setup.get("mode", "record")

    _WM_EN = {
        "top_left": "↖ Top-Left", "top_right": "↗ Top-Right",
        "center": "⊙ Center", "bottom_left": "↙ Bottom-Left",
        "bottom_right": "↘ Bottom-Right",
    }
    wm_desc  = "OFF" if pos is None else f"{_WM_EN.get(pos, pos)} → `{wm_text}`"
    size_key = setup.get("video_size", "original")
    size_lbl = VIDEO_SIZES.get(size_key, VIDEO_SIZES["original"])["label"]

    if mode == "download":
        header        = "📥 **Download Setup**"
        duration_line = ""
    else:
        header        = "🎛️ **Recording Setup**"
        duration_line = f"⏱ **Duration:** `{setup.get('timestamp', '—')}`\n"
        duration_line += f"⏩ **Auto Mode:** `{'✅ First+Last 1min' if auto else '❌ Off'}`\n"

    return (
        f"{header}\n\n"
        f"🔗 **URL:** `{setup['url'][:60]}...`\n"
        f"{duration_line}"
        f"📁 **Filename:** `{setup['filename']}`\n"
        f"🎵 **Audio:** `{', '.join(sel_labels)}`\n"
        f"🖼 **Watermark:** `{wm_desc}`\n"
        f"📐 **Size:** `{size_lbl}`\n\n"
        f"👇 Choose an option:"
    )


# ═════════════════════════════════════════════════════════════════════════════
#  UTILS  (was utils.py)
# ═════════════════════════════════════════════════════════════════════════════

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def make_job_key(user_id: int, job_id: str) -> str:
    return f"{user_id}:{job_id}"


def next_job_id(user_id: int) -> Optional[str]:
    used = set(user_tasks.get(user_id, {}).keys())
    for slot in ["slot1", "slot2", "slot3"]:
        if slot not in used:
            return slot
    return None


def slot_number(job_id: str) -> int:
    return int(job_id.replace("slot", ""))


async def runcmd(cmd: str, timeout: int = 120) -> Tuple[int, str, str]:
    args    = shlex.split(cmd)
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            process.kill()
        except Exception:
            pass
        return -1, "", f"Command timed out after {timeout}s"
    return (
        process.returncode,
        stdout.decode(errors="replace"),
        stderr.decode(errors="replace"),
    )


def time_to_seconds(time_str: str) -> int:
    try:
        h, m, s = time_str.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return 0


def TimeFormatter(milliseconds: int) -> str:
    seconds, _ = divmod(milliseconds, 1000)
    minutes, sec = divmod(seconds, 60)
    hours, min_ = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02}:{min_:02}:{sec:02}"
    return f"{min_:02}:{sec:02}"


async def get_duration_ffmpeg(input_file: str) -> int:
    try:
        cmd = (
            f'ffprobe -v error -show_entries format=duration '
            f'-of default=noprint_wrappers=1:nokey=1 "{input_file}"'
        )
        retcode, out, _ = await runcmd(cmd)
        if retcode == 0:
            return int(float(out.strip()))
    except Exception as e:
        LOG.warning(f"FFprobe duration failed: {e}")
    return 0


def _add_history(entry: dict):
    entry.setdefault("ts", time.time())
    history_log.append(entry)
    if len(history_log) > MAX_HISTORY:
        del history_log[0]


def build_metadata_args(tracks: list, selected_tracks: set, channel_name: str,
                        fallback_streams: int = 3) -> str:
    if not channel_name:
        return ""
    parts: list[str] = []
    if tracks:
        pool = (
            [tr for tr in tracks if tr["index"] in selected_tracks]
            if selected_tracks else tracks
        )
        for out_idx, track in enumerate(pool):
            lang  = track.get("language", "")
            iso   = lang[:3] if lang else ""
            label = LANG_FULL.get(lang, track.get("display", f"Audio {out_idx + 1}"))
            title = f"{channel_name} {label}".strip()
            safe  = title.replace('"', '\\"')
            parts += [
                f'-metadata:s:a:{out_idx} title="{safe}"',
                f'-metadata:s:a:{out_idx} handler_name="{safe}"',
            ]
            if iso:
                parts.append(f'-metadata:s:a:{out_idx} language={iso}')
    else:
        safe = channel_name.replace('"', '\\"')
        for i in range(fallback_streams):
            parts += [
                f'-metadata:s:a:{i} title="{safe}"',
                f'-metadata:s:a:{i} handler_name="{safe}"',
            ]
    return " ".join(parts)


def http_opts(url: str) -> str:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}/"
    return (
        f'-user_agent "{_UA}" '
        f'-headers "Referer: {origin}\\r\\n"'
    )


def get_video_media(msg):
    if not msg:
        return None
    return msg.video or msg.document or None


async def detect_stream_info(url: str) -> dict:
    cmd = (
        f'ffprobe -v quiet -timeout 15000000 {http_opts(url)} -print_format json '
        f'-show_streams "{url}"'
    )
    retcode, out, _ = await runcmd(cmd, timeout=25)
    result = {"video": None, "tracks": []}
    if retcode != 0 or not out.strip():
        return result
    try:
        streams   = json.loads(out).get("streams", [])
        audio_idx = 0
        for s in streams:
            ctype = s.get("codec_type", "")
            if ctype == "video" and result["video"] is None:
                w   = s.get("width",  0)
                h   = s.get("height", 0)
                fps_raw = s.get("r_frame_rate", "0/1")
                try:
                    num, den = fps_raw.split("/")
                    fps = round(int(num) / int(den), 2) if int(den) else 0
                except Exception:
                    fps = 0
                br = int(s.get("bit_rate", 0) or 0) // 1000
                result["video"] = {
                    "width": w, "height": h,
                    "codec": s.get("codec_name", "").upper(),
                    "bitrate_kbps": br, "fps": fps,
                }
            elif ctype == "audio":
                lang_tag = (
                    s.get("tags", {}).get("language", "")
                    or s.get("tags", {}).get("LANGUAGE", "")
                ).lower()
                codec      = s.get("codec_name", "audio").upper()
                disp_key   = LANG_MAP.get(lang_tag, lang_tag.upper() if lang_tag else f"Track {audio_idx + 1}")
                full_name  = LANG_FULL.get(lang_tag, disp_key)
                ch = int(s.get("channels", 0) or 0)
                if ch == 1:
                    ch_str = "mono"
                elif ch == 2:
                    ch_str = "stereo"
                elif ch > 2:
                    ch_str = f"{ch}ch"
                else:
                    ch_str = ""
                sr     = int(s.get("sample_rate", 0) or 0)
                sr_str = f"{sr // 1000}kHz" if sr >= 1000 else ""
                br     = int(s.get("bit_rate", 0) or 0) // 1000
                br_str = f"{br}kbps" if br > 0 else ""
                is_def = s.get("disposition", {}).get("default", 0) == 1
                def_str = " (Default)" if is_def else ""
                detail_parts = [p for p in [ch_str, br_str, sr_str] if p]
                if br_str and sr_str:
                    detail_str = f"{ch_str + ' ' if ch_str else ''}@ {br_str}, {sr_str}" if br_str else f"{ch_str + ', ' if ch_str else ''}{sr_str}"
                elif detail_parts:
                    detail_str = " ".join(detail_parts)
                else:
                    detail_str = ""
                if detail_str:
                    label = f"{full_name}{def_str} - {codec} {detail_str}".strip()
                else:
                    label = f"{full_name}{def_str} ({codec})"
                result["tracks"].append({
                    "index":        audio_idx,
                    "stream_index": s.get("index", audio_idx),
                    "language":     lang_tag,
                    "codec":        codec,
                    "label":        label,
                    "display":      disp_key,
                })
                audio_idx += 1
    except Exception as e:
        LOG.warning(f"Stream info parse error: {e}")
    return result


def format_quality_line(video: dict | None) -> str:
    if not video or not video.get("width"):
        return "Unknown"
    parts = [f"{video['width']}×{video['height']}"]
    if video.get("codec"):
        parts.append(video["codec"])
    if video.get("bitrate_kbps"):
        parts.append(f"{video['bitrate_kbps']}kbps")
    if video.get("fps"):
        parts.append(f"{video['fps']}fps")
    return " | ".join(parts)


# ═════════════════════════════════════════════════════════════════════════════
#  MODULE-COMPAT NAMESPACES
#  Handler code below calls limit_system.X() / playlist_manager.X() / verify.X()
#  These SimpleNamespace objects keep that calling convention working.
# ═════════════════════════════════════════════════════════════════════════════

limit_system = types.SimpleNamespace(
    get_user=get_user,
    mark_seen=mark_seen,
    is_new_user=is_new_user,
    is_unlimited=is_unlimited,
    use_rec=use_rec,
    apply_verify_bonus=apply_verify_bonus,
    daily_refresh_all=daily_refresh_all,
    set_rec=set_rec,
    add_rec=add_rec,
    format_limit_message=format_limit_message,
    _load=_ls_load,
)

playlist_manager = types.SimpleNamespace(
    get_playlists=get_playlists,
    add_playlist=add_playlist,
    delete_playlist=delete_playlist,
    fetch_and_parse=fetch_and_parse,
    get_groups=get_groups,
    channels_in_group=channels_in_group,
    cache_set=cache_set,
    cache_get=cache_get,
)

verify = types.SimpleNamespace(
    is_verified=is_verified,
    create_token=create_token,
    confirm_token=confirm_token,
    add_validity=add_validity,
    time_remaining=time_remaining,
)


# ═════════════════════════════════════════════════════════════════════════════
#  COOKIES — helpers
# ═════════════════════════════════════════════════════════════════════════════

def cookies_dir() -> str:
    path = join(config.DOWNLOAD_DIRECTORY, "cookies")
    os.makedirs(path, exist_ok=True)
    return path


def cookies_path(user_id: int) -> str:
    return join(cookies_dir(), f"{user_id}_cookies.txt")


def has_cookies(user_id: int) -> bool:
    return os.path.exists(cookies_path(user_id))


# ═════════════════════════════════════════════════════════════════════════════
#  COMMANDS — /start /verify /limit /setlimit /grant_access /alive
#             /help /status /history /recording_old /Hindi_or_English
# ═════════════════════════════════════════════════════════════════════════════

_RECORDING_OLD_EXPIRY = 2 * 3600   # 2 hours in seconds


@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user_id = message.from_user.id

    if len(message.command) > 1 and message.command[1].startswith("verify_"):
        token = message.command[1].replace("verify_", "", 1)
        if verify.confirm_token(user_id, token):
            limit_system.apply_verify_bonus(user_id)
            user_name = message.from_user.first_name or message.from_user.username or str(user_id)
            await message.reply_text(
                f"🎉 **Verification Successful!**\n"
                f"✅ **{user_name}** has successfully verified.\n\n"
                f"🎁 Your account has been upgraded, and you can now access **Rec 5** features!\n\n"
                f"📊 Check your updated limits using: /limit",
                reply_markup=build_main_keyboard(user_id)
            )
        else:
            await message.reply_text(
                "❌ Invalid or expired token. Send /start to get a new one.",
                reply_markup=build_main_keyboard(user_id)
            )
        return

    if limit_system.is_new_user(user_id):
        limit_system.get_user(user_id)
        await message.reply_text(
            limit_system.NEW_USER_WELCOME,
            reply_markup=build_main_keyboard(user_id)
        )

    if user_id in config.AUTH_USERS or verify.is_verified(user_id, config.OWNER_ID, config.AUTH_USERS):
        await message.reply_text(
            "🎬 **Welcome to Video Bot!**\n\n"
            "🎥 **Record:** `/rec http://link 00:00:00 Filename`\n"
            "📥 **Download:** `/download http://link Filename`\n"
            "🌐 **OTT/YouTube:** `/ott_download https://youtube.com/... Name`\n"
            "⏰ **Schedule:** `/schedule HH:MM URL 00:00:00 Filename`\n"
            "🗜 **Compress:** Reply to video + `/compress`\n"
            "📸 **Screenshots:** Reply to video + `/screenshot [1-30]`\n\n"
            f"📢 Channel: {config.CHANNEL_NAME}\n\n"
            "👇 Use the menu buttons below or type /help\n"
            "🌐 Language: /Hindi_or_English",
            reply_markup=build_main_keyboard(user_id)
        )
    else:
        token = verify.create_token(user_id)
        verify_url = f"https://t.me/{(await client.get_me()).username}?start=verify_{token}"
        short_url  = verify_url
        await message.reply_text(
            "🔒 **Access Restricted**\n\n"
            "This bot is private. To get **4 hours** of access, verify yourself:\n\n"
            f"👉 [Click here to verify]({short_url})\n\n"
            "_Or send_ `/verify {token}` _directly._",
            disable_web_page_preview=True,
        )


@app.on_message(filters.command("verify"))
async def verify_cmd(client, message: Message):
    user_id = message.from_user.id
    args    = message.command[1:]

    if user_id in config.OWNER_ID or user_id in config.AUTH_USERS:
        return await message.reply_text(
            "✅ **Aap Owner/Admin hain — verification ki zaroorat nahi!**\n\n"
            "Seedha /start use karein.",
            reply_markup=build_main_keyboard(user_id)
        )

    if args and len(args[0]) == 32:
        token = args[0]
        if verify.confirm_token(user_id, token):
            remaining = verify.time_remaining(user_id)
            ok, bonus_msg = limit_system.apply_verify_bonus(user_id)
            bonus_line = f"\n🎁 **Rec Bonus:** {bonus_msg}" if ok else ""
            await message.reply_text(
                f"✅ **Verified!** You have access for **{remaining}**."
                f"{bonus_line}\n\nType /start to use the bot.",
                reply_markup=build_main_keyboard(user_id)
            )
        else:
            await message.reply_text(
                "❌ **Invalid or expired token.**\n\nDobara /verify karein.",
                reply_markup=build_main_keyboard(user_id)
            )
        return

    user_data   = limit_system.get_user(user_id)
    verify_left = user_data.get("verify_left", 0)

    if verify_left <= 0:
        return await message.reply_text(
            "🚫 **ACCESS LOCKED (Limit 0)** 🚫\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "❌ Aapki aaj ki saari Verify aur Rec limit khatam ho gayi hai.\n\n"
            "🔄 Kal tak wait karein — system 12 ghante mein reset hoga.",
            reply_markup=build_main_keyboard(user_id)
        )

    token      = verify.create_token(user_id)
    bot_me     = await client.get_me()
    verify_url = f"https://t.me/{bot_me.username}?start=verify_{token}"
    url1 = shrink(verify_url)  or verify_url
    url2 = shrink2(verify_url) or verify_url

    next_step  = user_data.get("verify_done", 0)
    rec_reward = "+Rec 5" if next_step == 0 else ("Rec 4" if next_step == 1 else "Rec 3")

    await message.reply_text(
        "🔐 **Verification Required**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Aage bot ka istemal karne aur **{rec_reward}** ka quota unlock karne ke liye "
        "neeche diye gaye **kisi ek button** par click karke verification poora karein.\n\n"
        f"🆓 **Remaining Verify Chances:** {verify_left}\n\n"
        "⚠️ _Note: Verification poora karte hi aapki 'Verify Limit' chalu ho jayegi._\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Link 1 (ShortX)", url=url1),
                InlineKeyboardButton("✅ Link 2 (Shrinkme)", url=url2),
            ]
        ]),
        disable_web_page_preview=True
    )


@app.on_message(filters.command("limit"))
async def limit_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id in config.OWNER_ID or user_id in config.AUTH_USERS:
        await message.reply_text(
            "♾️ **Aapki Limit: UNLIMITED**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👑 **Owner / Admin** hain aap — koi bhi limit nahi hai!\n\n"
            "✅ Rec: **∞ Unlimited**\n"
            "✅ Download: **∞ Unlimited**\n"
            "✅ Verify: **Not required**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=build_main_keyboard(user_id)
        )
        return
    text = limit_system.format_limit_message(user_id)
    limit_system.mark_seen(user_id)
    await message.reply_text(text, reply_markup=build_main_keyboard(user_id), disable_web_page_preview=True)


@app.on_message(filters.command("setlimit") & filters.user(config.OWNER_ID))
async def setlimit_cmd(client, message: Message):
    args = message.command[1:]
    if len(args) < 2:
        return await message.reply_text(
            "❌ **Galat format!**\n\n"
            "📌 **Usage:**\n"
            "```\n/setlimit USER_ID 10\n/setlimit USER_ID +5\n/setlimit USER_ID -3\n```"
        )
    try:
        target_id = int(args[0])
        val_str   = args[1].strip()
    except (ValueError, IndexError):
        return await message.reply_text("❌ Invalid USER_ID.")
    try:
        if val_str.startswith("+"):
            limit_system.add_rec(target_id, int(val_str[1:]))
            action_text = f"➕ Added +{val_str[1:]} Rec"
        elif val_str.startswith("-"):
            limit_system.add_rec(target_id, -int(val_str[1:]))
            action_text = f"➖ Removed {val_str} Rec"
        else:
            limit_system.set_rec(target_id, int(val_str))
            action_text = f"🔧 Set to Rec {val_str}"
    except ValueError:
        return await message.reply_text("❌ Invalid value. Jaise: 10, +5, -3")
    new_rec = limit_system.get_user(target_id)["rec_limit"]
    await message.reply_text(
        f"✅ **Limit Updated!**\n\n"
        f"👤 **User ID:** `{target_id}`\n"
        f"🔧 **Action:** {action_text}\n"
        f"📊 **New Rec Limit:** Rec {new_rec}"
    )


@app.on_message(filters.command("grant_access") & filters.user(config.OWNER_ID))
async def grant_access_cmd(client, message: Message):
    args = message.command[1:]
    if len(args) < 1:
        return await message.reply_text("Usage: `/grant_access USER_ID [HOURS]`\nDefault hours: 24")
    try:
        target_id = int(args[0])
        hours     = float(args[1]) if len(args) > 1 else 24
    except ValueError:
        return await message.reply_text("❌ Invalid user ID or hours.")

    verify.add_validity(target_id, int(hours * 3600))
    remaining = verify.time_remaining(target_id)
    await message.reply_text(
        f"✅ **Access granted!**\n\n"
        f"👤 User: `{target_id}`\n"
        f"⏳ Valid for: **{remaining}**"
    )


@app.on_message(filters.command("alive"))
async def alive_cmd(client, message: Message):
    await message.reply_text(
        "✅ **Bot working, you can use it!**",
        reply_markup=build_main_keyboard(message.from_user.id)
    )


@app.on_message(filters.command("help") & allowed)
async def help_cmd(client, message: Message):
    user_id = message.from_user.id
    await message.reply_text(
        "🛠 **Bot Help Menu**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎥 **RECORDING**\n"
        "```\n/rec http://link 00:00:00 Filename\n```\n"
        "📥 **STREAM DOWNLOAD**\n"
        "```\n/download http://link Filename\n```\n"
        "🌐 **OTT / YouTube DOWNLOAD**\n"
        "```\n/ott_download https://youtube.com/... Filename\n```\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ **All Commands:**\n"
        "• 🎥 `/rec` — Record stream with duration\n"
        "• 📥 `/download` — Download full stream\n"
        "• 🌐 `/ott_download` — OTT/YouTube download\n"
        "• ⏰ `/schedule` — Pre-schedule a recording\n"
        "• 📋 `/schedules` — List pending schedules\n"
        "• 🗑 `/cancel_schedule` — Remove a schedule\n"
        "• 🗜 `/compress` — Compress video _(reply to video)_\n"
        "• 📸 `/screenshot [1-30]` — Screenshots _(reply to video)_\n"
        "• 🛑 `/cancel` — Stop active task\n"
        "• 📊 `/status` — All active tasks\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⏰ **Scheduling:**\n"
        "```\n"
        "/schedule 21:00 http://link 01:30:00 ShowName\n"
        "/schedule 09:30 dl http://vod.m3u8 Morning\n"
        "/schedule 18:00 ott https://yt/... Film\n"
        "```\n\n"
        "🍪 **Cookies:**\n"
        "• `/cookies_add` — Upload cookies.txt\n"
        "• `/cookies_status` — Check cookie info\n"
        "• `/del_cookies` — Delete cookies\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🆕 **Features:**\n"
        "• 🎵 Multi audio track selection\n"
        "• 🖼 Watermark (5 positions)\n"
        "• 📐 Video size presets\n"
        "• ⏩ Auto mode: First+Last 1min _(rec only)_\n"
        "• 🔢 Up to **3 simultaneous** tasks\n\n"
        f"🔸 Default filename: `{config.DEFAULT_FILENAME}`",
        reply_markup=build_main_keyboard(user_id),
        disable_web_page_preview=True
    )


@app.on_message(filters.command("status") & allowed)
async def status_cmd(client, message: Message):
    uid  = message.from_user.id
    jobs = user_status.get(uid, {})
    if not jobs:
        return await message.reply(
            "📭 No active recording tasks found.",
            reply_markup=build_main_keyboard(uid)
        )
    lines = [f"📊 **Active Recordings ({len(jobs)}/{MAX_CONCURRENT})**\n"]
    for job_id, status in sorted(jobs.items()):
        n        = slot_number(job_id)
        emoji    = SLOT_EMOJI[n - 1]
        start_dt = datetime.fromtimestamp(status["id"], tz=tz).strftime("%I:%M:%S %p")
        target_s = time_to_seconds(status["target"]) if status["target"] != "∞" else 0
        prog_s   = time_to_seconds(status["progress"])
        remaining = max(target_s - prog_s, 0)
        eta      = TimeFormatter(remaining * 1000) if target_s else "—"
        lines.append(
            f"{emoji} **Slot {n}**\n"
            f"  📁 `{status['filename']}`\n"
            f"  ⏱ `{status['progress']}` / `{status['target']}`\n"
            f"  ⏳ ETA: `{eta}`  🕒 Started: `{start_dt}`\n"
        )
    lines.append("🛑 Use /cancel to stop a recording")
    await message.reply_text("\n".join(lines), reply_markup=build_main_keyboard(uid))


@app.on_message(filters.command("history") & allowed)
async def history_cmd(client, message: Message):
    user_id  = message.from_user.id
    is_owner = user_id in config.OWNER_ID
    args     = message.command[1:]

    show_all   = "all"   in args
    show_stats = "stats" in args
    filter_u   = next((a for a in args if a.startswith("@")), None)

    if is_owner and (show_all or filter_u):
        entries = list(history_log)
    else:
        entries = [e for e in history_log if e["user_id"] == user_id]

    if filter_u:
        fname   = filter_u.lstrip("@").lower()
        entries = [e for e in entries if fname in (e.get("username") or "").lower()]

    if not entries:
        return await message.reply_text(
            "📭 **No history yet.**\n\nActivities appear here after recordings/downloads complete.",
            reply_markup=build_main_keyboard(user_id)
        )

    if show_stats:
        total  = len(history_log) if is_owner else len(entries)
        done   = sum(1 for e in entries if e["status"] == "done")
        canc   = sum(1 for e in entries if e["status"] == "cancelled")
        failed = sum(1 for e in entries if e["status"] == "failed")
        recs   = sum(1 for e in entries if e["type"] == "rec")
        dls    = sum(1 for e in entries if e["type"] == "download")
        otts   = sum(1 for e in entries if e["type"] == "ott")
        tot_dur = sum(e.get("duration_s", 0) for e in entries)
        tot_mb  = sum(e.get("size_mb", 0) for e in entries)

        user_block = ""
        if is_owner:
            uc   = Counter(f"{e.get('username','?')} ({e['user_id']})" for e in history_log)
            top5 = uc.most_common(5)
            user_block = (
                "\n━━━━━━━━━━━━━━━━━━━━\n"
                "👤 **Top Users:**\n" +
                "\n".join(f"  {i+1}. `{u}` — {c} tasks" for i, (u, c) in enumerate(top5))
            )

        await message.reply_text(
            f"📊 **History Stats**{'  (Global)' if is_owner else ''}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Total activities:** `{total}`\n"
            f"✅ **Completed:**        `{done}`\n"
            f"⚠️ **Cancelled:**        `{canc}`\n"
            f"❌ **Failed:**           `{failed}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎥 **Recordings:**  `{recs}`\n"
            f"📥 **Downloads:**   `{dls}`\n"
            f"🌐 **OTT/YouTube:** `{otts}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ **Total duration:** `{TimeFormatter(tot_dur * 1000)}`\n"
            f"💾 **Total size:**    `{tot_mb:.1f} MB`"
            f"{user_block}",
            reply_markup=build_main_keyboard(user_id)
        )
        return

    limit  = len(entries) if show_all else min(15, len(entries))
    recent = entries[-limit:][::-1]

    TYPE_EMOJI   = {"rec": "🎥", "download": "📥", "ott": "🌐"}
    STATUS_EMOJI = {"done": "✅", "cancelled": "⚠️", "failed": "❌"}

    lines = [f"📋 **Activity History** ({'Global · ' if is_owner and show_all else ''}last {len(recent)})\n"]
    for e in recent:
        dt      = datetime.fromtimestamp(e["ts"], tz).strftime("%d %b %I:%M %p")
        t_emoji = TYPE_EMOJI.get(e["type"], "📁")
        s_emoji = STATUS_EMOJI.get(e["status"], "❓")
        dur_str = TimeFormatter(e.get("duration_s", 0) * 1000) if e.get("duration_s") else "—"
        mb_str  = f"{e['size_mb']} MB" if e.get("size_mb") else "—"
        user_tag = f" · `@{e['username']}`" if is_owner else ""
        extra = ""
        if e["type"] == "ott" and e.get("res_label"):
            extra = f" · `{e['res_label']}` `{e.get('audio_label','')}`"
        lines.append(
            f"{t_emoji}{s_emoji} **{e['filename']}**{user_tag}\n"
            f"   ⏱ `{dur_str}` · 💾 `{mb_str}` · 🕒 `{dt}`{extra}\n"
        )

    if len(entries) > limit:
        lines.append(f"\n_…{len(entries) - limit} more. Use /history all to see everything._")

    lines.append("\n📊 /history stats — aggregated totals")
    await message.reply_text("\n".join(lines), reply_markup=build_main_keyboard(user_id))


@app.on_message(filters.command("recording_old") & allowed)
async def recording_old_cmd(client, message: Message):
    user_id = message.from_user.id
    cached  = recording_cache.get(user_id)

    if not cached:
        return await message.reply_text(
            "📭 **Koi purani recording nahi mili!**\n\n"
            "Pehle `/rec`, `/download` ya `/ott_download` se koi recording complete karein.",
            reply_markup=build_main_keyboard(user_id)
        )

    age_s = time.time() - cached["ts"]
    if age_s > _RECORDING_OLD_EXPIRY:
        recording_cache.pop(user_id, None)
        return await message.reply_text(
            "⏳ **Recording Expire Ho Gayi!**\n\n"
            "Aapki last recording 2 ghante pehle upload hui thi — ab uska link available nahi.\n\n"
            "Dobara record karne ke liye `/rec` ya `/download` use karein.",
            reply_markup=build_main_keyboard(user_id)
        )

    remaining_s  = int(_RECORDING_OLD_EXPIRY - age_s)
    rem_min, rem_sec = divmod(remaining_s, 60)
    rem_h,   rem_min = divmod(rem_min, 60)
    if rem_h:
        rem_str = f"{rem_h}h {rem_min}m"
    elif rem_min:
        rem_str = f"{rem_min}m {rem_sec}s"
    else:
        rem_str = f"{rem_sec}s"

    TYPE_EMOJI = {"rec": "🎥", "download": "📥", "ott": "🌐"}
    t_emoji    = TYPE_EMOJI.get(cached.get("type", "rec"), "📁")

    wait_msg = await message.reply_text(
        f"{t_emoji} **Aapki Recording Bhej Raha Hoon...**\n\n"
        f"📁 `{cached['filename']}`\n"
        f"⏳ Link valid hai: `{rem_str}` aur",
    )

    try:
        await client.forward_messages(
            chat_id=message.chat.id,
            from_chat_id=cached["chat_id"],
            message_ids=cached["msg_id"],
        )
        await wait_msg.delete()
    except Exception as e:
        LOG.warning(f"recording_old forward failed: {e}")
        try:
            await wait_msg.edit_text(
                "❌ **Forward Fail!**\n\n"
                "Original message mil nahi raha — shayad delete ho gaya.\n\n"
                f"`{str(e)[:500]}`",
                reply_markup=build_main_keyboard(user_id)
            )
        except Exception:
            pass
        recording_cache.pop(user_id, None)


@app.on_message(filters.command("Hindi_or_English") & allowed)
async def hindi_or_english_cmd(client, message: Message):
    user_id  = message.from_user.id
    cur_lang = get_lang(user_id)
    new_lang = "hi" if cur_lang == "en" else "en"
    set_lang(user_id, new_lang)
    if new_lang == "hi":
        await message.reply_text(
            "✅ **भाषा बदली: हिंदी**\n\nअब सभी बटन और मेसेज हिंदी में दिखेंगे।",
            reply_markup=build_main_keyboard(user_id)
        )
    else:
        await message.reply_text(
            "✅ **Language changed: English**\n\nAll buttons and messages will now appear in English.",
            reply_markup=build_main_keyboard(user_id)
        )


# ═════════════════════════════════════════════════════════════════════════════
#  OTT — progress callback, yt-dlp helpers, /ott_download, ott_download_task
# ═════════════════════════════════════════════════════════════════════════════

async def progress_for_pyrogram(current, total, ref_message, start, msg, save_dir,
                                 was_cancelled=False, job_id=None):
    now         = time.time()
    diff        = max(now - start, 1)
    percentage  = current * 100 / total
    speed       = current / diff
    uploaded_mb = current / (1024 * 1024)
    total_mb    = total   / (1024 * 1024)
    speed_mb    = speed   / (1024 * 1024)

    filled     = int(10 * percentage // 100)
    bar_filled = "▰" * filled
    bar_empty  = "▱" * (10 - filled)
    bar        = f"[{bar_filled}{bar_empty}]"

    if int(percentage) in {0, 10, 25, 50, 75, 90, 95, 99, 100} or current == total:
        eta    = TimeFormatter(int((total - current) / speed * 1000)) if speed > 0 else "00:00:00"
        n      = slot_number(job_id) if job_id else 1
        slot_e = SLOT_EMOJI[n - 1] if n <= 3 else "📤"
        label  = "Partial " if was_cancelled else ""
        try:
            await msg.edit_text(
                f"{slot_e} **Uploading {label}Recording**\n"
                f"`{bar}` `{percentage:.1f}%`\n"
                f"📊 `{uploaded_mb:.1f} / {total_mb:.1f} MB`\n"
                f"⚡ `{speed_mb:.1f} MB/s`  ⏳ `{eta}`"
            )
        except Exception:
            pass
        if current == total:
            done = "✅ Partial Sent!" if was_cancelled else "✅ Upload Completed!"
            try:
                await msg.edit_text(f"{done}\n🗑️ Cleaning up...")
                await asyncio.sleep(2)
                await msg.edit_text(done)
            except Exception:
                pass


async def ytdlp_download(
    url: str, output_path: str,
    cookies_file: Optional[str] = None,
    fmt: Optional[str] = None,
    audio_lang: Optional[str] = None,
) -> Tuple[int, str, str]:
    cmd_parts = [
        "yt-dlp", "--no-playlist", "--merge-output-format", "mkv",
        "-o", output_path,
    ]
    if audio_lang:
        base_fmt = fmt or "bestvideo+bestaudio/best"
        if "bestaudio" in base_fmt:
            lang_fmt      = base_fmt.replace("bestaudio", f"bestaudio[language={audio_lang}]", 1)
            effective_fmt = f"{lang_fmt}/{base_fmt}"
        else:
            effective_fmt = f"bestvideo+bestaudio[language={audio_lang}]/bestvideo+bestaudio/best"
        cmd_parts += ["-f", effective_fmt]
    elif fmt:
        cmd_parts += ["-f", fmt, "--audio-multistreams"]
    else:
        cmd_parts += ["--audio-multistreams"]

    if cookies_file and os.path.exists(cookies_file):
        cmd_parts += ["--cookies", cookies_file]
    cmd_parts.append(url)
    process = await asyncio.create_subprocess_exec(
        *cmd_parts, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()


async def detect_ott_formats(url: str, cookies_file: Optional[str] = None) -> dict:
    cmd = ["yt-dlp", "--no-playlist", "-J"]
    if cookies_file and os.path.exists(cookies_file):
        cmd += ["--cookies", cookies_file]
    cmd.append(url)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            return {"title": "", "heights": [], "langs": [], "duration": 0}
        data    = json.loads(stdout.decode())
        title   = data.get("title", "")
        dur     = int(data.get("duration", 0) or 0)
        heights: set = set()
        langs:   set = set()
        for f in data.get("formats", []):
            h = f.get("height")
            if h and f.get("vcodec", "none") not in ("none", None, ""):
                heights.add(int(h))
            lang = (f.get("language") or "").lower()[:3]
            if lang and f.get("acodec", "none") not in ("none", None, ""):
                langs.add(lang)
        return {
            "title":    title,
            "heights":  sorted(heights),
            "langs":    sorted(langs),
            "duration": dur,
        }
    except Exception as e:
        LOG.warning(f"detect_ott_formats error: {e}")
        return {"title": "", "heights": [], "langs": [], "duration": 0}


@app.on_message(filters.command("ott_download") & allowed)
async def ott_download_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Invalid Format!**\n\n"
            "📌 **Usage:**\n"
            "```\n/ott_download https://youtube.com/... MyFilename\n```\n\n"
            "🍪 Add cookies first with /cookies_add for OTT sites.",
            reply_markup=build_main_keyboard(message.from_user.id)
        )
    user_id = message.from_user.id
    if len(user_tasks.get(user_id, {})) >= MAX_CONCURRENT:
        return await message.reply_text(
            f"❌ **All {MAX_CONCURRENT} slots are busy!**\n📊 /status  |  🛑 /cancel",
            reply_markup=build_main_keyboard(user_id)
        )

    params       = " ".join(message.command[1:])
    parts        = params.split(" ", 1)
    url          = parts[0]
    raw_filename = parts[1].strip() if len(parts) > 1 else config.DEFAULT_FILENAME

    detect_msg = await message.reply_text(
        "🔍 **Detecting available qualities...**\n"
        "⏳ _Please wait a few seconds..._"
    )

    cookie_file = cookies_path(user_id) if has_cookies(user_id) else None
    info        = await detect_ott_formats(url, cookie_file)

    res_map: dict = {}
    for h in info["heights"]:
        lbl = _HEIGHT_LABEL.get(h, f"📺 {h}p")
        res_map[lbl] = _HEIGHT_FMT.get(h, f"bestvideo[height<={h}]+bestaudio/best[height<={h}]")
    res_map["🏆 Best"] = "bestvideo+bestaudio/best"

    audio_map: dict = {}
    for lang in info["langs"]:
        lbl = _LANG_CODE_TO_LABEL.get(lang, lang.upper())
        if lbl not in audio_map:
            audio_map[lbl] = lang
    audio_map["🌐 Multi"] = None

    if len(res_map) <= 1:
        res_map   = dict(OTT_RES_LABEL_TO_FMT)
    if not audio_map or list(audio_map.keys()) == ["🌐 Multi"]:
        audio_map = dict(OTT_AUDIO_LANGS)

    user_setup[user_id] = {
        "step": "ott_resolution",
        "url": url,
        "filename": raw_filename,
        "chat_id": message.chat.id,
        "reply_to": message.id,
        "ott_res_label": "",
        "ott_audio_label": "",
        "detected_res_map":   res_map,
        "detected_audio_map": audio_map,
        "detected_title":    info.get("title", ""),
        "detected_duration": info.get("duration", 0),
    }

    title_line  = f"📌 **Title:** `{info['title'][:55]}`\n" if info.get("title") else ""
    dur_line    = f"⏱ **Duration:** `{TimeFormatter(info['duration'] * 1000)}`\n" if info.get("duration") else ""
    res_count   = len(res_map) - 1
    audio_count = len([v for v in audio_map.values() if v is not None])

    try:
        await detect_msg.delete()
    except Exception:
        pass

    await message.reply_text(
        f"🌐 **OTT / YouTube Download**\n\n"
        f"{title_line}{dur_line}"
        f"📁 **File:** `{raw_filename}`\n"
        f"🍪 **Cookies:** `{'✅ Found' if has_cookies(user_id) else '❌ None'}`\n\n"
        f"📺 **{res_count} resolutions detected** · 🎧 **{audio_count} audio tracks**\n\n"
        f"👇 Select resolution:",
        reply_markup=build_ott_resolution_keyboard_dynamic(res_map)
    )


async def ott_download_task(client: Client, ref_message: Message, setup: dict, user_id: int):
    job_id = next_job_id(user_id)
    if not job_id:
        await ref_message.reply_text(f"❌ All {MAX_CONCURRENT} slots full!")
        return

    job_key      = make_job_key(user_id, job_id)
    n            = slot_number(job_id)
    emoji        = SLOT_EMOJI[n - 1]
    raw_filename = setup["filename"]
    url          = setup["url"]
    fmt          = setup.get("ott_format")
    audio_lang   = setup.get("ott_audio_lang")
    res_label    = setup.get("ott_res_label", "Best")
    audio_label  = setup.get("ott_audio_label", "Multi")

    save_dir    = join(config.DOWNLOAD_DIRECTORY, f"{int(time.time())}_{job_id}")
    os.makedirs(save_dir, exist_ok=True)
    output_tmpl = join(save_dir, f"{raw_filename}.%(ext)s")

    msg = await ref_message.reply_text(
        f"{emoji} **Slot {n} — Starting OTT Download...**\n"
        f"📁 `{raw_filename}`\n"
        f"📺 `{res_label}`  🎧 `{audio_label}`\n"
        f"🍪 Cookies: `{'✅ Found' if has_cookies(user_id) else '❌ None'}`",
        reply_markup=build_main_keyboard(user_id)
    )

    user_tasks.setdefault(user_id, {})[job_id] = time.time()
    user_status.setdefault(user_id, {})[job_id] = {
        "id": int(time.time()), "filename": raw_filename,
        "target": "∞", "progress": "00:00:00",
        "save_dir": save_dir, "mode": "ott",
    }
    dl_start = time.time()

    _ott_pulse = [0]

    async def ott_progress():
        while (
            user_id in user_tasks and
            job_id in user_tasks.get(user_id, {}) and
            job_key not in cancelled_jobs
        ):
            elapsed = time.time() - dl_start
            prog    = TimeFormatter(int(elapsed * 1000))
            if job_id in user_status.get(user_id, {}):
                user_status[user_id][job_id]["progress"] = prog
            _ott_pulse[0] = (_ott_pulse[0] + 1) % 10
            p   = _ott_pulse[0]
            bar = PROGRESS_EMPTY * p + PROGRESS_FILLED + PROGRESS_EMPTY * (9 - p)
            try:
                await msg.edit_text(
                    f"{emoji} <b>Slot {n} — Downloading (OTT/YT)</b>\n"
                    f"📁 <code>{raw_filename}</code>\n"
                    f"📺 <code>{res_label}</code>  🎧 <code>{audio_label}</code>\n"
                    f"{bar}\n"
                    f"⏱️ Elapsed: <code>{prog}</code>\n\n🛑 /cancel to stop",
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass
            await asyncio.sleep(5)

    prog_task = asyncio.create_task(ott_progress())
    progress_tasks.setdefault(user_id, {})[job_id] = prog_task

    try:
        cookie_file = cookies_path(user_id) if has_cookies(user_id) else None
        retcode, out, err = await ytdlp_download(url, output_tmpl, cookie_file, fmt, audio_lang)
        if job_id in progress_tasks.get(user_id, {}):
            progress_tasks[user_id][job_id].cancel()
        was_cancelled = job_key in cancelled_jobs
        if retcode != 0 and not was_cancelled:
            raise Exception(f"yt-dlp error:\n{err[-2000:]}")

        video_path = None
        for f in os.listdir(save_dir):
            if f.startswith(raw_filename):
                video_path = join(save_dir, f)
                break
        if not video_path or not os.path.exists(video_path):
            raise Exception("Downloaded file not found.")

        thumb_msg  = await ref_message.reply_text(f"{emoji} **Slot {n} — Generating thumbnail...**")
        dur        = await get_duration_ffmpeg(video_path)
        rand_sec   = random.randint(5, max(dur - 5, 6)) if dur > 10 else 1
        thumb_path = join(save_dir, "thumb.jpg")
        await runcmd(f'ffmpeg -y -ss {rand_sec} -i "{video_path}" -vframes 1 -q:v 2 "{thumb_path}"')
        await thumb_msg.delete()

        old_line = (
            "" if was_cancelled else
            "\n_🗑 Video auto-deleted from server in 2 hours._\n_📥 Use /recording_old to get this video again._"
        )
        caption = (
            f"{emoji} **{raw_filename}**\n\n"
            f"⏱ **Duration:** `{TimeFormatter(dur * 1000)}`\n"
            f"📺 **Resolution:** `{res_label}`\n"
            f"🎧 **Audio:** `{audio_label}`\n"
            f"📥 **Source:** OTT/YouTube\n"
            f"🍪 **Cookies:** `{'✅ Used' if cookie_file else '❌ None'}`\n"
            f"📁 **Format:** MKV\n\n"
            f"{'⚠️ _Partial (cancelled)_' if was_cancelled else '✅ _Downloaded successfully!_'}"
            f"{old_line}"
        )
        size_mb = round(os.path.getsize(video_path) / (1024 * 1024), 2) if os.path.exists(video_path) else 0
        uname   = ref_message.from_user.username or ref_message.from_user.first_name or str(user_id)
        _add_history({
            "type":        "ott",
            "status":      "cancelled" if was_cancelled else "done",
            "user_id":     user_id,
            "username":    uname,
            "filename":    raw_filename,
            "duration_s":  int(dur),
            "size_mb":     size_mb,
            "url":         url[:120],
            "res_label":   res_label,
            "audio_label": audio_label,
        })

        start_time = time.time()
        sent = await ref_message.reply_video(
            video=video_path, caption=caption, duration=dur,
            thumb=thumb_path if os.path.exists(thumb_path) else None,
            progress=progress_for_pyrogram,
            progress_args=(ref_message, start_time, msg, save_dir, was_cancelled, job_id)
        )
        if not was_cancelled and sent:
            recording_cache[user_id] = {
                "msg_id":   sent.id,
                "chat_id":  sent.chat.id,
                "filename": raw_filename,
                "ts":       time.time(),
                "type":     "ott",
            }
        shutil.rmtree(save_dir, ignore_errors=True)

    except Exception as e:
        LOG.error(f"ott_download error [{job_id}]: {e}")
        uname = ref_message.from_user.username or ref_message.from_user.first_name or str(user_id)
        _add_history({
            "type":        "ott",
            "status":      "cancelled" if job_key in cancelled_jobs else "failed",
            "user_id":     user_id,
            "username":    uname,
            "filename":    setup.get("filename", "?"),
            "duration_s":  0,
            "size_mb":     0,
            "url":         setup.get("url", "")[:120],
            "res_label":   setup.get("ott_res_label", ""),
            "audio_label": setup.get("ott_audio_label", ""),
        })
        if job_key not in cancelled_jobs:
            try:
                await msg.edit(f"{emoji} **Slot {n} — Download Failed!**\n\n`{str(e)[:3000]}`")
            except Exception:
                pass
        shutil.rmtree(save_dir, ignore_errors=True)
    finally:
        user_tasks.get(user_id, {}).pop(job_id, None)
        user_status.get(user_id, {}).pop(job_id, None)
        user_ffmpeg_pids.get(user_id, {}).pop(job_id, None)
        progress_tasks.get(user_id, {}).pop(job_id, None)
        cancelled_jobs.discard(job_key)
        for d in [user_tasks, user_status, user_ffmpeg_pids, progress_tasks]:
            if user_id in d and not d[user_id]:
                del d[user_id]


# ═════════════════════════════════════════════════════════════════════════════
#  SCHEDULE — helpers, /schedule /schedules /cancel_schedule /cancel
#             do_cancel_job
# ═════════════════════════════════════════════════════════════════════════════

def _next_sch_id(user_id: int) -> str:
    _sch_counter[user_id] = _sch_counter.get(user_id, 0) + 1
    return f"S{_sch_counter[user_id]}"


def _parse_schedule_time(time_str: str):
    now = datetime.now(tz)
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t_parsed = datetime.strptime(time_str, fmt)
            target   = now.replace(hour=t_parsed.hour, minute=t_parsed.minute,
                                   second=t_parsed.second, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target
        except ValueError:
            continue
    return None


def _format_wait(seconds: float) -> str:
    seconds = int(seconds)
    h, rem  = divmod(seconds, 3600)
    m, s    = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


async def _schedule_waiter(client: Client, user_id: int, chat_id: int,
                            sch_id: str, job: dict):
    now    = datetime.now(tz)
    wait_s = max((job["target_dt"] - now).total_seconds(), 0)
    await asyncio.sleep(wait_s)

    if sch_id not in scheduled_jobs.get(user_id, {}):
        return

    scheduled_jobs.get(user_id, {}).pop(sch_id, None)

    kind     = job["kind"]
    url      = job["url"]
    filename = job["filename"]
    duration = job.get("duration", "")

    fire_time = datetime.now(tz).strftime("%I:%M:%S %p")

    await client.send_message(
        chat_id,
        f"⏰ **Schedule {sch_id} Fired!**\n\n"
        f"🕒 **Time:** `{fire_time} IST`\n"
        f"📁 **File:** `{filename}`\n"
        f"🔗 **URL:** `{url[:60]}{'…' if len(url) > 60 else ''}`\n\n"
        f"🚀 Starting `/{kind}` now…",
        reply_markup=build_main_keyboard(user_id),
    )

    cmd_text = {
        "rec":          f"/rec {url} {duration} {filename}",
        "download":     f"/download {url} {filename}",
        "ott_download": f"/ott_download {url} {filename}",
    }.get(kind, f"/rec {url} {duration} {filename}")

    await client.send_message(chat_id, cmd_text)


@app.on_message(filters.command("schedule") & allowed)
async def schedule_cmd(client: Client, message: Message):
    args    = message.command[1:]
    user_id = message.from_user.id

    def _usage():
        return message.reply_text(
            "❌ **Invalid format.**\n\n"
            "📌 **Usage:**\n"
            "```\n"
            "/schedule HH:MM URL 00:00:00 Filename\n"
            "/schedule HH:MM dl URL Filename\n"
            "/schedule HH:MM ott https://... Filename\n"
            "```\n\n"
            "Examples:\n"
            "• `/schedule 21:00 http://stream 01:30:00 NightShow`\n"
            "• `/schedule 09:30 dl http://vod.m3u8 Morning`\n"
            "• `/schedule 18:00 ott https://youtube.com/... Movie`",
            reply_markup=build_main_keyboard(user_id),
            disable_web_page_preview=True,
        )

    if len(args) < 3:
        return await _usage()

    time_str  = args[0]
    target_dt = _parse_schedule_time(time_str)
    if not target_dt:
        return await message.reply_text(
            "❌ Invalid time format. Use **HH:MM** or **HH:MM:SS** (24-hour IST).",
            reply_markup=build_main_keyboard(user_id)
        )

    kind = "rec"
    rest = args[1:]
    if rest[0].lower() in ("dl", "download"):
        kind = "download"
        rest = rest[1:]
    elif rest[0].lower() in ("ott", "ott_download"):
        kind = "ott_download"
        rest = rest[1:]

    if not rest:
        return await _usage()

    url  = rest[0]
    rest = rest[1:]

    duration = ""
    if kind == "rec":
        if not rest:
            return await _usage()
        if rest[0].count(":") >= 1:
            duration = rest[0]
            rest     = rest[1:]
        else:
            return await _usage()

    filename = " ".join(rest).strip() if rest else config.DEFAULT_FILENAME

    sch_id = _next_sch_id(user_id)
    job = {
        "kind":      kind,
        "url":       url,
        "filename":  filename,
        "duration":  duration,
        "time_str":  time_str,
        "target_dt": target_dt,
    }

    scheduled_jobs.setdefault(user_id, {})[sch_id] = job
    job["task"] = asyncio.create_task(
        _schedule_waiter(client, user_id, message.chat.id, sch_id, job)
    )

    wait_s     = (target_dt - datetime.now(tz)).total_seconds()
    fire_label = target_dt.strftime("%I:%M %p")
    day_label  = "today" if target_dt.date() == datetime.now(tz).date() else "tomorrow"
    kind_emoji = {"rec": "🎥", "download": "📥", "ott_download": "🌐"}.get(kind, "🎥")
    dur_line   = f"⏱ **Duration:** `{duration}`\n" if duration else ""

    await message.reply_text(
        f"✅ **Schedule {sch_id} Created!**\n\n"
        f"{kind_emoji} **Type:** `/{kind}`\n"
        f"🕒 **Fire at:** `{fire_label} IST` ({day_label})\n"
        f"⏳ **In:** `{_format_wait(wait_s)}`\n"
        f"{dur_line}"
        f"📁 **File:** `{filename}`\n"
        f"🔗 **URL:** `{url[:60]}{'…' if len(url) > 60 else ''}`\n\n"
        f"📋 Use /schedules to see all · /cancel_schedule {sch_id} to remove",
        reply_markup=build_main_keyboard(user_id),
        disable_web_page_preview=True,
    )


@app.on_message(filters.command("schedules") & allowed)
async def schedules_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    jobs    = scheduled_jobs.get(user_id, {})
    if not jobs:
        return await message.reply_text(
            "📭 **No pending schedules.**\n\nUse /schedule to create one.",
            reply_markup=build_main_keyboard(user_id)
        )

    now        = datetime.now(tz)
    lines      = [f"📋 **Pending Schedules ({len(jobs)})**\n"]
    kind_emoji = {"rec": "🎥", "download": "📥", "ott_download": "🌐"}

    for sid, job in sorted(jobs.items()):
        wait_s    = max((job["target_dt"] - now).total_seconds(), 0)
        fire_time = job["target_dt"].strftime("%I:%M %p")
        day_label = "today" if job["target_dt"].date() == now.date() else "tomorrow"
        k_emoji   = kind_emoji.get(job["kind"], "🎥")
        dur_part  = f" · `{job['duration']}`" if job.get("duration") else ""
        lines.append(
            f"{k_emoji} **{sid}** — fires `{fire_time}` {day_label} _(in {_format_wait(wait_s)})_\n"
            f"   📁 `{job['filename']}`{dur_part}\n"
            f"   🔗 `{job['url'][:50]}{'…' if len(job['url']) > 50 else ''}`\n"
        )

    lines.append("🗑 /cancel_schedule <ID> to remove one")
    await message.reply_text("\n".join(lines), reply_markup=build_main_keyboard(user_id))


@app.on_message(filters.command("cancel_schedule") & allowed)
async def cancel_schedule_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    args    = message.command[1:]

    if not args:
        jobs = scheduled_jobs.get(user_id, {})
        if not jobs:
            return await message.reply_text(
                "📭 No pending schedules to cancel.",
                reply_markup=build_main_keyboard(user_id)
            )
        ids = ", ".join(sorted(jobs.keys()))
        return await message.reply_text(
            f"❓ **Which schedule to cancel?**\n\n"
            f"Pending: `{ids}`\n\n"
            f"Usage: `/cancel_schedule S1`",
            reply_markup=build_main_keyboard(user_id)
        )

    sch_id  = args[0].upper()
    user_js = scheduled_jobs.get(user_id, {})

    if sch_id not in user_js:
        return await message.reply_text(
            f"❌ Schedule `{sch_id}` not found.\n"
            f"Use /schedules to see pending ones.",
            reply_markup=build_main_keyboard(user_id)
        )

    job  = user_js.pop(sch_id)
    task = job.get("task")
    if task and not task.done():
        task.cancel()

    await message.reply_text(
        f"✅ **Schedule {sch_id} cancelled.**\n\n"
        f"📁 `{job['filename']}` @ `{job['time_str']} IST`",
        reply_markup=build_main_keyboard(user_id)
    )


@app.on_message(filters.command("cancel") & allowed)
async def cancel_command(client, message: Message):
    user_id = message.from_user.id

    if user_id in user_setup:
        user_setup.pop(user_id, None)
        return await message.reply_text(
            "❌ **Setup cancelled.**",
            reply_markup=build_main_keyboard(user_id)
        )

    jobs = user_tasks.get(user_id, {})
    if not jobs:
        return await message.reply_text(
            "❌ **No active recording to cancel!**",
            reply_markup=build_main_keyboard(user_id)
        )

    if len(jobs) == 1:
        job_id = list(jobs.keys())[0]
        await do_cancel_job(user_id, job_id, message)
        await message.reply_text("✅ Done.", reply_markup=build_main_keyboard(user_id))
    else:
        user_setup.setdefault(user_id, {})["step"] = "cancel"
        await message.reply_text(
            f"📋 **You have {len(jobs)} active recordings.**\nWhich one to cancel?",
            reply_markup=build_cancel_keyboard(user_id)
        )


async def do_cancel_job(user_id: int, job_id: str, ref_message: Message):
    job_key = make_job_key(user_id, job_id)
    cancelled_jobs.add(job_key)

    if user_id in progress_tasks and job_id in progress_tasks[user_id]:
        progress_tasks[user_id][job_id].cancel()
        del progress_tasks[user_id][job_id]

    if user_id in user_ffmpeg_pids and job_id in user_ffmpeg_pids[user_id]:
        pid = user_ffmpeg_pids[user_id][job_id]
        try:
            parent   = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except Exception:
                    pass
            parent.kill()
            psutil.wait_procs([parent] + children, timeout=3)
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            LOG.error(f"Kill FFmpeg error: {e}")
        del user_ffmpeg_pids[user_id][job_id]

    info     = user_status.get(user_id, {}).get(job_id, {})
    filename = info.get("filename", "Unknown")
    n        = slot_number(job_id)
    emoji    = SLOT_EMOJI[n - 1]

    await ref_message.reply_text(
        f"✅ **Recording Cancelled!**\n\n"
        f"{emoji} **Slot {n}:** `{filename}`\n"
        f"🛑 Stopped — uploading recorded portion..."
    )


# ═════════════════════════════════════════════════════════════════════════════
#  RECORD — /rec /download  +  handle_record (core task)
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("rec") & allowed)
async def rec_command(client: Client, message: Message):
    import re as _re
    _TS_PAT = _re.compile(r'^\d{2}:\d{2}:\d{2}$')

    user_id = message.from_user.id

    if len(message.command) < 3:
        return await message.reply_text(
            "❌ **Invalid Format!**\n\n"
            "📌 **Usage (URL):**\n"
            "```\n/rec http://m3u8link 01:00:00 FileName\n```\n\n"
            "📌 **Usage (Channel Name):**\n"
            "```\n/rec record ChannelName 01:00:00 FileName\n```\n\n"
            "• **URL** — m3u8 / rtmp / direct stream\n"
            "• **Channel Name** — name from your saved playlists\n"
            "• **Duration** — HH:MM:SS format\n"
            "• **Filename** — saved as `filename.mkv`",
            reply_markup=build_main_keyboard(user_id)
        )

    if len(user_tasks.get(user_id, {})) >= MAX_CONCURRENT:
        return await message.reply_text(
            f"❌ **Maximum {MAX_CONCURRENT} simultaneous recordings reached!**\n"
            f"📊 /status  |  🛑 /cancel",
            reply_markup=build_main_keyboard(user_id)
        )

    args = message.command[1:]

    # ── Format 2: /rec record ChannelName HH:MM:SS Filename ──────────────────
    if args[0].lower() == "record":
        remaining = args[1:]
        ts_idx = next((i for i, a in enumerate(remaining) if _TS_PAT.match(a)), None)

        if ts_idx is None or ts_idx == 0:
            return await message.reply_text(
                "❌ **Invalid Format!**\n\n"
                "📌 **Usage:**\n"
                "```\n/rec record ChannelName 01:00:00 FileName\n```\n\n"
                "• **ChannelName** — from your saved playlists\n"
                "• **Duration** — HH:MM:SS",
                reply_markup=build_main_keyboard(user_id)
            )

        ch_name  = " ".join(remaining[:ts_idx]).strip()
        timestamp = remaining[ts_idx]
        filename  = " ".join(remaining[ts_idx + 1:]).strip() or config.DEFAULT_FILENAME

        return await _rec_channel_search(client, message, user_id, ch_name, timestamp, filename)

    # ── Format 1: /rec URL HH:MM:SS Filename ─────────────────────────────────
    url       = args[0]
    timestamp = args[1]
    filename  = " ".join(args[2:]).strip() if len(args) > 2 else config.DEFAULT_FILENAME

    msg = await message.reply_text("🔍 **Detecting stream info...**")
    try:
        info = await detect_stream_info(url)
    except Exception as e:
        return await msg.edit_text(f"❌ **Stream detection failed!**\n\n`{e}`")

    tracks   = info["tracks"]
    video    = info["video"]
    selected = set(tr["index"] for tr in tracks)

    user_setup[user_id] = {
        "mode":            "record",
        "step":            "audio" if tracks else "watermark",
        "url":             url,
        "timestamp":       timestamp,
        "filename":        filename,
        "tracks":          tracks,
        "selected_tracks": selected,
        "watermark_pos":   None,
        "watermark_text":  config.DEFAULT_FILENAME,
        "auto_mode":       False,
        "video_size":      "original",
        "video_info":      video,
    }

    quality_line = format_quality_line(video)
    audio_line   = ", ".join(tr["label"] for tr in tracks) if tracks else "Auto"

    if tracks:
        text = (
            f"✅ **Stream Detected!**\n\n"
            f"📺 **Quality:** `{quality_line}`\n"
            f"🎵 **Audio Tracks:** `{audio_line}`\n"
            f"⏱ **Duration:** `{timestamp}`\n"
            f"📁 **File:** `{filename}`\n\n"
            f"👇 Select audio tracks to include:"
        )
        kb = build_audio_keyboard(tracks, selected, uid=user_id)
    else:
        text = (
            f"✅ **Stream Detected!**\n\n"
            f"📺 **Quality:** `{quality_line}`\n"
            f"🎵 **Audio:** No tracks — will auto-select\n\n"
        ) + setup_summary_text(user_setup[user_id])
        kb = build_watermark_keyboard(user_setup[user_id], uid=user_id)

    try:
        await msg.delete()
    except Exception:
        pass
    await message.reply_text(text, reply_markup=kb)


# ── /rec record helper: search playlists and launch ──────────────────────────

async def _rec_channel_search(client: Client, message: Message,
                               user_id: int, ch_name: str,
                               timestamp: str, filename: str):
    playlists = playlist_manager.get_playlists(user_id)

    if not playlists:
        return await message.reply_text(
            "📭 **No playlists saved.**\n\n"
            "Add one first: `/Playlist_add <url> [name]`",
            reply_markup=build_main_keyboard(user_id)
        )

    msg = await message.reply_text(f"🔍 **Searching for:** `{ch_name}`...")
    query_lc = ch_name.lower()
    matches: list = []

    for pl_idx, pl in enumerate(playlists):
        channels = playlist_manager.cache_get(user_id, pl_idx)
        if not channels:
            ok, err, channels = await playlist_manager.fetch_and_parse(pl["url"])
            if not ok:
                continue
            playlist_manager.cache_set(user_id, pl_idx, channels)
        for ch in channels:
            if query_lc in ch["name"].lower():
                matches.append({"ch": ch, "pl_idx": pl_idx, "pl_name": pl["name"]})

    if not matches:
        return await msg.edit_text(
            f"❌ **No channel found matching:** `{ch_name}`\n\n"
            "Try a shorter name or browse: /channel",
            reply_markup=build_main_keyboard(user_id)
        )

    exact = [m for m in matches if m["ch"]["name"].lower() == query_lc]
    if len(exact) == 1 or len(matches) == 1:
        chosen = (exact or matches)[0]
        await msg.delete()
        return await _activate_channel(
            client, message, user_id,
            chosen["ch"], chosen["pl_idx"], chosen["pl_name"],
            timestamp=timestamp, filename=filename
        )

    shown   = matches[:15]
    buttons = []
    for i, m in enumerate(shown):
        label = f"📡 {m['ch']['name'][:35]}  [{m['pl_name']}]"
        buttons.append([InlineKeyboardButton(label, callback_data=f"rrc_{i}")])

    user_setup[user_id] = user_setup.get(user_id, {})
    user_setup[user_id]["_rrc_results"]   = shown
    user_setup[user_id]["_rrc_timestamp"] = timestamp
    user_setup[user_id]["_rrc_filename"]  = filename

    await msg.edit_text(
        f"🔍 **{len(matches)} channels found** for `{ch_name}`:\n"
        f"{'_(Showing top 15)_' if len(matches) > 15 else ''}\n\n"
        "👇 Tap to select the channel:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(r"^rrc_(\d+)$"))
async def cb_rec_channel_select(client: Client, query):
    user_id = query.from_user.id
    idx     = int(query.matches[0].group(1))
    setup   = user_setup.get(user_id, {})
    results = setup.get("_rrc_results", [])

    if idx >= len(results):
        return await query.answer("Session expired. Try /rec record again.", show_alert=True)

    chosen    = results[idx]
    timestamp = setup.get("_rrc_timestamp", "01:00:00")
    filename  = setup.get("_rrc_filename",  config.DEFAULT_FILENAME)

    await query.answer()
    await query.message.delete()
    await _activate_channel(
        client, query.message, user_id,
        chosen["ch"], chosen["pl_idx"], chosen["pl_name"],
        timestamp=timestamp, filename=filename
    )


@app.on_message(filters.command("download") & allowed)
async def download_command(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Invalid Format!**\n\n"
            "📌 **Usage:**\n"
            "```\n/download http://link FileName\n```\n\n"
            "• **URL** — direct link / m3u8 stream\n"
            "• **Filename** — optional (saved as `filename.mkv`)",
            reply_markup=build_main_keyboard(message.from_user.id)
        )

    user_id = message.from_user.id
    if len(user_tasks.get(user_id, {})) >= MAX_CONCURRENT:
        return await message.reply_text(
            f"❌ **Maximum {MAX_CONCURRENT} simultaneous downloads reached!**\n"
            f"📊 /status  |  🛑 /cancel",
            reply_markup=build_main_keyboard(user_id)
        )

    args     = message.command[1:]
    url      = args[0]
    filename = " ".join(args[1:]).strip() if len(args) > 1 else config.DEFAULT_FILENAME

    msg = await message.reply_text("🔍 **Detecting stream info...**")
    try:
        info = await detect_stream_info(url)
    except Exception as e:
        return await msg.edit_text(f"❌ **Stream detection failed!**\n\n`{e}`")

    tracks   = info["tracks"]
    video    = info["video"]
    selected = set(tr["index"] for tr in tracks)

    user_setup[user_id] = {
        "mode":            "download",
        "step":            "audio" if tracks else "watermark",
        "url":             url,
        "timestamp":       None,
        "filename":        filename,
        "tracks":          tracks,
        "selected_tracks": selected,
        "watermark_pos":   None,
        "watermark_text":  config.DEFAULT_FILENAME,
        "auto_mode":       False,
        "video_size":      "original",
        "video_info":      video,
    }

    quality_line = format_quality_line(video)

    if tracks:
        text = (
            f"✅ **Stream Detected!**\n\n"
            f"📺 **Quality:** `{quality_line}`\n"
            f"🎵 **Audio Tracks:** `{', '.join(tr['label'] for tr in tracks)}`\n"
            f"📁 **File:** `{filename}`\n\n"
            f"👇 Select audio tracks to include:"
        )
        kb = build_audio_keyboard(tracks, selected, uid=user_id)
    else:
        text = (
            f"✅ **Stream Detected!**\n\n"
            f"📺 **Quality:** `{quality_line}`\n"
            f"🎵 **Audio:** No tracks — will auto-select\n\n"
        ) + setup_summary_text(user_setup[user_id])
        kb = build_watermark_keyboard(user_setup[user_id], uid=user_id)

    try:
        await msg.delete()
    except Exception:
        pass
    await message.reply_text(text, reply_markup=kb)


async def handle_record(client: Client, ref_message: Message, setup: dict, user_id: int):
    job_id = next_job_id(user_id)
    if job_id is None:
        await ref_message.reply_text(f"❌ All {MAX_CONCURRENT} recording slots are busy!")
        return

    job_key         = make_job_key(user_id, job_id)
    n               = slot_number(job_id)
    emoji           = SLOT_EMOJI[n - 1]
    mode            = setup.get("mode", "record")
    url             = setup["url"]
    timestamp       = setup.get("timestamp")
    raw_filename    = setup["filename"]
    tracks          = setup.get("tracks", [])
    selected_tracks = setup.get("selected_tracks", set())
    watermark_pos   = setup.get("watermark_pos")
    watermark_text  = setup.get("watermark_text", config.DEFAULT_FILENAME)
    auto_mode       = setup.get("auto_mode", False) if mode == "record" else False
    video_size_key  = setup.get("video_size", "original")
    is_download     = (mode == "download")
    action_label    = "Downloading" if is_download else "Recording"

    filename   = f"{raw_filename}.mkv"
    save_dir   = join(config.DOWNLOAD_DIRECTORY, f"{int(time.time())}_{job_id}")
    os.makedirs(save_dir, exist_ok=True)
    video_path = join(save_dir, filename)

    msg = await ref_message.reply_text(
        f"{emoji} **Slot {n} — Initializing {action_label.lower()}...**\n📁 `{raw_filename}`"
    )

    try:
        user_tasks.setdefault(user_id, {})[job_id] = time.time()
        duration = time_to_seconds(timestamp) if timestamp else 0
        user_status.setdefault(user_id, {})[job_id] = {
            "id": int(time.time()), "filename": raw_filename,
            "target": timestamp or "∞", "progress": "00:00:00",
            "save_dir": save_dir, "mode": mode,
        }

        recording_start = time.time()

        video_map = "-map 0:V?"
        if tracks and selected_tracks:
            audio_maps = " ".join(
                f"-map 0:a:{tr['index']}?"
                for tr in tracks if tr["index"] in selected_tracks
            )
            meta_args = build_metadata_args(tracks, selected_tracks, config.CHANNEL_NAME)
        elif tracks:
            audio_maps = "-map 0:a:0? -map 0:a:1? -map 0:a:2?"
            meta_args  = build_metadata_args(tracks, set(), config.CHANNEL_NAME)
        else:
            audio_maps = "-map 0:a:0? -map 0:a:1? -map 0:a:2?"
            meta_args  = build_metadata_args([], set(), config.CHANNEL_NAME)

        size_vf       = VIDEO_SIZES.get(video_size_key, VIDEO_SIZES["original"])["vf"]
        filters_chain = []
        if size_vf:
            filters_chain.append(size_vf)
        if watermark_pos and watermark_text:
            x, y      = WM_POSITIONS[watermark_pos]
            safe_text = watermark_text.replace("'", "\\'").replace(":", "\\:")
            filters_chain.append(
                f"drawtext=text='{safe_text}':"
                f"fontsize=28:fontcolor=white@0.85:"
                f"x={x}:y={y}:box=1:boxcolor=black@0.45:boxborderw=6"
            )

        if filters_chain:
            vf          = f'-vf "{",".join(filters_chain)}"'
            video_codec = "-c:v libx264 -preset slow -b:v 330k"
        else:
            vf          = ""
            video_codec = "-c:v copy"
        audio_codec = "-c:a aac -b:a 48k"

        _pulse_pos = [0]

        async def update_progress():
            while (
                user_id in user_tasks and
                job_id  in user_tasks.get(user_id, {}) and
                job_key not in cancelled_jobs
            ):
                elapsed  = time.time() - recording_start
                prog     = TimeFormatter(int(elapsed * 1000))
                if job_id in user_status.get(user_id, {}):
                    user_status[user_id][job_id]["progress"] = prog
                speed_mb = random.uniform(2.0, 8.0)
                try:
                    if is_download:
                        _pulse_pos[0] = (_pulse_pos[0] + 1) % 10
                        p   = _pulse_pos[0]
                        bar = (PROGRESS_EMPTY * p + PROGRESS_FILLED + PROGRESS_EMPTY * (9 - p))
                        await msg.edit_text(
                            f"{emoji} **Slot {n} — Downloading**\n"
                            f"📁 `{raw_filename}`\n"
                            f"{bar}\n"
                            f"⏱️ Elapsed: `{prog}`\n"
                            f"⚡ `{speed_mb:.1f} MB/s`\n\n🛑 /cancel to stop",
                            parse_mode=enums.ParseMode.HTML
                        )
                    else:
                        pct     = min((elapsed / duration) * 100, 100) if duration > 0 else 0
                        eta_sec = ((duration - elapsed) / (pct / 100)) if pct > 0 else 0
                        filled  = int(10 * pct // 100)
                        bar     = PROGRESS_FILLED * filled + PROGRESS_EMPTY * (10 - filled)
                        await msg.edit_text(
                            f"{emoji} **Slot {n} — Recording**\n"
                            f"📁 `{raw_filename}`\n"
                            f"{bar} `{pct:.1f}%`\n"
                            f"📊 `{prog}` / `{TimeFormatter(duration * 1000)}`\n"
                            f"⚡ `{speed_mb:.1f} MB/s`  ⏳ `{TimeFormatter(int(eta_sec * 1000))}`\n\n"
                            f"🛑 /cancel to stop",
                            parse_mode=enums.ParseMode.HTML
                        )
                except Exception:
                    pass
                await asyncio.sleep(5)

        prog_task = asyncio.create_task(update_progress())
        progress_tasks.setdefault(user_id, {})[job_id] = prog_task
        video_path_local = video_path

        # Embed source URL into file metadata so /Get_Media_information can retrieve it
        _safe_url = url.replace('"', '\\"')
        url_meta  = f'-metadata comment="{_safe_url}" -metadata source_url="{_safe_url}"'

        if auto_mode:
            await msg.edit_text(f"{emoji} **Slot {n} — Auto Mode: Recording first 1 min...**")
            part1       = join(save_dir, "part1.mkv")
            part2       = join(save_dir, "part2.mkv")
            concat_list = join(save_dir, "concat.txt")

            cmd1 = (
                f'ffmpeg -y {http_opts(url)} -probesize 10000000 -analyzeduration 15000000 '
                f'-i "{url}" {video_map} {audio_maps} {vf} '
                f'{video_codec} {audio_codec} {meta_args} {url_meta} -movflags +faststart -t 00:01:00 "{part1}"'
            )
            proc1 = await asyncio.create_subprocess_exec(
                *shlex.split(cmd1), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            user_ffmpeg_pids.setdefault(user_id, {})[job_id] = proc1.pid
            await proc1.communicate()
            user_ffmpeg_pids.get(user_id, {}).pop(job_id, None)

            if job_key not in cancelled_jobs:
                seek_to = max(duration - 60, 61)
                await msg.edit_text(f"{emoji} **Slot {n} — Auto Mode: Recording last 1 min...**")
                cmd2 = (
                    f'ffmpeg -y {http_opts(url)} -probesize 10000000 -analyzeduration 15000000 '
                    f'-ss {seek_to} -i "{url}" {video_map} {audio_maps} {vf} '
                    f'{video_codec} {audio_codec} {meta_args} {url_meta} -movflags +faststart -t 00:01:00 "{part2}"'
                )
                proc2 = await asyncio.create_subprocess_exec(
                    *shlex.split(cmd2), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                user_ffmpeg_pids.setdefault(user_id, {})[job_id] = proc2.pid
                await proc2.communicate()
                user_ffmpeg_pids.get(user_id, {}).pop(job_id, None)

                await msg.edit_text(f"{emoji} **Slot {n} — Joining parts...**")
                with open(concat_list, "w") as f_:
                    f_.write(f"file '{part1}'\n")
                    if os.path.exists(part2) and os.path.getsize(part2) > 0:
                        f_.write(f"file '{part2}'\n")
                rc, _, _ = await runcmd(
                    f'ffmpeg -y -f concat -safe 0 -i "{concat_list}" -c copy '
                    f'{url_meta} "{video_path}"'
                )
                video_path_local = video_path if rc == 0 else part1

        else:
            time_arg   = f"-t {timestamp}" if timestamp else ""
            ffmpeg_cmd = (
                f'ffmpeg -y {http_opts(url)} -probesize 10000000 -analyzeduration 15000000 '
                f'-i "{url}" {video_map} {audio_maps} {vf} '
                f'{video_codec} {audio_codec} {meta_args} {url_meta} -movflags +faststart {time_arg} "{video_path}"'
            )
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(ffmpeg_cmd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            user_ffmpeg_pids.setdefault(user_id, {})[job_id] = proc.pid
            LOG.info(f"FFmpeg PID {proc.pid} | user {user_id} | {job_id}")
            _, stderr_bytes = await proc.communicate()
            user_ffmpeg_pids.get(user_id, {}).pop(job_id, None)
            video_path_local = video_path

            was_cancelled = job_key in cancelled_jobs
            if proc.returncode != 0 and not was_cancelled:
                raise Exception(f"FFmpeg Error:\n{stderr_bytes.decode()[-2000:]}")

        if job_id in progress_tasks.get(user_id, {}):
            progress_tasks[user_id][job_id].cancel()
            del progress_tasks[user_id][job_id]

        was_cancelled = job_key in cancelled_jobs

        if not os.path.exists(video_path_local) or os.path.getsize(video_path_local) == 0:
            if was_cancelled:
                await msg.edit_text(f"{emoji} **Slot {n} — Cancelled. No video.**")
                return
            raise Exception("Video file missing or empty.")

        thumb_msg  = await ref_message.reply_text(f"{emoji} **Slot {n} — Generating thumbnail...**")
        dur        = await get_duration_ffmpeg(video_path_local) or (time_to_seconds(timestamp) if timestamp else 0)
        fixed_path = join(save_dir, f"fixed_{filename}")
        rc, _, _   = await runcmd(
            f'ffmpeg -y -i "{video_path_local}" -map 0 -c copy '
            f'-metadata creation_time="{time.strftime("%Y-%m-%dT%H:%M:%S")}" '
            f'{url_meta} "{fixed_path}"'
        )
        if rc == 0:
            os.replace(fixed_path, video_path_local)

        rand_sec   = random.randint(5, max(dur - 5, 6))
        thumb_path = join(save_dir, "thumb.jpg")
        await runcmd(f'ffmpeg -y -ss {rand_sec} -i "{video_path_local}" -vframes 1 -q:v 2 "{thumb_path}"')
        await thumb_msg.delete()

        sel_labels = [tr["label"] for tr in tracks if tr["index"] in selected_tracks] or ["All"]
        wm_desc    = "OFF" if not watermark_pos else f"{WM_LABEL.get(watermark_pos)} → {watermark_text}"
        size_label = VIDEO_SIZES.get(video_size_key, VIDEO_SIZES["original"])["label"]

        if is_download:
            status_line = "⚠️ _Partial download (cancelled)_" if was_cancelled else "✅ _Downloaded successfully!_"
            old_line    = "" if was_cancelled else "\n_🗑 Video auto-deleted from server in 2 hours._\n_📥 Use /recording_old to get this video again._"
            caption = (
                f"{emoji} **{raw_filename}**\n\n"
                f"⏱ **Duration:** `{TimeFormatter(dur * 1000)}`\n"
                f"🎵 **Audio:** `{', '.join(sel_labels)}`\n"
                f"🖼 **Watermark:** `{wm_desc}`\n"
                f"📁 **Format:** MKV\n\n{status_line}{old_line}"
            )
        else:
            auto_desc   = "✅ First+Last 1min" if auto_mode else "❌"
            status_line = "⚠️ _Partial recording (cancelled)_" if was_cancelled else "✅ _Recorded successfully!_"
            old_line    = "" if was_cancelled else "\n_🗑 Video auto-deleted from server in 2 hours._\n_📥 Use /recording_old to get this video again._"
            caption = (
                f"{emoji} **{raw_filename}**\n\n"
                f"⏱ **Duration:** `{TimeFormatter(dur * 1000)}`\n"
                f"🎵 **Audio:** `{', '.join(sel_labels)}`\n"
                f"🖼 **Watermark:** `{wm_desc}`\n"
                f"📐 **Size:** `{size_label}`\n"
                f"⏩ **Auto:** `{auto_desc}`\n"
                f"📁 **Format:** MKV\n\n{status_line}{old_line}"
            )

        size_mb = round(os.path.getsize(video_path_local) / (1024 * 1024), 2) if os.path.exists(video_path_local) else 0
        uname   = ref_message.from_user.username or ref_message.from_user.first_name or str(user_id)
        _add_history({
            "type":       "download" if is_download else "rec",
            "status":     "cancelled" if was_cancelled else "done",
            "user_id":    user_id,
            "username":   uname,
            "filename":   raw_filename,
            "duration_s": int(dur),
            "size_mb":    size_mb,
            "url":        url[:120],
        })

        start_time = time.time()
        sent = await ref_message.reply_video(
            video=video_path_local, caption=caption, duration=dur,
            thumb=thumb_path if os.path.exists(thumb_path) else None,
            progress=progress_for_pyrogram,
            progress_args=(ref_message, start_time, msg, save_dir, was_cancelled, job_id)
        )
        if not was_cancelled and sent:
            recording_cache[user_id] = {
                "msg_id":   sent.id,
                "chat_id":  sent.chat.id,
                "filename": raw_filename,
                "ts":       time.time(),
                "type":     "download" if is_download else "rec",
            }
        shutil.rmtree(save_dir, ignore_errors=True)

    except Exception as e:
        LOG.error(f"handle_record [{job_id}] error: {e}")
        uname = ref_message.from_user.username or ref_message.from_user.first_name or str(user_id)
        _add_history({
            "type":       "download" if setup.get("mode") == "download" else "rec",
            "status":     "cancelled" if job_key in cancelled_jobs else "failed",
            "user_id":    user_id,
            "username":   uname,
            "filename":   setup.get("filename", "?"),
            "duration_s": 0,
            "size_mb":    0,
            "url":        setup.get("url", "")[:120],
        })
        if job_key not in cancelled_jobs:
            try:
                await msg.edit(f"{emoji} **Slot {n} — Failed!**\n\n`{str(e)[:3000]}`")
            except Exception:
                pass
        shutil.rmtree(save_dir, ignore_errors=True)

    finally:
        user_tasks.get(user_id, {}).pop(job_id, None)
        user_status.get(user_id, {}).pop(job_id, None)
        user_ffmpeg_pids.get(user_id, {}).pop(job_id, None)
        progress_tasks.get(user_id, {}).pop(job_id, None)
        cancelled_jobs.discard(job_key)
        for d in [user_tasks, user_status, user_ffmpeg_pids, progress_tasks]:
            if user_id in d and not d[user_id]:
                del d[user_id]


# ═════════════════════════════════════════════════════════════════════════════
#  COMPRESS — /compress  +  run_compress (called by router)
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("compress") & allowed)
async def compress_cmd(client, message: Message):
    if not message.reply_to_message or not get_video_media(message.reply_to_message):
        return await message.reply_text(
            "❌ **Reply to a video message with /compress**",
            reply_markup=build_main_keyboard(message.from_user.id)
        )
    user_id = message.from_user.id
    compress_pending[user_id] = message.reply_to_message.id
    user_setup[user_id] = {"step": "compress"}
    await message.reply_text(
        "🗜 **Video Compress**\n\nSelect compression quality:",
        reply_markup=build_compress_keyboard(uid=user_id)
    )


async def run_compress(client, message: Message, user_id: int, canon_text: str):
    """canon_text is already the canonical English button label from the router."""
    cancel_en = t(None, "btn_cmp_cancel")

    if canon_text == cancel_en:
        compress_pending.pop(user_id, None)
        user_setup.pop(user_id, None)
        return await message.reply_text(
            "❌ Compression cancelled.",
            reply_markup=build_main_keyboard(user_id)
        )

    if canon_text not in COMPRESS_PRESETS:
        return await message.reply_text(
            "❓ Please choose a quality option.",
            reply_markup=build_compress_keyboard(uid=user_id)
        )

    video_msg_id = compress_pending.pop(user_id, None)
    if not video_msg_id:
        user_setup.pop(user_id, None)
        return await message.reply_text(
            "❌ Session expired. Reply to video and use /compress again.",
            reply_markup=build_main_keyboard(user_id)
        )

    ffmpeg_args, quality_desc = COMPRESS_PRESETS[canon_text]
    user_setup.pop(user_id, None)

    if len(user_tasks.get(user_id, {})) >= MAX_CONCURRENT:
        return await message.reply_text(
            f"❌ All {MAX_CONCURRENT} slots busy. Cancel one first.",
            reply_markup=build_main_keyboard(user_id)
        )

    job_id  = next_job_id(user_id)
    if not job_id:
        return
    job_key  = make_job_key(user_id, job_id)
    n        = slot_number(job_id)
    emoji_s  = SLOT_EMOJI[n - 1]
    save_dir = join(config.DOWNLOAD_DIRECTORY, f"{int(time.time())}_{job_id}_compress")
    os.makedirs(save_dir, exist_ok=True)

    user_tasks.setdefault(user_id, {})[job_id] = time.time()
    user_status.setdefault(user_id, {})[job_id] = {
        "id": int(time.time()), "filename": "Compressed Video",
        "target": "∞", "progress": "00:00:00",
        "save_dir": save_dir, "mode": "compress",
    }

    msg = await message.reply_text(
        f"{emoji_s} **Slot {n} — Starting compression ({quality_desc})...**",
        reply_markup=build_main_keyboard(user_id)
    )

    async def do_compress():
        try:
            await msg.edit_text(f"{emoji_s} **Slot {n} — Downloading original video...**")
            orig_path     = join(save_dir, "original.mkv")
            video_message = await client.get_messages(message.chat.id, video_msg_id)
            if not video_message or not get_video_media(video_message):
                raise Exception("Original video message not found.")
            await client.download_media(video_message, file_name=orig_path)

            if not os.path.exists(orig_path) or os.path.getsize(orig_path) == 0:
                raise Exception("Download failed or file is empty.")

            orig_size_mb = os.path.getsize(orig_path) / (1024 * 1024)
            await msg.edit_text(
                f"{emoji_s} **Slot {n} — Compressing...**\n"
                f"📦 Original: `{orig_size_mb:.1f} MB`  🎛 `{quality_desc}`"
            )

            out_path = join(save_dir, "compressed.mkv")
            rc, _, err = await runcmd(f'ffmpeg -y -i "{orig_path}" {ffmpeg_args} "{out_path}"')
            if rc != 0:
                raise Exception(f"FFmpeg error:\n{err[-1500:]}")

            new_size_mb = os.path.getsize(out_path) / (1024 * 1024)
            reduction   = max(0, (1 - new_size_mb / orig_size_mb) * 100)

            dur      = await get_duration_ffmpeg(out_path)
            rand_sec = random.randint(5, max(dur - 5, 6)) if dur > 10 else 1
            thumb_path = join(save_dir, "thumb.jpg")
            await runcmd(f'ffmpeg -y -ss {rand_sec} -i "{out_path}" -vframes 1 -q:v 2 "{thumb_path}"')

            caption = (
                f"🗜 **Compressed Video**\n\n"
                f"📦 **Original:** `{orig_size_mb:.1f} MB`\n"
                f"📉 **Compressed:** `{new_size_mb:.1f} MB`\n"
                f"✂️ **Reduction:** `{reduction:.1f}%`\n"
                f"🎛 **Quality:** `{quality_desc}`\n\n"
                f"✅ _Compression completed!_"
            )
            start_time = time.time()
            await msg.reply_video(
                video=out_path, caption=caption, duration=dur,
                thumb=thumb_path if os.path.exists(thumb_path) else None,
                progress=progress_for_pyrogram,
                progress_args=(msg, start_time, msg, save_dir, False, job_id)
            )
            shutil.rmtree(save_dir, ignore_errors=True)

        except Exception as e:
            LOG.error(f"compress error [{job_id}]: {e}")
            try:
                await msg.edit_text(f"{emoji_s} **Compression Failed!**\n\n`{str(e)[:2000]}`")
            except Exception:
                pass
            shutil.rmtree(save_dir, ignore_errors=True)
        finally:
            user_tasks.get(user_id, {}).pop(job_id, None)
            user_status.get(user_id, {}).pop(job_id, None)
            cancelled_jobs.discard(job_key)
            for d in [user_tasks, user_status]:
                if user_id in d and not d[user_id]:
                    del d[user_id]

    asyncio.create_task(do_compress())


# ═════════════════════════════════════════════════════════════════════════════
#  SCREENSHOT — /screenshot
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("screenshot") & allowed)
async def screenshot_cmd(client, message: Message):
    if not message.reply_to_message or not get_video_media(message.reply_to_message):
        return await message.reply_text(
            "❌ **Reply to a video with /screenshot [count]**\n\n"
            "Example: `/screenshot 10` → 10 screenshots (max 30)",
            reply_markup=build_main_keyboard(message.from_user.id)
        )
    try:
        count = int(message.command[1]) if len(message.command) > 1 else 1
        count = max(1, min(count, 30))
    except (ValueError, IndexError):
        count = 1

    user_id       = message.from_user.id
    video_message = message.reply_to_message
    msg = await message.reply_text(
        f"📸 **Extracting {count} screenshot{'s' if count > 1 else ''}...**",
        reply_markup=build_main_keyboard(user_id)
    )
    save_dir = join(config.DOWNLOAD_DIRECTORY, f"{int(time.time())}_ss_{user_id}")
    os.makedirs(save_dir, exist_ok=True)

    try:
        await msg.edit_text("📥 **Downloading video...**")
        orig_path = join(save_dir, "video.mkv")
        await client.download_media(video_message, file_name=orig_path)

        if not os.path.exists(orig_path) or os.path.getsize(orig_path) == 0:
            raise Exception("Video download failed or file is empty.")

        dur = await get_duration_ffmpeg(orig_path)

        await msg.edit_text(f"📸 **Extracting {count} screenshot{'s' if count > 1 else ''}...**")

        if dur <= 0:
            timestamps = [0]
            count = 1
        elif dur == 1:
            timestamps = [0]
            count = 1
        elif count == 1:
            timestamps = [max(dur // 2, 0)]
        else:
            usable_dur = max(dur - 2, 1)
            count      = min(count, usable_dur)
            step       = usable_dur / max(count - 1, 1)
            timestamps = [min(int(i * step), dur - 1) for i in range(count)]

        screenshot_paths = []
        for i, ts in enumerate(timestamps):
            ss_path = join(save_dir, f"ss_{i + 1:02d}.jpg")
            rc, _, _ = await runcmd(
                f'ffmpeg -y -ss {ts} -i "{orig_path}" -vframes 1 -q:v 2 "{ss_path}"'
            )
            if rc == 0 and os.path.exists(ss_path) and os.path.getsize(ss_path) > 0:
                screenshot_paths.append(ss_path)

        if not screenshot_paths:
            raise Exception("No screenshots could be extracted.")

        await msg.edit_text(
            f"📤 **Uploading {len(screenshot_paths)} screenshot{'s' if len(screenshot_paths) > 1 else ''}...**"
        )

        caption_main = (
            f"📸 **{len(screenshot_paths)} Screenshot{'s' if len(screenshot_paths) > 1 else ''}**\n"
            f"⏱ **Video Duration:** `{TimeFormatter(dur * 1000)}`"
        )
        for batch_start in range(0, len(screenshot_paths), 10):
            batch = screenshot_paths[batch_start: batch_start + 10]
            media_group = [
                InputMediaPhoto(sp, caption=caption_main if (batch_start == 0 and idx == 0) else "")
                for idx, sp in enumerate(batch)
            ]
            await message.reply_media_group(media_group)

        await msg.edit_text(
            f"✅ **{len(screenshot_paths)} screenshot{'s' if len(screenshot_paths) > 1 else ''} sent!**"
        )
        shutil.rmtree(save_dir, ignore_errors=True)

    except Exception as e:
        LOG.error(f"screenshot error: {e}")
        try:
            await msg.edit_text(f"❌ **Screenshot failed!**\n\n`{str(e)[:2000]}`")
        except Exception:
            pass
        shutil.rmtree(save_dir, ignore_errors=True)


# ═════════════════════════════════════════════════════════════════════════════
#  GET MEDIA INFORMATION — /Get_Media_information
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("Get_Media_information") & allowed)
async def get_media_info_cmd(client, message: Message):
    user_id = message.from_user.id
    replied = message.reply_to_message
    media   = get_video_media(replied) if replied else None

    if not media:
        return await message.reply_text(
            "❌ **Kisi video ko reply karke /Get_Media_information bhejo.**\n\n"
            "📌 Example:\n"
            "  — Video reply karo\n"
            "  — `/Get_Media_information` bhejo\n\n"
            "📊 Yeh command batayega:\n"
            "  • Video resolution, codec, fps, bitrate\n"
            "  • Har audio track — language, codec, channels, bitrate\n"
            "  • Total streams count\n"
            "  • File size aur duration",
            reply_markup=build_main_keyboard(user_id)
        )

    msg = await message.reply_text("🔍 **Analyzing media... please wait**")

    save_dir  = join(config.DOWNLOAD_DIRECTORY, f"{int(time.time())}_minfo_{user_id}")
    os.makedirs(save_dir, exist_ok=True)
    file_path = join(save_dir, "input_video")

    try:
        await msg.edit_text("📥 **Downloading video for analysis...**")
        await client.download_media(replied, file_name=file_path)

        # ffprobe — full JSON output
        probe_cmd = (
            f'ffprobe -v quiet -print_format json '
            f'-show_format -show_streams "{file_path}"'
        )
        rc, out, err = await runcmd(probe_cmd, timeout=60)

        if rc != 0 or not out.strip():
            raise Exception(f"ffprobe failed:\n{err[:500]}")

        data    = json.loads(out)
        streams = data.get("streams", [])
        fmt     = data.get("format", {})

        # ── File-level info ──────────────────────────────────────────────────
        duration_s   = float(fmt.get("duration", 0) or 0)
        file_size_b  = int(fmt.get("size", 0) or 0)
        overall_bps  = int(fmt.get("bit_rate", 0) or 0)
        format_name  = fmt.get("format_long_name", fmt.get("format_name", "Unknown"))
        nb_streams   = int(fmt.get("nb_streams", len(streams)))
        fmt_tags     = fmt.get("tags", {})
        source_url   = (
            fmt_tags.get("source_url") or fmt_tags.get("SOURCE_URL") or
            fmt_tags.get("comment")    or fmt_tags.get("COMMENT") or ""
        )

        def fmt_dur(s):
            h = int(s // 3600); m = int((s % 3600) // 60); sec = int(s % 60)
            ms = int((s - int(s)) * 1000)
            return f"{h:02}:{m:02}:{sec:02}.{ms:03}"

        def fmt_size(b):
            if b >= 1_073_741_824: return f"{b / 1_073_741_824:.2f} GB"
            if b >= 1_048_576:     return f"{b / 1_048_576:.2f} MB"
            if b >= 1024:          return f"{b / 1024:.2f} KB"
            return f"{b} B"

        def fmt_bps(bps):
            if bps <= 0: return "N/A"
            if bps >= 1_000_000: return f"{bps / 1_000_000:.2f} Mbps"
            return f"{bps // 1000} kbps"

        # ── Per-stream analysis ──────────────────────────────────────────────
        video_lines = []
        audio_lines = []
        other_lines = []
        v_count = a_count = 0

        for s in streams:
            ctype = s.get("codec_type", "unknown")
            idx   = s.get("index", "?")
            codec = s.get("codec_name", "?").upper()
            tags  = s.get("tags", {})

            if ctype == "video":
                v_count += 1
                w        = s.get("width", 0)
                h        = s.get("height", 0)
                fps_raw  = s.get("r_frame_rate", "0/1")
                try:
                    n, d = fps_raw.split("/")
                    fps  = round(int(n) / int(d), 2) if int(d) else 0
                except Exception:
                    fps = 0
                tbr_raw = s.get("avg_frame_rate", fps_raw)
                try:
                    n, d = tbr_raw.split("/")
                    tbr  = round(int(n) / int(d), 2) if int(d) else fps
                except Exception:
                    tbr = fps
                br      = int(s.get("bit_rate", 0) or 0) // 1000
                pix_fmt = s.get("pix_fmt", "?")
                profile = s.get("profile", "")
                level   = s.get("level", "")
                is_def  = s.get("disposition", {}).get("default", 0)

                level_str   = f" L{level/10:.1f}" if isinstance(level, int) and level > 0 else ""
                profile_str = f" [{profile}{level_str}]" if profile else ""
                br_str      = f"{br} kbps" if br > 0 else "N/A"
                fps_str     = f"{fps}" if fps == tbr else f"{fps} (avg {tbr})"

                video_lines.append(
                    f"  🎬 Stream #{idx} — **{codec}{profile_str}**\n"
                    f"     📐 Resolution : `{w}×{h}`\n"
                    f"     🎞 FPS         : `{fps_str}`\n"
                    f"     💾 Bitrate     : `{br_str}`\n"
                    f"     🎨 Pixel Fmt   : `{pix_fmt}`\n"
                    f"     {'✅ Default' if is_def else '➡ Non-default'}"
                )

            elif ctype == "audio":
                a_count  += 1
                lang_tag  = (tags.get("language") or tags.get("LANGUAGE") or "").lower()
                title_tag = tags.get("title") or tags.get("TITLE") or ""
                ch        = int(s.get("channels", 0) or 0)
                sr        = int(s.get("sample_rate", 0) or 0)
                br        = int(s.get("bit_rate", 0) or 0) // 1000
                is_def    = s.get("disposition", {}).get("default", 0)

                ch_str    = {0: "?ch", 1: "Mono", 2: "Stereo"}.get(ch, f"{ch}ch")
                sr_str    = f"{sr // 1000}kHz" if sr >= 1000 else (f"{sr}Hz" if sr else "N/A")
                br_str    = f"{br} kbps" if br > 0 else "N/A"
                lang_full = LANG_FULL.get(lang_tag, lang_tag.upper() if lang_tag else "Unknown")
                lang_disp = LANG_MAP.get(lang_tag, lang_tag.upper() if lang_tag else "?")
                title_str = f"\n     📝 Title       : `{title_tag}`" if title_tag else ""

                audio_lines.append(
                    f"  🎵 Stream #{idx} — **{codec}** | {lang_full} (`{lang_disp}`)\n"
                    f"     🔊 Channels    : `{ch_str}`\n"
                    f"     🎚 Sample Rate : `{sr_str}`\n"
                    f"     💾 Bitrate     : `{br_str}`"
                    f"{title_str}\n"
                    f"     {'✅ Default' if is_def else '➡ Non-default'}"
                )

            else:
                cname = s.get("codec_name", ctype)
                other_lines.append(f"  ➡ Stream #{idx} — {ctype.upper()} ({cname})")

        # ── Build final message ──────────────────────────────────────────────
        lines = [
            "📊 **MEDIA INFORMATION**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📦 **Format    :** `{format_name}`",
            f"⏱ **Duration  :** `{fmt_dur(duration_s)}`",
            f"💾 **File Size :** `{fmt_size(file_size_b)}`",
            f"📡 **Bitrate   :** `{fmt_bps(overall_bps)}`",
            f"🔢 **Streams   :** `{nb_streams} total` "
            f"(`{v_count}` video + `{a_count}` audio"
            f"{' + ' + str(len(other_lines)) + ' other' if other_lines else ''})",
            "",
        ]

        if source_url:
            lines += [
                "━━━ 🔗 SOURCE URL ━━━",
                f"`{source_url}`",
                "",
            ]

        if video_lines:
            lines.append(f"━━━ 🎬 VIDEO TRACKS ({v_count}) ━━━")
            lines.extend(video_lines)
            lines.append("")

        if audio_lines:
            lines.append(f"━━━ 🎵 AUDIO TRACKS ({a_count}) ━━━")
            lines.extend(audio_lines)
            lines.append("")

        if other_lines:
            lines.append("━━━ 📌 OTHER STREAMS ━━━")
            lines.extend(other_lines)
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

        result_text = "\n".join(lines)

        # Telegram 4096 char limit safety
        if len(result_text) > 4000:
            result_text = result_text[:3990] + "\n…_(truncated)_"

        await msg.edit_text(result_text)

    except Exception as e:
        LOG.error(f"get_media_info error: {e}")
        try:
            await msg.edit_text(f"❌ **Analysis failed!**\n\n`{str(e)[:1500]}`")
        except Exception:
            pass
    finally:
        shutil.rmtree(save_dir, ignore_errors=True)


# ═════════════════════════════════════════════════════════════════════════════
#  COOKIES — /cookies_add /cookies_status /del_cookies  + document handler
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("cookies_add") & allowed)
async def cookies_add_cmd(client, message: Message):
    user_id = message.from_user.id
    user_setup.setdefault(user_id, {})["awaiting_cookies"] = True
    await message.reply_text(
        "🍪 **Add Cookies**\n\n"
        "📎 **Reply to this message with your `cookies.txt` file.**\n\n"
        "📝 How to get cookies:\n"
        "• Install **EditThisCookie** or **Get cookies.txt** extension\n"
        "• Login to OTT platform\n"
        "• Export cookies as `cookies.txt` (Netscape format)\n\n"
        "⚠️ _Cookies are stored privately per user._",
        reply_markup=build_main_keyboard(user_id)
    )


@app.on_message(filters.document & allowed)
async def document_handler(client, message: Message):
    user_id = message.from_user.id
    setup   = user_setup.get(user_id, {})
    if not setup.get("awaiting_cookies"):
        return
    doc = message.document
    if not (doc.file_name or "").lower().endswith(".txt"):
        return await message.reply_text("❌ Please send a `.txt` file (cookies.txt).")
    msg = await message.reply_text("⏳ **Saving cookies...**")
    try:
        dest = cookies_path(user_id)
        await client.download_media(message, file_name=dest)
        setup.pop("awaiting_cookies", None)
        size_kb = os.path.getsize(dest) / 1024
        await msg.edit_text(
            f"✅ **Cookies saved!**\n\n"
            f"📦 **Size:** `{size_kb:.1f} KB`\n\n"
            f"Now use /ott_download with OTT URLs — cookies will be applied automatically. 🍪"
        )
    except Exception as e:
        LOG.error(f"cookies_add error: {e}")
        await msg.edit_text(f"❌ **Failed to save cookies:** `{e}`")


@app.on_message(filters.command("cookies_status") & allowed)
async def cookies_status_cmd(client, message: Message):
    user_id = message.from_user.id
    path    = cookies_path(user_id)
    if not os.path.exists(path):
        return await message.reply_text(
            "❌ **No cookies found!**\n\nUse /cookies_add to upload.",
            reply_markup=build_main_keyboard(user_id)
        )
    size_kb  = os.path.getsize(path) / 1024
    created  = datetime.fromtimestamp(os.path.getctime(path), tz=tz).strftime("%d-%m-%Y %I:%M:%S %p")
    modified = datetime.fromtimestamp(os.path.getmtime(path), tz=tz).strftime("%d-%m-%Y %I:%M:%S %p")
    with open(path, "r", errors="ignore") as f:
        lines = [l for l in f.readlines() if l.strip() and not l.startswith("#")]
    await message.reply_text(
        f"🍪 **Cookies Status**\n\n"
        f"✅ **Status:** Active\n"
        f"📦 **Size:** `{size_kb:.1f} KB`\n"
        f"🔢 **Entries:** `{len(lines)}`\n"
        f"🕒 **Uploaded:** `{created}`\n"
        f"🔄 **Modified:** `{modified}`\n\n"
        f"🗑 Use /del_cookies to remove",
        reply_markup=build_main_keyboard(user_id)
    )


@app.on_message(filters.command("del_cookies") & allowed)
async def del_cookies_cmd(client, message: Message):
    user_id = message.from_user.id
    path    = cookies_path(user_id)
    if not os.path.exists(path):
        return await message.reply_text("❌ **No cookies to delete!**", reply_markup=build_main_keyboard(user_id))
    os.remove(path)
    await message.reply_text(
        "🗑 **Cookies deleted successfully!**\n\nUse /cookies_add to upload new ones.",
        reply_markup=build_main_keyboard(user_id)
    )


# ═════════════════════════════════════════════════════════════════════════════
#  PLAYLIST — /Playlist_add /Playlist_delete /Channel_activate /channel
#             + all inline callback handlers
# ═════════════════════════════════════════════════════════════════════════════

async def _do_playlist_add(client: Client, message: Message):
    args    = message.command[1:]
    user_id = message.from_user.id

    if not args:
        return await message.reply_text(
            "❌ **Usage:** `/Playlist_add <url> [name]`\n\n"
            "**Example:**\n"
            "`/Playlist_add https://play.ksrtech.fun/playlist.php?token=KSR-xxx MyList`"
        )

    url  = args[0]
    name = " ".join(args[1:]).strip() if len(args) > 1 else \
           f"Playlist{len(playlist_manager.get_playlists(user_id)) + 1}"

    msg = await message.reply_text("🔍 **Checking playlist URL...**")

    ok, err, channels = await playlist_manager.fetch_and_parse(url)
    if not ok:
        return await msg.edit_text(f"❌ **Invalid Playlist!**\n\n`{err}`")

    groups = playlist_manager.get_groups(channels)
    success, result_msg = playlist_manager.add_playlist(user_id, name, url)

    if success:
        playlist_manager.cache_set(
            user_id,
            len(playlist_manager.get_playlists(user_id)) - 1,
            channels,
        )

    await msg.edit_text(
        f"{result_msg}\n\n"
        f"📺 **Channels:** `{len(channels)}`\n"
        f"📂 **Groups:** `{len(groups)}`\n"
        f"🔗 **URL:** `{url[:60]}{'...' if len(url) > 60 else ''}`\n\n"
        f"Use /channel to browse channels."
    )


@app.on_message(filters.command(["Playlist_add", "playlistadd"]) & allowed)
async def playlistadd_cmd(client: Client, message: Message):
    await _do_playlist_add(client, message)


async def _do_playlist_delete(client: Client, message: Message):
    user_id   = message.from_user.id
    playlists = playlist_manager.get_playlists(user_id)

    if not playlists:
        return await message.reply_text(
            "📭 **No playlists saved.** Add one with /Playlist_add"
        )

    args = message.command[1:]
    if not args:
        lines = "\n".join(
            f"  `{i + 1}.` **{p['name']}**" for i, p in enumerate(playlists)
        )
        return await message.reply_text(
            f"❌ **Usage:** `/Playlist_delete <name or number>`\n\n"
            f"**Your playlists:**\n{lines}"
        )

    target = " ".join(args).strip()
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(playlists):
            target = playlists[idx]["name"]

    success, result_msg = playlist_manager.delete_playlist(user_id, target)
    await message.reply_text(result_msg)


@app.on_message(filters.command(["Playlist_delete", "playlistdelete"]) & allowed)
async def playlistdelete_cmd(client: Client, message: Message):
    await _do_playlist_delete(client, message)


@app.on_message(filters.command("Channel_activate") & allowed)
async def channel_activate_cmd(client: Client, message: Message):
    user_id   = message.from_user.id
    args      = message.command[1:]
    playlists = playlist_manager.get_playlists(user_id)

    if not playlists:
        return await message.reply_text(
            "📭 **No playlists saved.**\n\n"
            "Add one first: `/Playlist_add <url> [name]`"
        )

    if not args:
        return await message.reply_text(
            "❌ **Usage:** `/Channel_activate <channel name>`\n\n"
            "**Example:** `/Channel_activate Star Sports 1 HD`\n\n"
            "ℹ️ Partial name search bhi kaam karega.\n"
            "📋 Channels dekhne ke liye: /channel"
        )

    query_str = " ".join(args).strip().lower()
    msg       = await message.reply_text(f"🔍 **Searching for:** `{' '.join(args)}`...")

    matches: list = []

    for pl_idx, pl in enumerate(playlists):
        channels = playlist_manager.cache_get(user_id, pl_idx)
        if not channels:
            ok, err, channels = await playlist_manager.fetch_and_parse(pl["url"])
            if not ok:
                continue
            playlist_manager.cache_set(user_id, pl_idx, channels)

        for ch in channels:
            if query_str in ch["name"].lower():
                matches.append({
                    "ch":      ch,
                    "pl_idx":  pl_idx,
                    "pl_name": pl["name"],
                })

    if not matches:
        return await msg.edit_text(
            f"❌ **No channel found matching:** `{' '.join(args)}`\n\n"
            "Try a shorter name or browse: /channel"
        )

    exact = [m for m in matches if m["ch"]["name"].lower() == query_str]
    if len(exact) == 1 or len(matches) == 1:
        chosen = (exact or matches)[0]
        await msg.delete()
        return await _activate_channel(
            client, message, user_id,
            chosen["ch"], chosen["pl_idx"], chosen["pl_name"]
        )

    shown   = matches[:15]
    buttons = []
    for i, m in enumerate(shown):
        ch_name = m["ch"]["name"][:35]
        label   = f"📡 {ch_name}  [{m['pl_name']}]"
        buttons.append([InlineKeyboardButton(label, callback_data=f"ca_{i}")])

    user_setup[user_id] = user_setup.get(user_id, {})
    user_setup[user_id]["_ca_results"] = shown

    await msg.edit_text(
        f"🔍 **{len(matches)} channels found** for `{' '.join(args)}`:\n"
        f"{'_(Showing top 15)_' if len(matches) > 15 else ''}\n\n"
        "👇 Tap the channel to activate:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(r"^ca_(\d+)$"))
async def cb_channel_activate(client: Client, query):
    user_id = query.from_user.id
    idx     = int(query.matches[0].group(1))
    results = (user_setup.get(user_id) or {}).get("_ca_results", [])

    if idx >= len(results):
        return await query.answer("Session expired. Try /Channel_activate again.", show_alert=True)

    chosen = results[idx]
    await query.answer()
    await query.message.delete()
    await _activate_channel(
        client, query.message, user_id,
        chosen["ch"], chosen["pl_idx"], chosen["pl_name"]
    )


async def _activate_channel(client: Client, ref_message: Message,
                             user_id: int, ch: dict, pl_idx: int, pl_name: str,
                             timestamp: str = "01:00:00", filename: str = None):
    stream_url = ch["url"]
    safe_name  = filename or ch["name"].replace("`", "'")[:40] or config.DEFAULT_FILENAME

    msg = await ref_message.reply_text(
        f"📡 **{ch['name']}**\n"
        f"📂 Playlist: `{pl_name}`\n"
        f"📂 Group: `{ch.get('group', 'General')}`\n\n"
        f"🔍 Stream detecting, please wait..."
    )

    if len(user_tasks.get(user_id, {})) >= MAX_CONCURRENT:
        return await msg.edit_text(
            f"❌ **{MAX_CONCURRENT} slots busy.**\n📊 /status  |  🛑 /cancel"
        )

    try:
        info = await detect_stream_info(stream_url)
    except Exception as e:
        LOG.error(f"channel_activate detect error: {e}")
        return await msg.edit_text(
            f"❌ **Stream detect failed!**\n\n`{e}`\n\n"
            "Channel URL check karein ya doosra channel try karein."
        )

    tracks   = info["tracks"]
    video    = info["video"]
    selected = set(tr["index"] for tr in tracks)

    user_setup[user_id] = {
        "mode":            "record",
        "step":            "audio" if tracks else "watermark",
        "url":             stream_url,
        "timestamp":       timestamp,
        "filename":        safe_name,
        "tracks":          tracks,
        "selected_tracks": selected,
        "watermark_pos":   None,
        "watermark_text":  config.DEFAULT_FILENAME,
        "auto_mode":       False,
        "video_size":      "original",
        "chat_id":         ref_message.chat.id,
        "reply_to":        ref_message.id,
        "video_info":      video,
    }

    quality_line = format_quality_line(video)
    audio_line   = ", ".join(tr["label"] for tr in tracks) if tracks else "Auto"

    if tracks:
        text = (
            f"✅ **Stream Ready!**\n\n"
            f"📡 **Channel:** `{ch['name']}`\n"
            f"📋 **Playlist:** `{pl_name}`\n"
            f"📺 **Quality:** `{quality_line}`\n"
            f"🎵 **Audio:** `{audio_line}`\n"
            f"⏱ **Duration:** `{timestamp}`\n"
            f"📁 **File:** `{safe_name}`\n\n"
            f"👇 Select audio tracks to include:"
        )
        kb = build_audio_keyboard(tracks, selected, uid=user_id)
    else:
        text = (
            f"✅ **Stream Ready!**\n\n"
            f"📡 **Channel:** `{ch['name']}`\n"
            f"📋 **Playlist:** `{pl_name}`\n"
            f"📺 **Quality:** `{quality_line}`\n"
            f"🎵 **Audio:** Auto-select\n\n"
        ) + setup_summary_text(user_setup[user_id])
        kb = build_watermark_keyboard(user_setup[user_id], uid=user_id)

    try:
        await msg.delete()
    except Exception:
        pass
    await ref_message.reply_text(text, reply_markup=kb)


@app.on_message(filters.command("channel") & allowed)
async def channel_cmd(client: Client, message: Message):
    user_id   = message.from_user.id
    playlists = playlist_manager.get_playlists(user_id)

    if not playlists:
        return await message.reply_text(
            "📭 **No playlists saved yet!**\n\n"
            "Add one first:\n"
            "`/playlistadd <url> [name]`\n\n"
            "**Example:**\n"
            "`/playlistadd https://play.ksrtech.fun/playlist.php?token=KSR-xxx MyList`"
        )

    buttons = [
        [InlineKeyboardButton(f"📋 {p['name']}", callback_data=f"plg_{i}")]
        for i, p in enumerate(playlists)
    ]
    await message.reply_text(
        "📺 **Select a Playlist:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(r"^plg_(\d+)$"))
async def cb_playlist_groups(client: Client, query):
    user_id   = query.from_user.id
    pl_idx    = int(query.matches[0].group(1))
    playlists = playlist_manager.get_playlists(user_id)

    if pl_idx >= len(playlists):
        return await query.answer("Playlist not found!", show_alert=True)

    pl = playlists[pl_idx]
    await query.answer()
    await query.message.edit_text(f"⏳ **Loading `{pl['name']}`...**")

    channels = playlist_manager.cache_get(user_id, pl_idx)
    if not channels:
        ok, err, channels = await playlist_manager.fetch_and_parse(pl["url"])
        if not ok:
            return await query.message.edit_text(f"❌ **Failed to load playlist:**\n`{err}`")
        playlist_manager.cache_set(user_id, pl_idx, channels)

    groups  = playlist_manager.get_groups(channels)
    buttons = []
    row = []
    for gi, g in enumerate(groups):
        count = len(playlist_manager.channels_in_group(channels, g))
        row.append(InlineKeyboardButton(f"{g} ({count})", callback_data=f"pgg_{pl_idx}_{gi}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="pl_back")])

    await query.message.edit_text(
        f"📂 **{pl['name']}** — Select a group:\n"
        f"📺 Total `{len(channels)}` channels in `{len(groups)}` groups",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(r"^pgg_(\d+)_(\d+)$"))
async def cb_group_channels(client: Client, query):
    user_id   = query.from_user.id
    pl_idx    = int(query.matches[0].group(1))
    grp_idx   = int(query.matches[0].group(2))
    playlists = playlist_manager.get_playlists(user_id)

    if pl_idx >= len(playlists):
        return await query.answer("Playlist not found!", show_alert=True)

    channels = playlist_manager.cache_get(user_id, pl_idx)
    if not channels:
        ok, err, channels = await playlist_manager.fetch_and_parse(playlists[pl_idx]["url"])
        if not ok:
            return await query.answer("Failed to load playlist.", show_alert=True)
        playlist_manager.cache_set(user_id, pl_idx, channels)

    groups = playlist_manager.get_groups(channels)
    if grp_idx >= len(groups):
        return await query.answer("Group not found!", show_alert=True)

    group_name  = groups[grp_idx]
    chs         = playlist_manager.channels_in_group(channels, group_name)
    page_size   = 20
    total_pages = (len(chs) - 1) // page_size + 1

    await query.answer()
    buttons = []
    for ci, ch in enumerate(chs[:page_size]):
        buttons.append([InlineKeyboardButton(
            f"📡 {ch['name']}", callback_data=f"plc_{pl_idx}_{grp_idx}_{ci}"
        )])

    nav = []
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"▶ Next (1/{total_pages})", callback_data=f"pgp_{pl_idx}_{grp_idx}_1"))
    nav.append(InlineKeyboardButton("🔙 Back", callback_data=f"plg_{pl_idx}"))
    buttons.append(nav)

    await query.message.edit_text(
        f"📡 **{group_name}** — {len(chs)} channels\nTap a channel to record:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(r"^pgp_(\d+)_(\d+)_(\d+)$"))
async def cb_channels_page(client: Client, query):
    user_id   = query.from_user.id
    pl_idx    = int(query.matches[0].group(1))
    grp_idx   = int(query.matches[0].group(2))
    page      = int(query.matches[0].group(3))
    playlists = playlist_manager.get_playlists(user_id)

    channels = playlist_manager.cache_get(user_id, pl_idx)
    if not channels:
        ok, err, channels = await playlist_manager.fetch_and_parse(playlists[pl_idx]["url"])
        if not ok:
            return await query.answer("Failed to load playlist.", show_alert=True)
        playlist_manager.cache_set(user_id, pl_idx, channels)

    groups      = playlist_manager.get_groups(channels)
    group_name  = groups[grp_idx]
    chs         = playlist_manager.channels_in_group(channels, group_name)
    page_size   = 20
    total_pages = (len(chs) - 1) // page_size + 1
    page        = max(0, min(page, total_pages - 1))
    start       = page * page_size

    await query.answer()
    buttons = []
    for ci, ch in enumerate(chs[start:start + page_size]):
        real_idx = start + ci
        buttons.append([InlineKeyboardButton(
            f"📡 {ch['name']}", callback_data=f"plc_{pl_idx}_{grp_idx}_{real_idx}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"pgp_{pl_idx}_{grp_idx}_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶ Next", callback_data=f"pgp_{pl_idx}_{grp_idx}_{page + 1}"))
    nav.append(InlineKeyboardButton("🔙 Back", callback_data=f"plg_{pl_idx}"))
    buttons.append(nav)

    await query.message.edit_text(
        f"📡 **{group_name}** — Page {page + 1}/{total_pages}:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(r"^plc_(\d+)_(\d+)_(\d+)$"))
async def cb_channel_selected(client: Client, query):
    user_id   = query.from_user.id
    pl_idx    = int(query.matches[0].group(1))
    grp_idx   = int(query.matches[0].group(2))
    ch_idx    = int(query.matches[0].group(3))
    playlists = playlist_manager.get_playlists(user_id)

    channels = playlist_manager.cache_get(user_id, pl_idx)
    if not channels:
        ok, err, channels = await playlist_manager.fetch_and_parse(playlists[pl_idx]["url"])
        if not ok:
            return await query.answer("Failed to load playlist.", show_alert=True)
        playlist_manager.cache_set(user_id, pl_idx, channels)

    groups     = playlist_manager.get_groups(channels)
    group_name = groups[grp_idx]
    chs        = playlist_manager.channels_in_group(channels, group_name)

    if ch_idx >= len(chs):
        return await query.answer("Channel not found!", show_alert=True)

    ch         = chs[ch_idx]
    stream_url = ch["url"]
    safe_name  = ch["name"].replace("`", "'")[:40] or config.DEFAULT_FILENAME
    timestamp  = "01:00:00"

    await query.answer()

    if len(user_tasks.get(user_id, {})) >= MAX_CONCURRENT:
        return await query.message.reply_text(
            f"❌ **Maximum {MAX_CONCURRENT} simultaneous recordings reached!**\n"
            f"📊 /status  |  🛑 /cancel",
            reply_markup=build_main_keyboard(user_id)
        )

    await query.message.edit_text(
        f"📡 **{ch['name']}**\n"
        f"📂 Group: `{ch.get('group', 'General')}`\n\n"
        f"🔍 Stream detect ho rahi hai, please wait...",
        reply_markup=None
    )

    try:
        info = await detect_stream_info(stream_url)
    except Exception as e:
        LOG.error(f"playlist detect_stream_info error: {e}")
        return await query.message.edit_text(
            f"❌ **Stream detect failed!**\n\n`{e}`\n\n"
            "Channel URL check karein ya doosra channel try karein.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data=f"pgg_{pl_idx}_{grp_idx}")
            ]])
        )

    tracks   = info["tracks"]
    video    = info["video"]
    selected = set(tr["index"] for tr in tracks)

    user_setup[user_id] = {
        "mode":            "record",
        "step":            "audio" if tracks else "watermark",
        "url":             stream_url,
        "timestamp":       timestamp,
        "filename":        safe_name,
        "tracks":          tracks,
        "selected_tracks": selected,
        "watermark_pos":   None,
        "watermark_text":  config.DEFAULT_FILENAME,
        "auto_mode":       False,
        "video_size":      "original",
        "chat_id":         query.message.chat.id,
        "reply_to":        query.message.id,
        "video_info":      video,
    }

    quality_line = format_quality_line(video)
    audio_line   = ", ".join(tr["label"] for tr in tracks) if tracks else "Auto"

    if tracks:
        text = (
            f"✅ **Stream Ready!**\n\n"
            f"📡 **Channel:** `{ch['name']}`\n"
            f"📺 **Quality:** `{quality_line}`\n"
            f"🎵 **Audio:** `{audio_line}`\n"
            f"⏱ **Duration:** `{timestamp}`\n"
            f"📁 **File:** `{safe_name}`\n\n"
            f"👇 Select audio tracks to include:"
        )
        kb = build_audio_keyboard(tracks, selected, uid=user_id)
    else:
        text = (
            f"✅ **Stream Ready!**\n\n"
            f"📡 **Channel:** `{ch['name']}`\n"
            f"📺 **Quality:** `{quality_line}`\n"
            f"🎵 **Audio:** No tracks — auto-select\n\n"
        ) + setup_summary_text(user_setup[user_id])
        kb = build_watermark_keyboard(user_setup[user_id], uid=user_id)

    await query.message.reply_text(text, reply_markup=kb)


@app.on_callback_query(filters.regex(r"^pl_back$"))
async def cb_pl_back(client: Client, query):
    user_id   = query.from_user.id
    playlists = playlist_manager.get_playlists(user_id)
    await query.answer()

    if not playlists:
        return await query.message.edit_text("📭 No playlists saved.")

    buttons = [
        [InlineKeyboardButton(f"📋 {p['name']}", callback_data=f"plg_{i}")]
        for i, p in enumerate(playlists)
    ]
    await query.message.edit_text(
        "📺 **Select a Playlist:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ═════════════════════════════════════════════════════════════════════════════
#  ROUTER — text_router + all step handlers
# ═════════════════════════════════════════════════════════════════════════════

_COMMANDS = [
    "start", "alive", "help", "status", "cancel", "rec", "download",
    "ott_download", "compress", "screenshot",
    "cookies_add", "cookies_status", "del_cookies",
    "schedule", "schedules", "cancel_schedule",
    "verify", "history", "recording_old", "Hindi_or_English",
    "Playlist_add", "playlistadd",
    "Playlist_delete", "playlistdelete",
    "Channel_activate", "channel",
    "setlimit", "grant_access",
]


@app.on_message(filters.text & allowed & ~filters.command(_COMMANDS))
async def text_router(client, message: Message):
    user_id = message.from_user.id
    raw     = message.text.strip()
    canon   = to_canonical(raw)
    setup   = user_setup.get(user_id, {})
    step    = setup.get("step", "")

    if canon == t(None, "btn_help"):
        return await help_cmd(client, message)

    if canon == t(None, "btn_status"):
        return await status_cmd(client, message)

    hint_map = {
        t(None, "btn_record"):     t(user_id, "hint_record"),
        t(None, "btn_download"):   t(user_id, "hint_download"),
        t(None, "btn_ott"):        t(user_id, "hint_ott"),
        t(None, "btn_compress"):   t(user_id, "hint_compress"),
        t(None, "btn_screenshot"): t(user_id, "hint_screenshot"),
        t(None, "btn_cookies"):    t(user_id, "hint_cookies"),
    }
    if canon in hint_map:
        return await message.reply_text(
            hint_map[canon], reply_markup=build_main_keyboard(user_id)
        )

    if step == "audio":
        return await _handle_audio(client, message, raw, canon, setup, user_id)

    if step == "watermark":
        return await _handle_watermark(client, message, raw, canon, setup, user_id)

    if step == "wm_text_input":
        setup["watermark_text"] = raw
        setup["step"] = "watermark"
        return await message.reply_text(
            f"✅ **Watermark text set to:** `{raw}`\n\n" + setup_summary_text(setup),
            reply_markup=build_watermark_keyboard(setup, uid=user_id)
        )

    if step == "size":
        return await _handle_size(client, message, raw, canon, setup, user_id)

    if step == "cancel":
        return await _handle_cancel(client, message, canon, user_id)

    if step == "compress":
        return await _handle_compress(client, message, canon, setup, user_id)

    if step == "ott_resolution":
        return await _handle_ott_resolution(client, message, raw, setup, user_id)

    if step == "ott_audio":
        return await _handle_ott_audio(client, message, raw, canon, setup, user_id)


async def _handle_audio(client, message: Message, raw: str, canon: str,
                        setup: dict, user_id: int):
    tracks        = setup.get("tracks", [])
    selected: set = setup.get("selected_tracks", set())

    clean_raw = raw.lstrip("✅❌ ").strip()
    matched   = next((tr for tr in tracks if tr["label"] == clean_raw), None)

    if matched:
        idx = matched["index"]
        selected.discard(idx) if idx in selected else selected.add(idx)
        setup["selected_tracks"] = selected
        sel_count = len(selected)
        return await message.reply_text(
            f"🎵 **Audio Tracks** — {sel_count}/{len(tracks)} selected\n"
            f"Selected: `{', '.join(tr['label'] for tr in tracks if tr['index'] in selected) or 'None'}`",
            reply_markup=build_audio_keyboard(tracks, selected, uid=user_id)
        )

    btn_select_all_en = t(None, "btn_select_all")
    btn_back_en       = t(None, "btn_back")
    btn_next_wm_en    = t(None, "btn_next_wm")
    btn_cancel_en     = t(None, "btn_cancel_setup")

    if canon == btn_select_all_en:
        setup["selected_tracks"] = (
            set() if len(selected) == len(tracks)
            else set(tr["index"] for tr in tracks)
        )
        label = "all deselected" if not setup["selected_tracks"] else "all selected"
        return await message.reply_text(
            f"🔁 Tracks {label}.",
            reply_markup=build_audio_keyboard(tracks, setup["selected_tracks"], uid=user_id)
        )

    if canon == btn_back_en:
        user_setup.pop(user_id, None)
        return await message.reply_text(
            t(user_id, "msg_setup_cancelled"),
            reply_markup=build_main_keyboard(user_id)
        )

    if canon == btn_next_wm_en:
        setup["step"] = "watermark"
        return await message.reply_text(
            setup_summary_text(setup),
            reply_markup=build_watermark_keyboard(setup, uid=user_id)
        )

    if canon == btn_cancel_en:
        user_setup.pop(user_id, None)
        return await message.reply_text(
            t(user_id, "msg_setup_cancelled"),
            reply_markup=build_main_keyboard(user_id)
        )


async def _handle_watermark(client, message: Message, raw: str, canon: str,
                             setup: dict, user_id: int):
    clean_canon = canon.lstrip("✅ ").strip()
    clean_raw   = raw.lstrip("✅ ").strip()

    if clean_canon in WM_LABEL_BILINGUAL or clean_raw in WM_LABEL_BILINGUAL:
        pos_key = WM_LABEL_BILINGUAL.get(clean_canon) or WM_LABEL_BILINGUAL.get(clean_raw)
        setup["watermark_pos"] = pos_key
        return await message.reply_text(
            f"✅ **Watermark set!**\n\n" + setup_summary_text(setup),
            reply_markup=build_watermark_keyboard(setup, uid=user_id)
        )

    wm_off_en   = t(None, "btn_wm_off")
    wm_text_en  = t(None, "btn_wm_text")
    auto_en     = t(None, "btn_auto_mode")
    next_sz_en  = t(None, "btn_next_size")
    start_dl_en = t(None, "btn_start_dl")
    cancel_en   = t(None, "btn_cancel")

    if wm_off_en in canon or "Watermark OFF" in canon or "वॉटरमार्क बंद" in raw:
        setup["watermark_pos"] = None
        return await message.reply_text(
            "🚫 **Watermark disabled.**\n\n" + setup_summary_text(setup),
            reply_markup=build_watermark_keyboard(setup, uid=user_id)
        )

    if canon == wm_text_en:
        setup["step"] = "wm_text_input"
        return await message.reply_text(
            t(user_id, "msg_wm_text_prompt"),
            reply_markup=ReplyKeyboardRemove()
        )

    if "Auto: First+Last" in canon or "ऑटो" in raw:
        setup["auto_mode"] = not setup.get("auto_mode", False)
        s = "✅ ON" if setup["auto_mode"] else "❌ OFF"
        return await message.reply_text(
            f"⏱️ **Auto Mode:** {s}\n\n" + setup_summary_text(setup),
            reply_markup=build_watermark_keyboard(setup, uid=user_id)
        )

    if canon == next_sz_en:
        setup["step"] = "size"
        return await message.reply_text(
            "📐 **Select Video Size:**",
            reply_markup=build_size_keyboard(setup.get("video_size", "original"), uid=user_id)
        )

    if canon == start_dl_en:
        setup["step"] = "running"
        await message.reply_text(
            "📥 **Starting download...**",
            reply_markup=build_main_keyboard(user_id)
        )
        s = user_setup.pop(user_id)
        asyncio.create_task(handle_record(client, message, s, user_id))
        return

    if canon == cancel_en:
        user_setup.pop(user_id, None)
        return await message.reply_text(
            t(user_id, "msg_setup_cancelled"),
            reply_markup=build_main_keyboard(user_id)
        )


async def _handle_size(client, message: Message, raw: str, canon: str,
                       setup: dict, user_id: int):
    clean = canon.lstrip("✅ ").strip()

    if clean in SIZE_LABEL_TO_KEY:
        setup["video_size"] = SIZE_LABEL_TO_KEY[clean]
        return await message.reply_text(
            f"✅ **Size selected:** {clean}\n\n" + setup_summary_text(setup),
            reply_markup=build_size_keyboard(setup["video_size"], uid=user_id)
        )

    back_wm_en  = t(None, "btn_back_wm")
    start_rec_en= t(None, "btn_start_rec")
    cancel_en   = t(None, "btn_cancel")

    if canon == back_wm_en:
        setup["step"] = "watermark"
        return await message.reply_text(
            setup_summary_text(setup),
            reply_markup=build_watermark_keyboard(setup, uid=user_id)
        )

    if canon == start_rec_en:
        is_unlimited = user_id in config.OWNER_ID or user_id in config.AUTH_USERS
        ok, use_msg  = limit_system.use_rec(user_id, unlimited=is_unlimited)
        if not ok:
            user_setup.pop(user_id, None)
            return await message.reply_text(
                f"❌ **Rec Limit Khatam!**\n\n{use_msg}\n\n"
                "📊 /limit — apni limit dekhen\n"
                "🔐 /verify — aur Rec unlock karein",
                reply_markup=build_main_keyboard(user_id)
            )
        setup["step"] = "running"
        await message.reply_text(
            "🎬 **Starting recording...**",
            reply_markup=build_main_keyboard(user_id)
        )
        s = user_setup.pop(user_id)
        asyncio.create_task(handle_record(client, message, s, user_id))
        return

    if canon == cancel_en:
        user_setup.pop(user_id, None)
        return await message.reply_text(
            t(user_id, "msg_setup_cancelled"),
            reply_markup=build_main_keyboard(user_id)
        )


async def _handle_cancel(client, message: Message, canon: str, user_id: int):
    cancel_all_en = t(None, "btn_cancel_all")
    close_en      = t(None, "btn_close_menu")

    if canon == cancel_all_en:
        jobs = list(user_tasks.get(user_id, {}).keys())
        for job_id in jobs:
            await do_cancel_job(user_id, job_id, message)
        user_setup.pop(user_id, None)
        return await message.reply_text(
            t(user_id, "msg_all_cancelled"),
            reply_markup=build_main_keyboard(user_id)
        )

    if canon == close_en:
        user_setup.pop(user_id, None)
        return await message.reply_text(
            t(user_id, "msg_menu_closed"),
            reply_markup=build_main_keyboard(user_id)
        )

    for job_id, info in list(user_status.get(user_id, {}).items()):
        n = slot_number(job_id)
        if f"Cancel Slot {n}:" in canon:
            await do_cancel_job(user_id, job_id, message)
            user_setup.pop(user_id, None)
            return await message.reply_text(
                f"✅ Slot {n} cancelled.",
                reply_markup=build_main_keyboard(user_id)
            )

    await message.reply_text(
        "❓ Unknown option.",
        reply_markup=build_cancel_keyboard(user_id, uid=user_id)
    )


async def _handle_compress(client, message: Message, canon: str, setup: dict, user_id: int):
    await run_compress(client, message, user_id, canon)


async def _handle_ott_resolution(client, message: Message, raw: str,
                                  setup: dict, user_id: int):
    canon     = to_canonical(raw)
    cancel_en = t(None, "btn_ott_cancel")

    if canon == cancel_en:
        user_setup.pop(user_id, None)
        return await message.reply_text(
            "❌ OTT download cancelled.",
            reply_markup=build_main_keyboard(user_id)
        )

    res_map   = setup.get("detected_res_map",   OTT_RES_LABEL_TO_FMT)
    audio_map = setup.get("detected_audio_map", OTT_AUDIO_LANGS)

    clean = raw.lstrip("✅ ").strip()
    if clean in res_map:
        setup["ott_res_label"] = clean
        setup["ott_format"]    = res_map[clean]
        setup["step"]          = "ott_audio"
        return await message.reply_text(
            f"✅ **Resolution:** `{clean}`\n\n🎧 Now select audio language:",
            reply_markup=build_ott_audio_keyboard_dynamic(
                audio_map, setup.get("ott_audio_label", ""), uid=user_id
            )
        )

    await message.reply_text(
        "❓ Please pick a resolution.",
        reply_markup=build_ott_resolution_keyboard_dynamic(
            res_map, setup.get("ott_res_label", ""), uid=user_id
        )
    )


async def _handle_ott_audio(client, message: Message, raw: str, canon: str,
                             setup: dict, user_id: int):
    res_map   = setup.get("detected_res_map",   OTT_RES_LABEL_TO_FMT)
    audio_map = setup.get("detected_audio_map", OTT_AUDIO_LANGS)

    cancel_en  = t(None, "btn_ott_cancel")
    back_res_en= t(None, "btn_back_res")

    if canon == cancel_en:
        user_setup.pop(user_id, None)
        return await message.reply_text(
            "❌ OTT download cancelled.",
            reply_markup=build_main_keyboard(user_id)
        )

    if canon == back_res_en:
        setup["step"] = "ott_resolution"
        return await message.reply_text(
            "📺 Select resolution:",
            reply_markup=build_ott_resolution_keyboard_dynamic(
                res_map, setup.get("ott_res_label", ""), uid=user_id
            )
        )

    clean = raw.lstrip("✅ ").strip()
    if clean in audio_map:
        setup["ott_audio_label"] = clean
        setup["ott_audio_lang"]  = audio_map[clean]
        setup["step"] = "running"

        title_line = f"📌 `{setup['detected_title'][:50]}`\n" if setup.get("detected_title") else ""
        dur_line   = f"⏱ `{TimeFormatter(setup['detected_duration'] * 1000)}`\n" if setup.get("detected_duration") else ""

        await message.reply_text(
            f"✅ **Setup Complete!**\n\n"
            f"{title_line}{dur_line}"
            f"📺 **Resolution:** `{setup.get('ott_res_label', 'Best')}`\n"
            f"🎧 **Audio:** `{clean}`\n"
            f"📁 **File:** `{setup['filename']}`\n\n"
            f"📥 Starting download...",
            reply_markup=build_main_keyboard(user_id)
        )
        s = user_setup.pop(user_id)
        asyncio.create_task(ott_download_task(client, message, s, user_id))
        return

    await message.reply_text(
        "❓ Please pick an audio language.",
        reply_markup=build_ott_audio_keyboard_dynamic(
            audio_map, setup.get("ott_audio_label", ""), uid=user_id
        )
    )
