from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, CallbackQueryHandler

from settings import TOKEN
from handlers import (
    start, top50, history_cmd, clear_history_cmd,
    random_game_cmd, button_handler, get_game, help_cmd
)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top50", top50))
    app.add_handler(CommandHandler("random", random_game_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("clear", clear_history_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_game))

    print("Бот іске қосылды... 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()