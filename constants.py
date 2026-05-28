"""
OTT Recorder Bot — constants, subsystems and pure helpers.
Sections: CONSTANTS · VERIFY · LANG · LIMIT SYSTEM · SHORTENER · PLAYLIST MANAGER
"""

import asyncio
import json
import os
import re
import random
import secrets
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
import requests as _req_lib

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

# ── Recording quality presets (replaces VIDEO_SIZES in rec setup) ─────────────
REC_QUALITY_PRESETS: Dict[str, dict] = {
    "480p":     {"label": "📺 480p",     "vf": "scale=-2:480",  "mb_per_min": 5.8},
    "576p":     {"label": "📺 576p",     "vf": "scale=-2:576",  "mb_per_min": 6.3},
    "640p":     {"label": "📺 640p",     "vf": "scale=-2:640",  "mb_per_min": 9.8},
    "720p":     {"label": "📺 720p",     "vf": "scale=-2:720",  "mb_per_min": 13.0},
    "1080p":    {"label": "🔵 1080p",    "vf": "scale=-2:1080", "mb_per_min": 17.0},
    "original": {"label": "🔓 Original", "vf": None,            "mb_per_min": None},
}
REC_QUALITY_LABEL_TO_KEY: Dict[str, str] = {v["label"]: k for k, v in REC_QUALITY_PRESETS.items()}

# ── Aspect Ratio presets (applied after quality/size vf) ─────────────────────
ASPECT_RATIO_PRESETS: Dict[str, dict] = {
    "none":           {"label": "🔓 None (Keep as-is)",  "vf": None},
    "21_9":           {"label": "🎬 21:9 Aspect",         "vf": "crop=ih*21/9:ih,scale=1280:549"},
    "16_9":           {"label": "📺 16:9 Aspect",         "vf": "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"},
    "4_5":            {"label": "📱 4:5 Aspect",          "vf": "scale=720:900:force_original_aspect_ratio=decrease,pad=720:900:(ow-iw)/2:(oh-ih)/2"},
    "16_9_bars":      {"label": "◼ 16:9 Black Bars",      "vf": "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"},
    "16_9_zoom":      {"label": "🔍 16:9 Zoom",           "vf": "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720"},
    "scale_1280_720": {"label": "📐 scale=1280:720",      "vf": "scale=1280:720"},
}
ASPECT_LABEL_TO_KEY: Dict[str, str] = {v["label"]: k for k, v in ASPECT_RATIO_PRESETS.items()}


def _ts_to_secs(ts: str) -> int:
    """HH:MM:SS → total seconds, returns 0 on failure."""
    try:
        parts = ts.strip().split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0
    except Exception:
        return 0

SLOT_EMOJI = ["1️⃣", "2️⃣", "3️⃣"]

COMPRESS_PRESETS: Dict[str, tuple] = {
    "🔵 High Quality":   ("-c:v libx264 -crf 23 -preset fast -c:a aac -b:a 128k", "High (good quality, moderate size)"),
    "🟡 Medium Quality": ("-c:v libx264 -crf 28 -preset fast -c:a aac -b:a 96k",  "Medium (balanced)"),
    "🔴 Low (Smallest)": ("-c:v libx264 -crf 32 -preset fast -c:a aac -b:a 64k",  "Low (small size, lower quality)"),
}

OTT_RES_LABEL_TO_FMT: Dict[str, str] = {}

OTT_AUDIO_LANGS: Dict[str, Optional[str]] = {"🌐 Multi": None}

OTT_COMPRESS_SIZES: Dict[str, int] = {
    "❌ No Compress": 0,
    "~50 MB":  50,
    "~100 MB": 100,
    "~200 MB": 200,
    "~300 MB": 300,
    "~500 MB": 500,
    "~600 MB": 600,
    "~700 MB": 700,
    "~900 MB": 900,
}

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
    "btn_next_aspect":  {"en": "📐 Next: Aspect Ratio →", "hi": "📐 आगे: आस्पेक्ट रेशियो →"},
    "btn_back_size":    {"en": "◀️ Quality/Size",        "hi": "◀️ क्वालिटी/साइज़"},
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

PLAYLIST_FILE = os.path.join(os.path.dirname(__file__), "user_playlists.json")

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


