from deep_translator import GoogleTranslator
from data import user_history


def translate_kz(text: str) -> str:
    if not text or text in ("Нет данных", "No data", "-"):
        return "Деректер жоқ"
    try:
        return GoogleTranslator(source='auto', target='kk').translate(text[:4500])
    except:
        return text


def add_to_history(user_id: int, game_name: str):
    if user_id not in user_history:
        user_history[user_id] = []
    if game_name in user_history[user_id]:
        user_history[user_id].remove(game_name)
    user_history[user_id].insert(0, game_name)
    user_history[user_id] = user_history[user_id][:10]