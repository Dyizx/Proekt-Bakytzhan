import random
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes

from settings import API_KEY
from data import CATEGORIES, TOP_50_GAMES, user_history
from utils import translate_kz, add_to_history
from services import get_steam_link, get_youtube_review, fetch_game_data


async def fetch_by_filter(genre=None, platform=None, year=None):
    try:
        params = f"key={API_KEY}&page_size=8&ordering=-rating"
        if genre:
            params += f"&genres={genre}"
        if platform:
            params += f"&platforms={platform}"
        if year:
            params += f"&dates={year}-01-01,{year}-12-31"
        url = f"https://api.rawg.io/api/games?{params}"
        data = requests.get(url, timeout=10).json()
        return data.get("results", [])
    except:
        return []


async def fetch_new_games():
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        url = f"https://api.rawg.io/api/games?key={API_KEY}&dates={month_ago},{today}&ordering=-added&page_size=8"
        data = requests.get(url, timeout=10).json()
        return data.get("results", [])
    except:
        return []


async def compare_games(game1_name, game2_name, send_text):
    try:
        r1 = fetch_game_data(game1_name)
        r2 = fetch_game_data(game2_name)
        if not r1 or not r2:
            await send_text("❌ Бір немесе екі ойын да табылмады")
            return
        g1, d1, _ = r1
        g2, d2, _ = r2

        def get_req(details):
            for p in details.get("platforms", []):
                if p["platform"]["slug"] == "pc":
                    req = p.get("requirements_en") or p.get("requirements")
                    if req:
                        return req.get("minimum", "Деректер жоқ")
            return "Деректер жоқ"

        p1 = [p["platform"]["name"] for p in g1.get("platforms", [])]
        p2 = [p["platform"]["name"] for p in g2.get("platforms", [])]
        gen1 = [g["name"] for g in d1.get("genres", [])]
        gen2 = [g["name"] for g in d2.get("genres", [])]

        stars1 = "⭐" * round(g1.get("rating", 0)) + "☆" * (5 - round(g1.get("rating", 0)))
        stars2 = "⭐" * round(g2.get("rating", 0)) + "☆" * (5 - round(g2.get("rating", 0)))

        winner = g1["name"] if g1.get("rating", 0) >= g2.get("rating", 0) else g2["name"]

        text = (
            f"📊 *Салыстыру нәтижесі:*\n\n"
            f"{'─' * 30}\n"
            f"🎮 *{g1['name']}*\n"
            f"⭐ Рейтинг: {stars1} {g1.get('rating', 0)}/5\n"
            f"🎭 Жанр: {', '.join(gen1) or 'Жоқ'}\n"
            f"🖥 Платформа: {', '.join(p1[:3]) or 'Жоқ'}\n"
            f"📅 Шыққан: {d1.get('released', 'Жоқ')}\n"
            f"⚙️ Талаптар: {get_req(d1)[:100]}...\n\n"
            f"{'─' * 30}\n"
            f"🎮 *{g2['name']}*\n"
            f"⭐ Рейтинг: {stars2} {g2.get('rating', 0)}/5\n"
            f"🎭 Жанр: {', '.join(gen2) or 'Жоқ'}\n"
            f"🖥 Платформа: {', '.join(p2[:3]) or 'Жоқ'}\n"
            f"📅 Шыққан: {d2.get('released', 'Жоқ')}\n"
            f"⚙️ Талаптар: {get_req(d2)[:100]}...\n\n"
            f"{'─' * 30}\n"
            f"🏆 *Жеңімпаз: {winner}*"
        )
        await send_text(text, parse_mode="Markdown")
    except Exception as e:
        await send_text(f"❌ Қате: {str(e)}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Топ 50 ойын", callback_data="goto_top50")],
        [InlineKeyboardButton("🆕 Жаңа ойындар", callback_data="new_games")],
        [InlineKeyboardButton("🔍 Фильтр", callback_data="filter_menu"),
         InlineKeyboardButton("📊 Салыстыру", callback_data="compare_start")],
        [InlineKeyboardButton("🎲 Кездейсоқ ойын", callback_data="random")],
        [InlineKeyboardButton("📜 Тарих", callback_data="history"),
         InlineKeyboardButton("❓ Көмек", callback_data="help")],
    ]
    text = (
        "👋 Сәлем! Мен *Game\\_InfoBot* — ойындар туралы ақпарат беретін ботпын.\n\n"
        "🎮 Ойын атын жазсаң — толық ақпарат аласың\n\n"
        "📌 *Қолжетімді командалар:*\n"
        "🔹 /top50 — үздік 50 ойын тізімі\n"
        "🔹 /random — кездейсоқ ойын\n"
        "🔹 /history — іздеу тарихы\n"
        "🔹 /clear — тарихты тазалау\n"
        "🔹 /help — барлық командалар\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


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


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "❓ *Барлық командалар тізімі:*\n\n"
        "🔹 /start — ботты іске қосу, басты мәзір\n"
        "🔹 /top50 — үздік 50 ойын санаттары бойынша\n"
        "🔹 /random — кездейсоқ ойын туралы ақпарат\n"
        "🔹 /history — соңғы 10 іздеген ойын тарихы\n"
        "🔹 /clear — іздеу тарихын тазалау\n"
        "🔹 /help — осы командалар тізімі\n\n"
        "💡 *Қолдану:*\n"
        "Кез келген ойын атауын жай жазсаң болады\n"
        "Мысалы: `Minecraft`, `GTA V`, `Elden Ring`"
    )
    keyboard = [
        [InlineKeyboardButton("🎮 Топ 50 ойын", callback_data="goto_top50")],
        [InlineKeyboardButton("🎲 Кездейсоқ ойын", callback_data="random")],
    ]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


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
    await get_game(update, context, game_name)


async def get_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_name: str = None):
    if game_name is None:
        game_name = update.message.text
    user_id = update.message.from_user.id

    async def send_text(text, **kwargs):
        return await update.message.reply_text(text, **kwargs)

    async def send_photo(photo, caption, **kwargs):
        return await update.message.reply_photo(photo=photo, caption=caption, **kwargs)

    async def send_media_group(media, **kwargs):
        return await update.message.reply_media_group(media, **kwargs)

    if context.user_data.get("compare_mode") and not context.user_data.get("compare_first"):
        context.user_data["compare_first"] = game_name
        keyboard = [[InlineKeyboardButton(
            f"✅ {game_name} таңдалды — екіншісін жаз",
            callback_data=f"compare_second:{game_name}"
        )]]
        await update.message.reply_text(
            f"✅ *{game_name}* таңдалды\nЕнді екінші ойын атауын жаз 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if context.user_data.get("compare_waiting"):
        context.user_data["compare_waiting"] = False
        context.user_data["compare_mode"] = False
        first_game = context.user_data.pop("compare_first", None)
        if first_game:
            await update.message.reply_text("⏳ Салыстырылуда...")
            await compare_games(first_game, game_name, send_text)
            return

    add_to_history(user_id, game_name)
    await fetch_and_send_game(game_name, send_text, send_photo, send_media_group, user_id, context)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async def send_text(text, **kwargs):
        return await query.message.reply_text(text, **kwargs)

    async def send_photo(photo, caption, **kwargs):
        return await query.message.reply_photo(photo=photo, caption=caption, **kwargs)

    async def send_media_group(media, **kwargs):
        return await query.message.reply_media_group(media, **kwargs)

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
        await fetch_and_send_game(game_name, send_text, send_photo, send_media_group, user_id, context)

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

    elif query.data == "filter_menu":
        keyboard = [
            [InlineKeyboardButton("🎭 Жанр бойынша", callback_data="filter_genre")],
            [InlineKeyboardButton("🖥 Платформа бойынша", callback_data="filter_platform")],
            [InlineKeyboardButton("📅 Жыл бойынша", callback_data="filter_year")],
            [InlineKeyboardButton("⬅️ Артқа", callback_data="back_main")],
        ]
        await query.edit_message_text(
            "🔍 *Фильтр таңда:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "filter_genre":
        keyboard = [
            [InlineKeyboardButton("⚔️ Action", callback_data="genre:action"),
             InlineKeyboardButton("🧙 RPG", callback_data="genre:role-playing-games-rpg")],
            [InlineKeyboardButton("🎯 Shooter", callback_data="genre:shooter"),
             InlineKeyboardButton("🏎 Racing", callback_data="genre:racing")],
            [InlineKeyboardButton("⚽ Sports", callback_data="genre:sports"),
             InlineKeyboardButton("🧩 Puzzle", callback_data="genre:puzzle")],
            [InlineKeyboardButton("🌍 Adventure", callback_data="genre:adventure"),
             InlineKeyboardButton("🎮 Arcade", callback_data="genre:arcade")],
            [InlineKeyboardButton("⬅️ Артқа", callback_data="filter_menu")],
        ]
        await query.edit_message_text(
            "🎭 *Жанрды таңда:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "filter_platform":
        keyboard = [
            [InlineKeyboardButton("🖥 PC", callback_data="platform:4"),
             InlineKeyboardButton("🎮 PlayStation 5", callback_data="platform:187")],
            [InlineKeyboardButton("🎮 PlayStation 4", callback_data="platform:18"),
             InlineKeyboardButton("🎮 Xbox One", callback_data="platform:1")],
            [InlineKeyboardButton("🎮 Nintendo Switch", callback_data="platform:7"),
             InlineKeyboardButton("📱 Android", callback_data="platform:21")],
            [InlineKeyboardButton("⬅️ Артқа", callback_data="filter_menu")],
        ]
        await query.edit_message_text(
            "🖥 *Платформаны таңда:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "filter_year":
        keyboard = [
            [InlineKeyboardButton("2024", callback_data="year:2024"),
             InlineKeyboardButton("2023", callback_data="year:2023")],
            [InlineKeyboardButton("2022", callback_data="year:2022"),
             InlineKeyboardButton("2021", callback_data="year:2021")],
            [InlineKeyboardButton("2020", callback_data="year:2020"),
             InlineKeyboardButton("2019", callback_data="year:2019")],
            [InlineKeyboardButton("⬅️ Артқа", callback_data="filter_menu")],
        ]
        await query.edit_message_text(
            "📅 *Жылды таңда:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("genre:"):
        genre = query.data[6:]
        await query.edit_message_text("⏳ Іздеуде...")
        games = await fetch_by_filter(genre=genre)
        if not games:
            await query.edit_message_text("Ойын табылмады ❌")
            return
        keyboard = [
            [InlineKeyboardButton(f"🎮 {g['name']} ⭐{g['rating']}", callback_data=f"game:{g['name']}")]
            for g in games[:8]
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Артқа", callback_data="filter_genre")])
        await query.edit_message_text(
            "🎭 *Нәтижелер:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("platform:"):
        platform = query.data[9:]
        await query.edit_message_text("⏳ Іздеуде...")
        games = await fetch_by_filter(platform=platform)
        if not games:
            await query.edit_message_text("Ойын табылмады ❌")
            return
        keyboard = [
            [InlineKeyboardButton(f"🎮 {g['name']} ⭐{g['rating']}", callback_data=f"game:{g['name']}")]
            for g in games[:8]
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Артқа", callback_data="filter_platform")])
        await query.edit_message_text(
            "🖥 *Нәтижелер:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("year:"):
        year = query.data[5:]
        await query.edit_message_text("⏳ Іздеуде...")
        games = await fetch_by_filter(year=year)
        if not games:
            await query.edit_message_text("Ойын табылмады ❌")
            return
        keyboard = [
            [InlineKeyboardButton(f"🎮 {g['name']} ⭐{g['rating']}", callback_data=f"game:{g['name']}")]
            for g in games[:8]
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Артқа", callback_data="filter_year")])
        await query.edit_message_text(
            f"📅 *{year} жылғы ойындар:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "new_games":
        await query.edit_message_text("⏳ Жаңа ойындар іздеуде...")
        games = await fetch_new_games()
        if not games:
            await query.edit_message_text("Ойын табылмады ❌")
            return
        keyboard = [
            [InlineKeyboardButton(f"🎮 {g['name']} ⭐{g['rating']}", callback_data=f"game:{g['name']}")]
            for g in games[:8]
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Артқа", callback_data="back_main")])
        await query.edit_message_text(
            "🆕 *Жаңа ойындар:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "compare_start":
        context.user_data["compare_mode"] = True
        context.user_data["compare_first"] = None
        context.user_data["compare_waiting"] = False
        await query.edit_message_text(
            "📊 *Салыстыру режимі қосылды!*\n\n"
            "Бірінші ойын атауын жаз 👇",
            parse_mode="Markdown"
        )

    elif query.data.startswith("compare_second:"):
        first_game = query.data[15:]
        context.user_data["compare_first"] = first_game
        context.user_data["compare_waiting"] = True
        await query.edit_message_text(
            f"✅ *{first_game}* таңдалды\n\n"
            f"Енді екінші ойын атауын жаз 👇",
            parse_mode="Markdown"
        )

    elif query.data == "help":
        text = (
            "❓ *Барлық командалар тізімі:*\n\n"
            "🔹 /start — ботты іске қосу, басты мәзір\n"
            "🔹 /top50 — үздік 50 ойын санаттары бойынша\n"
            "🔹 /random — кездейсоқ ойын туралы ақпарат\n"
            "🔹 /history — соңғы 10 іздеген ойын тарихы\n"
            "🔹 /clear — іздеу тарихын тазалау\n"
            "🔹 /help — осы командалар тізімі\n\n"
            "💡 *Қолдану:*\n"
            "Кез келген ойын атауын жай жазсаң болады\n"
            "Мысалы: `Minecraft`, `GTA V`, `Elden Ring`"
        )
        keyboard = [
            [InlineKeyboardButton("🎮 Топ 50 ойын", callback_data="goto_top50")],
            [InlineKeyboardButton("🎲 Кездейсоқ ойын", callback_data="random")],
            [InlineKeyboardButton("⬅️ Артқа", callback_data="back_main")],
        ]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "back_main":
        keyboard = [
            [InlineKeyboardButton("🎮 Топ 50 ойын", callback_data="goto_top50")],
            [InlineKeyboardButton("🆕 Жаңа ойындар", callback_data="new_games")],
            [InlineKeyboardButton("🔍 Фильтр", callback_data="filter_menu"),
             InlineKeyboardButton("📊 Салыстыру", callback_data="compare_start")],
            [InlineKeyboardButton("🎲 Кездейсоқ ойын", callback_data="random")],
            [InlineKeyboardButton("📜 Тарих", callback_data="history"),
             InlineKeyboardButton("❓ Көмек", callback_data="help")],
        ]
        await query.edit_message_text(
            "👋 Басты мәзір:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "cancel":
        try:
            await query.message.delete()
        except:
            pass

    elif query.data == "delete_all":
        try:
            current_id = query.message.message_id
            saved_ids = context.bot_data.get(f"game_msgs_{current_id}", [])
            if saved_ids:
                for msg_id in saved_ids:
                    try:
                        await context.bot.delete_message(
                            chat_id=query.message.chat_id,
                            message_id=msg_id
                        )
                    except:
                        pass
            else:
                for i in range(6):
                    try:
                        await context.bot.delete_message(
                            chat_id=query.message.chat_id,
                            message_id=current_id - i
                        )
                    except:
                        pass
        except:
            pass

    elif query.data.startswith("game:"):
        game_name = query.data[5:]
        await query.message.reply_text(
            f"🔍 *{game_name}* іздеуде...",
            parse_mode="Markdown"
        )
        add_to_history(user_id, game_name)
        await fetch_and_send_game(game_name, send_text, send_photo, send_media_group, user_id, context)


async def fetch_and_send_game(game_name, send_text, send_photo, send_media_group, user_id=None, context=None):
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

    card = (
        f"🎮 *{name}*\n"
        f"📅 Шыққан күні: {release_date}\n"
        f"🏢 Әзірлеуші: {developers_text}\n"
        f"🏷 Баспагер: {publishers_text}\n"
        f"🎭 Жанр: {genres_text}\n"
        f"🖥 Платформалар: {platforms_text}\n\n"
        f"{stars} *{rating}/5* ({rating_count:,} баға)\n\n"
        f"📖 *Сипаттама:*\n{description}\n"
    )
    if website:
        card += f"\n🌐 [Ресми сайт]({website})"

    req_text = (
        f"⚙️ *Жүйелік талаптар (ДК):*\n\n"
        f"🔻 *Ең төменгі:*\n{req_minimum}\n\n"
        f"🔺 *Ұсынылатын:*\n{req_recommended}\n"
    )

    action_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Steam-да сатып ал", url=steam_link)],
        [InlineKeyboardButton("▶️ YouTube шолу", url=youtube_link)],
        [
            InlineKeyboardButton("📜 Тарих", callback_data="history"),
            InlineKeyboardButton("🎲 Кездейсоқ", callback_data="random"),
        ],
        [
            InlineKeyboardButton("🗑 Барлығын жою", callback_data="delete_all"),
            InlineKeyboardButton("🚫 Бас тарту", callback_data="cancel"),
        ],
        [InlineKeyboardButton("⬅️ Артқа", callback_data="back_main")],
    ])

    sent_ids = []

    if cover:
        msg1 = await send_photo(cover, caption=card[:1024], parse_mode="Markdown")
        if msg1:
            sent_ids.append(msg1.message_id)
    else:
        msg1 = await send_text(card, parse_mode="Markdown")
        if msg1:
            sent_ids.append(msg1.message_id)

    msg2 = await send_text(req_text, parse_mode="Markdown", reply_markup=action_keyboard)
    if msg2:
        sent_ids.append(msg2.message_id)

    if screenshots:
        media = [InputMediaPhoto(media=screenshots[0], caption="📸 Скриншоттар")]
        for s in screenshots[1:]:
            media.append(InputMediaPhoto(media=s))
        msgs = await send_media_group(media)
        if msgs:
            for m in msgs:
                sent_ids.append(m.message_id)

    if context and msg2:
        context.bot_data[f"game_msgs_{msg2.message_id}"] = sent_ids