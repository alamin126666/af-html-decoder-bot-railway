#!/usr/bin/env python3
import asyncio, base64, json, os, re, pickle, logging, tempfile, shutil
from datetime import datetime
from threading import Thread
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from telegram import Update, InlineKeyboardButton as _TelegramInlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.error import RetryAfter, BadRequest
from playwright.async_api import async_playwright

BOT_TOKEN      = os.environ.get("BOT_TOKEN", "")
OWNER_ID       = int(os.environ.get("OWNER_ID", "0"))
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "BDALAMINHACKER")
DB_FILE        = "database.pkl"
if not BOT_TOKEN: raise ValueError("BOT_TOKEN not set.")
if not OWNER_ID:  raise ValueError("OWNER_ID not set.")

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot API 9.4 button accents are presets, not arbitrary hex colors.
# Premium custom emoji IDs are optional and are supplied by the bot owner.
_BUTTON_STYLES = {"primary", "success", "danger"}
_EMOJI_ID_DEFAULTS = {
    "BUTTON_EMOJI_DECODE": "6057408307029613998",
    "BUTTON_EMOJI_DEVELOPER": "5418063924933173277",
    "BUTTON_EMOJI_CHANNEL": "5413337163100083587",
    "BUTTON_EMOJI_PRIVATE_CHANNEL": "5197288647275071607",
    "BUTTON_EMOJI_JOINED": "6226699395098745883",
    "BUTTON_EMOJI_CONTACT": "4956475826762679249",
    "PREMIUM_EMOJI_LIGHTNING_ID": "6057408307029613998",
    "PREMIUM_EMOJI_BRAND_ID": "5212936673423274058",
    "PREMIUM_EMOJI_DEVELOPER_ID": "5418063924933173277",
    "PREMIUM_EMOJI_RADAR_ID": "5413337163100083587",
    "PREMIUM_EMOJI_LOCK_ID": "5197288647275071607",
    "PREMIUM_EMOJI_CHECK_ID": "6226699395098745883",
    "PREMIUM_EMOJI_UNLOCK_ID": "5291873529464122510",
    "PREMIUM_EMOJI_SAMRAT_ID": "6233454545431697495",
    "PREMIUM_EMOJI_BASE777_ID": "6115956897481758272",
    "PREMIUM_EMOJI_TMS_DECODE_ID": "5354889508674360491",
    "PREMIUM_EMOJI_TMS_SAVE_ID": "5278306981906493285",
    "PREMIUM_EMOJI_SEARCH_ID": "5188311512791393083",
    "PREMIUM_EMOJI_RDX_SEARCH_ID": "6332075107741075109",
    "PREMIUM_EMOJI_KEY_ID": "5278573677900752088",
    "PREMIUM_EMOJI_SAVE_ID": "5373342633798167891",
    "PREMIUM_EMOJI_SERVER_ID": "4956324463525233747",
    "PREMIUM_EMOJI_CAMERA_ID": "5260623291583831521",
    "PREMIUM_EMOJI_IMAGE_ID": "6082610788575485716",
    "PREMIUM_EMOJI_ATTACHMENT_ID": "5377844313575150051",
    "PREMIUM_EMOJI_GEAR_ID": "5341715473882955310",
    "PREMIUM_EMOJI_STATS_ID": "6226505614764285291",
    "PREMIUM_EMOJI_USERS_ID": "5453957997418004470",
    "PREMIUM_EMOJI_ALIEN_ID": "5370869711888194012",
    "PREMIUM_EMOJI_FOLDER_ID": "5431736674147114227",
    "PREMIUM_EMOJI_CLIPBOARD_ID": "5197269100878907942",
    "PREMIUM_EMOJI_DIAMOND_ID": "5314382594068984646",
    "PREMIUM_EMOJI_WARNING_ID": "6100210821525150079",
    "PREMIUM_EMOJI_CHECKMARK_ID": "6226569455158172824",
    "PREMIUM_EMOJI_CROSS_ID": "6294194896349699910",
    "PREMIUM_EMOJI_ADD_ID": "4956507094124594921",
    "PREMIUM_EMOJI_TARGET_ID": "5310278924616356636",
    "PREMIUM_EMOJI_TAG_ID": "5240228673738527951",
    "PREMIUM_EMOJI_CROWN_ID": "4958725487682650920",
    "PREMIUM_EMOJI_BULB_ID": "6100202351849642503",
    "PREMIUM_EMOJI_SPEECH_ID": "4956475826762679249",
    "PREMIUM_EMOJI_COMPUTER_ID": "5193177581888755275",
    "PREMIUM_EMOJI_PIN_ID": "6226705193304595830",
    "PREMIUM_EMOJI_ANNOUNCEMENT_ID": "6068999367199561082",
    "PREMIUM_EMOJI_BACK_ID": "6114123268568914133",
    "PREMIUM_EMOJI_RED_CIRCLE_ID": "6069113458710811277",
    "PREMIUM_EMOJI_BLUE_DIAMOND_ID": "5456145097844340698",
    "PREMIUM_EMOJI_ORANGE_DIAMOND_ID": "5206676058509696004",
    "PREMIUM_EMOJI_BLUE_SQUARE_ID": "6320953010755214903",
    "PREMIUM_EMOJI_DOWN_TRIANGLE_ID": "5017305457165861770",
    "PREMIUM_EMOJI_BLACK_HEART_ID": "6160962640005831966",
    "PREMIUM_EMOJI_CABINET_ID": "5262529363710060188",
    "PREMIUM_EMOJI_TRASH_ID": "4958534924278694938",
    "PREMIUM_EMOJI_ROBOT_ID": "5372981976804366741",
    "PREMIUM_EMOJI_TEST_TUBE_ID": "4956561910792192697",
    "PREMIUM_EMOJI_ID_BADGE_ID": "5260561650213220533",
    "PREMIUM_EMOJI_NO_ENTRY_ID": "5424857974784925603",
    "PREMIUM_EMOJI_TOOLS_ID": "5863945989127148135",
    "PREMIUM_EMOJI_SHIELD_ID": "4958900559139570572",
    "PREMIUM_EMOJI_SATELLITE_ID": "5467403607286502523",
    "PREMIUM_EMOJI_GREEN_CIRCLE_ID": "5267231042934154418",
    "PREMIUM_EMOJI_NEW_ID": "6255963343748601579",
}

_PREMIUM_EMOJI_SETTINGS = {
    "🧑‍💻": "PREMIUM_EMOJI_DEVELOPER_ID", "🧬": "PREMIUM_EMOJI_BRAND_ID",
    "⚡": "PREMIUM_EMOJI_LIGHTNING_ID", "📡": "PREMIUM_EMOJI_RADAR_ID",
    "🔐": "PREMIUM_EMOJI_LOCK_ID", "✅": "PREMIUM_EMOJI_CHECK_ID",
    "🔓": "PREMIUM_EMOJI_UNLOCK_ID", "🔎": "PREMIUM_EMOJI_SEARCH_ID",
    "🔍": "PREMIUM_EMOJI_RDX_SEARCH_ID", "🔑": "PREMIUM_EMOJI_KEY_ID",
    "💾": "PREMIUM_EMOJI_SAVE_ID", "🖥️": "PREMIUM_EMOJI_SERVER_ID",
    "📸": "PREMIUM_EMOJI_CAMERA_ID", "🖼️": "PREMIUM_EMOJI_IMAGE_ID",
    "📎": "PREMIUM_EMOJI_ATTACHMENT_ID", "⚙️": "PREMIUM_EMOJI_GEAR_ID",
    "📊": "PREMIUM_EMOJI_STATS_ID", "👥": "PREMIUM_EMOJI_USERS_ID",
    "👾": "PREMIUM_EMOJI_ALIEN_ID", "🗂": "PREMIUM_EMOJI_FOLDER_ID",
    "📋": "PREMIUM_EMOJI_CLIPBOARD_ID",
    "♦": "PREMIUM_EMOJI_DIAMOND_ID", "⚠️": "PREMIUM_EMOJI_WARNING_ID",
    "✔": "PREMIUM_EMOJI_CHECKMARK_ID", "❌": "PREMIUM_EMOJI_CROSS_ID",
    "➕": "PREMIUM_EMOJI_ADD_ID", "🎯": "PREMIUM_EMOJI_TARGET_ID",
    "🏷": "PREMIUM_EMOJI_TAG_ID", "👑": "PREMIUM_EMOJI_CROWN_ID",
    "💡": "PREMIUM_EMOJI_BULB_ID", "💬": "PREMIUM_EMOJI_SPEECH_ID",
    "💻": "PREMIUM_EMOJI_COMPUTER_ID", "📌": "PREMIUM_EMOJI_PIN_ID",
    "📣": "PREMIUM_EMOJI_ANNOUNCEMENT_ID", "🔙": "PREMIUM_EMOJI_BACK_ID",
    "🔴": "PREMIUM_EMOJI_RED_CIRCLE_ID", "🔷": "PREMIUM_EMOJI_BLUE_DIAMOND_ID",
    "🔸": "PREMIUM_EMOJI_ORANGE_DIAMOND_ID", "🔹": "PREMIUM_EMOJI_BLUE_SQUARE_ID",
    "🔻": "PREMIUM_EMOJI_DOWN_TRIANGLE_ID", "🖤": "PREMIUM_EMOJI_BLACK_HEART_ID",
    "🗄": "PREMIUM_EMOJI_CABINET_ID", "🗑": "PREMIUM_EMOJI_TRASH_ID",
    "🤖": "PREMIUM_EMOJI_ROBOT_ID", "🧪": "PREMIUM_EMOJI_TEST_TUBE_ID",
    "🪪": "PREMIUM_EMOJI_ID_BADGE_ID", "🚷": "PREMIUM_EMOJI_NO_ENTRY_ID",
    "🛠": "PREMIUM_EMOJI_TOOLS_ID", "🛡": "PREMIUM_EMOJI_SHIELD_ID",
    "🛰": "PREMIUM_EMOJI_SATELLITE_ID", "🟢": "PREMIUM_EMOJI_GREEN_CIRCLE_ID",
    "🆕": "PREMIUM_EMOJI_NEW_ID", "🧑‍💻": "PREMIUM_EMOJI_DEVELOPER_ID",
}

def _button_style(setting, fallback="primary"):
    value = os.environ.get(setting, fallback).strip().lower()
    return value if value in _BUTTON_STYLES else fallback

def _button_emoji(setting):
    value = os.environ.get(setting, "").strip()
    if value.isdigit():
        return value
    return _EMOJI_ID_DEFAULTS.get(setting)

def _menu_text(fallback_emoji, label, emoji_setting):
    # The Telegram button icon replaces the Unicode fallback when configured.
    return f"{label}" if _button_emoji(emoji_setting) else f"{fallback_emoji}  {label}"

def _premium_emoji(fallback_emoji, setting):
    emoji_id = _button_emoji(setting)
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback_emoji}</tg-emoji>' if emoji_id else fallback_emoji

def _premiumize_html(text):
    """Replace configured emoji in HTML message text, preserving existing tg-emoji tags."""
    parts = re.split(r'(<tg-emoji\b[^>]*>.*?</tg-emoji>)', str(text), flags=re.I | re.S)
    for index in range(0, len(parts), 2):
        for emoji, setting in sorted(_PREMIUM_EMOJI_SETTINGS.items(), key=lambda item: len(item[0]), reverse=True):
            emoji_id = _button_emoji(setting)
            if emoji_id:
                replacement = f'<tg-emoji emoji-id="{emoji_id}">{emoji}</tg-emoji>'
                if emoji == "💻":
                    parts[index] = re.sub(r'(?<!\u200d)💻', lambda _: replacement, parts[index])
                else:
                    parts[index] = parts[index].replace(emoji, replacement)
    return "".join(parts)

def InlineKeyboardButton(text, *args, **kwargs):
    """Attach a configured Premium emoji as the icon of inline buttons that start with one."""
    if "icon_custom_emoji_id" not in kwargs:
        for emoji, setting in sorted(_PREMIUM_EMOJI_SETTINGS.items(), key=lambda item: len(item[0]), reverse=True):
            if text.startswith(emoji) and (emoji_id := _button_emoji(setting)):
                text = text[len(emoji):].lstrip()
                kwargs["icon_custom_emoji_id"] = emoji_id
                break
    return _TelegramInlineKeyboardButton(text, *args, **kwargs)

async def _reply_html(message, text, **kwargs):
    return await message.reply_text(_premiumize_html(text), parse_mode=ParseMode.HTML, **kwargs)

async def _reply_text(message, text, **kwargs):
    updated = _premiumize_html(text)
    if updated != text:
        kwargs.setdefault("parse_mode", ParseMode.HTML)
    return await message.reply_text(updated, **kwargs)

def _menu_button(text, style_setting, emoji_setting, fallback_style="primary"):
    return KeyboardButton(
        text=text,
        style=_button_style(style_setting, fallback_style),
        icon_custom_emoji_id=_button_emoji(emoji_setting),
    )

# ══════════════════════════════════════════════════════
#   RATE-LIMIT-SAFE  editMessageText  WRAPPER
# ══════════════════════════════════════════════════════
async def safe_edit(msg, text, **kwargs):
    """Edit a message, honouring Telegram's 429 retry_after header.

    Telegram enforces ~1 editMessageText/second per chat.  When the bot
    sends animation frames faster than that it receives HTTP 429 with a
    Retry-After header.  python-telegram-bot raises RetryAfter; without
    this wrapper those errors are silently swallowed and the API keeps
    getting hammered, producing the flood of 429s visible in the logs.

    This wrapper sleeps for the server-mandated delay (plus a 0.5 s
    safety margin) and tries up to 3 times before giving up quietly.
    """
    updated = _premiumize_html(text)
    if updated != text:
        text = updated
        kwargs.setdefault("parse_mode", ParseMode.HTML)
    for attempt in range(3):
        try:
            await msg.edit_text(text, **kwargs)
            return
        except RetryAfter as e:
            wait = e.retry_after + 0.5
            logger.warning(f"Rate-limited (429) — sleeping {wait:.1f}s (attempt {attempt+1})")
            await asyncio.sleep(wait)
        except BadRequest:
            # "Message is not modified" or similar — not an error worth retrying
            return
        except Exception:
            return

flask_app = Flask(__name__)
@flask_app.route("/")
def home(): return "Bot is alive!"
def run_flask(): flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# ══════════════════════════════════════════════════════
#   DATABASE
# ══════════════════════════════════════════════════════
def _default_db():
    return {"users": {}, "admins": [], "channels": [],
            "settings": {"bot_active": True},
            "stats": {"total_decodes": 0, "phpkobo": 0, "custom": 0, "samrat_mc": 0, "base_777": 0, "tms_cyber": 0, "rdx": 0, "server": 0}}

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "rb") as f: data = pickle.load(f)
            for k, v in _default_db().items(): data.setdefault(k, v)
            for key, value in _default_db()["stats"].items():
                data["stats"].setdefault(key, value)
            return data
        except Exception as e: logger.error(f"DB load error: {e}")
    return _default_db()

def save_db(db):
    try:
        with open(DB_FILE, "wb") as f: pickle.dump(db, f)
    except Exception as e: logger.error(f"DB save error: {e}")

db = load_db()

def is_owner(uid): return uid == OWNER_ID
def is_admin(uid): return uid == OWNER_ID or uid in db["admins"]
def is_banned(uid): return db["users"].get(uid, {}).get("banned", False)
def bot_active(): return db["settings"].get("bot_active", True)

def register_user(user):
    if user.id not in db["users"]:
        db["users"][user.id] = {"username": user.username or "", "name": user.full_name or "",
                                "joined": datetime.now().isoformat(), "banned": False, "private_acked": []}
        save_db(db)
    elif "private_acked" not in db["users"][user.id]:
        db["users"][user.id]["private_acked"] = []; save_db(db)

async def check_channels(bot, uid):
    if not db["channels"]: return True, []
    acked = db["users"].get(uid, {}).get("private_acked", [])
    missing = []
    for ch in db["channels"]:
        try:
            m = await bot.get_chat_member(ch["id"], uid)
            if m.status in ("left", "kicked"): missing.append(ch)
        except Exception:
            if not (ch.get("type") == "private" and ch["id"] in acked): missing.append(ch)
    return len(missing) == 0, missing

# ══════════════════════════════════════════════════════
#   NODE.JS CHECK  (for RDX engine)
# ══════════════════════════════════════════════════════
def get_node_path():
    node = shutil.which("node") or shutil.which("nodejs")
    return node

def check_node_js():
    node = get_node_path()
    if node:
        logger.info(f"✔  Node.js found → {node}")
    else:
        logger.warning("⚠  Node.js NOT found — RDX engine will fall back to browser render.")
    return node

# ══════════════════════════════════════════════════════
#   KEYBOARDS
# ══════════════════════════════════════════════════════
def channels_inline_kb(missing):
    rows = []
    for ch in missing:
        is_private = ch.get("type") == "private"
        icon = "🔐" if is_private else "📡"
        emoji_id = _button_emoji("BUTTON_EMOJI_PRIVATE_CHANNEL" if is_private else "BUTTON_EMOJI_CHANNEL")
        label = ch.get("name", "Channel")
        if not emoji_id:
            label = f"{icon}  {label}"
        rows.append([InlineKeyboardButton(label, url=ch.get("link", ""), icon_custom_emoji_id=emoji_id)])
    return InlineKeyboardMarkup(rows)

def joined_reply_kb():
    return ReplyKeyboardMarkup(
        [[_menu_button(_menu_text("✅", "𝗜'𝘃𝗲 𝗝𝗼𝗶𝗻𝗲𝗱 𝗔𝗹𝗹 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀", "BUTTON_EMOJI_JOINED"), "BUTTON_STYLE_JOINED", "BUTTON_EMOJI_JOINED", "success")]],
        resize_keyboard=True, one_time_keyboard=True
    )

def main_kb():
    return ReplyKeyboardMarkup(
        [[_menu_button(_menu_text("⚡", "𝗛𝗧𝗠𝗟 𝗗𝗲𝗰𝗼𝗱𝗲𝗿", "BUTTON_EMOJI_DECODE"), "BUTTON_STYLE_DECODE", "BUTTON_EMOJI_DECODE", "primary"),
          _menu_button(_menu_text("🧑‍💻", "𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿", "BUTTON_EMOJI_DEVELOPER"), "BUTTON_STYLE_DEVELOPER", "BUTTON_EMOJI_DEVELOPER", "success")]],
        resize_keyboard=True,
    )

# ══════════════════════════════════════════════════════
#   WELCOME  — NEW DESIGN  (Auto-Detect Engines)
# ══════════════════════════════════════════════════════
async def send_welcome(bot, chat_id, first_name):
    txt = (
        "╔══════════════════════════════╗\n"
        f"  {_premium_emoji('🧬', 'PREMIUM_EMOJI_BRAND_ID')}  <b>𝗛𝗧𝗠𝗟  𝗗𝗘𝗖𝗢𝗗𝗘𝗥  𝗕𝗢𝗧</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"{_premium_emoji('👾', 'PREMIUM_EMOJI_ALIEN_ID')}  𝒲𝑒𝓁𝒸𝑜𝓂𝑒,  <b>{first_name}</b>!\n\n"
        "𝙸 𝚌𝚊𝚗 𝚒𝚗𝚜𝚝𝚊𝚗𝚝𝚕𝚢 𝚍𝚎𝚌𝚛𝚢𝚙𝚝 𝚊𝚗𝚢\n"
        "𝚎𝚗𝚌𝚛𝚢𝚙𝚝𝚎𝚍 <b>.html</b> 𝚏𝚒𝚕𝚎 𝚢𝚘𝚞 𝚜𝚎𝚗𝚍.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"〔 {_premium_emoji('⚙️', 'PREMIUM_EMOJI_GEAR_ID')}  <b>𝗗𝗲𝗰𝗿𝘆𝗽𝘁𝗶𝗼𝗻 𝗘𝗻𝗴𝗶𝗻𝗲𝘀</b> 〕\n\n"
        f"◈  {_premium_emoji('⚡', 'PREMIUM_EMOJI_LIGHTNING_ID')} <b>𝗽𝗵𝗽𝗸𝗼𝗯𝗼</b>   ╌  𝖺𝗎𝗍𝗈-𝖽𝖾𝗍𝖾𝖼𝗍\n"
        "◈  🧬 <b>𝗛𝗕 𝗘𝗡𝗖 𝗩𝟭</b>  ╌  𝖺𝗎𝗍𝗈-𝖽𝖾𝗍𝖾𝖼𝗍\n"
        "◈  🔐 <b>𝗦𝗔𝗠𝗥𝗔𝗧 𝗠𝗖</b>  ╌  𝖺𝗎𝗍𝗈-𝖽𝖾𝗍𝖾𝖼𝗍  🆕\n"
        f"◈  {_premium_emoji('🧱', 'PREMIUM_EMOJI_BASE777_ID')} <b>𝗕𝗔𝗦𝗘 𝟳𝟳𝟳</b>  ╌  𝖺𝗎𝗍𝗈-𝖽𝖾𝗍𝖾𝖼𝗍  🆕\n"
        f"◈  {_premium_emoji('🛡️', 'PREMIUM_EMOJI_TMS_DECODE_ID')} <b>𝗧𝗠𝗦 𝗖𝗬𝗕𝗘𝗥</b>  ╌  𝖺𝗎𝗍𝗈-𝖽𝖾𝗍𝖾𝖼𝗍  🆕\n"
        "◈  🔓 <b>𝗥𝗗𝗫 𝘃𝟳.𝟭</b>  ╌  𝖺𝗎𝗍𝗈-𝖽𝖾𝗍𝖾𝖼𝗍\n"
        f"◈  {_premium_emoji('🖥️', 'PREMIUM_EMOJI_SERVER_ID')} <b>𝗦𝗲𝗿𝘃𝗲𝗿</b>    ╌  𝚜𝚝𝚊𝚗𝚍𝚊𝚛𝚍 𝚎𝚗𝚌\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🔻  𝚄𝚜𝚎 𝚝𝚑𝚎 𝚖𝚎𝚗𝚞 𝚋𝚎𝚕𝚘𝚠 𝚝𝚘 𝚜𝚝𝚊𝚛𝚝 ↓"
    )
    await bot.send_message(chat_id, _premiumize_html(txt), parse_mode=ParseMode.HTML, reply_markup=main_kb())

def ban_text(uid):
    return (
        "╔══════════════════════╗\n"
        "  🚷  <b>𝗔𝗖𝗖𝗘𝗦𝗦  𝗗𝗘𝗡𝗜𝗘𝗗</b>\n"
        "╚══════════════════════╝\n\n"
        "𝚈𝚘𝚞 𝚑𝚊𝚟𝚎 𝚋𝚎𝚎𝚗 <b>𝗯𝗮𝗻𝗻𝗲𝗱</b> 𝚏𝚛𝚘𝚖 𝚝𝚑𝚒𝚜 𝚋𝚘𝚝.\n\n"
        f"🪪  <b>𝗬𝗼𝘂𝗿 𝗜𝗗</b>  ╌  <code>{uid}</code>\n"
        f"👑  <b>𝗢𝘄𝗻𝗲𝗿</b>   ╌  @{OWNER_USERNAME}\n\n"
        "𝙲𝚘𝚗𝚝𝚊𝚌𝚝 𝚝𝚑𝚎 𝙾𝚠𝚗𝚎𝚛 𝚠𝚒𝚝𝚑 𝚢𝚘𝚞𝚛 𝙸𝙳."
    )

# ══════════════════════════════════════════════════════
#   BROWSER RENDERER  (Server Engine)
# ══════════════════════════════════════════════════════
async def render_html(path):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page    = await context.new_page()
        await page.goto(f"file://{os.path.abspath(path)}", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        html       = await page.evaluate("() => document.documentElement.outerHTML")
        screenshot = await page.screenshot(full_page=True, type="png")
        await browser.close()
    return html, screenshot

async def take_screenshot(html_path):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context(viewport={"width": 1280, "height": 800})

        # A decoded file may still contain third-party scripts or an embedded
        # redirect.  Screenshots must render the decoded artifact only; they
        # must never turn a successful RDX decode into another server render.
        async def block_external(route):
            url = route.request.url.lower()
            if url.startswith(("http://", "https://", "ws://", "wss://")):
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", block_external)
        page = await context.new_page()
        await page.goto(
            f"file://{os.path.abspath(html_path)}",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await asyncio.sleep(2)
        screenshot = await page.screenshot(full_page=True, type="png")
        await browser.close()
    return screenshot

# ══════════════════════════════════════════════════════
#   PHPKOBO ENGINE  (unchanged logic)
# ══════════════════════════════════════════════════════
def _js_unescape(s):
    s = s.replace('\n', '\\n')
    s = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
    s = s.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
    s = s.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
    return s

def detect_phpkobo(html):
    # Do not inspect only the first script: phpkobo wrappers are often
    # preceded by a small bootstrap/config block.  Require both the dynamic
    # Function constructor and its characteristic _Srkpv/B payload marker.
    for sm in re.finditer(r'<script[^>]*>([\s\S]*?)<\/script>', html, re.IGNORECASE):
        sc = sm.group(1)
        has_function = re.search(r'\bFunction\s*\(\s*["\']', sc) is not None
        has_payload = re.search(r'_Srkpv\s*=|\bB[0-9A-Za-z\\]{8,}', sc) is not None
        if has_function and has_payload:
            return True
    return False

def decode_phpkobo(html):
    sm = re.search(r'<script[^>]*>([\s\S]*?)<\/script>', html, re.IGNORECASE)
    if not sm: raise ValueError("No <script> tag found")
    sc = sm.group(1).lstrip(';').strip()
    if 'Function("' in sc:
        inner = sc[sc.index('Function("')+10 : sc.rindex('")()')  ]
    elif "Function('" in sc:
        inner = sc[sc.index("Function('")+10 : sc.rindex("')()")  ]
    else: raise ValueError("phpkobo wrapper not found")
    code = _js_unescape(inner)
    p    = code.find('_Srkpv=')
    if p < 0: raise ValueError("_Srkpv not found")
    qs    = code.index('"', p+7)+1
    qe    = code.index('";', qs)
    srkpv = code[qs:qe].rstrip('\\').rstrip('"')
    bi    = srkpv.find('B')
    if bi < 0: raise ValueError("B marker not found")
    sp    = srkpv[bi+1:].rstrip('\\').rstrip('"')
    if len(sp) < 8: raise ValueError("Payload too short")
    hdr   = sp[-8:]; step = int(hdr[4:6],16); start = int(hdr[6:8],16); sp = sp[:-8]
    sp    = re.sub(r'[Xx]','e', re.sub(r'[Yy]','a', re.sub(r'[Zz]','c', sp)))
    sp    = re.sub(r'[^0-9a-fA-F]','0', sp)
    pairs = re.findall(r'.{2}', sp)
    if not pairs: raise ValueError("No hex pairs")
    W = [0]*256; j = start
    for i in range(256): W[j] = i; j = (j+step)%256
    bv = [(int(px,16)-W[i%256]+256)%256 for i,px in enumerate(pairs)]
    r  = bytes(bv).decode('utf-8', errors='replace')
    if len(r) < 30: raise ValueError("Result too short")
    return r

# ══════════════════════════════════════════════════════
#   HB ENC V1 ENGINE  (symbol map + Base64 + rolling XOR)
# ══════════════════════════════════════════════════════
def detect_custom_cipher(html: str) -> bool:
    """Detect the HB ENC V1 CIPHER_PAYLOAD wrapper without executing its JS."""
    signature = (
        "CIPHER_PAYLOAD" in html
        or (re.search(r'const\s+_0x(?:emj|data|seed)\b', html) is not None
            and re.search(r'(?:window\.)?atob\s*\(', html) is not None
            and re.search(r'new\s+(?:Uint8Array|TextDecoder)', html) is not None)
    )
    return bool(signature and re.search(r'document\s*\.\s*write\s*\(', html, re.I))


def _decode_custom_xor_wrapper(script_body: str):
    """Decode one nested var _k/var _b rolling-XOR wrapper, if present."""
    m = re.search(
        r'var\s+_k\s*=\s*(\d+)\s*,\s*_b\s*=\s*\[([0-9,\s]+)\]',
        script_body,
    )
    if not m:
        return None
    inc_m = re.search(r'_k\s*=\s*\(_k\s*\+\s*(\d+)\)\s*&\s*255', script_body[m.end():])
    if not inc_m:
        raise ValueError("HB ENC V1 XOR increment not found")
    key, increment = int(m.group(1)), int(inc_m.group(1))
    values = [int(x) for x in m.group(2).split(',') if x.strip()]
    out = bytearray(len(values))
    current = key
    for i, value in enumerate(values):
        out[i] = value ^ current
        current = (current + increment) & 0xff
    return bytes(out).decode('utf-8', errors='replace')


def _clean_custom_nested_scripts(html: str) -> str:
    """Replace nested encrypted CSS/JS script wrappers with clean assets."""
    script_rx = re.compile(r'<script([^>]*)>([\s\S]*?)</script>', re.IGNORECASE)

    def replace_script(match):
        attrs, body = match.group(1), match.group(2)
        decoded = body
        changed = False
        for _ in range(8):
            next_layer = _decode_custom_xor_wrapper(decoded)
            if next_layer is None:
                break
            decoded = next_layer
            changed = True
        if not changed:
            return match.group(0)
        # The sample uses one encrypted CSS block and one application JS
        # block.  Preserve each as the correct executable asset type.
        looks_css = bool(re.search(
            r'(?:^|\s)(?:\*\s*,|\*\s*::(?:before|after)|[:.#][\w-]+|@(?:media|keyframes)|:root)\s*\{',
            decoded,
        ))
        if looks_css and not re.search(r'^\s*(?:\(?\s*function\b|const\b|let\b|var\b)', decoded):
            return f"<style>\n{decoded}\n</style>"
        return f"<script{attrs}>\n{decoded}\n</script>"

    return script_rx.sub(replace_script, html)


def decode_custom_cipher(html: str) -> str:
    """Decode HB ENC V1 CIPHER_PAYLOAD statically and fully clean nested layers."""
    emj_match = re.search(r'const\s+_0xemj\s*=\s*(\[[\s\S]*?\]);', html)
    data_match = re.search(r'const\s+_0xdata\s*=\s*("(?:\\.|[^"\\])*")\s*;', html)
    seed_match = re.search(r'const\s+_0xseed\s*=\s*(\d+)\s*;', html)
    if not (emj_match and data_match and seed_match):
        raise ValueError("HB ENC V1 constants not found")

    symbols = json.loads(emj_match.group(1))
    data = json.loads(data_match.group(1))
    seed = int(seed_match.group(1))
    std = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    if len(symbols) != len(std):
        raise ValueError("Invalid HB ENC V1 symbol table")
    char_map = dict(zip(symbols, std))
    char_map["•"] = "="
    encoded = "".join(char_map.get(ch, ch) for ch in data)
    encoded += "=" * ((4 - len(encoded) % 4) % 4)
    try:
        binary = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError(f"HB ENC V1 Base64 reconstruction failed: {exc}") from exc

    decoded_bytes = bytearray(len(binary))
    current = seed
    for i, value in enumerate(binary):
        decoded_bytes[i] = value ^ current
        current = (current + 31) & 0xff
    decoded = bytes(decoded_bytes).decode('utf-8', errors='replace')
    if len(decoded) < 100 or not re.search(r'<(?:!doctype\s+html|html\b|body\b)', decoded, re.I):
        raise ValueError("HB ENC V1 result is not valid HTML")

    decoded = _clean_custom_nested_scripts(decoded)
    # Remove only the custom protection branding/comments; keep application
    # comments and all HTML/CSS/JS content intact.
    decoded = re.sub(r'<!--\s*CIPHER_PAYLOAD:[\s\S]*?-->', '', decoded, flags=re.I)
    decoded = re.sub(r'\n{3,}', '\n\n', decoded).strip() + '\n'
    return decoded

# ══════════════════════════════════════════════════════
#   SAMRAT MC ENGINE  (static multi-stage XOR/KDF decoder)
# ══════════════════════════════════════════════════════
def detect_samrat_mc(html: str) -> bool:
    """Identify the SAMRAT MC wrapper from its distinctive static constants."""
    return all(re.search(pattern, html, re.I) for pattern in (
        r'const\s+MASTER\s*=\s*new\s+Uint8Array\s*\(',
        r'const\s+RAW_BLOBS\s*=',
        r'const\s+KDF_ITER\s*=',
        r'const\s+MAGIC\s*=\s*["\']POLY_45L_',
    ))


def _samrat_js_string(html: str, name: str) -> str:
    match = re.search(r'const\s+' + re.escape(name) + r'\s*=\s*("(?:\\.|[^"\\])*")\s*;', html)
    if not match:
        raise ValueError(f"SAMRAT MC constant {name} not found")
    return json.loads(match.group(1))


def _samrat_hash_string(value: str, length: int) -> bytes:
    """Mirror the wrapper's JS charCodeAt/Math.imul hash using UTF-16 units."""
    encoded = value.encode("utf-16-le", errors="surrogatepass")
    h1, h2 = 0x811C9DC5, 0x01000193
    for pos in range(0, len(encoded), 2):
        char = encoded[pos] | (encoded[pos + 1] << 8)
        h1 = ((h1 ^ char) * 0x01000193) & 0xFFFFFFFF
        h2 = ((h2 ^ char) * 0x85EBCA6B) & 0xFFFFFFFF
    return bytes(((h1 >> ((j % 4) * 8)) ^ (h2 >> ((j % 4) * 8)) ^ (j * 37)) & 0xFF
                 for j in range(length))


def _samrat_kdf(master: bytes, seed: bytes, iterations: int) -> bytes:
    state = bytearray(64)
    state[:32] = master[:32]
    state[32:64] = seed[:32]
    hashes = [0x811C9DC5, 0x01000193, 0xDEADBEEF, 0xCAFEBABE]
    multipliers = [0x01000193, 0x85EBCA6B, 0xC2B2AE35, 0x27D4EB2F]
    for round_no in range(iterations):
        for j in range(64):
            x = state[(j + round_no) % 64] ^ (round_no & 0xFF)
            hashes[0] = ((hashes[0] ^ x) * multipliers[0]) & 0xFFFFFFFF
            hashes[1] = ((hashes[1] ^ (x + 1)) * multipliers[1]) & 0xFFFFFFFF
            hashes[2] = ((hashes[2] ^ (x + 2)) * multipliers[2]) & 0xFFFFFFFF
            hashes[3] = ((hashes[3] ^ (x + 3)) * multipliers[3]) & 0xFFFFFFFF
    return bytes(((hashes[i % 4] >> ((i % 4) * 8)) ^ (i * 37) ^ (hashes[0] & 0xFF)) & 0xFF
                 for i in range(32))


def _samrat_derive_key(key: bytes, layer: int) -> bytes:
    return bytes(key[(j + layer) % len(key)] ^ ((layer * 17 + j * 29 + 11) & 0xFF)
                 for j in range(len(key)))


def _samrat_decrypt_blob(blob: str, key: bytes, layers: int) -> str:
    data = base64.b64decode(blob + "=" * ((4 - len(blob) % 4) % 4), validate=True)
    for layer in range(layers, 0, -1):
        layer_key = _samrat_derive_key(key, layer)
        data = bytes(value ^ layer_key[i % len(layer_key)] ^ ((i * 31 + 7) & 0xFF)
                     for i, value in enumerate(data))
    return data.decode("utf-8", errors="strict")


def _remove_samrat_owner_banner(html: str) -> str:
    """Strip only the wrapper's injected owner banner, retaining page content."""
    start = re.search(r'<div\b(?=[^>]*\bid\s*=\s*["\']__OWNER_HEADER__["\'])[^>]*>', html, re.I)
    if not start:
        return html
    depth = 1
    tags = re.compile(r'<div\b[^>]*>|</div\s*>', re.I)
    for tag in tags.finditer(html, start.end()):
        if tag.group(0).startswith("</"):
            depth -= 1
        elif not tag.group(0).rstrip().endswith("/>"):
            depth += 1
        if depth == 0:
            return html[:start.start()] + html[tag.end():]
    return html


def decode_samrat_mc(html: str) -> str:
    """Decode SAMRAT MC layers as data; never evaluate the input's JavaScript."""
    if not detect_samrat_mc(html):
        raise ValueError("SAMRAT MC wrapper not found")
    master_match = re.search(r'const\s+MASTER\s*=\s*new\s+Uint8Array\s*\(\s*(\[[\d,\s]+\])\s*\)', html, re.I)
    blobs_match = re.search(r'const\s+RAW_BLOBS\s*=\s*', html, re.I)
    if not master_match or not blobs_match:
        raise ValueError("SAMRAT MC key or payload not found")
    master = bytes(json.loads(master_match.group(1)))
    blobs, _ = json.JSONDecoder().raw_decode(html[blobs_match.end():])
    inner = int(re.search(r'const\s+INNER\s*=\s*(\d+)', html, re.I).group(1))
    stages = int(re.search(r'const\s+STAGES\s*=\s*(\d+)', html, re.I).group(1))
    iterations = int(re.search(r'const\s+KDF_ITER\s*=\s*(\d+)', html, re.I).group(1))
    magic = _samrat_js_string(html, "MAGIC")
    owner = _samrat_js_string(html, "OWNER")
    hash_parts = "".join(_samrat_js_string(html, name) for name in ("H1", "H2", "H3"))
    key = _samrat_kdf(master, _samrat_hash_string(owner + hash_parts, 32), iterations)

    if len(blobs) < stages:
        raise ValueError("SAMRAT MC payload has fewer stages than declared")
    code = None
    for index in range(stages):
        plaintext = _samrat_decrypt_blob(blobs[index][::-1], key, inner)
        if not plaintext.startswith(magic):
            raise ValueError(f"SAMRAT MC integrity marker failed at stage {index + 1}")
        packet = json.loads(plaintext[len(magic):])
        if packet.get("final"):
            code = packet.get("code")
            break
        seed = bytes(packet["seed"])
        key = _samrat_kdf(master, seed, iterations)
    if not isinstance(code, str) or not re.search(r'<(?:!doctype\s+html|html\b|body\b)', code, re.I):
        raise ValueError("SAMRAT MC final stage did not contain HTML")
    return re.sub(r'\n{3,}', '\n\n', _remove_samrat_owner_banner(code)).strip() + '\n'


# ══════════════════════════════════════════════════════
#   BASE 777 ENGINE  (static Base64 HTML wrapper)
# ══════════════════════════════════════════════════════
def detect_base_777(html: str) -> bool:
    """Detect BASE 777's encoded HTML wrapper without running its JavaScript."""
    return bool(
        re.search(r'var\s+encoded\s*=\s*"(?:\\.|[^"\\])*"\s*;', html)
        and re.search(r'atob\s*\(\s*encoded\s*\)', html, re.I)
        and re.search(r'document\s*\.\s*write\s*\(\s*html\s*\)', html, re.I)
        and re.search(r'new\s+TextDecoder\s*\(', html, re.I)
    )


def decode_base_777(html: str) -> str:
    """Recover BASE 777 HTML from Base64 data; never execute the wrapper JS."""
    if not detect_base_777(html):
        raise ValueError("BASE 777 wrapper not found")
    match = re.search(r'var\s+encoded\s*=\s*("(?:\\.|[^"\\])*")\s*;', html)
    if not match:
        raise ValueError("BASE 777 encoded payload not found")
    encoded = json.loads(match.group(1))
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8", errors="strict")
    except Exception as exc:
        raise ValueError(f"BASE 777 Base64 payload is invalid: {exc}") from exc
    if len(decoded) < 100 or not re.search(r'<(?:!doctype\s+html|html\b|body\b)', decoded, re.I):
        raise ValueError("BASE 777 payload did not contain HTML")
    return decoded.strip() + "\n"


# ══════════════════════════════════════════════════════
#   TMS CYBER ENGINE  (symbol map + reverse Base64 + XOR/shift)
# ══════════════════════════════════════════════════════
def detect_tms_cyber(html: str) -> bool:
    """Identify TMS CYBER's seven-layer symbol-mapped payload wrapper."""
    return all(re.search(pattern, html, re.I) for pattern in (
        r'const\s+_0xstd\s*=',
        r'const\s+_0xemj\s*=\s*\[',
        r'const\s+_0xdata\s*=',
        r'const\s+_0xseed\s*=\s*\d+',
        r'const\s+_0xstep\s*=\s*\d+',
        r'const\s+_0xshift\s*=\s*\d+',
        r'document\s*\.\s*write\s*\(\s*_0xdecoded\s*\)',
    ))


def decode_tms_cyber(html: str) -> str:
    """Decode TMS CYBER as bytes/strings only; do not execute its JavaScript."""
    if not detect_tms_cyber(html):
        raise ValueError("TMS CYBER wrapper not found")
    symbols_match = re.search(r'const\s+_0xemj\s*=\s*(\[[\s\S]*?\])\s*;', html)
    data_match = re.search(r'const\s+_0xdata\s*=\s*("(?:\\.|[^"\\])*")\s*;', html)
    if not (symbols_match and data_match):
        raise ValueError("TMS CYBER symbol table or payload not found")

    symbols = json.loads(symbols_match.group(1))
    data = json.loads(data_match.group(1))
    std_match = re.search(r'const\s+_0xstd\s*=\s*("(?:\\.|[^"\\])*")\s*;', html)
    if not std_match:
        raise ValueError("TMS CYBER Base64 alphabet not found")
    standard = json.loads(std_match.group(1))
    if len(symbols) != len(standard):
        raise ValueError("Invalid TMS CYBER symbol table")

    symbol_map = dict(zip(symbols, standard))
    symbol_map["•"] = "="
    reversed_base64 = "".join(symbol_map.get(char, char) for char in data)
    encoded = reversed_base64[::-1]
    try:
        binary = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError(f"TMS CYBER Base64 reconstruction failed: {exc}") from exc

    def constant(name):
        match = re.search(r'const\s+' + re.escape(name) + r'\s*=\s*(\d+)\s*;', html)
        if not match:
            raise ValueError(f"TMS CYBER constant {name} not found")
        return int(match.group(1))

    current = constant("_0xseed") & 0xFF
    step = constant("_0xstep") & 0xFF
    shift = constant("_0xshift")
    output = bytearray(len(binary))
    for i, value in enumerate(binary):
        output[i] = ((value ^ current) - shift + 256) & 0xFF
        current = (current + step) & 0xFF
    try:
        decoded = output.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"TMS CYBER output is not UTF-8: {exc}") from exc
    if len(decoded) < 100 or not re.search(r'<(?:!doctype\s+html|html\b|body\b)', decoded, re.I):
        raise ValueError("TMS CYBER result did not contain valid HTML")
    return decoded.strip() + "\n"


_TMS_CYBER_ANIMATION = [
    (_premium_emoji("🔓", "PREMIUM_EMOJI_TMS_DECODE_ID"), "Decoding TMS CYBER payload"),
    (_premium_emoji("💾", "PREMIUM_EMOJI_TMS_SAVE_ID"), "Saving and sending decoded file"),
]


def _tms_cyber_msg(step):
    emoji, label = _TMS_CYBER_ANIMATION[step]
    return f"{emoji}  <b>TMS CYBER</b>\n\n{emoji}  {label}..."

# ══════════════════════════════════════════════════════
#   RDX DECODER v7.1 ENGINE  (Node.js subprocess)
# ══════════════════════════════════════════════════════
def detect_rdx(html: str) -> bool:
    """Detect RDX obfuscation — tolerate minification and wrapper variants."""
    for sm in re.finditer(r'<script[^>]*>([\s\S]*?)<\/script>', html, re.IGNORECASE):
        sc = sm.group(1)
        if len(sc) < 180:
            continue
        # P1/P3: indirect eval of a variable, with or without a semicolon.
        if re.search(r'\(0\s*,\s*eval\)\(\s*[A-Za-z_$][\w$]*\s*\)', sc):
            return True
        if re.search(r'try\s*\{[\s\S]{0,120}\(0\s*,\s*eval\)\(', sc):
            return True
        # P2 and hybrid wrappers: decoder loop plus document output.
        if re.search(r'while\s*\(', sc) and re.search(r'document\s*\.\s*(?:write|writeln|open)\s*\(', sc):
            return True
        if re.search(r'(?:document\s*\.\s*open|document\s*\.\s*write)', sc) and re.search(
            r'(?:fromCharCode|decodeURIComponent|atob|String\.fromCharCode|_\$)', sc
        ):
            return True
    return False

async def decode_rdx(in_path: str, out_path: str) -> str:
    """
    Decode HTML using RDX Decoder v7.1 via Node.js subprocess.
    Writes decoded output to out_path and returns the HTML string.
    """
    node = get_node_path()
    if not node:
        raise FileNotFoundError("Node.js not installed — RDX engine unavailable.")

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RDX_DECODER_v7_1.js")
    if not os.path.exists(script):
        raise FileNotFoundError("RDX_DECODER_v7_1.js not found next to main.py.")

    proc = await asyncio.create_subprocess_exec(
        node, script, in_path, out_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
    except asyncio.TimeoutError:
        proc.kill()
        raise TimeoutError("RDX decoder timed out (90 s).")

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"RDX node error: {err[:300]}")

    with open(out_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

# ══════════════════════════════════════════════════════
#   INIT ANIMATION  — New Braille Spinner
# ══════════════════════════════════════════════════════
_INIT_FRAMES = [
    "🔹  𝙸𝚗𝚒𝚝 𝙴𝚗𝚐𝚒𝚗𝚎𝚜  ▰▱▱",
    "🔷  𝚅𝚎𝚛𝚒𝚏𝚢 𝙵𝚒𝚕𝚎  ▰▰▱",
    "✅  𝗔𝗟𝗟  𝗦𝗬𝗦𝗧𝗘𝗠𝗦  𝗚𝗢!",
]

async def _decode_start(update, context):
    msg = await _reply_text(update.message, "⠿  𝙸𝚗𝚒𝚝𝚒𝚊𝚕𝚒𝚣𝚒𝚗𝚐...")
    for frame in _INIT_FRAMES:
        await asyncio.sleep(1.1)
        await safe_edit(msg, frame)
    await asyncio.sleep(0.5)
    try: await msg.delete()
    except: pass

    context.user_data["waiting_for_html"] = True
    await _reply_html(update.message, 
        "╔══════════════════════════╗\n"
        f"  {_premium_emoji('🗂', 'PREMIUM_EMOJI_FOLDER_ID')}  <b>𝗦𝗲𝗻𝗱 𝗬𝗼𝘂𝗿 𝗙𝗶𝗹𝗲</b>\n"
        "╚══════════════════════════╝\n\n"
        "𝚂𝚎𝚗𝚍 𝚢𝚘𝚞𝚛 𝚎𝚗𝚌𝚛𝚢𝚙𝚝𝚎𝚍 <b>.html</b> 𝚏𝚒𝚕𝚎 ↓\n\n"
        "🔸  <b>𝗦𝘂𝗽𝗽𝗼𝗿𝘁𝗲𝗱:</b>  .html  ╌  .htm\n\n"
        "〔 𝙰𝚞𝚝𝚘-𝙳𝚎𝚝𝚎𝚌𝚝𝚜:  𝗽𝗵𝗽𝗸𝗼𝗯𝗼  ·  𝗦𝗔𝗠𝗥𝗔𝗧 𝗠𝗖  ·  𝗥𝗗𝗫  ·  𝗦𝗲𝗿𝘃𝗲𝗿 〕"
    )

# ══════════════════════════════════════════════════════
#   PHPKOBO  CHECKLIST  ANIMATION
# ══════════════════════════════════════════════════════
_PK = [
    (_premium_emoji("🔎", "PREMIUM_EMOJI_SEARCH_ID"), "𝙴𝚗𝚌𝚛𝚢𝚙𝚝 𝚃𝚢𝚙𝚎  ╌  𝗽𝗵𝗽𝗸𝗼𝗯𝗼"),
    (_premium_emoji("🔓", "PREMIUM_EMOJI_UNLOCK_ID"), "𝙱𝚢𝚝𝚎𝚜 𝙳𝚎𝚌𝚛𝚢𝚙𝚝𝚎𝚍"),
    (_premium_emoji("💾", "PREMIUM_EMOJI_SAVE_ID"), "𝙾𝚞𝚝𝚙𝚞𝚝 𝚂𝚊𝚟𝚎𝚍"),
]

def _pk_msg(cur):
    h = f"{_premium_emoji('⚡', 'PREMIUM_EMOJI_LIGHTNING_ID')}  <b>𝗣𝗛𝗣𝗞𝗢𝗕𝗢  𝗗𝗲𝗰𝗿𝘆𝗽𝘁  𝗘𝗻𝗴𝗶𝗻𝗲</b>\n\n"
    lines = []
    for i, (icon, label) in enumerate(_PK):
        if i < cur:    lines.append(f"  ✦  {icon}  {label}")
        elif i == cur: lines.append(f"  ⟳  {icon}  {label}...")
        else:          lines.append(f"  ◌  {icon}  {label}")
    return h + "\n".join(lines)

# ══════════════════════════════════════════════════════
#   RDX v7.1  CHECKLIST  ANIMATION  (NEW)
# ══════════════════════════════════════════════════════
_RDX = [
    (_premium_emoji("🔍", "PREMIUM_EMOJI_RDX_SEARCH_ID"), "𝙴𝚗𝚌𝚛𝚢𝚙𝚝 𝚃𝚢𝚙𝚎  ╌  𝗥𝗗𝗫 𝘃𝟳.𝟭"),
    (_premium_emoji("🔑", "PREMIUM_EMOJI_KEY_ID"), "𝙻𝚊𝚢𝚎𝚛 𝙳𝚎𝚌𝚘𝚍𝚒𝚗𝚐"),
    (_premium_emoji("💾", "PREMIUM_EMOJI_SAVE_ID"), "𝙾𝚞𝚝𝚙𝚞𝚝 𝚂𝚊𝚟𝚎𝚍"),
]

def _rdx_msg(cur):
    h = f"{_premium_emoji('🔓', 'PREMIUM_EMOJI_UNLOCK_ID')}  <b>𝗥𝗗𝗫  𝗗𝗲𝗰𝗿𝘆𝗽𝘁  𝗘𝗻𝗴𝗶𝗻𝗲  𝘃𝟳.𝟭</b>\n\n"
    lines = []
    for i, (icon, label) in enumerate(_RDX):
        if i < cur:    lines.append(f"  ✦  {icon}  {label}")
        elif i == cur: lines.append(f"  ⟳  {icon}  {label}...")
        else:          lines.append(f"  ◌  {icon}  {label}")
    return h + "\n".join(lines)

# ══════════════════════════════════════════════════════
#   SERVER ENGINE  PROGRESS BAR  ANIMATION  (Updated)
# ══════════════════════════════════════════════════════
_BR = [
    ( 0,  "𝙴𝚗𝚌𝚛𝚢𝚙𝚝 𝚃𝚢𝚙𝚎  ╌  𝗦𝗲𝗿𝘃𝗲𝗿"),
    (50,  "𝚁𝚎𝚊𝚍 𝚃𝚑𝚎 𝙷𝚝𝚖𝚕.."),
    (97,  "𝙵𝚒𝚗𝚊𝚕𝚒𝚣𝚒𝚗𝚐..."),
]

def _br_msg(idx):
    pct, label = _BR[idx % len(_BR)]
    filled = int(pct / 10)
    bar    = "█" * filled + "░" * (10 - filled)
    return (
        f"{_premium_emoji('🖥️', 'PREMIUM_EMOJI_SERVER_ID')}  <b>𝗦𝗲𝗿𝘃𝗲𝗿  𝗥𝗲𝗻𝗱𝗲𝗿  𝗘𝗻𝗴𝗶𝗻𝗲</b>\n\n"
        f"  [{bar}]  {pct}%\n\n"
        f"  🔹  {label}"
    )

# ══════════════════════════════════════════════════════
#   DECODE  STEP 2 — PROCESS  (Automatic engine detection)
# ══════════════════════════════════════════════════════
async def _do_decode(update, context, doc, fname):
    msg = await _reply_text(update.message, "🛰️  𝙴𝚜𝚝𝚊𝚋𝚕𝚒𝚜𝚑𝚒𝚗𝚐 𝚌𝚘𝚗𝚗𝚎𝚌𝚝𝚒𝚘𝚗...")

    try:
        file_obj = await context.bot.get_file(doc.file_id)
        with tempfile.TemporaryDirectory() as tmp:
            in_path  = os.path.join(tmp, fname)
            await file_obj.download_to_drive(in_path)
            base     = fname.rsplit(".", 1)
            out_name = f"{base[0]}_decoded.{base[1]}" if len(base) == 2 else f"{fname}_decoded"
            out_path = os.path.join(tmp, out_name)

            with open(in_path, "r", encoding="utf-8", errors="replace") as f: raw = f.read()

            decoded    = None
            screenshot = None
            method     = ""
            tms_cyber = detect_tms_cyber(raw)

            # Preserve the existing progress animation for the older engines.
            # BASE 777 and SAMRAT MC are intentionally direct, with no animation.
            if not (detect_base_777(raw) or detect_samrat_mc(raw) or tms_cyber):
                await asyncio.sleep(1.1)
                await safe_edit(msg, "🧪  𝙰𝚗𝚊𝚕𝚢𝚣𝚒𝚗𝚐 𝚎𝚗𝚌𝚛𝚢𝚙𝚝𝚒𝚘𝚗...")

            # ── ENGINE 1: phpkobo ──────────────────────────────────
            if detect_phpkobo(raw):
                for step in range(len(_PK)):
                    await safe_edit(msg, _pk_msg(step), parse_mode=ParseMode.HTML)
                    await asyncio.sleep(1.1)
                decoded = decode_phpkobo(raw)
                method  = f"{_premium_emoji('⚡', 'PREMIUM_EMOJI_LIGHTNING_ID')}  𝗽𝗵𝗽𝗸𝗼𝗯𝗼 𝙴𝚗𝚐𝚒𝚗𝚎"
                with open(out_path, "w", encoding="utf-8") as f: f.write(decoded)
                await safe_edit(msg, f"{_premium_emoji('📸', 'PREMIUM_EMOJI_CAMERA_ID')}  𝙲𝚊𝚙𝚝𝚞𝚛𝚒𝚗𝚐 𝚜𝚌𝚛𝚎𝚎𝚗𝚜𝚑𝚘𝚝...", parse_mode=ParseMode.HTML)
                screenshot = await take_screenshot(out_path)
                db["stats"]["phpkobo"] = db["stats"].get("phpkobo", 0) + 1

            # ── ENGINE 2: TMS CYBER ───────────────────────────────
            # Keep this ahead of HB ENC: both wrappers use _0xemj/_0xdata.
            elif tms_cyber:
                await safe_edit(msg, _tms_cyber_msg(0), parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.6)
                decoded = decode_tms_cyber(raw)
                method = f"{_premium_emoji('🛡️', 'PREMIUM_EMOJI_TMS_DECODE_ID')}  𝗧𝗠𝗦 𝗖𝗬𝗕𝗘𝗥 𝙴𝚗𝚐𝚒𝚗𝚎"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(decoded)
                screenshot = await take_screenshot(out_path)
                db["stats"]["tms_cyber"] = db["stats"].get("tms_cyber", 0) + 1

            # ── ENGINE 3: HB ENC V1 ────────────────────────────────
            elif detect_custom_cipher(raw):
                await safe_edit(msg, "🧬  𝗛𝗕 𝗘𝗡𝗖 𝗩𝟭 𝙳𝚎𝚝𝚎𝚌𝚝𝚎𝚍...")
                await asyncio.sleep(1.1)
                decoded = decode_custom_cipher(raw)
                method = "🧬  𝗛𝗕 𝗘𝗡𝗖 𝗩𝟭 𝙴𝚗𝚐𝚒𝚗𝚎"
                with open(out_path, "w", encoding="utf-8") as f: f.write(decoded)
                await safe_edit(msg, "🔓  𝗛𝗕 𝗘𝗡𝗖 𝗩𝟭 𝙻𝚊𝚢𝚎𝚛𝚜 𝙳𝚎𝚌𝚘𝚍𝚎𝚍...")
                screenshot = await take_screenshot(out_path)
                db["stats"]["custom"] = db["stats"].get("custom", 0) + 1

            # ── ENGINE 4: SAMRAT MC ───────────────────────────────
            elif detect_samrat_mc(raw):
                decoded = decode_samrat_mc(raw)
                method = f"{_premium_emoji('🔐', 'PREMIUM_EMOJI_SAMRAT_ID')}  𝗦𝗔𝗠𝗥𝗔𝗧 𝗠𝗖 𝙴𝚗𝚐𝚒𝚗𝚎"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(decoded)
                await safe_edit(msg, f"{_premium_emoji('📸', 'PREMIUM_EMOJI_CAMERA_ID')}  𝙲𝚊𝚙𝚝𝚞𝚛𝚒𝚗𝚐 𝚜𝚌𝚛𝚎𝚎𝚗𝚜𝚑𝚘𝚝...", parse_mode=ParseMode.HTML)
                screenshot = await take_screenshot(out_path)
                db["stats"]["samrat_mc"] = db["stats"].get("samrat_mc", 0) + 1

            # ── ENGINE 5: BASE 777 ────────────────────────────────
            elif detect_base_777(raw):
                decoded = decode_base_777(raw)
                method = f"{_premium_emoji('🧱', 'PREMIUM_EMOJI_BASE777_ID')}  𝗕𝗔𝗦𝗘 𝟳𝟳𝟳 𝙴𝚗𝚐𝚒𝚗𝚎"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(decoded)
                await safe_edit(msg, f"{_premium_emoji('📸', 'PREMIUM_EMOJI_CAMERA_ID')}  𝙲𝚊𝚙𝚝𝚞𝚛𝚒𝚗𝚐 𝚜𝚌𝚛𝚎𝚎𝚗𝚜𝚑𝚘𝚝...", parse_mode=ParseMode.HTML)
                screenshot = await take_screenshot(out_path)
                db["stats"]["base_777"] = db["stats"].get("base_777", 0) + 1

            # ── ENGINE 6: RDX v7.1 ────────────────────────────────
            elif detect_rdx(raw):
                # Start decode task in background
                rdx_task = asyncio.create_task(decode_rdx(in_path, out_path))
                # Show animated checklist while task runs
                for step in range(len(_RDX)):
                    await safe_edit(msg, _rdx_msg(step), parse_mode=ParseMode.HTML)
                    await asyncio.sleep(3.0)
                # If still running, show finalizing
                if not rdx_task.done():
                    await safe_edit(msg, "⚙️  𝙵𝚒𝚗𝚊𝚕𝚒𝚣𝚒𝚗𝚐 𝚁𝙳𝚇 𝚍𝚎𝚌𝚘𝚍𝚎...")
                try:
                    # Keep the fallback boundary around decoding only.  A
                    # screenshot/rendering failure must not re-run the
                    # encrypted input through the Server engine.
                    decoded    = await rdx_task
                    method     = f"{_premium_emoji('🔓', 'PREMIUM_EMOJI_UNLOCK_ID')}  𝗥𝗗𝗫 𝘃𝟳.𝟭 𝙴𝚗𝚐𝚒𝚗𝚎"
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(decoded)
                    db["stats"]["rdx"] = db["stats"].get("rdx", 0) + 1
                except Exception as rdx_e:
                    # Fallback to Server engine only when the RDX decoder
                    # itself failed.  Never use it for screenshot failures.
                    logger.warning(f"RDX engine failed ({rdx_e}), falling back to Server engine")
                    await safe_edit(msg, "⚠️  𝚁𝙳𝚇 𝚏𝚊𝚒𝚕𝚎𝚍, 𝚞𝚜𝚒𝚗𝚐 𝚂𝚎𝚛𝚟𝚎𝚛 𝙴𝚗𝚐𝚒𝚗𝚎...")
                    await asyncio.sleep(3.0)
                    task = asyncio.create_task(render_html(in_path))
                    i = 0
                    while not task.done():
                        await safe_edit(msg, _br_msg(i), parse_mode=ParseMode.HTML)
                        i += 1; await asyncio.sleep(3.0)
                    decoded, screenshot = await task
                    method = "🖥️  𝗦𝗲𝗿𝘃𝗲𝗿 𝙴𝚗𝚐𝚒𝚗𝚎 (𝚏𝚊𝚕𝗹𝗯𝗮𝗰𝗸)"
                    with open(out_path, "w", encoding="utf-8") as f: f.write(decoded)
                    db["stats"]["server"] = db["stats"].get("server", 0) + 1
                else:
                    await safe_edit(msg, f"{_premium_emoji('📸', 'PREMIUM_EMOJI_CAMERA_ID')}  𝙲𝚊𝚙𝚝𝚞𝚛𝚒𝚗𝚐 𝚜𝚌𝚛𝚎𝚎𝚗𝚜𝚑𝚘𝚝...", parse_mode=ParseMode.HTML)
                    screenshot = await take_screenshot(out_path)

            # ── ENGINE 4: Server / Browser ─────────────────────────
            else:
                task = asyncio.create_task(render_html(in_path))
                i = 0
                while not task.done():
                    await safe_edit(msg, _br_msg(i), parse_mode=ParseMode.HTML)
                    i += 1; await asyncio.sleep(3.0)
                decoded, screenshot = await task
                method = "🖥️  𝗦𝗲𝗿𝘃𝗲𝗿 𝙴𝚗𝚐𝚒𝚗𝚎"
                with open(out_path, "w", encoding="utf-8") as f: f.write(decoded)
                db["stats"]["server"] = db["stats"].get("server", 0) + 1

            # ── Update global stats ────────────────────────────────
            db["stats"]["total_decodes"] = db["stats"].get("total_decodes", 0) + 1
            save_db(db)

            # ── Send results ───────────────────────────────────────
            if tms_cyber:
                await safe_edit(msg, _tms_cyber_msg(1), parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.6)
            else:
                await safe_edit(msg, "✦  𝙳𝚘𝚗𝚎!  𝚂𝚎𝚗𝚍𝚒𝚗𝚐 𝚛𝚎𝚜𝚞𝚕𝚝𝚜...")
                await asyncio.sleep(0.4)

            if screenshot:
                import io
                await update.message.reply_photo(
                    photo=io.BytesIO(screenshot),
                    caption=_premiumize_html((
                        f"{_premium_emoji('🖼️', 'PREMIUM_EMOJI_IMAGE_ID')}  <b>𝗣𝗮𝗴𝗲 𝗦𝗰𝗿𝗲𝗲𝗻𝘀𝗵𝗼𝘁</b>\n\n"
                        f"{_premium_emoji('⚙️', 'PREMIUM_EMOJI_GEAR_ID')}  <b>𝗠𝗲𝘁𝗵𝗼𝗱</b>  ╌  {method}\n"
                        f"{_premium_emoji('📎', 'PREMIUM_EMOJI_ATTACHMENT_ID')}  𝙵𝚒𝚕𝚎 𝚜𝚎𝚗𝚍𝚒𝚗𝚐 𝚋𝚎𝚕𝚘𝚠 ↓"
                    )),
                    parse_mode=ParseMode.HTML,
                )

            with open(out_path, "rb") as f:
                await update.message.reply_document(
                    document=f, filename=out_name,
                    caption=_premiumize_html((
                        "╔══════════════════════════╗\n"
                        f"  {_premium_emoji('✅', 'PREMIUM_EMOJI_CHECK_ID')}  <b>𝗗𝗲𝗰𝗼𝗱𝗲 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹!</b>\n"
                        "╚══════════════════════════╝\n\n"
                        f"{_premium_emoji('🗂', 'PREMIUM_EMOJI_FOLDER_ID')}  <b>𝗙𝗶𝗹𝗲</b>    ╌  <code>{out_name}</code>\n"
                        f"{_premium_emoji('⚙️', 'PREMIUM_EMOJI_GEAR_ID')}  <b>𝗠𝗲𝘁𝗵𝗼𝗱</b>  ╌  {method}"
                    )),
                    parse_mode=ParseMode.HTML,
                )
            try: await msg.delete()
            except: pass

    except Exception as e:
        logger.error(f"Decode error: {e}")
        await safe_edit(
            msg,
            "╔══════════════════╗\n"
            "  ❌  <b>𝗗𝗲𝗰𝗼𝗱𝗲 𝗙𝗮𝗶𝗹𝗲𝗱</b>\n"
            "╚══════════════════╝\n\n"
            f"<code>{e}</code>",
            parse_mode=ParseMode.HTML)

# ══════════════════════════════════════════════════════
#   DEVELOPER INFO  — New Design
# ══════════════════════════════════════════════════════
async def _dev_info(update, context):
    txt = (
        "╔══════════════════════════╗\n"
        f"  {_premium_emoji('🧑‍💻', 'PREMIUM_EMOJI_DEVELOPER_ID')}  <b>𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿 𝗣𝗿𝗼𝗳𝗶𝗹𝗲</b>\n"
        "╚══════════════════════════╝\n\n"
        "🏷  <b>𝗡𝗮𝗺𝗲</b>   ╌  𝘽𝘿 𝘼𝙇𝘼𝙈𝙄𝙉\n\n"
        "🎯  <b>𝗗𝗿𝗲𝗮𝗺</b>  ╌  𝙃𝙖𝙘𝙠𝙞𝙣𝙜  ♦  𝙏𝙧𝙖𝙙𝙞𝙣𝙜  ♦  𝙈𝙤𝙣𝙚𝙮\n\n"
        "💡  <b>𝗪𝗼𝗿𝗸</b>   ╌  𝙉𝙤𝙩 𝘼𝙣𝙮𝙩𝙝𝙞𝙣𝙜\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🛠  <b>𝗕𝗼𝘁 𝗜𝗻𝗳𝗼</b>\n\n"
        "◈  𝗽𝗵𝗽𝗸𝗼𝗯𝗼  𝙴𝚗𝚐𝚒𝚗𝚎\n"
        "◈  𝗥𝗗𝗫 𝘃𝟳.𝟭  𝙴𝚗𝚐𝚒𝚗𝚎\n"
        "◈  𝗦𝗲𝗿𝘃𝗲𝗿    𝙴𝚗𝚐𝚒𝚗𝚎\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "𝚃𝚑𝚊𝚗𝚔𝚜 𝚏𝚘𝚛 𝚟𝚒𝚜𝚒𝚝𝚒𝚗𝚐!  𝙷𝚒𝚝 𝚝𝚑𝚎 𝚋𝚞𝚝𝚝𝚘𝚗 ↓"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿",
                             url=f"https://t.me/{OWNER_USERNAME}",
                             style=_button_style("BUTTON_STYLE_CONTACT", "primary"),
                             icon_custom_emoji_id=_button_emoji("BUTTON_EMOJI_CONTACT"))
    ]])
    await _reply_html(update.message, txt, reply_markup=kb)

# ══════════════════════════════════════════════════════
#   BOT STATISTICS  — New Design
# ══════════════════════════════════════════════════════
async def _bot_status(update, context):
    pub  = sum(1 for c in db["channels"] if c.get("type","public") == "public")
    priv = sum(1 for c in db["channels"] if c.get("type") == "private")
    pk   = db["stats"].get("phpkobo", 0)
    samrat_mc = db["stats"].get("samrat_mc", 0)
    base_777 = db["stats"].get("base_777", 0)
    tms_cyber = db["stats"].get("tms_cyber", 0)
    rdx  = db["stats"].get("rdx", 0)
    srv  = db["stats"].get("server", 0)
    txt  = (
        "╔══════════════════════════╗\n"
        f"  {_premium_emoji('📊', 'PREMIUM_EMOJI_STATS_ID')}  <b>𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝗶𝘀𝘁𝗶𝗰𝘀</b>\n"
        "╚══════════════════════════╝\n\n"
        f"{_premium_emoji('👥', 'PREMIUM_EMOJI_USERS_ID')}  <b>𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀</b>     ╌  <b>{len(db['users'])}</b>\n\n"
        f"{_premium_emoji('⚡', 'PREMIUM_EMOJI_LIGHTNING_ID')}  <b>𝗗𝗲𝗰𝗼𝗱𝗲𝘀 𝗗𝗼𝗻𝗲</b>   ╌  <b>{db['stats'].get('total_decodes',0)}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "〔 𝗘𝗻𝗴𝗶𝗻𝗲 𝗕𝗿𝗲𝗮𝗸𝗱𝗼𝘄𝗻 〕\n\n"
        f"{_premium_emoji('⚡', 'PREMIUM_EMOJI_LIGHTNING_ID')}  <b>𝗽𝗵𝗽𝗸𝗼𝗯𝗼</b>  ╌  <b>{pk}</b>\n"
        f"🔐  <b>𝗦𝗔𝗠𝗥𝗔𝗧 𝗠𝗖</b>  ╌  <b>{samrat_mc}</b>\n"
        f"{_premium_emoji('🧱', 'PREMIUM_EMOJI_BASE777_ID')}  <b>𝗕𝗔𝗦𝗘 𝟳𝟳𝟳</b>  ╌  <b>{base_777}</b>\n"
        f"{_premium_emoji('🛡️', 'PREMIUM_EMOJI_TMS_DECODE_ID')}  <b>𝗧𝗠𝗦 𝗖𝗬𝗕𝗘𝗥</b>  ╌  <b>{tms_cyber}</b>\n"
        f"{_premium_emoji('🔓', 'PREMIUM_EMOJI_UNLOCK_ID')}  <b>𝗥𝗗𝗫 𝘃𝟳.𝟭</b>  ╌  <b>{rdx}</b>\n"
        f"{_premium_emoji('🖥️', 'PREMIUM_EMOJI_SERVER_ID')}  <b>𝗦𝗲𝗿𝘃𝗲𝗿</b>    ╌  <b>{srv}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{_premium_emoji('📡', 'PREMIUM_EMOJI_RADAR_ID')}  <b>𝗣𝘂𝗯 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀</b>   ╌  <b>{pub}</b>\n\n"
        f"🔐  <b>𝗣𝗿𝗶𝘃 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀</b>  ╌  <b>{priv}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🖤  𝙸 𝚕𝚘𝚟𝚎 𝚖𝚢 𝚞𝚜𝚎𝚛𝚜 — 𝚒𝚝'𝚜 𝚏𝚛𝚎𝚎."
    )
    await _reply_html(update.message, txt)

# ══════════════════════════════════════════════════════
#   ADMIN PANEL
# ══════════════════════════════════════════════════════
def _panel_text():
    pub  = sum(1 for c in db["channels"] if c.get("type","public") == "public")
    priv = sum(1 for c in db["channels"] if c.get("type") == "private")
    st   = "🟢  𝙾𝚗𝚕𝚒𝚗𝚎" if bot_active() else "🔴  𝙾𝚏𝚏𝚕𝚒𝚗𝚎"
    return (
        "╔══════════════════════════╗\n"
        "  👑  <b>𝗔𝗱𝗺𝗶𝗻  𝗣𝗮𝗻𝗲𝗹</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🤖  <b>𝗦𝘁𝗮𝘁𝘂𝘀</b>    ╌  {st}\n"
        f"👥  <b>𝗨𝘀𝗲𝗿𝘀</b>     ╌  <b>{len(db['users'])}</b>\n"
        f"{_premium_emoji('📡', 'PREMIUM_EMOJI_RADAR_ID')}  <b>𝗣𝘂𝗯 𝗖𝗵</b>   ╌  <b>{pub}</b>\n"
        f"🔐  <b>𝗣𝗿𝗶𝘃 𝗖𝗵</b>  ╌  <b>{priv}</b>\n"
        f"🛡  <b>𝗔𝗱𝗺𝗶𝗻𝘀</b>   ╌  <b>{len(db['admins'])}</b>\n"
        f"{_premium_emoji('⚡', 'PREMIUM_EMOJI_LIGHTNING_ID')}  <b>𝗗𝗲𝗰𝗼𝗱𝗲𝘀</b>  ╌  <b>{db['stats'].get('total_decodes',0)}</b>"
    )

def _panel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡  𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀",  callback_data="admin_channels"),
         InlineKeyboardButton("🛡  𝗔𝗱𝗺𝗶𝗻𝘀",    callback_data="admin_admins")],
        [InlineKeyboardButton("🚷  𝗕𝗮𝗻",         callback_data="admin_ban"),
         InlineKeyboardButton("✅  𝗨𝗻𝗯𝗮𝗻",       callback_data="admin_unban")],
        [InlineKeyboardButton("📣  𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁",  callback_data="admin_broadcast"),
         InlineKeyboardButton("🗄  𝗗𝗕 𝗘𝘅𝗽𝗼𝗿𝘁", callback_data="admin_export")],
        [InlineKeyboardButton("🔴  𝗧𝘂𝗿𝗻 𝗕𝗼𝘁 𝗢𝗙𝗙" if bot_active() else "🟢  𝗧𝘂𝗿𝗻 𝗕𝗼𝘁 𝗢𝗡",
                              callback_data="admin_toggle_bot")],
    ])

async def _show_admin_panel(update, context):
    await _reply_html(update.message, _panel_text(), reply_markup=_panel_kb())

# ══════════════════════════════════════════════════════
#   COMMAND HANDLERS
# ══════════════════════════════════════════════════════
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    if not bot_active() and not is_admin(user.id):
        await _reply_text(update.message, "🔴  𝗕𝗼𝘁 𝗶𝘀 𝗼𝗳𝗳𝗹𝗶𝗻𝗲.  𝙿𝚕𝚎𝚊𝚜𝚎 𝚝𝚛𝚢 𝚊𝚐𝚊𝚒𝚗 𝚕𝚊𝚝𝚎𝚛."); return
    if is_banned(user.id):
        await _reply_html(update.message, ban_text(user.id)); return
    joined, missing = await check_channels(context.bot, user.id)
    if not joined:
        n = len(missing)
        await _reply_html(update.message, 
            "╔══════════════════════════╗\n"
            f"  {_premium_emoji('📡', 'PREMIUM_EMOJI_RADAR_ID')}  <b>𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻</b>\n"
            "╚══════════════════════════╝\n\n"
            f"𝙹𝚘𝚒𝚗 <b>{n}</b> 𝚌𝚑𝚊𝚗𝚗𝚎𝚕{'𝚜' if n>1 else ''} 𝚝𝚘 𝚞𝚜𝚎 𝚝𝚑𝚒𝚜 𝚋𝚘𝚝.\n\n"
            "𝚃𝚊𝚙 𝚋𝚎𝚕𝚘𝚠 𝚝𝚘 𝚓𝚘𝚒𝚗, 𝚝𝚑𝚎𝚗 𝚙𝚛𝚎𝚜𝚜 𝚝𝚑𝚎 𝚋𝚞𝚝𝚝𝚘𝚗 ↓",
            reply_markup=joined_reply_kb(),
        )
        await _reply_text(update.message, f"{_premium_emoji('🗂', 'PREMIUM_EMOJI_FOLDER_ID')}  𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝘁𝗼 𝗝𝗼𝗶𝗻:", parse_mode=ParseMode.HTML, reply_markup=channels_inline_kb(missing))
        return
    await send_welcome(context.bot, user.id, user.first_name)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data.startswith("admin_"):
        if not is_admin(q.from_user.id):
            await q.answer("❌  𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱!", show_alert=True); return
        await _admin_cb(update, context, q.data)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not bot_active() and not is_admin(user.id): return
    if is_banned(user.id): return
    if not context.user_data.get("waiting_for_html"):
        await _reply_html(update.message, 
            f"⚠️  𝙿𝚛𝚎𝚜𝚜  <b>{_premium_emoji('⚡', 'PREMIUM_EMOJI_LIGHTNING_ID')} 𝗛𝗧𝗠𝗟 𝗗𝗲𝗰𝗼𝗱𝗲𝗿</b>  𝚏𝚒𝚛𝚜𝚝.", reply_markup=main_kb()); return
    doc   = update.message.document
    fname = doc.file_name or "file.html"
    if not (fname.lower().endswith(".html") or fname.lower().endswith(".htm")):
        await _reply_html(update.message, "⚠️  𝙾𝚗𝚕𝚢 <b>.html</b> / <b>.htm</b> 𝚏𝚒𝚕𝚎𝚜 𝚜𝚞𝚙𝚙𝚘𝚛𝚝𝚎𝚍."); return
    context.user_data["waiting_for_html"] = False
    await _do_decode(update, context, doc, fname)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ""

    if text == "#000000":
        if is_admin(user.id): await _show_admin_panel(update, context)
        else: await _reply_text(update.message, "❌  𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱.")
        return

    action = context.user_data.get("admin_action")
    if action and is_admin(user.id):
        await _process_admin_input(update, context, action, text); return

    if not bot_active() and not is_admin(user.id):
        await _reply_text(update.message, "🔴  𝗕𝗼𝘁 𝗶𝘀 𝗼𝗳𝗳𝗹𝗶𝗻𝗲."); return
    if is_banned(user.id): return
    if context.user_data.get("waiting_for_html"):
        await _reply_text(update.message, f"{_premium_emoji('🗂', 'PREMIUM_EMOJI_FOLDER_ID')}  𝙿𝚕𝚎𝚊𝚜𝚎 𝚜𝚎𝚗𝚍 𝚊 .𝚑𝚝𝚖𝚕 𝚏𝚒𝚕𝚎.", parse_mode=ParseMode.HTML); return

    if "𝗜'𝘃𝗲 𝗝𝗼𝗶𝗻𝗲𝗱" in text or "Joined" in text:
        rec = db["users"].setdefault(user.id, {"username":"","name":"","joined":"","banned":False,"private_acked":[]})
        if "private_acked" not in rec: rec["private_acked"] = []
        for ch in db["channels"]:
            if ch.get("type")=="private" and ch["id"] not in rec["private_acked"]:
                rec["private_acked"].append(ch["id"])
        save_db(db)
        joined, missing = await check_channels(context.bot, user.id)
        if not joined:
            n = len(missing)
            await _reply_html(update.message, 
                f"⚠️  <b>𝗡𝗼𝘁 𝗬𝗲𝘁!</b>  𝚂𝚝𝚒𝚕𝚕 <b>{n}</b> 𝚌𝚑𝚊𝚗𝚗𝚎𝚕{'𝚜' if n>1 else ''} 𝚙𝚎𝚗𝚍𝚒𝚗𝚐 ↓",
                reply_markup=joined_reply_kb())
            await _reply_text(update.message, f"{_premium_emoji('🗂', 'PREMIUM_EMOJI_FOLDER_ID')}  𝗣𝗲𝗻𝗱𝗶𝗻𝗴 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀:", parse_mode=ParseMode.HTML, reply_markup=channels_inline_kb(missing))
            return
        if is_banned(user.id): await _reply_html(update.message, ban_text(user.id)); return
        await send_welcome(context.bot, user.id, user.first_name); return

    if "𝗛𝗧𝗠𝗟 𝗗𝗲𝗰𝗼𝗱𝗲𝗿" in text or "Decode" in text:
        joined, missing = await check_channels(context.bot, user.id)
        if not joined:
            n = len(missing)
            await _reply_html(update.message, 
                f"{_premium_emoji('📡', 'PREMIUM_EMOJI_RADAR_ID')}  <b>𝗝𝗼𝗶𝗻 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱</b>  ╌  𝙹𝚘𝚒𝚗 <b>{n}</b> 𝚌𝚑𝚊𝚗𝚗𝚎𝚕{'𝚜' if n>1 else ''} 𝚏𝚒𝚛𝚜𝚝 ↓",
                reply_markup=joined_reply_kb())
            await _reply_text(update.message, f"{_premium_emoji('🗂', 'PREMIUM_EMOJI_FOLDER_ID')}  𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀:", parse_mode=ParseMode.HTML, reply_markup=channels_inline_kb(missing)); return
        await _decode_start(update, context)

    elif "𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿" in text or "Developer" in text:
        joined, missing = await check_channels(context.bot, user.id)
        if not joined:
            n = len(missing)
            await _reply_html(update.message, 
                f"{_premium_emoji('📡', 'PREMIUM_EMOJI_RADAR_ID')}  <b>𝗝𝗼𝗶𝗻 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱</b>  ╌  𝙹𝚘𝚒𝚗 <b>{n}</b> 𝚌𝚑𝚊𝚗𝚗𝚎𝚕{'𝚜' if n>1 else ''} 𝚏𝚒𝚛𝚜𝚝 ↓",
                reply_markup=joined_reply_kb())
            await _reply_text(update.message, f"{_premium_emoji('🗂', 'PREMIUM_EMOJI_FOLDER_ID')}  𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀:", parse_mode=ParseMode.HTML, reply_markup=channels_inline_kb(missing)); return
        await _dev_info(update, context)

    # Statistics hidden from users — accessible via admin panel only

# ══════════════════════════════════════════════════════
#   ADMIN CALLBACK ROUTER
# ══════════════════════════════════════════════════════
async def _admin_cb(update, context, data):
    q = update.callback_query
    async def edit(txt, kb=None):
        try: await q.message.edit_text(_premiumize_html(txt), parse_mode=ParseMode.HTML, reply_markup=kb)
        except: pass

    if data == "admin_back": await edit(_panel_text(), _panel_kb())

    elif data == "admin_toggle_bot":
        db["settings"]["bot_active"] = not bot_active(); save_db(db)
        await q.answer(f"Bot is now {'Online' if bot_active() else 'Offline'}!", show_alert=True)
        await edit(_panel_text(), _panel_kb())

    elif data == "admin_export":
        try:
            with open(DB_FILE,"rb") as f:
                await context.bot.send_document(q.from_user.id, f, filename="database.pkl",
                                                caption="🗄  𝗗𝗮𝘁𝗮𝗯𝗮𝘀𝗲 𝚎𝚡𝚙𝚘𝚛𝚝𝚎𝚍!")
            await q.answer("✅  Sent!", show_alert=True)
        except Exception as e: await q.answer(f"❌ {e}", show_alert=True)

    elif data == "admin_channels":
        txt = f"╔══════════════════════╗\n  {_premium_emoji('📡', 'PREMIUM_EMOJI_RADAR_ID')}  <b>𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝗟𝗶𝘀𝘁</b>\n╚══════════════════════╝\n\n"
        for i,ch in enumerate(db["channels"],1):
            is_public = ch.get("type", "public") == "public"
            icon = _premium_emoji("📡", "PREMIUM_EMOJI_RADAR_ID") if is_public else _premium_emoji("🔐", "PREMIUM_EMOJI_LOCK_ID")
            lbl  = "𝗣𝘂𝗯𝗹𝗶𝗰" if ch.get("type","public")=="public" else "𝗣𝗿𝗶𝘃𝗮𝘁𝗲"
            txt += f"  {i}.  {icon}  <b>{ch.get('name','?')}</b>  ╌  {lbl}\n"
        if not db["channels"]: txt += "  𝙽𝚘 𝚌𝚑𝚊𝚗𝚗𝚎𝚕𝚜 𝚊𝚍𝚍𝚎𝚍 𝚢𝚎𝚝."
        await edit(txt, InlineKeyboardMarkup([
            [InlineKeyboardButton("➕  𝗔𝗱𝗱 𝗣𝘂𝗯𝗹𝗶𝗰",  callback_data="admin_add_public_channel"),
             InlineKeyboardButton("➕  𝗔𝗱𝗱 𝗣𝗿𝗶𝘃𝗮𝘁𝗲", callback_data="admin_add_private_channel")],
            [InlineKeyboardButton("🗑  𝗥𝗲𝗺𝗼𝘃𝗲",      callback_data="admin_remove_channel")],
            [InlineKeyboardButton("🔙  𝗕𝗮𝗰𝗸",         callback_data="admin_back")],
        ]))

    elif data == "admin_add_public_channel":
        context.user_data["admin_action"] = "add_public_channel"
        await edit(
            "📡  <b>𝗔𝗱𝗱 𝗣𝘂𝗯𝗹𝗶𝗰 𝗖𝗵𝗮𝗻𝗻𝗲𝗹</b>\n\n"
            "𝚂𝚎𝚗𝚍 𝚒𝚗 𝚝𝚑𝚒𝚜 𝚏𝚘𝚛𝚖𝚊𝚝:\n\n"
            "<code>CHANNEL_ID | CHANNEL_LINK</code>\n\n"
            "𝙾𝚛 𝚓𝚞𝚜𝚝: <code>@username</code>\n\n"
            "⚠️  𝙱𝚘𝚝 𝚖𝚞𝚜𝚝 𝚋𝚎 𝚊𝚗 <b>𝗔𝗱𝗺𝗶𝗻</b> 𝚘𝚏 𝚝𝚑𝚎 𝚌𝚑𝚊𝚗𝚗𝚎𝚕."
        )

    elif data == "admin_add_private_channel":
        context.user_data["admin_action"] = "add_private_channel"
        await edit(
            "🔐  <b>𝗔𝗱𝗱 𝗣𝗿𝗶𝘃𝗮𝘁𝗲 𝗖𝗵𝗮𝗻𝗻𝗲𝗹</b>\n\n"
            "𝚂𝚎𝚗𝚍 𝚒𝚗 𝚝𝚑𝚒𝚜 𝚏𝚘𝚛𝚖𝚊𝚝:\n\n"
            "<code>CHANNEL_ID | INVITATION_LINK</code>\n\n"
            "𝙴𝚡: <code>-1001234567890 | https://t.me/+aBcD</code>\n\n"
            "📌  𝙻𝚒𝚗𝚔 𝚖𝚞𝚜𝚝 𝚜𝚝𝚊𝚛𝚝 𝚠𝚒𝚝𝚑 <b>https://t.me/+</b>"
        )

    elif data == "admin_remove_channel":
        if not db["channels"]: await q.answer("No channels!", show_alert=True); return
        rows = [[InlineKeyboardButton(
            f"🗑  {'📡' if ch.get('type','public')=='public' else '🔐'}  {ch.get('name','?')}",
            callback_data=f"admin_del_ch_{i}")] for i,ch in enumerate(db["channels"])]
        rows.append([InlineKeyboardButton("🔙  𝗕𝗮𝗰𝗸", callback_data="admin_channels")])
        await edit("🗑  <b>𝗦𝗲𝗹𝗲𝗰𝘁 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝘁𝗼 𝗥𝗲𝗺𝗼𝘃𝗲:</b>", InlineKeyboardMarkup(rows))

    elif data.startswith("admin_del_ch_"):
        idx = int(data.split("_")[-1])
        if 0 <= idx < len(db["channels"]):
            name = db["channels"].pop(idx).get("name","?"); save_db(db)
            await q.answer(f"✅ {name} removed!", show_alert=True)
            await _admin_cb(update, context, "admin_channels")

    elif data == "admin_admins":
        txt = "╔══════════════════════╗\n  🛡  <b>𝗔𝗱𝗺𝗶𝗻 𝗟𝗶𝘀𝘁</b>\n╚══════════════════════╝\n\n"
        for aid in db["admins"]:
            ud = db["users"].get(aid,{}); txt += f"  ◈  {ud.get('name','Unknown')}  ╌  <code>{aid}</code>\n"
        if not db["admins"]: txt += "  𝙽𝚘 𝚊𝚍𝚖𝚒𝚗𝚜 𝚊𝚍𝚍𝚎𝚍."
        await edit(txt, InlineKeyboardMarkup([
            [InlineKeyboardButton("➕  𝗔𝗱𝗱 𝗔𝗱𝗺𝗶𝗻",    callback_data="admin_add_admin"),
             InlineKeyboardButton("🗑  𝗥𝗲𝗺𝗼𝘃𝗲 𝗔𝗱𝗺𝗶𝗻", callback_data="admin_remove_admin")],
            [InlineKeyboardButton("🔙  𝗕𝗮𝗰𝗸",          callback_data="admin_back")],
        ]))

    elif data == "admin_add_admin":
        context.user_data["admin_action"] = "add_admin"
        await edit("🛡  𝚂𝚎𝚗𝚍 𝚝𝚑𝚎 𝚄𝚜𝚎𝚛 𝙸𝙳 𝚘𝚏 𝚝𝚑𝚎 𝚗𝚎𝚠 𝚊𝚍𝚖𝚒𝚗:")

    elif data == "admin_remove_admin":
        if not db["admins"]: await q.answer("No admins!", show_alert=True); return
        rows = [[InlineKeyboardButton(
            f"🗑  {db['users'].get(aid,{}).get('name','Unknown')}  ({aid})",
            callback_data=f"admin_del_adm_{aid}")] for aid in db["admins"]]
        rows.append([InlineKeyboardButton("🔙  𝗕𝗮𝗰𝗸", callback_data="admin_admins")])
        await edit("🗑  <b>𝗦𝗲𝗹𝗲𝗰𝘁 𝗔𝗱𝗺𝗶𝗻 𝘁𝗼 𝗥𝗲𝗺𝗼𝘃𝗲:</b>", InlineKeyboardMarkup(rows))

    elif data.startswith("admin_del_adm_"):
        aid = int(data.split("_")[-1])
        if aid in db["admins"]:
            db["admins"].remove(aid); save_db(db)
            await q.answer("✅ Admin removed!", show_alert=True)
            await _admin_cb(update, context, "admin_admins")

    elif data == "admin_ban":
        context.user_data["admin_action"] = "ban_user"
        await edit("🚷  𝚂𝚎𝚗𝚍 𝚝𝚑𝚎 𝚄𝚜𝚎𝚛 𝙸𝙳 𝚝𝚘 𝚋𝚊𝚗:")

    elif data == "admin_unban":
        context.user_data["admin_action"] = "unban_user"
        await edit("✅  𝚂𝚎𝚗𝚍 𝚝𝚑𝚎 𝚄𝚜𝚎𝚛 𝙸𝙳 𝚝𝚘 𝚞𝚗𝚋𝚊𝚗:")

    elif data == "admin_broadcast":
        context.user_data["admin_action"] = "broadcast"
        await edit(
            "📣  <b>𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁</b>\n\n"
            "𝚃𝚢𝚙𝚎 𝚢𝚘𝚞𝚛 𝚖𝚎𝚜𝚜𝚊𝚐𝚎. 𝚃𝚘 𝚊𝚍𝚍 𝚋𝚞𝚝𝚝𝚘𝚗𝚜:\n\n"
            "<code>Message text\nButton Label|https://link.com</code>"
        )

# ══════════════════════════════════════════════════════
#   ADMIN INPUT PROCESSOR
# ══════════════════════════════════════════════════════
async def _process_admin_input(update, context, action, text):
    context.user_data.pop("admin_action", None)

    if action == "add_public_channel":
        raw = text.strip()
        if raw.startswith("@"):
            try:
                chat = await context.bot.get_chat(raw)
                link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat.id).lstrip('-100')}"
                ch   = {"id":chat.id,"name":chat.title or str(chat.id),"type":"public","link":link,"username":f"@{chat.username}" if chat.username else ""}
                if chat.id in [c["id"] for c in db["channels"]]:
                    await _reply_text(update.message, "⚠️  𝙲𝚑𝚊𝚗𝚗𝚎𝚕 𝚊𝚕𝚛𝚎𝚊𝚍𝚢 𝚒𝚗 𝚕𝚒𝚜𝚝!")
                else:
                    db["channels"].append(ch); save_db(db)
                    await _reply_html(update.message, f"✅  <b>{chat.title}</b> 𝚊𝚍𝚍𝚎𝚍!\n{_premium_emoji('📋', 'PREMIUM_EMOJI_CLIPBOARD_ID')}  𝗜𝗗  ╌  <code>{chat.id}</code>\n🔗  {link}")
            except: await _reply_html(update.message, "❌  𝙲𝚑𝚊𝚗𝚗𝚎𝚕 𝚗𝚘𝚝 𝚏𝚘𝚞𝚗𝚍. 𝙼𝚊𝚔𝚎 𝚜𝚞𝚛𝚎 𝚋𝚘𝚝 𝚒𝚜 𝚊𝚗 𝙰𝚍𝚖𝚒𝚗.")
        elif "|" in raw:
            p = [x.strip() for x in raw.split("|",1)]
            try:
                ch_id=int(p[0]); lnk=p[1]
                if not lnk.startswith("https://t.me/"): await _reply_text(update.message, "❌  𝙸𝚗𝚟𝚊𝚕𝚒𝚍 𝚕𝚒𝚗𝚔 𝚏𝚘𝚛𝚖𝚊𝚝."); return
                name=str(ch_id)
                try:
                    chat=await context.bot.get_chat(ch_id); name=chat.title or name
                except: pass
                if ch_id in [c["id"] for c in db["channels"]]: await _reply_text(update.message, "⚠️  𝙰𝚕𝚛𝚎𝚊𝚍𝚢 𝚒𝚗 𝚕𝚒𝚜𝚝!")
                else:
                    db["channels"].append({"id":ch_id,"name":name,"type":"public","link":lnk,"username":""}); save_db(db)
                    await _reply_html(update.message, f"✅  <b>{name}</b> 𝚊𝚍𝚍𝚎𝚍!\n{_premium_emoji('📋', 'PREMIUM_EMOJI_CLIPBOARD_ID')}  𝗜𝗗  ╌  <code>{ch_id}</code>\n🔗  {lnk}")
            except ValueError: await _reply_text(update.message, "❌  𝙸𝚗𝚟𝚊𝚕𝚒𝚍 𝙲𝚑𝚊𝚗𝚗𝚎𝚕 𝙸𝙳.")
        else: await _reply_html(update.message, "❌  𝚄𝚜𝚎: <code>@username</code>  𝚘𝚛  <code>ID | LINK</code>")

    elif action == "add_private_channel":
        raw = text.strip()
        if "|" not in raw: await _reply_html(update.message, "❌  𝚄𝚜𝚎: <code>CHANNEL_ID | INVITATION_LINK</code>"); return
        p = [x.strip() for x in raw.split("|",1)]
        try:
            ch_id=int(p[0]); inv=p[1]
            if not (inv.startswith("https://t.me/+") or inv.startswith("https://t.me/joinchat/")):
                await _reply_text(update.message, "❌  𝙻𝚒𝚗𝚔 𝚖𝚞𝚜𝚝 𝚜𝚝𝚊𝚛𝚝 𝚠𝚒𝚝𝚑 https://t.me/+"); return
            name=str(ch_id)
            try:
                chat=await context.bot.get_chat(ch_id); name=chat.title or name
            except: pass
            if ch_id in [c["id"] for c in db["channels"]]: await _reply_text(update.message, "⚠️  𝙰𝚕𝚛𝚎𝚊𝚍𝚢 𝚒𝚗 𝚕𝚒𝚜𝚝!")
            else:
                db["channels"].append({"id":ch_id,"name":name,"type":"private","link":inv,"username":""}); save_db(db)
                await _reply_html(update.message, f"✅  <b>{name}</b> 𝚊𝚍𝚍𝚎𝚍!\n{_premium_emoji('📋', 'PREMIUM_EMOJI_CLIPBOARD_ID')}  𝗜𝗗  ╌  <code>{ch_id}</code>\n🔗  {inv}")
        except ValueError: await _reply_text(update.message, "❌  𝙸𝚗𝚟𝚊𝚕𝚒𝚍 𝙲𝚑𝚊𝚗𝚗𝚎𝚕 𝙸𝙳.")

    elif action == "add_admin":
        try:
            aid=int(text.strip())
            if aid==OWNER_ID: await _reply_text(update.message, "⚠️  𝙾𝚠𝚗𝚎𝚛 𝚊𝚕𝚛𝚎𝚊𝚍𝚢 𝚑𝚊𝚜 𝚑𝚒𝚐𝚑𝚎𝚜𝚝 𝚊𝚞𝚝𝚑𝚘𝚛𝚒𝚝𝚢!")
            elif aid in db["admins"]: await _reply_text(update.message, "⚠️  𝙰𝚕𝚛𝚎𝚊𝚍𝚢 𝚊𝚗 𝚊𝚍𝚖𝚒𝚗!")
            else:
                db["admins"].append(aid); save_db(db)
                await _reply_html(update.message, f"✅  𝙸𝙳 <code>{aid}</code> 𝚒𝚜 𝚗𝚘𝚠 𝚊𝚗 𝚊𝚍𝚖𝚒𝚗!")
        except ValueError: await _reply_text(update.message, "❌  𝚂𝚎𝚗𝚍 𝚊 𝚟𝚊𝚕𝚒𝚍 𝚄𝚜𝚎𝚛 𝙸𝙳.")

    elif action == "ban_user":
        try:
            bid=int(text.strip())
            if bid==OWNER_ID: await _reply_text(update.message, "❌  𝙾𝚠𝚗𝚎𝚛 𝚌𝚊𝚗𝚗𝚘𝚝 𝚋𝚎 𝚋𝚊𝚗𝚗𝚎𝚍!")
            else:
                if bid not in db["users"]: db["users"][bid]={"username":"","name":"Unknown","joined":"","banned":True,"private_acked":[]}
                else: db["users"][bid]["banned"]=True
                save_db(db); await _reply_html(update.message, f"✅  𝙸𝙳 <code>{bid}</code> 𝚋𝚊𝚗𝚗𝚎𝚍!")
        except ValueError: await _reply_text(update.message, "❌  𝚂𝚎𝚗𝚍 𝚊 𝚟𝚊𝚕𝚒𝚍 𝚄𝚜𝚎𝚛 𝙸𝙳.")

    elif action == "unban_user":
        try:
            uid=int(text.strip())
            if uid in db["users"]:
                db["users"][uid]["banned"]=False; save_db(db)
                await _reply_html(update.message, f"✅  𝙸𝙳 <code>{uid}</code> 𝚞𝚗𝚋𝚊𝚗𝚗𝚎𝚍!")
            else: await _reply_text(update.message, "⚠️  𝙸𝙳 𝚗𝚘𝚝 𝚒𝚗 𝚍𝚊𝚝𝚊𝚋𝚊𝚜𝚎.")
        except ValueError: await _reply_text(update.message, "❌  𝚂𝚎𝚗𝚍 𝚊 𝚟𝚊𝚕𝚒𝚍 𝚄𝚜𝚎𝚛 𝙸𝙳.")

    elif action == "broadcast":
        lines=text.strip().split("\n"); msg_lines=[]; btn_rows=[]
        for line in lines:
            if "|" in line:
                p=line.split("|",1)
                if p[1].strip().startswith("http"): btn_rows.append([InlineKeyboardButton(p[0].strip(), url=p[1].strip())]); continue
            msg_lines.append(line)
        btxt="\n".join(msg_lines).strip(); markup=InlineKeyboardMarkup(btn_rows) if btn_rows else None
        total=len(db["users"]); ok=fail=0
        prog=await _reply_text(update.message, f"📣  𝙱𝚛𝚘𝚊𝚍𝚌𝚊𝚜𝚝𝚒𝚗𝚐...  0/{total}")
        for uid in list(db["users"].keys()):
            try: await context.bot.send_message(uid,btxt,reply_markup=markup); ok+=1
            except: fail+=1
            await asyncio.sleep(0.05)  # ~20 sends/s to stay under global rate limit
            if (ok+fail)%20==0 or (ok+fail)==total:
                await safe_edit(prog, f"📣  𝙱𝚛𝚘𝚊𝚍𝚌𝚊𝚜𝚝𝚒𝚗𝚐...\n✅ {ok}  ❌ {fail}  /  {total}")
        await safe_edit(
            prog,
            "╔══════════════════════╗\n  📣  <b>𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲!</b>\n╚══════════════════════╝\n\n"
            f"✅  𝚂𝚎𝚗𝚝    ╌  <b>{ok}</b>\n❌  𝙵𝚊𝚒𝚕𝚎𝚍  ╌  <b>{fail}</b>\n👥  𝚃𝚘𝚝𝚊𝚕   ╌  <b>{total}</b>",
            parse_mode=ParseMode.HTML)

# ══════════════════════════════════════════════════════
#   MAIN
# ══════════════════════════════════════════════════════
def main():
    check_node_js()
    Thread(target=run_flask, daemon=True).start()
    logger.info("Flask keep-alive started.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Bot polling started.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
