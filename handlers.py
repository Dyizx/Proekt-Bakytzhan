import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes

from settings import API_KEY
from data import CATEGORIES, TOP_50_GAMES, user_history
from utils import translate_kz, add_to_history
from services import get_steam_link, get_youtube_review, fetch_game_data


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Топ 50 ойын", callback_data="goto_top50")],
        [InlineKeyboardButton("🎲 Кездейсоқ ойын", callback_data="random")],
        [InlineKeyboardButton("📜 Тарих", callback_data="history")],
    ]
    text = (
        "👋 Сәлем! Мен ойындар туралы ақпарат беретін ботпын.\n\n"
        "📌 Командалар:\n"
        "🔹 Ойын атын жаз — толық ақпарат аласың\n"
        "🔹 /top50 — үздік 50 ойын тізімі\n"
        "🔹 /random — кездейсоқ ойын\n"
        "🔹 /history — іздеу тарихы\n"
        "🔹 /clear — тарихты тазалау\n"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def top50(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"cat:{cat}")]
        for cat in CATEGORIES
    ]
    keyboard.append([InlineKeyboardButton("🎲 Кездейсоқ ойын", callback_data="random")])
    keyboard.append([InlineKeyboardButton("📜 Тарих", callback_data="history")])
    await update.message.reply_text(
        "🎮 Санатты таңда:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    history = user_history.get(user_id, [])
    if not history:
        await update.message.reply_text("📜 Тарих бос.\n\nОйын атын жазып іздеп көр!")
        return
    keyboard = [
        [InlineKeyboardButton(f"🎮 {g}", callback_data=f"game:{g}")]
        for g in history
    ]
    keyboard.append([InlineKeyboardButton("🗑 Тарихты тазалау", callback_data="clear_history")])
    keyboard.append([InlineKeyboardButton("⬅️ Артқа", callback_data="back_main")])
    await update.message.reply_text(
        "📜 *Іздеу тарихы:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def clear_history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_history[user_id] = []
    await update.message.reply_text("🗑 Тарих тазаланды!")


async def random_game_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_name = random.choice(TOP_50_GAMES)
    await update.message.reply_text(
        f"🎲 Кездейсоқ ойын: *{game_name}*\nАқпарат іздеуде...",
        parse_mode="Markdown"
    )
    update.message.text = game_name
    await get_game(update, context)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async def send_text(text, **kwargs):
        await query.message.reply_text(text, **kwargs)

    async def send_photo(photo, caption, **kwargs):
        await query.message.reply_photo(photo=photo, caption=caption, **kwargs)

    async def send_media_group(media, **kwargs):
        await query.message.reply_media_group(media, **kwargs)

    if query.data == "history":
        history = user_history.get(user_id, [])
        if not history:
            await query.message.reply_text("📜 Тарих бос.\n\nОйын атын жазып іздеп көр!")
            return
        keyboard = [
            [InlineKeyboardButton(f"🎮 {g}", callback_data=f"game:{g}")]
            for g in history
        ]
        keyboard.append([InlineKeyboardButton("🗑 Тарихты тазалау", callback_data="clear_history")])
        keyboard.append([InlineKeyboardButton("⬅️ Артқа", callback_data="back_main")])
        await query.message.reply_text(
            "📜 *Іздеу тарихы:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "clear_history":
        user_history[user_id] = []
        await query.edit_message_text("🗑 Тарих тазаланды!")

    elif query.data == "random":
        game_name = random.choice(TOP_50_GAMES)
        await query.message.reply_text(
            f"🎲 Кездейсоқ ойын: *{game_name}*\nАқпарат іздеуде...",
            parse_mode="Markdown"
        )
        add_to_history(user_id, game_name)
        await fetch_and_send_game(game_name, send_text, send_photo, send_media_group, user_id)

    elif query.data == "goto_top50":
        keyboard = [
            [InlineKeyboardButton(cat, callback_data=f"cat:{cat}")]
            for cat in CATEGORIES
        ]
        keyboard.append([InlineKeyboardButton("🎲 Кездейсоқ ойын", callback_data="random")])
        keyboard.append([InlineKeyboardButton("⬅️ Артқа", callback_data="back_main")])
        await query.edit_message_text(
            "🎮 Санатты таңда:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("cat:"):
        cat = query.data[4:]
        games = CATEGORIES.get(cat, [])
        keyboard = [
            [InlineKeyboardButton(f"🎮 {g}", callback_data=f"game:{g}")]
            for g in games
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Артқа", callback_data="goto_top50")])
        keyboard.append([InlineKeyboardButton("🚫 Бас тарту", callback_data="cancel")])
        await query.edit_message_text(
            f"{cat}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "back_main":
        keyboard = [
            [InlineKeyboardButton("🎮 Топ 50 ойын", callback_data="goto_top50")],
            [InlineKeyboardButton("🎲 Кездейсоқ ойын", callback_data="random")],
            [InlineKeyboardButton("📜 Тарих", callback_data="history")],
        ]
        await query.edit_message_text(
            "👋 Басты мәзір:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "cancel":
        await query.edit_message_text("🚫 Бас тартылды. Ойын атын жазып іздей аласың.")

    elif query.data.startswith("game:"):
        game_name = query.data[5:]
        await query.message.reply_text(
            f"🔍 *{game_name}* іздеуде...",
            parse_mode="Markdown"
        )
        add_to_history(user_id, game_name)
        await fetch_and_send_game(game_name, send_text, send_photo, send_media_group, user_id)

    elif query.data == "delete_msg":
        await query.message.delete()


async def get_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_name = update.message.text
    user_id = update.message.from_user.id

    async def send_text(text, **kwargs):
        await update.message.reply_text(text, **kwargs)

    async def send_photo(photo, caption, **kwargs):
        await update.message.reply_photo(photo=photo, caption=caption, **kwargs)

    async def send_media_group(media, **kwargs):
        await update.message.reply_media_group(media, **kwargs)

    add_to_history(user_id, game_name)
    await fetch_and_send_game(game_name, send_text, send_photo, send_media_group, user_id)


async def fetch_and_send_game(game_name, send_text, send_photo, send_media_group, user_id=None):
    result = fetch_game_data(game_name)

    if not result:
        await send_text("Ойын табылмады ❌")
        return

    game, details, screenshots = result

    name = game["name"]
    rating = game.get("rating", 0)
    rating_count = game.get("ratings_count", 0)
    platforms = [p["platform"]["name"] for p in game.get("platforms", [])]
    platforms_text = ", ".join(platforms) if platforms else "Деректер жоқ"
    cover = game.get("background_image")

    genres = [g["name"] for g in details.get("genres", [])]
    genres_text = translate_kz(", ".join(genres)) if genres else "Деректер жоқ"

    developers = [d["name"] for d in details.get("developers", [])]
    developers_text = ", ".join(developers) if developers else "Деректер жоқ"

    publishers = [p["name"] for p in details.get("publishers", [])]
    publishers_text = ", ".join(publishers) if publishers else "Деректер жоқ"

    release_date = details.get("released", "Деректер жоқ")
    website = details.get("website", "")

    description_raw = details.get("description_raw", "")
    description_short = description_raw[:1000] if description_raw else ""
    description = translate_kz(description_short) if description_short else "Сипаттама жоқ"

    req_minimum = "Деректер жоқ"
    req_recommended = "Деректер жоқ"
    for p in details.get("platforms", []):
        if p["platform"]["slug"] == "pc":
            req = p.get("requirements_en") or p.get("requirements")
            if req:
                req_minimum = translate_kz(req.get("minimum", "Деректер жоқ"))
                req_recommended = translate_kz(req.get("recommended", "Деректер жоқ"))
            break

    steam_link = get_steam_link(name)
    youtube_link = get_youtube_review(name)

    stars = "⭐" * round(rating) + "☆" * (5 - round(rating))

    card = f"""🎮 *{name}*
📅 Шыққан күні: {release_date}
🏢 Әзірлеуші: {developers_text}
🏷 Баспагер: {publishers_text}
🎭 Жанр: {genres_text}
🖥 Платформалар: {platforms_text}

{stars} *{rating}/5* ({rating_count:,} баға)

📖 *Сипаттама:*
{description}
"""
    if website:
        card += f"\n🌐 [Ресми сайт]({website})"

    req_text = f"""⚙️ *Жүйелік талаптар (ДК):*

🔻 *Ең төменгі:*
{req_minimum}

🔺 *Ұсынылатын:*
{req_recommended}
"""

    action_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Steam-да сатып ал", url=steam_link)],
        [InlineKeyboardButton("▶️ YouTube шолу", url=youtube_link)],
        [
            InlineKeyboardButton("📜 Тарих", callback_data="history"),
            InlineKeyboardButton("🎲 Кездейсоқ", callback_data="random"),
        ],
        [
            InlineKeyboardButton("🗑 Жою", callback_data="delete_msg"),
            InlineKeyboardButton("🚫 Бас тарту", callback_data="cancel"),
        ],
        [InlineKeyboardButton("⬅️ Артқа", callback_data="back_main")],
    ])

    if cover:
        await send_photo(cover, caption=card[:1024], parse_mode="Markdown")
    else:
        await send_text(card, parse_mode="Markdown")

    await send_text(req_text, parse_mode="Markdown", reply_markup=action_keyboard)

    if screenshots:
        media = [InputMediaPhoto(media=screenshots[0], caption="📸 Скриншоттар")]
        for s in screenshots[1:]:
            media.append(InputMediaPhoto(media=s))
        await send_media_group(media)