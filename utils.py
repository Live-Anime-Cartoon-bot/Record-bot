"""
OTT Recorder Bot — state, keyboards and utility functions.
Sections: STATE · KEYBOARDS · UTILS · MODULE-COMPAT · COOKIES-HELPERS
"""

import asyncio
import logging
import os
import shlex
import time
import types
from datetime import datetime
from os.path import join
from typing import Dict, List, Optional, Tuple

import pytz
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
from constants import *
from constants import _ls_load, _ts_to_secs  # private names not exported by *

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


def build_size_keyboard(selected: str = "original", uid=None, duration_s: int = 0) -> ReplyKeyboardMarkup:
    rows = []
    mins = duration_s / 60 if duration_s else 0
    for key, val in REC_QUALITY_PRESETS.items():
        check = "✅ " if selected == key else ""
        if mins > 0 and val["mb_per_min"]:
            est_mb = val["mb_per_min"] * mins
            size_hint = f"  (~{est_mb:.0f} MB)"
        else:
            size_hint = ""
        rows.append([KeyboardButton(f"{check}{val['label']}{size_hint}")])
    rows.append([KeyboardButton(t(uid, "btn_back_wm"))])
    rows.append([KeyboardButton(t(uid, "btn_next_aspect")), KeyboardButton(t(uid, "btn_cancel"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_aspect_keyboard(selected: str = "none", uid=None) -> ReplyKeyboardMarkup:
    rows = []
    for key, val in ASPECT_RATIO_PRESETS.items():
        check = "✅ " if selected == key else ""
        rows.append([KeyboardButton(f"{check}{val['label']}")])
    rows.append([KeyboardButton(t(uid, "btn_back_size"))])
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
    # Always show Default Audio first
    default_lbl = "🎯 Default Audio"
    check_def = "✅ " if selected == default_lbl else ""
    rows.append([KeyboardButton(f"{check_def}{default_lbl}")])
    for lbl in audio_map:
        check = "✅ " if selected == lbl else ""
        rows.append([KeyboardButton(f"{check}{lbl}")])
    rows.append([KeyboardButton(t(uid, "btn_back_res"))])
    rows.append([KeyboardButton(t(uid, "btn_ott_cancel"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_ott_compress_keyboard(uid=None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("❌ No Compress"), KeyboardButton("~50 MB"), KeyboardButton("~100 MB")],
            [KeyboardButton("~200 MB"), KeyboardButton("~300 MB"), KeyboardButton("~500 MB")],
            [KeyboardButton("~600 MB"), KeyboardButton("~700 MB"), KeyboardButton("~900 MB")],
            [KeyboardButton(t(uid, "btn_ott_cancel"))],
        ],
        resize_keyboard=True,
    )


def setup_summary_text(setup: dict) -> str:
    tracks   = setup.get("tracks", [])
    selected = setup.get("selected_tracks", set())

    # Show "All" when nothing is manually picked OR when every track is selected
    all_indices = {tr["index"] for tr in tracks}
    if not selected or selected >= all_indices:
        audio_label = "All"
    else:
        sel_labels  = [tr["label"] for tr in tracks if tr["index"] in selected]
        audio_label = ", ".join(sel_labels) if sel_labels else "All"

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
    size_key   = setup.get("video_size", "original")
    size_lbl   = REC_QUALITY_PRESETS.get(size_key, REC_QUALITY_PRESETS["original"])["label"]
    asp_key    = setup.get("aspect_ratio", "none")
    asp_lbl    = ASPECT_RATIO_PRESETS.get(asp_key, ASPECT_RATIO_PRESETS["none"])["label"]

    if mode == "download":
        header        = "📥 **Download Setup**"
        duration_line = ""
    else:
        header        = "🎛️ **Recording Setup**"
        duration_line = f"⏱ **Duration:** `{setup.get('timestamp', '—')}`\n"
        duration_line += f"⏩ **Auto Mode:** `{'✅ First+Last 1min' if auto else '❌ Off'}`\n"

    return (
        f"{header}\n\n"
        f"{duration_line}"
        f"📁 **Filename:** `{setup['filename']}`\n"
        f"🎵 **Audio:** `{audio_label}`\n"
        f"🖼 **Watermark:** `{wm_desc}`\n"
        f"📐 **Size:** `{size_lbl}`\n"
        f"🎞 **Aspect:** `{asp_lbl}`\n\n"
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


def _friendly_stream_error(exc_or_str) -> str:
    """Turn a raw ffprobe/exception message into a clean, readable reason."""
    raw = str(exc_or_str).strip()
    # aiohttp / ffprobe errors often start with ": " — strip it
    raw = raw.lstrip(":").strip()
    lower = raw.lower()
    if "404" in raw or "not found" in lower:
        return "URL not found (404) — stream may be offline or the link is wrong."
    if "403" in raw or "forbidden" in lower:
        return "Access denied (403) — stream may be geo-blocked or requires a subscription."
    if "401" in raw or "unauthorized" in lower:
        return "Unauthorized (401) — stream requires login or a valid token."
    if "timed out" in lower or "timeout" in lower:
        return "Connection timed out — stream may be offline or too slow."
    if "connection refused" in lower or "refused" in lower:
        return "Connection refused — server is unreachable."
    if "ssl" in lower or "certificate" in lower:
        return "SSL/certificate error — stream server has an invalid certificate."
    if "no route to host" in lower or "network" in lower:
        return "Network error — check your internet connection."
    if raw:
        return raw
    return "Unknown error — stream may be offline or the URL is invalid."


async def detect_stream_info(url: str) -> dict:
    cmd = (
        f'ffprobe -v error -timeout 15000000 {http_opts(url)} -print_format json '
        f'-show_streams "{url}"'
    )
    retcode, out, err = await runcmd(cmd, timeout=25)
    result = {"video": None, "tracks": []}
    if retcode != 0 or not out.strip():
        # Build a meaningful error from stderr
        err_clean = err.strip().lstrip(":").strip() if err else ""
        reason    = _friendly_stream_error(err_clean) if err_clean else "ffprobe exited with no output."
        raise RuntimeError(reason)
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


