import os
import json
import logging
import random
import asyncio
import signal
import sys
import time
import re
import difflib
import atexit
from copy import deepcopy
from telegram import (Update, ReplyKeyboardMarkup, BotCommand, BotCommandScopeChat,
                      InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Application, CommandHandler, MessageHandler, CallbackQueryHandler, TypeHandler,
                          ApplicationHandlerStop, filters, ContextTypes)

# --- Настройка ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
DATA_FILE = "game_data.json"
HEAL_INTERVAL = 60
HEAL_AMOUNT = 15
AUTOSAVE_INTERVAL = 30
DAILY_ATTACKS = 100   # базовый лимит атак (боёв) в день на игрока

try:
    import pics      # картинки (нужен Pillow); без него бот работает без картинок
except Exception as e:
    pics = None
    logger.warning("Картинки отключены: %s", e)
PIC_IDS = {}
CREATURE_PIC = {"Гоблин": "goblin", "Скелет": "skeleton", "Огр": "ogre", "Волк": "wolf"}

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не найден TELEGRAM_BOT_TOKEN! Сначала сделай export в терминале.")

# --- Существа ---
CREATURES = {
    "Гоблин": {"hp": 80, "attack": 12},
    "Скелет": {"hp": 100, "attack": 15},
    "Огр": {"hp": 150, "attack": 20},
    "Волк": {"hp": 90, "attack": 18}
}

# --- Правда или действие: 100 вопросов и 100 заданий ---
TRUTHS = "Какой самый неловкий момент в твоей жизни?|Чего ты боишься больше всего?|Какую самую большую ложь ты говорил(а) родителям?|О чём ты мечтаешь прямо сейчас?|Какой твой самый странный страх?|Какое самое глупое, что ты делал(а) ради шутки?|Что бы ты сделал(а), если бы стал(а) невидимкой на один день?|Какая твоя любимая игра и почему?|Какую свою привычку ты считаешь самой странной?|Кому из друзей ты доверяешь больше всех?|Какой подарок был самым лучшим в твоей жизни?|Что тебя раздражает больше всего?|Какую суперсилу ты бы выбрал(а)?|Какой фильм ты смотрел(а) больше трёх раз?|Какое твоё самое любимое блюдо?|Что ты делаешь, когда тебе скучно?|Какая твоя самая смешная детская история?|Если бы ты мог(ла) жить в любой стране, какую бы выбрал(а)?|Какой навык ты хотел(а) бы освоить за неделю?|Какое слово ты чаще всего говоришь?|Что самое странное ты ел(а) в жизни?|Ты когда-нибудь проспал(а) важное дело? Что случилось?|Какую песню ты можешь слушать бесконечно?|Какое твоё самое большое достижение?|О чём ты жалеешь больше всего?|Какой был твой самый неудачный день?|Кем ты хотел(а) стать в детстве?|Какая у тебя самая странная привычка перед сном?|Что ты никогда бы не стал(а) есть?|Какой самый смешной случай был у тебя в школе?|Если бы у тебя был миллион, на что бы ты потратил(а) его в первую очередь?|Какую вещь ты потерял(а) и до сих пор скучаешь по ней?|Что может рассмешить тебя до слёз?|Какую ложь ты говорил(а) чаще всего?|Что бы ты изменил(а) в своём характере?|Какое место на Земле ты мечтаешь посетить?|Какой самый странный сон тебе снился?|С каким героем из фильма или игры ты бы поменялся(ась) местами?|Что бы ты сделал(а), если бы выиграл(а) в лотерею?|Какая у тебя самая бесполезная суперспособность?|Какой секрет ты готов(а) рассказать прямо сейчас?|Какой у тебя самый нелюбимый предмет в школе или дело на работе?|Когда ты в последний раз смеялся(ась) до слёз?|Какой твой любимый мем?|Что ты чаще всего делаешь в телефоне?|Сколько часов в день ты проводишь в телефоне?|Какое приложение ты не можешь удалить?|Какая твоя самая необычная мечта?|Какое животное ты бы хотел(а) завести?|Какую еду ты можешь есть каждый день?|Как бы ты назвал(а) свою автобиографию?|Какой совет ты бы дал(а) себе пять лет назад?|Какую профессию ты бы никогда не выбрал(а)?|Что больше всего удивило тебя в этом году?|Какой твой любимый день недели?|Ты веришь в приведения?|Что ты делаешь, когда злишься?|Какую книгу ты бы посоветовал(а) прочитать всем?|Какое твоё самое любимое воспоминание?|Какую модную вещь ты не понимаешь?|Что бы ты взял(а) с собой на необитаемый остров?|Какой самый длинный срок ты не спал(а)?|Каким ты видишь себя через десять лет?|Какая у тебя самая любимая игра на телефоне?|Кто твой любимый блогер или стример?|Что бы ты сделал(а), если бы стал(а) президентом на один день?|Какая у тебя самая сильная сторона?|А какая самая слабая?|Какой подарок ты хотел(а) бы получить?|Что для тебя идеальный выходной?|Какой запах напоминает тебе о детстве?|Что самое смешное ты слышал(а) от учителя или начальника?|Ты когда-нибудь списывал(а)? Как это было?|Что ты больше любишь: утро или ночь?|Какая привычка других людей раздражает тебя больше всего?|Какое прозвище у тебя было?|Какой твой самый большой талант?|Чему ты научился(ась) недавно?|Какую игру из детства ты вспоминаешь с теплом?|Если бы ты был(а) животным, то каким?|Какой цвет тебе нравится больше всего и почему?|Какую страну ты бы никогда не хотел(а) посетить?|Что бы ты никогда не променял(а) ни на какие деньги?|Какое твоё любимое время года?|Ты умеешь готовить? Какое блюдо получается у тебя лучше всего?|Какая самая странная вещь есть у тебя дома?|Какое самое раннее воспоминание ты помнишь?|Что ты думаешь о ранних подъёмах?|Какую шутку ты считаешь самой смешной?|Какой самый смелый поступок ты совершил(а)?|С кем из знаменитостей ты хотел(а) бы пообедать?|Что бы ты сделал(а), если бы застрял(а) в лифте на час?|Какое самое далёкое место, где ты был(а)?|Какая твоя любимая отговорка?|Какой предмет ты берёшь с собой везде?|О чём ты чаще всего привираешь по мелочи?|Что ты делаешь первым делом, когда просыпаешься?|Что тебя вдохновляет?|Чем бы ты занялся(ась), если бы не нужно было работать или учиться?|Что бы ты хотел(а), чтобы люди помнили о тебе?".split("|")

DARES = "Отправь голосовое, где ты поёшь любимую песню.|Опиши свой день только смайликами.|Сфотографируй то, что лежит справа от тебя, и отправь в чат.|Скажи скороговорку три раза подряд без ошибок.|Напиши стих про своё последнее блюдо.|Отправь голосовое с криком петуха.|Сделай 10 приседаний и напиши, как ты себя чувствуешь.|Придумай и напиши рекламу своей любимой еды.|Отправь голосовое, где ты говоришь голосом робота.|Напиши сообщение, где все слова начинаются на одну букву.|Станцуй под любую песню 30 секунд и напиши «готово».|Отправь самое старое фото из галереи (если не стесняешься).|Придумай себе имя супергероя и опиши его силу.|Отправь голосовое, где ты читаешь любой текст голосом диктора новостей.|Назови 10 животных за 15 секунд.|Опиши то, что видишь за окном, в стиле детектива.|Изобрази кошку и напиши, как это было.|Сделай комплимент первому, кому напишешь после этого задания.|Сочини двустишие про свой телефон.|Отправь голосовое с самым длинным «ааааа», на которое хватит дыхания.|Придумай новое слово и объясни, что оно значит.|Сфотографируй своё рабочее место или место учёбы и отправь в чат.|Напиши три слова, которые описывают твоё настроение, не называя эмоций.|Расскажи анекдот голосовым сообщением.|Следующие три минуты общайся в чате только в рифму.|Сделай 5 отжиманий (или 10 приседаний, если отжиматься тяжело).|Придумай рецепт нового блюда из трёх продуктов, которые есть дома.|Напиши короткую сказку из пяти предложений про свой телефон.|Отправь свой любимый смайлик и объясни, почему он тебе нравится.|Закрой глаза, нарисуй дом, сфотографируй и отправь.|Прочитай любое предложение голосом пирата и отправь голосовое.|Сфотографируй самую смешную вещь рядом с тобой.|Придумай слоган для своего города.|Напиши своё имя задом наперёд и придумай, каким был бы человек с таким именем.|Опиши любой предмет рядом так, будто это волшебный артефакт.|Отправь голосовое, где ты говоришь голосом мультяшного героя.|Посчитай от 1 до 20 на другом языке (как получится).|Придумай тост за свой любимый безалкогольный напиток.|Сделай рекламу воздуха как товара.|Напиши сообщение так, будто тебе 90 лет.|Постой на одной ноге 30 секунд и напиши, сколько удалось.|Назови пять фильмов, в названии которых есть цвет.|Придумай новую суперсилу и опиши, как ты её используешь.|Скажи «Карл у Клары украл кораллы» пять раз подряд быстро.|Опиши свой день так, будто это эпизод приключенческого фильма.|Нарисуй любое животное одним росчерком, не отрывая руки, и отправь фото.|Напиши список из пяти вещей, без которых ты не проживёшь день.|Спой «С днём рождения» голосом оперного певца (голосовое).|Придумай и расскажи короткую страшилку в три предложения.|Изобрази в чате человека, который проснулся в 5 утра.|Скажи комплимент самому себе вслух и напиши его в чат.|Назови три самых смешных слова, которые знаешь.|Приготовь себе бутерброд самым странным способом и расскажи как.|Напиши рэп из четырёх строк про свою жизнь.|Опиши своё утро, не используя букву «о».|Сделай 15 прыжков на месте и напиши «выжил(а)».|Выбери случайную песню и расскажи, о чём она, одним предложением.|Придумай название для своего будущего кафе и меню из трёх блюд.|Напиши близкому человеку, что он классный (можно маме).|Придумай три причины, почему коты управляют миром.|Назови подряд пять слов на букву «С» за 10 секунд.|Отправь голосовое с шёпотом, в котором ты рассказываешь выдуманный секрет.|Представь, что ты ведущий прогноза погоды, и расскажи прогноз на завтра.|Опиши любой предмет в комнате, не называя его, чтобы другие угадали.|Покажи самый смешной танец и опиши словами, как это выглядело.|Напиши письмо самому себе через год из трёх предложений.|Сделай наклон, дотянись руками до пола и напиши, получилось ли.|Назови 5 стран на разные буквы за 10 секунд.|Придумай название для фильма про свой день.|Придумай и расскажи смешную историю с участием трёх случайных предметов.|Скажи «привет» на трёх разных языках.|Отправь голосовое, где ты смеёшься злодейским смехом.|Придумай хэштег, который описывает тебя.|Нарисуй автопортрет за 30 секунд и отправь фото.|Расскажи, каким супергероем ты был(а) бы в школе или на работе.|Опиши в виде стихотворения, что ты сейчас слышишь вокруг.|Опиши вкус воды так, будто ты дегустатор вина.|Придумай песню из трёх строк про понедельник.|Назови самое длинное слово, которое знаешь, и напиши его.|Хлопни в ладоши 20 раз за 10 секунд и напиши, успел(а) ли.|Отправь голосовое, где ты говоришь голосом очень уставшего человека.|Придумай мотивационную цитату от имени питомца или любого предмета.|Выпей стакан воды без остановки и напиши, как это было.|Придумай новую игру из трёх правил и объясни её.|Расскажи самую смешную историю дня за одну минуту.|Напиши слово «бот» в десяти разных стилях (КАПСОМ, с точками и так далее).|Представь, что ты инопланетянин, и напиши первое сообщение землянам.|Опиши любимого героя фильма тремя словами, пусть другие угадают.|Подбрось монетку 10 раз и напиши, сколько раз выпал орёл.|Назови семь дней недели задом наперёд.|Отправь голосовое с песней из трёх слов, которую сочиняешь на ходу.|Придумай три совета для тех, кто вечно опаздывает.|Напиши рецепт идеального чая так, будто это зелье.|Попробуй поймать свою тень рукой и опиши, как прошло.|Расскажи в трёх предложениях, чему бы ты научил(а) инопланетян о Земле.|Скажи вслух «Я лучший(ая)!» три раза и добавь, почему.|Придумай шутку про программистов или котиков.|Нарисуй смайлик на листе бумаги и отправь фото.|Опиши свой любимый запах, не называя его источник.|Улыбнись своему отражению в зеркале 10 секунд и напиши, удалось ли не засмеяться.".split("|")

# --- Глобальные состояния ---
active_games = {}
user_data = {}
dirty = False      # есть несохранённые изменения
duo_counter = 0    # уникальные ID комнат

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return {int(k): v for k, v in json.load(f).items()}
        except Exception as e:
            logger.error(f"Ошибка чтения файла данных: {e}")
    return {}

def save_data():
    global dirty
    try:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)  # файл не побьётся, даже если бот упадёт во время записи
        _save_world()
        dirty = False
        logger.info("Данные сохранены.")
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")

def get_user_data_safe(user_id: int):
    global dirty
    if user_id not in user_data:
        user_data[user_id] = {"level": 1, "attack": 10, "hp": 100, "max_hp": 100}
        dirty = True
    d = user_data[user_id]
    for key, default in (("xp", 0), ("coins", 0), ("bought_hp", 0), ("bought_atk", 0), ("wins", 0), ("pvp_wins", 0),
                         ("pvp_games", 0), ("rating", 1000), ("tower_best", 0), ("boss_kills", 0), ("streak", 0),
                         ("class", ""), ("clan", ""), ("nick", ""), ("inv", list), ("eq", dict), ("ach", list),
                         ("titles", list), ("q", dict)):
        if key not in d:   # новые поля для старых игроков
            d[key] = default() if callable(default) else default
            dirty = True
    return deepcopy(user_data[user_id])

def update_user_data(user_id: int, data: dict):
    global dirty
    user_data[user_id] = data
    dirty = True

def new_duo_id():
    global duo_counter
    duo_counter += 1
    return f"duo_{duo_counter}"

def xp_needed(level: int) -> int:
    """Сколько XP нужно, чтобы перейти с этого уровня на следующий."""
    return 100 + (level - 1) * 50

def add_xp(data: dict, amount: int) -> int:
    """Добавляет XP. Если набрано достаточно, повышает уровень. Возвращает, сколько уровней получено."""
    if data.get('xp_until', 0) > time.time():
        amount = int(amount * 1.5)   # купленный бонус опыта
    amount = int(amount * (1 + equip_bonus(data)[2] / 200))   # амулет даёт ещё и немного опыта
    data['xp'] = data.get('xp', 0) + amount
    gained = 0
    while data['xp'] >= xp_needed(data['level']):
        data['xp'] -= xp_needed(data['level'])
        data['level'] += 1
        data['max_hp'] += 20
        data['hp'] = data['max_hp']
        gained += 1
    return gained

def xp_status(data: dict, levels: int = 0) -> str:
    text = f"📊 XP: {data['xp']}/{xp_needed(data['level'])}"
    if levels:
        text = f"🆙 Новый уровень: {data['level']}! Макс. HP +{20 * levels}, здоровье восстановлено.\n" + text
    return text

def pick_no_repeat(game: dict, key: str, source: list):
    """Берёт случайный пункт, не повторяя уже выпавшие, пока не кончится весь список."""
    pool = game.setdefault(key, [])
    if not pool:
        pool.extend(source)
        random.shuffle(pool)
    return pool.pop()

# --- КНОПКИ ---
B_DUEL = "⚔️ Дуэль"
B_CREATURE = "👹 Существо"
B_GUESS = "🎲 Угадай число"
B_FRIEND = "👥 Игра с другом"
B_TOD = "🎭 Правда или действие"
B_STATS = "📊 Статистика"
B_HELP = "📖 Помощь"
B_ATTACK = "⚔️ Атака"
B_FLEE = "🏃 Уйти"
B_TRUTH = "🔮 Правда"
B_DARE = "🔥 Действие"
B_STOP = "🛑 Стоп"
B_LEAVE = "🚪 Выйти"
B_SHOP = "🛒 Магазин"
B_BUY_HP = "❤️ Купить HP"
B_BUY_ATK = "⚔️ Купить атаку"
B_BUY_POTION = "🧪 Купить зелье"
B_BACK = "⬅️ Назад"
B_TOWER = "🗼 Башня"
B_BOSS = "🐉 Босс мира"
B_PVP = "⚔️ PvP"
B_RATING = "🏆 Рейтинг"
B_INV = "🎒 Инвентарь"
B_CLASS = "🧙 Класс"
B_QUESTS = "📅 Задания"
B_ACH = "🏅 Достижения"
B_CLAN = "👥 Клан"
B_SKILL = "💥 Навык"
B_DEFEND = "🛡 Защита"
B_HIT = "💥 Ударить босса"
B_REFRESH = "🔄 Обновить"
B_FIND = "🎯 Найти соперника"
B_EQUIP = "✨ Надеть лучшее"
B_JUNK = "🗑 Продать хлам"
B_WARRIOR = "🛡 Воин"
B_MAGE = "🔮 Маг"
B_ARCHER = "🏹 Лучник"
B_CLANTOP = "🏆 Топ кланов"
B_CLANLEAVE = "🚪 Покинуть клан"
B_ZONE = "🔴 Красная точка"
B_REF = "🎁 Друзья"
B_BAL = "💰 Баланс"
B_BUY_ENERGY = "⚡ Энергетик"
B_BUY_CHEST = "🎁 Сундук"
B_BUY_RARE = "💎 Редкий сундук"
B_BUY_EPIC = "👑 Эпический сундук"
B_BUY_XP = "📈 Бонус XP"
B_BUY_LUCK = "🍀 Удача"
B_BUY_NICK = "🏷 Смена ника"
B_CAMP = "🗺 Кампания"
B_FARM = "🌾 Ферма"
B_BUY_BOOST = "🚀 Разгон фермы"
B_HERO = "🎒 Герой"
B_UP_W, B_UP_A, B_UP_M, B_BUY_BAG = "🔨 Оружие", "🔨 Броня", "🔨 Амулет", "🎒 Рюкзак"
B_DISM, B_FORGE = "♻️ Разобрать хлам", "🔨 Ковка"

MAIN_KB = ReplyKeyboardMarkup([
    [B_ZONE, B_FARM], [B_GUESS, B_TOD], [B_HERO, B_SHOP], [B_RATING, B_BAL], [B_HELP]], resize_keyboard=True)
DUEL_KB = ReplyKeyboardMarkup([[B_ATTACK, B_SKILL], [B_DEFEND, B_FLEE]], resize_keyboard=True)
TOD_KB = ReplyKeyboardMarkup([[B_TRUTH, B_DARE], [B_STOP]], resize_keyboard=True)
LEAVE_KB = ReplyKeyboardMarkup([[B_LEAVE]], resize_keyboard=True)
SHOP_KB = ReplyKeyboardMarkup([
    [B_BUY_HP, B_BUY_ATK, B_BUY_POTION], [B_BUY_CHEST, B_BUY_RARE, B_BUY_EPIC],
    [B_UP_W, B_UP_A, B_UP_M], [B_BUY_BAG, B_BUY_BOOST],
    [B_BUY_XP, B_BUY_LUCK, B_BUY_NICK], [B_BUY_ENERGY, B_BACK]], resize_keyboard=True)
ZONE_KB = ReplyKeyboardMarkup([[B_DUEL, B_CREATURE], [B_CAMP, B_TOWER], [B_PVP, B_BOSS], [B_FRIEND, B_BACK]], resize_keyboard=True)
BACK_KB = ReplyKeyboardMarkup([[B_BACK]], resize_keyboard=True)
BOSS_KB = ReplyKeyboardMarkup([[B_HIT], [B_REFRESH, B_BACK]], resize_keyboard=True)
PVP_KB = ReplyKeyboardMarkup([[B_FIND], [B_RATING, B_BACK]], resize_keyboard=True)
INV_KB = ReplyKeyboardMarkup([[B_EQUIP, B_JUNK], [B_DISM, B_FORGE], [B_BACK]], resize_keyboard=True)
CLASS_KB = ReplyKeyboardMarkup([[B_WARRIOR, B_MAGE, B_ARCHER], [B_BACK]], resize_keyboard=True)
CLAN_KB = ReplyKeyboardMarkup([[B_CLANTOP, B_CLANLEAVE], [B_BACK]], resize_keyboard=True)
SCREEN_KB = {"boss": BOSS_KB, "pvp": PVP_KB, "inv": INV_KB, "class": CLASS_KB, "clan": CLAN_KB,
             "quests": BACK_KB, "ach": BACK_KB, "rating": BACK_KB,
             "redzone": ZONE_KB, "ref": BACK_KB}

def _norm(t: str) -> str:
    return t.replace("\ufe0f", "").strip().lower()

# Нажатие кнопки приходит как текст, превращаем его в обычное слово-команду
BUTTON_ALIASES = {_norm(k): v for k, v in {
    B_DUEL: "дуэль", B_CREATURE: "существо", B_GUESS: "угадай", B_FRIEND: "друг", B_TOD: "пд",
    B_STATS: "статистика", B_HELP: "помощь", B_ATTACK: "атака", B_FLEE: "уйти",
    B_TRUTH: "правда", B_DARE: "действие", B_STOP: "стоп", B_LEAVE: "/leave",
    B_SHOP: "магазин", B_BUY_HP: "купить хп", B_BUY_ATK: "купить атаку", B_BUY_POTION: "купить зелье", B_BACK: "/leave",
    B_TOWER: "башня", B_BOSS: "босс мира", B_PVP: "pvp", B_RATING: "рейтинг", B_INV: "инвентарь", B_CLASS: "класс",
    B_QUESTS: "задания", B_ACH: "достижения", B_CLAN: "клан", B_SKILL: "навык", B_DEFEND: "защита",
    B_HIT: "ударить босса", B_REFRESH: "обновить", B_FIND: "найти соперника", B_EQUIP: "надеть лучшее",
    B_JUNK: "продать хлам", B_WARRIOR: "воин", B_MAGE: "маг", B_ARCHER: "лучник",
    B_CLANTOP: "топ кланов", B_CLANLEAVE: "покинуть клан",
    B_ZONE: "красная точка", B_REF: "друзья", B_BAL: "баланс", B_BUY_ENERGY: "купить энергетик",
    B_BUY_CHEST: "купить сундук", B_BUY_RARE: "купить редкий сундук", B_BUY_EPIC: "купить эпический сундук",
    B_BUY_XP: "купить опыт", B_BUY_LUCK: "купить удачу", B_BUY_NICK: "купить смену ника",
}.items()}

def keyboard_for(user_id: int):
    """Какие кнопки показывать игроку прямо сейчас, зависит от того, в какой он игре."""
    game = active_games.get(user_id)
    if game and game.get("game") == "duel":
        return DUEL_KB
    if f"tod_{user_id}" in active_games:
        return TOD_KB
    if f"shop_{user_id}" in active_games:
        return SHOP_KB
    if f"solo_{user_id}" in active_games:
        return LEAVE_KB
    for g in active_games.values():
        if g.get("type") == "guess_duo" and user_id in (g.get("creator"), g.get("partner")):
            return LEAVE_KB
    scr = active_games.get(f"scr_{user_id}")
    if scr:
        return CONFIRM_KB if scr.get("confirm") else SCREEN_KB.get(scr.get("kind"), BACK_KB)
    return MAIN_KB

def is_private(update: Update) -> bool:
    """True, если это личный чат с ботом (а не группа)."""
    chat = update.effective_chat
    return chat is None or chat.type == "private"

def room_in_this_chat(room: dict, update: Update) -> bool:
    """Комната в личке работает в личных чатах, комната в группе только в своей группе."""
    if room.get("private", True):
        return is_private(update)
    return update.effective_chat is not None and update.effective_chat.id == room.get("chat_id")

async def reply(update: Update, text: str, html: bool = False):
    # В группах кнопки не показываем: клавиатура была бы одна на всех участников
    markup = keyboard_for(update.effective_user.id) if is_private(update) else None
    kw = {"parse_mode": "HTML"} if html else {}
    await update.message.reply_text(text, reply_markup=markup, **kw)

async def send_msg(bot, chat_id, text):
    markup = keyboard_for(chat_id) if chat_id > 0 else None  # у групп id отрицательные
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)

async def reply_pic(update: Update, kind: str, text: str):
    """Ответ с картинкой. Если картинок нет или отправка не удалась, шлёт обычный текст."""
    markup = keyboard_for(update.effective_user.id) if is_private(update) else None
    if pics and len(text) <= 1000 and (is_private(update) or kind == "win"):
        try:
            src = PIC_IDS.get(kind)
            if src is None:
                path = pics.get_pic(kind)
                if path:
                    with open(path, "rb") as f:
                        src = f.read()
            if src:
                msg = await update.message.reply_photo(photo=src, caption=text, reply_markup=markup)
                PIC_IDS.setdefault(kind, msg.photo[-1].file_id)
                return
        except Exception as e:
            logger.warning(f"Картинка '{kind}' не отправилась: {e}")
    await update.message.reply_text(text, reply_markup=markup)

async def send_pic(bot, kind: str, chat_id, text: str):
    """Как reply_pic, но для сообщений, которые бот шлёт игроку в личку сам."""
    markup = keyboard_for(chat_id) if chat_id > 0 else None
    if pics and len(text) <= 1000 and chat_id > 0:
        try:
            src = PIC_IDS.get(kind)
            if src is None:
                path = pics.get_pic(kind)
                if path:
                    with open(path, "rb") as f:
                        src = f.read()
            if src:
                msg = await bot.send_photo(chat_id=chat_id, photo=src, caption=text, reply_markup=markup)
                PIC_IDS.setdefault(kind, msg.photo[-1].file_id)
                return
        except Exception as e:
            logger.warning(f"Картинка '{kind}' не отправилась: {e}")
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)

# --- лимит атак ---
def attacks_used(data: dict) -> int:
    """Сколько атак игрок сделал сегодня (счётчик сам обнуляется с новым днём)."""
    day = time.strftime("%Y-%m-%d")
    if data.get("att_day") != day:
        data["att_day"] = day
        data["att_used"] = 0
    return data.get("att_used", 0)

# --- магазин ---
POTION_PRICE = 25
SHOP_ALIASES = {"хп": "hp", "атаку": "atk", "зелье": "potion", "энергетик": "energy", "сундук": "chest",
                "редкий сундук": "rare", "эпический сундук": "epic", "опыт": "xp", "удачу": "luck", "смену ника": "nick", "разгон": "boost", "улучшение оружия": "up_weapon", "улучшение брони": "up_armor",
                "улучшение амулета": "up_amulet", "рюкзак": "bag"}
SHOP_FLAT = {"potion": POTION_PRICE, "chest": 800, "rare": 3000, "epic": 10000, "xp": 150, "luck": 120, "nick": 30, "boost": 200, "energy": 160}
def price_hp(d): return 60 + 15 * d.get("bought_hp", 0)
def price_atk(d): return 100 + 25 * d.get("bought_atk", 0)

UPGRADE_COSTS = [5000, 7500, 11000, 16000, 23000, 33000, 47000, 66000, 92000, 128000]   # цена повышения с уровня u до u+1
GEAR_MAX_LVL = 10
GEAR_SLOT_OF = {"up_weapon": "weapon", "up_armor": "armor", "up_amulet": "amulet"}

def bag_price(d: dict) -> int:
    return 10000 + 3000 * (d.get("inv_extra", 0) // INV_STEP)   # от 10000 €, каждое расширение дороже

def upgrade_price(d: dict, slot: str) -> int:
    it = d.get("eq", {}).get(slot)
    return UPGRADE_COSTS[min(it.get("u", 0) if it else 0, GEAR_MAX_LVL - 1)]

def shop_price(d: dict, item: str) -> int:
    if item in GEAR_SLOT_OF:
        return upgrade_price(d, GEAR_SLOT_OF[item])
    if item == "bag":
        return bag_price(d)
    return {"hp": price_hp, "atk": price_atk}.get(item, lambda _d: SHOP_FLAT[item])(d)

def shop_text(d: dict) -> str:
    now = time.time()
    cls = CLASSES.get(d.get("class", ""), ("класс не выбран",))[0]

    def gear_line(icon, slot, name):
        it = d.get("eq", {}).get(slot)
        u = it.get("u", 0) if it else 0
        if not it:
            return f"{icon} {name}: слот пуст, сначала надень предмет"
        if u >= GEAR_MAX_LVL:
            return f"{icon} {name}: максимальный уровень ({u}/{GEAR_MAX_LVL})"
        return f"{icon} {name} +1 уровень ({u}→{u + 1}) — цена {upgrade_price(d, slot)} €"

    cap = inv_capacity(d)
    bag = (f"🎒 Рюкзак: максимум ({cap} мест)" if cap >= INV_BASE + INV_MAX_EXTRA
           else f"🎒 Рюкзак +{INV_STEP} мест ({cap}→{cap + INV_STEP}) — цена {bag_price(d)} €")
    lines = [f"🛒 МАГАЗИН · баланс {d['coins']} €", "В каждой строке слово «цена» — это стоимость в €.", "",
             "❤️ ГЕРОЙ",
             f"❤️ +20 к макс. HP — цена {price_hp(d)} €", f"⚔️ +2 к атаке — цена {price_atk(d)} €",
             f"🧪 Зелье, полное HP — цена {POTION_PRICE} €", "",
             f"🎁 СУНДУКИ (снаряжение твоего класса: {cls})",
             f"🎁 Обычный сундук — цена {SHOP_FLAT['chest']} €",
             f"💎 Редкий сундук, редкий и выше — цена {SHOP_FLAT['rare']} €",
             f"👑 Эпический сундук, эпический и выше — цена {SHOP_FLAT['epic']} €", "",
             f"🔨 УЛУЧШЕНИЯ (снаряжение до {GEAR_MAX_LVL} уровня)",
             gear_line("⚔️", "weapon", "Оружие"), gear_line("🛡", "armor", "Броня"), gear_line("📿", "amulet", "Амулет"),
             bag, f"🌾 Разгон фермы ×1.5 на 24 ч — цена {SHOP_FLAT['boost']} €", "",
             "📈 УСИЛЕНИЯ",
             f"📈 Бонус XP ×1.5 на 24 ч — цена {SHOP_FLAT['xp']} €",
             f"🍀 Удача на 24 ч (добыча чуть чаще) — цена {SHOP_FLAT['luck']} €",
             f"🏷 Смена ника без ожидания — цена {SHOP_FLAT['nick']} €", ""]
    active = []
    if d.get("xp_until", 0) > now:
        active.append(f"📈 XP ×1.5 ещё {int((d['xp_until'] - now) // 3600)} ч")
    if d.get("luck_until", 0) > now:
        active.append(f"🍀 удача ещё {int((d['luck_until'] - now) // 3600)} ч")
    if active:
        lines += ["Сейчас действует: " + " · ".join(active), ""]
    on = d.get("att_extra_day") == time.strftime("%Y-%m-%d") and d.get("att_extra", 0) > 0
    lines.append(f"⚡ Энергетик (лимит атак +10 на сегодня){' · уже действует' if on else ''} — цена {SHOP_FLAT['energy']} €")
    return "\n".join(lines)

async def open_shop(update: Update, data: dict):
    uid = update.effective_user.id
    if uid in active_games and active_games[uid].get("game") == "duel":
        await reply(update, "⚠️ Сначала закончи бой.")
        return
    active_games[f"shop_{uid}"] = {"game": "shop"}
    await reply_pic(update, "shop", "🛒 Магазин: выбирай товары кнопками")
    await reply(update, shop_text(data))

async def buy_item(update: Update, user_id: int, data: dict, item: str):
    if user_id in active_games and active_games[user_id].get("game") == "duel":
        await reply(update, "⚠️ Сначала закончи бой.")
        return
    active_games[f"shop_{user_id}"] = {"game": "shop"}
    price = shop_price(data, item)
    if item in GEAR_SLOT_OF:
        it = data.get("eq", {}).get(GEAR_SLOT_OF[item])
        if not it:
            await reply(update, "ℹ️ В этом слоте ничего не надето. Сначала надень предмет: «🎒 Герой» → «🎒 Инвентарь».")
            return
        if it.get("u", 0) >= GEAR_MAX_LVL:
            await reply(update, f"ℹ️ Предмет уже на максимальном уровне ({GEAR_MAX_LVL}/{GEAR_MAX_LVL}).")
            return
        if not gear_ok(it, data):
            await reply(update, gear_mismatch_text(it, data))
            return
    if item == "bag" and data.get("inv_extra", 0) >= INV_MAX_EXTRA:
        await reply(update, f"ℹ️ Рюкзак уже расширен до максимума ({INV_BASE + INV_MAX_EXTRA} мест).")
        return
    if item == "energy" and data.get("att_extra_day") == time.strftime("%Y-%m-%d") and data.get("att_extra", 0) > 0:
        await reply(update, "⚡ Энергетик уже действует сегодня и не накапливается. Завтра можно купить снова. Монеты не потрачены.")
        return
    if data['coins'] < price:
        await reply(update, f"❌ Не хватает монет: нужно {price} €, у тебя {data['coins']} €.")
        return
    if item == "potion" and data['hp'] >= data['max_hp']:
        await reply(update, "ℹ️ У тебя и так полное HP, монеты не потрачены.")
        return
    data['coins'] -= price
    loot = None
    now = time.time()
    if item == "hp":
        data['max_hp'] += 20; data['hp'] += 20; data['bought_hp'] += 1
        done = "❤️ Макс. HP +20!"
    elif item == "atk":
        data['attack'] += 2; data['bought_atk'] += 1
        done = "⚔️ Атака +2!"
    elif item == "potion":
        data['hp'] = data['max_hp']
        done = "🧪 HP восстановлено полностью!"
    elif item == "energy":
        data['att_extra'] = 10
        data['att_extra_day'] = time.strftime("%Y-%m-%d")
        done = f"⚡ Лимит атак на сегодня +10: теперь {attacks_used(data)}/{attack_limit(data)} (до суточного сброса)"
    elif item in ("chest", "rare", "epic"):
        boost, min_r = {"chest": (0, 0), "rare": (2, 1), "epic": (3, 2)}[item]
        it = roll_loot(data, boost=boost, force=True, min_r=min_r)
        how = add_item(data, it)
        loot = (f"loot_{RARITY_KEY[it['r']]}", f"🎁 Из сундука выпало!\n{item_line(it)}\n→ {how}")
        done = "🎁 Сундук открыт!" + quest_event(data, "loot")
    elif item == "xp":
        data['xp_until'] = max(now, data.get('xp_until', 0)) + 86400
        done = "📈 Опыт ×1.5 на 24 часа!"
    elif item == "luck":
        data['luck_until'] = max(now, data.get('luck_until', 0)) + 86400
        done = "🍀 Удача на 24 часа: добыча падает чаще и лучше!"
    elif item in GEAR_SLOT_OF:
        it = data["eq"][GEAR_SLOT_OF[item]]
        it["u"] = it.get("u", 0) + 1
        done = f"🔨 Улучшено: {item_line(it)} (уровень {it['u']}/{GEAR_MAX_LVL})"
    elif item == "bag":
        data['inv_extra'] = data.get('inv_extra', 0) + INV_STEP
        done = f"🎒 Рюкзак расширен: теперь {inv_capacity(data)} мест (максимум {INV_BASE + INV_MAX_EXTRA})"
    elif item == "boost":
        data['farm_boost'] = max(now, data.get('farm_boost', 0)) + 86400
        done = "🚀 Доход фермы ×1.5 на 24 часа!"
    else:
        data['nick_ts'] = 0
        done = "🏷 Теперь ник можно сменить сразу: /nick Новый ник"
    done += quest_event(data, "shop")
    update_user_data(user_id, data)
    await reply(update, f"✅ Куплено: {done}\n\n{shop_text(data)}")
    if loot:
        await reply_pic(update, loot[0], loot[1])

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    await open_shop(update, get_user_data_safe(update.effective_user.id))

async def auto_heal(context: ContextTypes.DEFAULT_TYPE):
    healed_users = 0
    for uid, data in user_data.items():
        if data['hp'] < data['max_hp']:
            old_hp = data['hp']
            data['hp'] = min(data['max_hp'], data['hp'] + HEAL_AMOUNT)
            update_user_data(uid, data)
            healed_users += 1
    if healed_users > 0:
        logger.info(f"Авто-лечение завершено. Обработано {healed_users} игроков.")

# --- АДМИН-ПАНЕЛЬ (доступна только владельцу бота) ---
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
except ValueError:
    ADMIN_ID = 0
ONLINE_WINDOW = 300   # сколько секунд после последнего сообщения игрок считается «онлайн»
BAN_NOTICE = {}
ADMIN_COMMANDS = [
    BotCommand("admin", "Админ-панель"),
    BotCommand("give", "Выдать €: /give я 1кк"),
    BotCommand("giveall", "Выдать всем: /giveall 1000 да"),
    BotCommand("giveitem", "Выдать предмет: /giveitem я оружие легендарный"),
    BotCommand("setlevel", "Установить уровень: /setlevel я 50"),
    BotCommand("resetlimits", "Сбросить дневные лимиты"),
    BotCommand("broadcast", "Рассылка всем игрокам"),
    BotCommand("spawnboss", "Запустить мирового босса сейчас"),
    BotCommand("user", "Карточка игрока: /user ID или имя"),
    BotCommand("ban", "Забанить: /ban ID причина"),
    BotCommand("unban", "Разбанить: /unban ID"),
]
ADMIN_HOME = ("👑 Админ-панель\n\n💶 /give кому сумма: выдать € (я, ID или ник; 1кк, 3ккк; минус забирает)\n"
              "💶 /giveall сумма да: выдать всем\n🎁 /giveitem кому слот редкость\n⭐ /setlevel кому уровень\n"
              "♻️ /resetlimits кому|все\n📢 /broadcast текст: рассылка\n🐉 /spawnboss [Название] [HP]: мировой босс сейчас\n/user · /ban · /unban\n\nИли жми кнопки:")
ADMIN_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("📊 Статистика", callback_data="adm_stats"),
     InlineKeyboardButton("🏆 Рейтинг (все)", callback_data="adm_rating")],
    [InlineKeyboardButton("🕵️ Мультиводство", callback_data="adm_multi"),
     InlineKeyboardButton("🚫 Баны", callback_data="adm_bans")],
    [InlineKeyboardButton("💶 Выдать €", callback_data="adm_give"),
     InlineKeyboardButton("🎁 Предметы и уровни", callback_data="adm_item")],
    [InlineKeyboardButton("📢 Рассылка", callback_data="adm_bc"),
     InlineKeyboardButton("📜 Журнал", callback_data="adm_log")],
    [InlineKeyboardButton("🐉 Запустить босса мира", callback_data="adm_boss")],
    [InlineKeyboardButton("🔄 Главная", callback_data="adm_home")]])

def is_admin(update: Update) -> bool:
    u = update.effective_user
    return bool(ADMIN_ID and u and u.id == ADMIN_ID and is_private(update))

def fmt_time(ts) -> str:
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(ts)) if ts else "—"

def label(uid) -> str:
    d = user_data.get(uid, {})
    un = f" @{d['username']}" if d.get("username") else ""
    shown = f"{d['nick']} ({d.get('name') or '?'})" if d.get("nick") else (d.get("name") or "?")
    return f"{shown}{un} [{uid}]"

def record_pair(a: int, b: int):
    """Запоминает, что двое сыграли вместе (для проверки на мультиводство)."""
    global dirty
    for x, y in ((a, b), (b, a)):
        get_user_data_safe(x)
        p = user_data[x].setdefault("partners", {})
        p[str(y)] = p.get(str(y), 0) + 1
    dirty = True

def drop_games(uid: int):
    keys = [k for k, v in active_games.items()
            if k in (uid, f"solo_{uid}", f"tod_{uid}", f"shop_{uid}", f"scr_{uid}")
            or (isinstance(v, dict) and uid in (v.get("creator"), v.get("partner")))]
    for k in keys:
        del active_games[k]

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускается перед всеми обработчиками: отмечает активность и не пускает забаненных."""
    global dirty
    u = update.effective_user
    if not u or u.is_bot:
        return
    is_new = u.id not in user_data
    get_user_data_safe(u.id)
    rec = user_data[u.id]
    now = int(time.time())
    rec.setdefault("first_seen", now if is_new else 0)   # 0 = дата входа неизвестна (старый игрок)
    rec["last_seen"] = now
    rec["name"] = u.first_name or ""
    rec["username"] = u.username or ""
    dirty = True
    if rec.get("banned") and u.id != ADMIN_ID:
        msg = update.effective_message
        if msg and is_private(update) and time.time() - BAN_NOTICE.get(u.id, 0) > 600:
            BAN_NOTICE[u.id] = time.time()
            try:
                await msg.reply_text("🚫 Доступ к боту ограничен администратором.")
            except Exception:
                pass
        raise ApplicationHandlerStop
    today = time.strftime("%Y-%m-%d")
    if rec.get("last_day") != today:
        yday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
        rec["streak"] = (rec.get("streak", 0) + 1) if rec.get("last_day") == yday else 1
        rec["last_day"] = today
        bonus = min(10 * rec["streak"], 100)
        rec["coins"] = rec.get("coins", 0) + bonus
        if update.message and is_private(update):
            await reply_pic(update, "daily", f"🔥 Серия заходов: {rec['streak']} дн.\nЕжедневная награда: +{bonus} €")
    notes = ensure_world()
    if rec.get("ref_by") and not rec.get("ref_paid") and rec.get("level", 1) >= REF_LEVEL:
        notes += pay_referral(u.id, rec)
    if notes:
        await send_notes(context.bot, notes)

def stats_text() -> str:
    now = time.time()
    day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d"))
    vals = list(user_data.values())
    online = sum(1 for d in vals if now - d.get("last_seen", 0) <= ONLINE_WINDOW)
    today = sum(1 for d in vals if d.get("first_seen", 0) >= day0)
    week = sum(1 for d in vals if d.get("first_seen", 0) >= now - 7 * 86400)
    unknown = sum(1 for d in vals if not d.get("first_seen"))
    top = sorted(user_data.items(), key=lambda kv: (kv[1]["level"], kv[1].get("xp", 0)), reverse=True)[:5]
    lines = [f"📊 Статистика\n🟢 Онлайн (за {ONLINE_WINDOW // 60} мин): {online}\n👥 Всего игроков: {len(vals)}",
             f"🆕 Новых сегодня: {today} · за неделю: {week}",
             f"🚫 В бане: {sum(1 for d in vals if d.get('banned'))}", "", "🏆 Топ по уровню:"]
    lines += [f"{i}. {label(uid)} — ур. {d['level']}" for i, (uid, d) in enumerate(top, 1)]
    lines += admin_rating_lines()
    if unknown:
        lines.append(f"\nℹ️ У {unknown} старых игроков дата первого входа неизвестна.")
    return "\n".join(lines)

def card_text(uid: int) -> str:
    d = user_data[uid]
    partners = sorted(d.get("partners", {}).items(), key=lambda kv: -kv[1])[:3]
    ago = f"{int((time.time() - d['last_seen']) // 60)} мин назад" if d.get("last_seen") else "—"
    t = (f"👤 {label(uid)}\n⭐ Уровень {d['level']} · XP {d.get('xp', 0)} · ⚔️ {d['attack']} · "
         f"❤️ {d['hp']}/{d['max_hp']} · € {d.get('coins', 0)}\n"
         f"📅 Первый вход: {fmt_time(d.get('first_seen'))}\n🕒 Был: {ago}\n"
         f"👥 Игр на двоих: {sum(d.get('partners', {}).values())}")
    if partners:
        t += "\n🔗 Чаще всего с: " + ", ".join(f"{label(int(k))} ×{v}" for k, v in partners)
    if d.get("banned"):
        t += f"\n🚫 В БАНЕ: {d.get('ban_reason') or 'без причины'}"
    return t

def bans_text() -> str:
    rows = [f"🚫 {label(uid)} — {d.get('ban_reason') or 'без причины'}" for uid, d in user_data.items() if d.get("banned")]
    return "🚫 Баны\n\n" + ("\n".join(rows[:30]) if rows else "Пока никого нет.")

def norm_name(name) -> str:
    return re.sub(r"[\W_]+", "", (name or "").lower())

def multi_report() -> str:
    """Подсказки о возможном мультиводстве. Это эвристика, а не доказательство."""
    now = time.time()
    flags = []
    for uid, d in user_data.items():          # 1. пары, играющие почти только друг с другом
        total = sum(d.get("partners", {}).values())
        for pid, cnt in d.get("partners", {}).items():
            other = int(pid)
            other_total = sum(user_data.get(other, {}).get("partners", {}).values()) or 1
            if uid < other and cnt >= 5 and cnt / total >= 0.8 and cnt / other_total >= 0.8:
                flags.append((cnt + 10, f"🔗 {label(uid)} и {label(other)}: {cnt} игр на двоих почти только друг с другом"))
    buckets = {}                              # 2. похожие имена
    for uid, d in user_data.items():
        key = norm_name(d.get("name"))
        if len(key) >= 3:
            buckets.setdefault(key[:3], []).append(uid)
    for ids in buckets.values():
        ids = ids[:60]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                na, nb = norm_name(user_data[a].get("name")), norm_name(user_data[b].get("name"))
                fa, fb = user_data[a].get("first_seen", 0), user_data[b].get("first_seen", 0)
                close = bool(fa and fb and abs(fa - fb) <= 3600)
                if difflib.SequenceMatcher(None, na, nb).ratio() >= 0.85 and (len(na) >= 5 or close):
                    flags.append((5 if close else 3, f"👥 Похожие имена: {label(a)} и {label(b)}" + (" · созданы с разницей до часа" if close else "")))
    for uid, d in user_data.items():          # 3. слишком быстрый рост
        fs = d.get("first_seen")
        if fs:
            age = max(1.0, (now - fs) / 86400)
            if d["level"] > 3 + 4 * age:
                flags.append((d["level"], f"🚀 Быстрый рост: {label(uid)} — ур. {d['level']} за {age:.1f} дн."))
    for uid, d in user_data.items():          # 3.5. частые переводы €
        for pid, cnt in d.get("tr_to", {}).items():
            if cnt >= 5:
                flags.append((cnt + 6, f"💸 Частые переводы: {label(uid)} → {label(int(pid))} ×{cnt}"))
    byref = {}
    for uid, d in user_data.items():          # 4. много «друзей» за час, которые не играют
        if d.get("ref_by"):
            byref.setdefault(d["ref_by"], []).append(d)
    for rid, kids in byref.items():
        times = sorted(k.get("first_seen", 0) for k in kids if k.get("first_seen"))
        idle = sum(1 for k in kids if k.get("wins", 0) == 0 and k["level"] <= 1)
        if len(kids) >= 4 and times and times[-1] - times[0] <= 3600 and idle >= len(kids) - 1:
            flags.append((len(kids) + 8, f"🎁 Подозрительные рефералы: {label(rid)} привёл {len(kids)} аккаунтов за час, почти все без игры"))
    flags.sort(key=lambda x: -x[0])
    body = "\n\n".join(t for _, t in flags[:12]) if flags else "Подозрительного не найдено."
    return "🕵️ Проверка на мультиводство\n(это подсказки, а не доказательства)\n\n" + body

def find_players(query: str):
    q = query.strip().lstrip("@").lower()
    if not q:
        return []
    if q.isdigit():
        return [int(q)] if int(q) in user_data else []
    return [uid for uid, d in user_data.items()
            if q in str(d.get("name", "")).lower() or q in str(d.get("username", "")).lower() or q in str(d.get("nick", "")).lower()][:5]

def resolve_target(arg: str):
    if arg.isdigit():
        return int(arg)
    found = find_players(arg)
    return found[0] if len(found) == 1 else None

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_user:
        await update.message.reply_text(f"🆔 Твой Telegram ID: {update.effective_user.id}")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update) and update.message:
        await update.message.reply_text(ADMIN_HOME, reply_markup=ADMIN_KB)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    if not (ADMIN_ID and update.effective_user and update.effective_user.id == ADMIN_ID):
        return
    extra = await admin_extra(q.data, update, context)
    if extra is not None:
        text, markup = extra
    else:
        texts = {"adm_stats": stats_text, "adm_multi": multi_report, "adm_bans": bans_text, "adm_rating": admin_rating_all}
        text, markup = texts.get(q.data, lambda: ADMIN_HOME)(), ADMIN_KB
    try:
        await q.edit_message_text(text[:3900], reply_markup=markup)
    except Exception:
        pass  # текст не изменился

async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or not update.message:
        return
    found = find_players(" ".join(context.args or []))
    if not found:
        await update.message.reply_text("Игрок не найден. Пример: /user 12345 или /user Вася")
        return
    await update.message.reply_text("\n\n".join(card_text(u) for u in found)[:3900])

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global dirty
    if not is_admin(update) or not update.message:
        return
    if not context.args:
        await update.message.reply_text("Пример: /ban 12345 спам")
        return
    uid = resolve_target(context.args[0])
    if uid is None:
        await update.message.reply_text("Не нашёл игрока (или таких несколько). Укажи точный ID.")
        return
    if uid == ADMIN_ID:
        await update.message.reply_text("Себя банить нельзя.")
        return
    get_user_data_safe(uid)
    user_data[uid]["banned"] = True
    user_data[uid]["ban_reason"] = " ".join(context.args[1:])[:200]
    dirty = True
    drop_games(uid)
    await update.message.reply_text(f"🚫 Забанен: {label(uid)}")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global dirty
    if not is_admin(update) or not update.message:
        return
    uid = resolve_target(context.args[0]) if context.args else None
    if uid is None or uid not in user_data or not user_data[uid].get("banned"):
        await update.message.reply_text("Такого игрока в бане нет. Пример: /unban 12345")
        return
    user_data[uid].pop("banned", None)
    user_data[uid].pop("ban_reason", None)
    dirty = True
    await update.message.reply_text(f"✅ Разбанен: {label(uid)}")

# =====================================================================
#   ИГРОВЫЕ СИСТЕМЫ: ник, классы, лут, башня, мировой босс, PvP, сезоны, задания, достижения, кланы
# =====================================================================
WORLD_FILE = "world_data.json"
world = {"boss": {}, "clans": {}, "season": "", "week": ""}
PVP_DAILY = 10
SKILL_CD = 3
CLAN_COST = 200
CLASS_CHANGE_COST = 200
BOSS_NAMES = ["Древний Дракон", "Король Огров", "Повелитель Теней", "Ледяной Титан", "Ужас Бездны"]
BAD_NICK = ("admin", "админ", "moderator", "модератор", "владелец")
SLOTS = {"weapon": ("⚔️", ["Меч", "Топор", "Кинжал", "Копьё"]),
         "armor": ("🛡", ["Кольчуга", "Латы", "Щит", "Доспех"]),
         "amulet": ("📿", ["Амулет", "Талисман", "Кулон"])}
RARITY = [("⚪", "Обычный", 1.0), ("🔵", "Редкий", 1.8), ("🟣", "Эпический", 3.0), ("🟠", "Легендарный", 5.0)]
RARITY_KEY = ["common", "rare", "epic", "legendary"]
SELL_PRICE = [5, 15, 50, 200]
CLASSES = {
    "warrior": ("🛡 Воин", "получает на 15% меньше урона, навык «Мощный удар» ×1.8; своя броня на 25% сильнее"),
    "mage": ("🔮 Маг", "навык «Огненный шар» наносит ×2.6 урона; своё оружие на 20% сильнее"),
    "archer": ("🏹 Лучник", "25% шанс критического удара ×2, навык «Град стрел» (3 выстрела); свои амулеты на 25% сильнее"),
}
SKILLS = {"": ("Сильный удар", 1.6), "warrior": ("Мощный удар", 1.8), "mage": ("Огненный шар", 2.6), "archer": ("Град стрел", 0.9)}
QUEST_POOL = [
    ("win", "Победить в боях", 3, 40), ("guess", "Угадать число", 2, 30), ("pvp", "Сыграть на арене", 2, 40),
    ("tower", "Пройти этажи башни", 3, 45), ("boss", "Ударить мирового босса", 3, 35), ("shop", "Купить что-нибудь в магазине", 1, 30),
]
ACH = {
    "first_win": ("Первая кровь", "Победи в первом бою", lambda d: d.get("wins", 0) >= 1, 20),
    "wins_10": ("Боец", "10 побед в боях", lambda d: d.get("wins", 0) >= 10, 50),
    "wins_100": ("Ветеран", "100 побед в боях", lambda d: d.get("wins", 0) >= 100, 300),
    "lvl_10": ("Десятка", "Достигни 10 уровня", lambda d: d["level"] >= 10, 100),
    "lvl_25": ("Мастер", "Достигни 25 уровня", lambda d: d["level"] >= 25, 250),
    "lvl_50": ("Легенда", "Достигни 50 уровня", lambda d: d["level"] >= 50, 600),
    "tower_10": ("Покоритель башни", "Пройди 10 этажей башни", lambda d: d.get("tower_best", 0) >= 10, 150),
    "tower_30": ("Хозяин башни", "Пройди 30 этажей башни", lambda d: d.get("tower_best", 0) >= 30, 400),
    "legend": ("Счастливчик", "Найди легендарный предмет", lambda d: d.get("found_legend", 0) >= 1, 200),
    "pvp_10": ("Гладиатор", "10 побед на арене", lambda d: d.get("pvp_wins", 0) >= 10, 150),
    "boss_kill": ("Убийца драконов", "Участвуй в победе над мировым боссом", lambda d: d.get("boss_kills", 0) >= 1, 250),
    "clan": ("Соратник", "Вступи в клан", lambda d: bool(d.get("clan")), 30),
    "streak_7": ("Постоянство", "7 дней подряд в игре", lambda d: d.get("streak", 0) >= 7, 100),
}

def touch():
    global dirty
    dirty = True

def load_world():
    if os.path.exists(WORLD_FILE):
        try:
            with open(WORLD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка чтения мира: {e}")
    return {}

def _save_world():
    try:
        tmp = WORLD_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(world, f, ensure_ascii=False, indent=2)
        os.replace(tmp, WORLD_FILE)
    except Exception as e:
        logger.error(f"Ошибка сохранения мира: {e}")

def week_id() -> str:
    return time.strftime("%G-W%V")

def season_id() -> str:
    return time.strftime("%Y-%m")

def pname(uid, fallback="Игрок") -> str:
    """Игровое имя: ник, если задан, иначе имя из Telegram."""
    d = user_data.get(uid, {})
    return d.get("nick") or d.get("name") or fallback

def bar(cur, mx, n=10) -> str:
    filled = max(0, min(n, round(n * cur / mx))) if mx else 0
    return "🟥" * filled + "⬜" * (n - filled)

async def send_notes(bot, notes):
    for uid, text in notes[:300]:
        try:
            await send_msg(bot, chat_id=int(uid), text=text)
        except Exception:
            pass

def give(uid, coins=0, xp=0):
    rec = user_data.get(int(uid))
    if rec is None:
        return
    rec["coins"] = rec.get("coins", 0) + coins
    if xp:
        add_xp(rec, xp)
    touch()

# ---------------- ник ----------------
async def nick_apply(update: Update, arg: str):
    uid = update.effective_user.id
    get_user_data_safe(uid)
    rec = user_data[uid]
    arg = " ".join(arg.split())
    if not arg:
        cur = rec.get("nick") or "не задан (показывается имя из Telegram)"
        await reply(update, f"🏷 Твой ник: {cur}\n\nСменить: /nick Новый ник\nСбросить: /nick сброс\n"
                            "2–16 символов: буквы, цифры, пробел, дефис, подчёркивание. Менять можно раз в сутки.")
        return
    if arg.lower() in ("сброс", "reset"):
        rec.pop("nick", None)
        rec["nick"] = ""
        touch()
        await reply(update, "✅ Ник сброшен, теперь показывается имя из Telegram.")
        return
    left = 86400 - (time.time() - rec.get("nick_ts", 0))
    if rec.get("nick") and left > 0:
        await reply(update, f"⏳ Ник можно менять раз в сутки. Подожди ещё {int(left // 3600)} ч {int(left % 3600 // 60)} мин.")
        return
    if not re.fullmatch(r"[\w\- ]{2,16}", arg) or arg.isdigit():
        await reply(update, "❌ Ник: 2–16 символов, буквы, цифры, пробел, дефис, подчёркивание, и не одни цифры.")
        return
    if uid != ADMIN_ID and any(b in arg.lower() for b in BAD_NICK):
        await reply(update, "❌ Такой ник использовать нельзя.")
        return
    if any(u != uid and str(d.get("nick", "")).lower() == arg.lower() for u, d in user_data.items()):
        await reply(update, "❌ Этот ник уже занят, выбери другой.")
        return
    rec["nick"] = arg
    rec["nick_ts"] = time.time()
    touch()
    await reply(update, f"✅ Теперь тебя зовут «{arg}». Это имя видно в рейтингах, кланах и боях с другими игроками.")

async def nick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_user:
        await nick_apply(update, " ".join(context.args or []))

# ---------------- экипировка и лут ----------------
WEAPON_PCT = [0.05, 0.10, 0.18, 0.30]   # оружие: прибавка к атаке в % от базовой атаки героя (кроме своей силы)
ARMOR_PCT = [0.04, 0.08, 0.14, 0.22]    # броня: какую долю входящего урона она гасит

def equip_bonus(data: dict):
    """(прибавка к атаке, гашение урона числом, % к € с побед). Считается только снаряжение своего класса, с учётом прокачки."""
    atk = dfn = coin = 0
    for it in data.get("eq", {}).values():
        if not gear_ok(it, data):
            continue
        f = gear_factor(it)
        if it["s"] == "weapon":
            atk += int((it["p"] + int(data.get("attack", 0) * WEAPON_PCT[it["r"]])) * f)
        elif it["s"] == "armor":
            dfn += int(it["p"] * f)
        else:
            coin += int(it["p"] * f)
    return atk, dfn, coin

def armor_pct(data: dict) -> float:
    """Доля входящего урона, которую гасит надетая броня (не больше 60%)."""
    return min(0.6, sum(ARMOR_PCT[it["r"]] * gear_factor(it) for it in data.get("eq", {}).values()
                        if it["s"] == "armor" and gear_ok(it, data)))

def total_attack(data: dict) -> int:
    return data["attack"] + equip_bonus(data)[0]

def item_line(it: dict) -> str:
    e, rn, _ = RARITY[it["r"]]
    u = it.get("u", 0)
    p = int(it["p"] * gear_factor(it))
    stat = {"weapon": f"+{p} к атаке", "armor": f"−{p} получаемого урона", "amulet": f"+{p}% монет"}[it["s"]]
    cls = f" · {CLASSES[it['c']][0].split()[0]}" if it.get("c") in CLASSES else ""
    return f"{e} {SLOTS[it['s']][0]} {it['n']}{f' +{u}' if u else ''} · {rn}{cls} · {stat}"

def sell_price(it: dict, data: dict) -> int:
    return SELL_PRICE[it["r"]] * (1 + data["level"] // 10)

LOOT_BASE_CHANCE = 0.04   # шанс снаряжения за обычную победу: редкая находка, а не плата за бой
GEAR_NAMES = {
    "": {s: SLOTS[s][1] for s in SLOTS},   # универсальные предметы (старые и для героев без класса)
    "warrior": {"weapon": ["Меч", "Боевой топор", "Секира"], "armor": ["Латы", "Кольчуга", "Тяжёлый щит"],
                "amulet": ["Талисман храбрости", "Знак легиона"]},
    "mage": {"weapon": ["Посох", "Жезл", "Гримуар"], "armor": ["Мантия", "Роба", "Плащ мага"],
             "amulet": ["Кристалл силы", "Руна мудрости"]},
    "archer": {"weapon": ["Лук", "Арбалет", "Охотничий кинжал"], "armor": ["Кожаный доспех", "Куртка следопыта", "Наручи"],
               "amulet": ["Амулет охотника", "Перо удачи"]},
}

def gear_ok(it: dict, data: dict) -> bool:
    """Предмет без класса подходит всем, предмет класса только бойцу этого класса."""
    return not it.get("c") or it["c"] == data.get("class", "")

CLASS_GEAR_MULT = {"warrior": {"armor": 1.25}, "mage": {"weapon": 1.20}, "archer": {"amulet": 1.25, "weapon": 1.05}}

def gear_factor(it: dict) -> float:
    """Сила предмета: +8% за каждый уровень закалки и бонус класса за своё «родное» снаряжение."""
    return (1 + 0.08 * it.get("u", 0)) * CLASS_GEAR_MULT.get(it.get("c", ""), {}).get(it["s"], 1.0)

def gear_name(slot: str, cls: str) -> str:
    return random.choice(GEAR_NAMES.get(cls, GEAR_NAMES[""])[slot])

def gear_mismatch_text(it: dict, data: dict) -> str:
    need = CLASSES[it["c"]][0]
    mine = CLASSES.get(data.get("class", ""), ("без класса",))[0]
    return (f"🚫 «{it['n']}» — снаряжение класса {need}. Ты сейчас: {mine}, поэтому надеть его нельзя.\n"
            "Смени класс в «🎒 Герой» → «🧙 Класс» или продай предмет.")

def unequip_mismatched(data: dict) -> int:
    """Снимает в рюкзак снаряжение чужого класса (например, после смены класса)."""
    eq, moved = data.setdefault("eq", {}), 0
    for slot in list(eq):
        if not gear_ok(eq[slot], data):
            data.setdefault("inv", []).append(eq.pop(slot))
            moved += 1
    return moved

INV_BASE, INV_STEP, INV_MAX_EXTRA = 30, 10, 150

def inv_capacity(d: dict) -> int:
    return INV_BASE + min(INV_MAX_EXTRA, d.get("inv_extra", 0))

def roll_loot(data: dict, boost=0, force=False, min_r=0):
    """Снаряжение выпадает редко. Основная масса предметов начального уровня, сильные встречаются очень редко."""
    if data.get("luck_until", 0) > time.time():
        boost += 1   # купленная удача
    if not force and random.random() > min(0.30, LOOT_BASE_CHANCE + boost * 0.03):
        return None
    weights = [max(40, 88 - boost * 6), 10 + boost * 2, 2 + boost * 0.8, 0.3 + boost * 0.2]
    r = max(min_r, random.choices(range(4), weights=weights)[0])
    slot = random.choice(list(SLOTS))
    cls = data.get("class", "")
    it = {"n": gear_name(slot, cls), "s": slot, "r": r, "p": calc_power(slot, r, data["level"])}
    if cls:
        it["c"] = cls
    return it

def add_item(data: dict, it: dict) -> str:
    if it["r"] == 3:
        data["found_legend"] = data.get("found_legend", 0) + 1
    eq = data.setdefault("eq", {})
    ok = gear_ok(it, data)
    if it["s"] not in eq and ok:
        eq[it["s"]] = it
        return "сразу надето ✅"
    inv = data.setdefault("inv", [])
    if len(inv) >= inv_capacity(data):
        data["coins"] += sell_price(it, data)
        return "рюкзак полон, продано автоматически"
    inv.append(it)
    return "лежит в рюкзаке" + ("" if ok else " (снаряжение другого класса)")

def loot_reward(data: dict, boost=0):
    """Бросает добычу. Возвращает (картинка, текст) или None."""
    it = roll_loot(data, boost)
    if not it:
        return None
    how = add_item(data, it)
    return f"loot_{RARITY_KEY[it['r']]}", f"🎁 Добыча!\n{item_line(it)}\n→ {how}"

def inv_text(data: dict) -> str:
    a, d, c = equip_bonus(data)
    eq = data.get("eq", {})
    cls = CLASSES.get(data.get("class", ""))
    lines = [f"🎒 Инвентарь · {cls[0] if cls else 'класс не выбран'} · 🔩 осколков: {data.get('shards', 0)}",
             f"Бонусы: ⚔️ +{a} к атаке · 🛡 −{d} урона и −{int(armor_pct(data) * 100)}% урона · 📿 +{c}% € и +{c // 2}% XP", "", "Надето:"]
    for slot in SLOTS:
        lines.append("  " + (item_line(eq[slot]) if slot in eq else f"{SLOTS[slot][0]} — пусто"))
    inv = data.get("inv", [])
    lines.append(f"\nВ рюкзаке ({len(inv)}/{inv_capacity(data)}):")
    lines += [f"{i}. {'🚫 ' if not gear_ok(it, data) else ''}{item_line(it)}" for i, it in enumerate(inv[:15], 1)] or ["  пусто"]
    if len(inv) > 15:
        lines.append(f"…и ещё {len(inv) - 15}")
    if any(not gear_ok(it, data) for it in inv):
        lines.append("🚫 — снаряжение другого класса, надеть его нельзя")
    if not cls:
        lines.append("\n💡 Выбери класс: «🎒 Герой» → «🧙 Класс». От него зависит, какое снаряжение тебе подходит.")
    lines.append("\nКоманды: «надеть N», «продать N», «выбросить N». Продажа и выброс спрашивают подтверждение.\n"
                 "🔨 Ковка: снаряжение и закалка за осколки. ♻️ Разбор хлама даёт осколки.")
    return "\n".join(lines)

def equip_best(data: dict) -> int:
    eq = data.setdefault("eq", {})
    inv = data.setdefault("inv", [])
    changed = 0
    for slot in SLOTS:
        cands = [it for it in inv if it["s"] == slot and gear_ok(it, data)]   # чужой класс не рассматриваем
        if not cands:
            continue
        best = max(cands, key=lambda it: (it["p"] * gear_factor(it), it["r"]))
        cur = eq.get(slot)
        if cur is None or (best["p"] * gear_factor(best), best["r"]) > (cur["p"] * gear_factor(cur), cur["r"]):
            inv.remove(best)
            if cur:
                inv.append(cur)
            eq[slot] = best
            changed += 1
    return changed

def sell_junk(data: dict):
    inv = data.setdefault("inv", [])
    keep, total, n = [], 0, 0
    for it in inv:
        if it["r"] <= 1:
            total += sell_price(it, data)
            n += 1
        else:
            keep.append(it)
    data["inv"] = keep
    data["coins"] += total
    return n, total

# ---------------- задания, серия, достижения ----------------
def quests_today(data: dict) -> dict:
    day = time.strftime("%Y-%m-%d")
    q = data.setdefault("q", {})
    if q.get("day") != day:
        q.clear()
        q.update({"day": day, "have": {}, "done": [], "ids": [x[0] for x in random.sample(QUEST_POOL, 3)]})
    return q

def quest_event(data: dict, kind: str, n=1) -> str:
    q = quests_today(data)
    out = ""
    for qid, text, need, coins in QUEST_POOL:
        if qid == kind and qid in q["ids"] and qid not in q["done"]:
            q["have"][qid] = q["have"].get(qid, 0) + n
            if q["have"][qid] >= need:
                q["done"].append(qid)
                data["coins"] += coins
                add_xp(data, 15)
                out += f"\n📅 Задание выполнено: {text} (+{coins} €, +15 XP)"
    return out

def quests_text(data: dict) -> str:
    q = quests_today(data)
    lines = ["📅 Задания на сегодня"]
    for qid, text, need, coins in QUEST_POOL:
        if qid in q["ids"]:
            mark = "✅" if qid in q["done"] else "▫️"
            lines.append(f"{mark} {text}: {min(q['have'].get(qid, 0), need)}/{need} · {coins} €")
    lines.append(f"\n🔥 Серия заходов: {data.get('streak', 0)} дн. Награда за вход растёт каждый день (до 100 €).")
    return "\n".join(lines)

def check_ach(data: dict) -> str:
    got = data.setdefault("ach", [])
    out = ""
    for key, (name, desc, cond, coins) in ACH.items():
        if key not in got and cond(data):
            got.append(key)
            data["coins"] += coins
            data.setdefault("titles", []).append(name)
            data["title"] = name
            out += f"\n🏅 Достижение «{name}»: +{coins} €"
    return out

def ach_text(data: dict) -> str:
    got = data.get("ach", [])
    lines = [f"🏅 Достижения ({len(got)}/{len(ACH)})"]
    for key, (name, desc, cond, coins) in ACH.items():
        lines.append(f"{'✅' if key in got else '🔒'} {name}: {desc} · {coins} €")
    if data.get("title"):
        lines.append(f"\n🎖 Текущий титул: {data['title']}")
    return "\n".join(lines)

# ---------------- кланы ----------------
def find_clan(name: str):
    for k in world["clans"]:
        if k.lower() == name.lower():
            return k
    return None

def clan_points(data: dict, n: int):
    c = world["clans"].get(data.get("clan", ""))
    if c:
        c["week"] += n
        c["total"] += n
        touch()

def clan_text(data: dict) -> str:
    name = data.get("clan")
    c = world["clans"].get(name)
    if not c:
        return ("👥 Клан\n\nТы пока не в клане.\n"
                f"Создать: «клан создать Название» ({CLAN_COST} €)\nВступить: «клан вступить Название»\n"
                "Топ кланов: «клан топ»\n\nКланы соревнуются неделю: лучшим три клана получают награды.")
    members = sorted(c["members"], key=lambda u: -user_data.get(u, {}).get("level", 0))
    lines = [f"👥 Клан «{name}»", f"Очков за неделю: {c['week']} · всего: {c['total']}",
             f"Участников: {len(members)}/30", ""]
    for u in members[:10]:
        lines.append(("👑 " if u == c["owner"] else "• ") + f"{pname(u)} — ур. {user_data.get(u, {}).get('level', 1)}")
    lines.append("\nОчки приносят победы в боях, башня, арена и урон по мировому боссу.")
    return "\n".join(lines)

def clan_top_text() -> str:
    top = sorted(world["clans"].items(), key=lambda kv: (-kv[1]["week"], -kv[1]["total"]))[:10]
    lines = ["🏆 Топ кланов (неделя)"]
    lines += [f"{i}. {n} — {c['week']} оч. ({len(c['members'])} уч.)" for i, (n, c) in enumerate(top, 1)] or ["Пока нет кланов."]
    lines.append("\nНаграды в конце недели: 🥇 300 · 🥈 200 · 🥉 100 € каждому участнику")
    return "\n".join(lines)

async def clan_command(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict, orig: str):
    parts = orig.split(None, 2)
    action = parts[1].lower() if len(parts) > 1 else ""
    arg = " ".join(parts[2].split()) if len(parts) > 2 else ""
    if action == "топ":
        await reply_pic(update, "clan_top", clan_top_text())
    elif action == "создать":
        if data.get("clan"):
            await reply(update, "⚠️ Ты уже в клане. Сначала выйди: «клан выйти».")
        elif not re.fullmatch(r"[\w\- ]{3,16}", arg):
            await reply(update, "❌ Название клана: 3–16 символов, буквы, цифры, пробел, дефис.")
        elif find_clan(arg):
            await reply(update, "❌ Клан с таким названием уже есть.")
        elif data["coins"] < CLAN_COST:
            await reply(update, f"❌ Не хватает монет: нужно {CLAN_COST} €, у тебя {data['coins']} €.")
        else:
            data["coins"] -= CLAN_COST
            data["clan"] = arg
            world["clans"][arg] = {"owner": user_id, "members": [user_id], "week": 0, "total": 0}
            an = check_ach(data)
            update_user_data(user_id, data)
            await reply_pic(update, "clan", f"✅ Клан «{arg}» создан!{an}\n\n{clan_text(data)}")
    elif action == "вступить":
        name = find_clan(arg) if arg else None
        if data.get("clan"):
            await reply(update, "⚠️ Ты уже в клане.")
        elif not name:
            await reply(update, "❌ Клан не найден. Список: «клан топ».")
        elif len(world["clans"][name]["members"]) >= 30:
            await reply(update, "❌ В клане уже 30 участников.")
        else:
            world["clans"][name]["members"].append(user_id)
            data["clan"] = name
            an = check_ach(data)
            update_user_data(user_id, data)
            await reply_pic(update, "clan", f"✅ Ты вступил в клан «{name}»!{an}\n\n{clan_text(data)}")
    elif action == "выйти":
        await clan_leave(update, user_id, data)
    else:
        await reply_pic(update, "clan", clan_text(data))

async def clan_leave(update: Update, user_id: int, data: dict):
    name = data.get("clan")
    c = world["clans"].get(name)
    if not c:
        await reply(update, "ℹ️ Ты не состоишь в клане.")
        return
    if user_id in c["members"]:
        c["members"].remove(user_id)
    if not c["members"]:
        del world["clans"][name]
    elif c["owner"] == user_id:
        c["owner"] = c["members"][0]
    data["clan"] = ""
    update_user_data(user_id, data)
    await reply(update, f"🚪 Ты вышел из клана «{name}».")

# ---------------- мир: мировой босс, недели, сезоны ----------------
def new_boss(week: str):
    hp = 3000 + 150 * min(len(user_data), 300)
    idx = int(week.split("W")[1]) % len(BOSS_NAMES)
    world["boss"] = {"week": week, "name": BOSS_NAMES[idx], "hp": hp, "max": hp, "dmg": {}, "dead": False, "last": 0}
    touch()

def weekly_rollover() -> list:
    notes = []
    b = world.get("boss") or {}
    if b and not b.get("dead"):
        for u, dm in b.get("dmg", {}).items():
            coins = min(200, dm // 20)
            if coins:
                give(u, coins)
                notes.append((u, f"🐉 Босс «{b['name']}» не был повержен, но твой урон {dm} принёс {coins} €."))
    ranked = sorted(world["clans"].items(), key=lambda kv: -kv[1]["week"])
    for place, (name, c) in enumerate([x for x in ranked if x[1]["week"] > 0][:3]):
        coins = (300, 200, 100)[place]
        for u in c["members"]:
            give(u, coins)
            notes.append((u, f"🏆 Клан «{name}» занял {place + 1} место за неделю: +{coins} € каждому участнику!"))
    for c in world["clans"].values():
        c["week"] = 0
    return notes

def season_rollover(old: str) -> list:
    notes = []
    players = sorted(((d.get("rating", 1000), u) for u, d in user_data.items() if d.get("pvp_games", 0) > 0 and not d.get("banned")), reverse=True)
    for place, (r, u) in enumerate(players[:3]):
        coins = (500, 300, 150)[place]
        give(u, coins)
        title = ("Чемпион ", "Вице-чемпион ", "Призёр ")[place] + old
        user_data[u].setdefault("titles", []).append(title)
        user_data[u]["title"] = title
        notes.append((u, f"🏆 Сезон {old} завершён! Ты занял {place + 1} место (рейтинг {r}): +{coins} € и титул «{title}»."))
    for d in user_data.values():
        d["rating"] = 1000 + (d.get("rating", 1000) - 1000) // 2
    touch()
    return notes

def ensure_world() -> list:
    """Следит за сменой недели и сезона. Возвращает список (игрок, текст) для рассылки."""
    notes = []
    wk, ss = week_id(), season_id()
    if world.get("week") != wk:
        if world.get("week"):
            notes += weekly_rollover()
        world["week"] = wk
        new_boss(wk)
    if world.get("season") != ss:
        if world.get("season"):
            notes += season_rollover(world["season"])
        world["season"] = ss
        touch()
    return notes

def boss_text(user_id: int) -> str:
    if not world.get("boss"):
        ensure_world()   # босс создаётся, если его ещё нет
    b = world.get("boss") or {}
    if not b:
        return "🐉 Босс пока не появился."
    dmg = b.get("dmg", {})
    top = sorted(dmg.items(), key=lambda kv: -kv[1])[:5]
    lines = [f"🐉 Мировой босс: {b['name']}", bar(b["hp"], b["max"]),
             f"❤️ {b['hp']}/{b['max']}" + (" · ПОВЕРЖЕН ✅" if b.get("dead") else ""),
             f"Твой урон: {dmg.get(str(user_id), 0)}", "", "🏆 Лучшие бойцы:"]
    lines += [f"{i}. {pname(int(u))} — {v}" for i, (u, v) in enumerate(top, 1)] or ["Пока никто не бил."]
    lines.append("\nКаждый удар тратит 1 атаку из дневного лимита. Новый босс появляется каждый понедельник.")
    return "\n".join(lines)

def boss_defeated(killer: int) -> list:
    b = world["boss"]
    total = sum(b["dmg"].values()) or 1
    ranked = sorted(b["dmg"].items(), key=lambda kv: -kv[1])
    notes = []
    for place, (u, dm) in enumerate(ranked):
        uid = int(u)
        rec = user_data.get(uid)
        if rec is None:
            continue
        coins = 100 + int(400 * dm / total) + (200 if uid == killer else 0)
        give(uid, coins, 100)
        rec["boss_kills"] = rec.get("boss_kills", 0) + 1
        text = f"🐉 «{b['name']}» повержен! Твой урон: {dm}. Награда: +{coins} € и +100 XP."
        if uid == killer:
            text += " Ты нанёс последний удар (+200 €)!"
        if place < 3:
            lr = loot_reward(rec, boost=3)
            if lr:
                text += f"\n{lr[1]}"
        notes.append((uid, text))
    touch()
    return notes

async def boss_hit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict):
    await send_notes(context.bot, ensure_world())
    b = world["boss"]
    if b.get("dead"):
        await reply(update, "🐉 Босс уже повержен. Новый появится в понедельник.")
        return
    if attacks_used(data) >= attack_limit(data):
        await reply(update, f"⚡ Лимит атак на сегодня исчерпан ({attack_limit(data)}/{attack_limit(data)}).")
        return
    data["att_used"] = attacks_used(data) + 1
    dmg = min(b["hp"], max(1, int(total_attack(data) * random.uniform(2.0, 3.0))))
    b["hp"] -= dmg
    b["dmg"][str(user_id)] = b["dmg"].get(str(user_id), 0) + dmg
    data["coins"] += 2
    qn = quest_event(data, "boss")
    clan_points(data, max(1, dmg // 50))
    update_user_data(user_id, data)
    text = f"💥 Ты нанёс боссу {dmg} урона!{qn}\n\n{boss_text(user_id)}"
    kind = "worldboss"
    if b["hp"] <= 0:
        b["dead"] = True
        b["last"] = user_id
        notes = boss_defeated(user_id)
        mine = [t for u, t in notes if u == user_id]
        an = check_ach(user_data[user_id])
        text = f"💥 Последний удар: {dmg} урона!\n" + (mine[0] if mine else "") + an
        kind = "worldboss_win"
        await send_notes(context.bot, [(u, t) for u, t in notes if u != user_id])
    touch()
    await reply_pic(update, kind, text)

# ---------------- арена (PvP) ----------------
def fighter(d: dict) -> dict:
    return {"hp": d["max_hp"], "att": total_attack(d), "dfn": equip_bonus(d)[1], "red": armor_pct(d), "cls": d.get("class", "")}

def simulate(a: dict, b: dict):
    """Автобой двух игроков. Возвращает (победил ли первый, раундов)."""
    hp = [a["hp"], b["hp"]]
    f = [a, b]
    turn = random.choice([0, 1])
    rounds = 0
    while hp[0] > 0 and hp[1] > 0 and rounds < 80:
        att, tgt = f[turn], f[1 - turn]
        d = random.randint(max(1, att["att"] - 3), att["att"] + 3)
        if att["cls"] == "archer" and random.random() < 0.25:
            d *= 2
        if att["cls"] == "mage" and rounds % 6 >= 4:
            d = int(d * 1.8)
        d = max(1, int((d - tgt["dfn"]) * (1 - tgt.get("red", 0))))
        if tgt["cls"] == "warrior":
            d = max(1, int(d * 0.85))
        hp[1 - turn] -= d
        turn = 1 - turn
        rounds += 1
    if hp[0] > 0 and hp[1] > 0:
        return hp[0] / a["hp"] >= hp[1] / b["hp"], rounds
    return hp[0] > 0, rounds

async def pvp_fight(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict):
    day = time.strftime("%Y-%m-%d")
    if data.get("pvp_day") != day:
        data["pvp_day"], data["pvp_used"] = day, 0
    if data["pvp_used"] >= PVP_DAILY:
        await reply(update, f"⏳ Лимит арены на сегодня исчерпан ({PVP_DAILY}/{PVP_DAILY}). Приходи завтра.")
        return
    mine = data.get("rating", 1000)
    cands = sorted((abs(d.get("rating", 1000) - mine), u) for u, d in user_data.items() if u != user_id and not d.get("banned"))[:8]
    if not cands:
        await reply(update, "😕 Пока нет соперников. Позови друзей в бота.")
        return
    opp = random.choice(cands)[1]
    od = user_data[opp]
    won, rounds = simulate(fighter(data), fighter(od))
    ro = od.get("rating", 1000)
    exp = 1 / (1 + 10 ** ((ro - mine) / 400))
    delta = round(24 * ((1 if won else 0) - exp)) or (1 if won else -1)
    data["rating"] = max(0, mine + delta)
    od["rating"] = max(0, ro - delta)
    data["pvp_used"] += 1
    data["pvp_games"] = data.get("pvp_games", 0) + 1
    od["pvp_games"] = od.get("pvp_games", 0) + 1
    if won:
        data["pvp_wins"] = data.get("pvp_wins", 0) + 1
        coins = 15 + abs(delta)
        data["coins"] += coins
        add_xp(data, 20)
        clan_points(data, 2)
        res = f"🏆 Победа над {pname(opp)}! Рейтинг {delta:+d} → {data['rating']}. +{coins} € и +20 XP."
    else:
        add_xp(data, 5)
        res = f"💀 Поражение от {pname(opp)}. Рейтинг {delta:+d} → {data['rating']}. +5 XP."
    qn = quest_event(data, "pvp")
    an = check_ach(data)
    update_user_data(user_id, data)
    try:
        await send_msg(context.bot, chat_id=opp, text=f"⚔️ {pname(user_id)} вызвал тебя на арене и {'проиграл' if won else 'победил'}. Рейтинг {-delta:+d} → {od['rating']}.")
    except Exception:
        pass
    await reply_pic(update, "pvp_win" if won else "pvp_lose", f"{res}\n⚔️ Боёв сегодня: {data['pvp_used']}/{PVP_DAILY} · раундов: {rounds}{qn}{an}")

# ---------------- бой: классы, навыки, башня ----------------
def make_enemy(floor: int) -> dict:
    if floor % 10 == 0:
        return {"name": f"Страж башни {floor // 10}", "hp": 150 + floor * 40, "attack": 15 + int(floor * 2.5)}
    name = list(CREATURES)[(floor - 1) % len(CREATURES)]
    c = CREATURES[name]
    return {"name": name, "hp": c["hp"] + floor * 18, "attack": c["attack"] + int(floor * 1.5)}

def tower_game(data: dict, floor: int) -> dict:
    e = make_enemy(floor)
    return {"game": "duel", "mode": "tower", "floor": floor, "player_hp": data["hp"], "bot_hp": e["hp"],
            "bot_attack": e["attack"], "round": 1, "opponent": e["name"], "cd": 0, "boss": floor % 10 == 0}

async def start_tower(update: Update, user_id: int, data: dict):
    if user_id in active_games and active_games[user_id].get("game") == "duel":
        await reply(update, "⚠️ Бой уже идёт.")
        return
    if data["hp"] <= 0:
        await reply(update, "🩸 У тебя 0 HP. Подожди лечения (+15 HP каждую минуту).")
        return
    if attacks_used(data) >= attack_limit(data):
        await reply(update, f"⚡ Лимит атак на сегодня исчерпан ({attack_limit(data)}/{attack_limit(data)}). Новые атаки появятся завтра.")
        return
    g = tower_game(data, 1)
    active_games[user_id] = g
    await reply_pic(update, "tower", f"🗼 БАШНЯ · этаж 1\nПротивник: {g['opponent']} (HP {g['bot_hp']})\nРекорд: этаж {data.get('tower_best', 0)}\n"
                                      "HP между этажами сохраняется (+20% за этаж). Поражение завершает забег.\nВыбирай действие.")

async def fight_action(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict, game: dict, action: str):
    cls = data.get("class", "")
    cd = game.get("cd", 0)
    if action == "навык" and cd > 0:
        await reply(update, f"⏳ Навык перезаряжается: ещё {cd} ход(а).")
        return
    att = total_attack(data)
    dfn = equip_bonus(data)[1]
    if attacks_used(data) >= attack_limit(data):
        await reply(update, f"⚡ Лимит атак на сегодня исчерпан ({attacks_used(data)}/{attack_limit(data)}). "
                            "Выйти из боя: «🏃 Уйти». Лимит можно расширить в магазине: ⚡ Энергетик.")
        return
    game.setdefault("bot_max", game["bot_hp"])
    data["att_used"] = attacks_used(data) + 1
    opp = game["opponent"]
    defending = False

    def swing(mult=1.0):
        base = random.randint(max(1, att - 3), att + 3) * mult
        crit = cls == "archer" and random.random() < 0.25
        return max(1, int(base * (2 if crit else 1))), crit

    if action == "защита":
        defending = True
        heal = max(1, data["max_hp"] // 20)
        game["player_hp"] = min(data["max_hp"], game["player_hp"] + heal)
        log = f"🛡 Ты закрылся щитом и восстановил {heal} HP.\n"
    elif action == "навык":
        sname, mult = SKILLS.get(cls, SKILLS[""])
        if cls == "archer":
            dmg = sum(swing(mult)[0] for _ in range(3))
            log = f"🏹 {sname}: три выстрела, всего {dmg} урона!\n"
        else:
            dmg = max(1, int(random.randint(max(1, att - 3), att + 3) * mult))
            log = f"💥 {sname}: {dmg} урона!\n"
        game["bot_hp"] -= dmg
    else:
        dmg, crit = swing()
        game["bot_hp"] -= dmg
        log = f"{'💥 Крит! ' if crit else ''}Ты нанёс {dmg} урона {opp}!\n"
    game["cd"] = SKILL_CD if action == "навык" else max(0, cd - 1)

    if game["bot_hp"] <= 0:
        await fight_win(update, context, user_id, data, game, log)
        return
    boss = bool(game.get("boss"))
    game["turn"] = game.get("turn", 0) + 1
    if boss and not game.get("rage") and game["bot_hp"] * 2 < game["bot_max"]:
        game["rage"] = True
        game["bot_attack"] = int(game["bot_attack"] * 1.25)
        log += f"🔥 {opp} впадает в ярость!\n"
    d_in = random.randint(max(1, game["bot_attack"] - 5), game["bot_attack"] + 5)
    if boss and game["turn"] % 4 == 0:
        d_in = int(d_in * 1.8)
        log += f"💥 {opp} бьёт мощным ударом!\n"
    d_in = max(1, d_in - dfn)
    d_in = max(1, int(d_in * (1 - armor_pct(data))))   # броня гасит часть каждого удара
    if cls == "warrior":
        d_in = max(1, int(d_in * 0.85))
    if defending:
        d_in = max(1, int(d_in * 0.4))
    game["player_hp"] -= d_in
    data["hp"] = max(0, game["player_hp"])
    log += f"🤖 {opp} нанёс {d_in} урона.\n"
    if boss and game["turn"] % 4 == 3:
        log += f"⚠️ {opp} готовит мощный удар: прикройся защитой!\n"
    update_user_data(user_id, data)
    if game["player_hp"] <= 0:
        del active_games[user_id]
        if game.get("mode") == "tower":
            await reply_pic(update, "lose", f"{log}💀 Башня победила на этаже {game['floor']}. Рекорд: {data.get('tower_best', 0)}. /menu.")
        else:
            await reply_pic(update, "lose", f"{log}💀 Поражение. /menu.")
        return
    head = f"🗼 Этаж {game['floor']} · " if game.get("mode") == "tower" else ""
    cdtxt = f" · навык через {game['cd']} х." if game["cd"] else ""
    await reply(update, f"{log}{head}❤️ Ты: {game['player_hp']}/{data['max_hp']} · враг: {game['bot_hp']}\n"
                        f"⚡ Атак сегодня: {data['att_used']}/{attack_limit(data)}{cdtxt}\nВыбирай действие.")

async def fight_win(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict, game: dict, log: str):
    amulet = equip_bonus(data)[2]
    loot = None
    if game.get("mode") == "camp":
        await camp_win(update, context, user_id, data, game, log)
        return
    if game.get("mode") == "tower":
        floor = game["floor"]
        mult = 3 if floor % 10 == 0 else 1
        xp_gain = (10 + floor * 2) * mult
        coin_gain = int((5 + floor * 2) * mult * (1 + amulet / 100))
        data["coins"] += coin_gain
        shards = (1 + floor // 5) * mult
        data["shards"] = data.get("shards", 0) + shards
        levels = add_xp(data, xp_gain)
        data["tower_best"] = max(data.get("tower_best", 0), floor)
        data["hp"] = data["max_hp"] if levels else min(data["max_hp"], game["player_hp"] + data["max_hp"] // 5)
        loot = loot_reward(data, boost=3 if mult == 3 else 0)
        notes = quest_event(data, "tower") + (quest_event(data, "loot") if loot else "")
        clan_points(data, 1)
        notes += check_ach(data)
        update_user_data(user_id, data)
        head = f"{log}🗼 Этаж {floor} пройден! +{xp_gain} XP, +{coin_gain} €, +{shards} 🔩\n{xp_status(data, levels)}{notes}"
        if attacks_used(data) >= attack_limit(data):
            active_games.pop(user_id, None)
            text = head + f"\n\n⚡ Лимит атак на сегодня исчерпан: забег завершён на этаже {floor}. Рекорд: {data['tower_best']}. /menu."
            pic = "tower"
        else:
            nxt = tower_game(data, floor + 1)
            active_games[user_id] = nxt
            text = head + f"\n\n🗼 Этаж {floor + 1}: {nxt['opponent']} (HP {nxt['bot_hp']})\nВыбирай действие."
            pic = "tower_boss" if (floor + 1) % 10 == 0 else "tower"
    else:
        boss = bool(game.get("boss"))
        tier = game.get("tier", 0)
        mult = (1.0, 1.6, 2.5)[tier]
        xp_gain, coin_gain = (60, 30) if boss else (int(40 * mult), int(20 * mult))
        coin_gain = int(coin_gain * (1 + amulet / 100))
        shards = random.randint(8, 12) if boss else random.randint(2, 4) + tier * 3
        power = 5 if boss else (2, 3, 5)[tier]
        data["attack"] += power
        data["hp"] = data["max_hp"]
        data["coins"] += coin_gain
        data["shards"] = data.get("shards", 0) + shards
        data["wins"] = data.get("wins", 0) + 1
        levels = add_xp(data, xp_gain)
        loot = loot_reward(data, boost=2 if boss else tier)
        notes = quest_event(data, "win") + (quest_event(data, "loot") if loot else "")
        clan_points(data, 1)
        notes += check_ach(data)
        del active_games[user_id]
        update_user_data(user_id, data)
        text = (f"{log}🎉 Победа! +{xp_gain} XP, +{coin_gain} €, +{shards} 🔩 осколков и +{power} к атаке. HP восстановлено.\n"
                f"{xp_status(data, levels)}{notes}")
        pic = "win"
    await reply_pic(update, pic, text)
    if loot:
        await reply_pic(update, loot[0], loot[1])

# ---------------- экраны ----------------
SCREEN_WORDS = {"босс мира": "boss", "pvp": "pvp", "рейтинг": "rating", "инвентарь": "inv", "класс": "class",
                "задания": "quests", "достижения": "ach", "клан": "clan", "красная точка": "redzone", "красная зона": "redzone", "друзья": "ref"}

def class_text(data: dict) -> str:
    cur = CLASSES.get(data.get("class", ""))
    lines = ["🧙 Выбор класса", f"Сейчас: {cur[0] if cur else 'не выбран'}", ""]
    lines += [f"{n} — {desc}" for n, desc in CLASSES.values()]
    lines.append(f"\nПервый выбор бесплатный, смена стоит {CLASS_CHANGE_COST} €. Навык в бою перезаряжается {SKILL_CD} хода.")
    return "\n".join(lines)

def screen_content(kind: str, user_id: int, data: dict):
    if kind in SCREEN_RENDER:
        return SCREEN_RENDER[kind](user_id, data)
    if kind == "redzone":
        return "redzone", (f"🔴 Красная точка\n\n⚔️ Дуэль с Боссом\n👹 Бой с существом\n🗼 Башня\n⚔️ Арена (PvP)\n"
                          f"👥 Угадай число с другом\n🐉 Босс мира\n\n⚡ Атак сегодня: {attacks_used(data)}/{attack_limit(data)}\n"
                          "Выбери режим кнопками.")
    if kind == "ref":
        return "referral", ref_text(user_id)
    if kind == "boss":
        return "worldboss", boss_text(user_id)
    if kind == "pvp":
        used = data.get("pvp_used", 0) if data.get("pvp_day") == time.strftime("%Y-%m-%d") else 0
        return "pvp", (f"⚔️ Арена\nРейтинг: {data.get('rating', 1000)} · побед: {data.get('pvp_wins', 0)}\n"
                       f"Боёв сегодня: {used}/{PVP_DAILY}\n\nСоперник подбирается по рейтингу, бой идёт автоматически "
                       "по вашим характеристикам, классам и экипировке. За победу монеты и XP.")
    if kind == "rating":
        return "rating", rating_text(user_id)
    if kind == "inv":
        return "inventory", inv_text(data)
    if kind == "class":
        return "class", class_text(data)
    if kind == "quests":
        return "quests", quests_text(data)
    if kind == "ach":
        return "achievements", ach_text(data)
    return "clan", clan_text(data)

async def open_screen(update: Update, kind: str, user_id: int, data: dict):
    st = {"game": "screen", "kind": kind, "page": 0}
    cur = active_games.get(f"scr_{user_id}")
    if cur and cur.get("kind") in ("redzone", "farm", "hero", "inv") and kind != cur.get("kind"):
        st["parent"] = cur["kind"]   # «Назад» вернёт в предыдущий раздел
    active_games[f"scr_{user_id}"] = st
    pic, text = screen_content(kind, user_id, data)
    await reply_pic(update, pic, text)

async def screens_dispatch(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict, text: str) -> bool:
    orig = update.message.text.strip()
    fighting = user_id in active_games and active_games[user_id].get("game") == "duel"
    scr = active_games.get(f"scr_{user_id}", {}).get("kind")
    if await screens2(update, context, user_id, data, text, scr, orig, fighting):
        return True
    if text == "башня":
        await start_tower(update, user_id, data)
        return True
    if text in SCREEN_WORDS:
        if fighting:
            await reply(update, "⚠️ Сначала закончи бой.")
        elif SCREEN_WORDS[text] == "rating" and scr == "pvp":
            await reply(update, rating_text(user_id))
        else:
            await open_screen(update, SCREEN_WORDS[text], user_id, data)
        return True
    if text.startswith("клан "):
        await clan_command(update, context, user_id, data, orig if BUTTON_ALIASES.get(_norm(orig)) is None else text)
        return True
    if scr == "boss" and text in ("ударить босса", "обновить"):
        if text == "обновить":
            await send_notes(context.bot, ensure_world())
            await reply(update, boss_text(user_id))
        else:
            await boss_hit(update, context, user_id, data)
        return True
    if scr == "pvp" and text == "найти соперника":
        await pvp_fight(update, context, user_id, data)
        return True
    if scr == "inv":
        m = re.fullmatch(r"(надеть|продать) (\d+)", text)
        if text == "надеть лучшее":
            n = equip_best(data)
            update_user_data(user_id, data)
            skipped = sum(1 for it in data.get("inv", []) if not gear_ok(it, data))
            note = f"🚫 Снаряжение другого класса пропущено: {skipped}\n" if skipped else ""
            await reply_pic(update, "inventory", (f"✅ Улучшено слотов: {n}\n" if n else "ℹ️ Лучше ничего нет.\n") + note + "\n" + inv_text(data))
            return True
        if text == "разобрать хлам":
            n, total = dismantle_junk(data)
            update_user_data(user_id, data)
            await reply_pic(update, "inventory", f"♻️ Разобрано предметов: {n}, получено {total} осколков (эпические и легендарные остались)\n\n{inv_text(data)}")
            return True
        if text == "продать хлам":
            n, total = sell_junk(data)
            update_user_data(user_id, data)
            await reply_pic(update, "inventory", f"🗑 Продано предметов: {n}, получено {total} € (эпические и легендарные остаются)\n\n{inv_text(data)}")
            return True
        if m:
            idx = int(m.group(2)) - 1
            inv = data.get("inv", [])
            if not 0 <= idx < len(inv):
                await reply(update, "❌ Нет предмета с таким номером.")
                return True
            it = inv[idx]
            if m.group(1) == "продать":
                data["coins"] += sell_price(it, data)
                inv.pop(idx)
                msg = f"🗑 Продано: {item_line(it)}"
            elif not gear_ok(it, data):
                await reply(update, gear_mismatch_text(it, data))
                return True
            else:
                cur = data.setdefault("eq", {}).get(it["s"])
                inv.pop(idx)
                if cur:
                    inv.append(cur)
                data["eq"][it["s"]] = it
                msg = f"✅ Надето: {item_line(it)}"
            update_user_data(user_id, data)
            await reply_pic(update, "inventory", f"{msg}\n\n{inv_text(data)}")
            return True
    if scr == "class" and text in ("воин", "маг", "лучник"):
        key = {"воин": "warrior", "маг": "mage", "лучник": "archer"}[text]
        cur = data.get("class", "")
        if cur == key:
            await reply(update, "ℹ️ Этот класс уже выбран.")
        elif cur and data["coins"] < CLASS_CHANGE_COST:
            await reply(update, f"❌ Смена класса стоит {CLASS_CHANGE_COST} €, у тебя {data['coins']} €.")
        else:
            if cur:
                data["coins"] -= CLASS_CHANGE_COST
            data["class"] = key
            moved = unequip_mismatched(data)
            put_on = equip_best(data)
            update_user_data(user_id, data)
            extra = (f"\n🔁 Снаряжение другого класса снято в рюкзак: {moved}" if moved else "") + (f"\n✅ Надето подходящего снаряжения: {put_on}" if put_on else "")
            await reply_pic(update, "class", f"✅ Выбран класс {CLASSES[key][0]}: {CLASSES[key][1]}.\nНавык и особенности работают в боях и на арене.{extra}")
        return True
    if scr == "clan" and text == "топ кланов":
        await reply_pic(update, "clan_top", clan_top_text())
        return True
    if scr == "clan" and text == "покинуть клан":
        await clan_leave(update, user_id, data)
        return True
    return False

# =====================================================================
#   ОБНОВЛЕНИЕ 12: рефералы, подменю «Красная точка», баланс
# =====================================================================
BOT_USERNAME = os.getenv("BOT_USERNAME", "mrinigame_bot")
REF_WELCOME = 50       # бонус новичку, пришедшему по ссылке
REF_LEVEL = 3          # какого уровня должен достичь друг, чтобы пригласивший получил награду

def in_duo_room(uid: int) -> bool:
    return any(g.get("type") == "guess_duo" and uid in (g.get("creator"), g.get("partner")) for g in active_games.values())

def ref_text(uid: int) -> str:
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    kids = [d for d in user_data.values() if d.get("ref_by") == uid]
    done = sum(1 for k in kids if k.get("ref_paid"))
    me = user_data.get(uid, {})
    lines = ["🎁 Приглашай друзей", f"Твоя ссылка:\n{link}", "",
             f"Пришло по ссылке: {len(kids)} · дошли до {REF_LEVEL} уровня: {done}", "", "Награды:",
             f"• друг получает {REF_WELCOME} € при входе",
             f"• ты получаешь 100 € и 50 XP, когда друг достигнет {REF_LEVEL} уровня",
             "• 3 друга: ещё +150 € · 10 друзей: эпический предмет · 25 друзей: легендарный предмет и титул «Лидер сообщества»"]
    if me.get("ref_by"):
        lines.append(f"\nТебя пригласил(а): {pname(me['ref_by'])}")
    return "\n".join(lines)

async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает /start ref_<id> у новичка (запись о нём только что создана)."""
    args = context.args or []
    uid = update.effective_user.id
    if not args or not args[0].startswith("ref_"):
        return
    rec = user_data.get(uid)
    if rec is None or "ref_by" in rec or time.time() - rec.get("first_seen", 0) > 600 or not rec.get("first_seen"):
        return
    try:
        rid = int(args[0][4:])
    except ValueError:
        return
    ref = user_data.get(rid)
    if rid == uid or ref is None or ref.get("banned") or ref.get("ref_by") == uid:
        return
    rec["ref_by"] = rid
    rec["ref_paid"] = False
    rec["coins"] += REF_WELCOME
    ref["refs"] = ref.get("refs", 0) + 1
    touch()
    await reply(update, f"🎁 Тебя пригласил(а) {pname(rid)}! Приветственный бонус: +{REF_WELCOME} €")
    try:
        await send_msg(context.bot, chat_id=rid, text=f"👋 По твоей ссылке пришёл {pname(uid)}. Когда он достигнет {REF_LEVEL} уровня, ты получишь награду!")
    except Exception:
        pass

def pay_referral(uid: int, rec: dict) -> list:
    """Награда пригласившему, когда друг дорос до нужного уровня."""
    rid = rec.get("ref_by")
    rec["ref_paid"] = True
    touch()
    ref = user_data.get(rid)
    if ref is None or ref.get("banned") or rec.get("banned"):
        return []
    give(rid, 100, 50)
    ref["refs_done"] = ref.get("refs_done", 0) + 1
    n = ref["refs_done"]
    text = f"🎁 {pname(uid)} достиг {REF_LEVEL} уровня! Награда за друга: +100 € и +50 XP."
    if n == 3:
        give(rid, 150)
        text += "\n🏆 3 друга: бонус +150 €!"
    if n in (10, 25):
        it = roll_loot(ref, boost=3, force=True, min_r=2 if n == 10 else 3)
        text += f"\n🏆 {n} друзей: подарок!\n{item_line(it)} → {add_item(ref, it)}"
    if n == 25:
        ref.setdefault("titles", []).append("Лидер сообщества")
        ref["title"] = "Лидер сообщества"
    return [(rid, text)]

async def ref_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id
    data = get_user_data_safe(uid)
    if not is_private(update):
        await reply(update, ref_text(uid))
    elif uid in active_games and active_games[uid].get("game") == "duel":
        await reply(update, "⚠️ Сначала закончи бой.")
    else:
        await open_screen(update, "ref", uid, data)

async def balance_show(update: Update, data: dict):
    bonus = equip_bonus(data)[2]
    text = f"💰 Твой баланс: {data['coins']} €"
    if bonus:
        text += f"\nАмулет даёт +{bonus}% монет с побед."
    text += "\n\nМонеты можно потратить в 🛒 магазине."
    await reply_pic(update, "balance", text)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_user:
        await balance_show(update, get_user_data_safe(update.effective_user.id))

async def scr_back(update: Update, user_id: int, pic_kind: str):
    """Шаг назад из раздела: во вложенный раздел (Красная точка) или в главное меню."""
    st = active_games.get(f"scr_{user_id}")
    if st:
        st.pop("confirm", None)
    parent = st.get("parent") if st else None
    if parent:
        st["kind"] = parent
        st.pop("parent", None)
        pic, text = screen_content(parent, user_id, get_user_data_safe(user_id))
        await reply_pic(update, pic, text)
    else:
        active_games.pop(f"scr_{user_id}", None)
        await reply_pic(update, pic_kind, "✅ Вы вышли в меню. /start для меню.")

# =====================================================================
#   ОБНОВЛЕНИЕ 14: кампания, ферма, переводы €, выдача €, рейтинги, лимит атак
# =====================================================================
_LOC_DATA = [
    ("forest", "🌲 Тёмный лес", 1, [("Гоблин", "goblin"), ("Волк", "wolf"), ("Лесной разбойник", "goblin")], "Вожак волков",
     "В лесу завелась стая, жители боятся выходить из домов.", "Вожак повержен, лес снова безопасен. Впереди пещера эха."),
    ("cave", "🕳 Пещера эха", 6, [("Скелет", "skeleton"), ("Пещерный тролль", "ogre"), ("Летучая тварь", "wolf")], "Король пещер",
     "В глубине пещеры слышен гул: там кто-то охраняет сокровища.", "Король пещер пал. На горизонте виден проклятый замок."),
    ("castle", "🏰 Проклятый замок", 12, [("Призрак", "skeleton"), ("Рыцарь тьмы", "ogre"), ("Вампир", "goblin")], "Лорд замка",
     "Над замком вечная ночь, в окнах горит холодный свет.", "Проклятие снято, но туман с болот уже ползёт к замку."),
    ("swamp", "🌫 Туманные болота", 20, [("Болотная ведьма", "goblin"), ("Трясинник", "ogre"), ("Гигантская пиявка", "wolf")], "Хозяйка топей",
     "В тумане мелькают огни, путники пропадают без вести.", "Хозяйка топей побеждена, туман рассеивается. Дальше пески пустыни."),
    ("desert", "🏜 Пустыня теней", 30, [("Песчаный скорпион", "wolf"), ("Мумия", "skeleton"), ("Дух бури", "goblin")], "Фараон-призрак",
     "Под песками спит древняя гробница, а по ночам пески оживают.", "Фараон развеян ветром. Вдали сверкают ледяные пики."),
    ("ice", "❄️ Ледяные пики", 42, [("Ледяной волк", "wolf"), ("Йети", "ogre"), ("Морозный страж", "skeleton")], "Ледяной титан",
     "Метель не стихает, а в расщелинах слышны шаги великана.", "Титан рассыпался льдом. На юге дымится огненный вулкан."),
    ("volcano", "🌋 Огненный вулкан", 56, [("Огненный элементаль", "goblin"), ("Лавовый голем", "ogre"), ("Пеплохвост", "wolf")], "Дракон пепла",
     "Земля дрожит, из жерла вылетают искры и раскалённые камни.", "Дракон пепла падает в лаву. Следующая цель — затонувший город."),
    ("sunken", "🌊 Затонувший город", 72, [("Утопленник", "skeleton"), ("Кракен-детёныш", "ogre"), ("Глубинный страж", "wolf")], "Владыка глубин",
     "Под водой светятся башни древнего города, и кто-то зовёт на дно.", "Владыка глубин усмирён. Над облаками виден свет цитадели."),
    ("sky", "☁️ Небесная цитадель", 90, [("Грозовой орёл", "wolf"), ("Облачный страж", "ogre"), ("Громовой дух", "goblin")], "Архангел бури",
     "Цитадель парит над облаками, а в небе грохочут молнии.", "Буря стихла. Внизу, в тёмном лесу, зашевелились пауки."),
    ("spider", "🕸 Лес пауков", 110, [("Паук-ткач", "goblin"), ("Ядовитая королева", "ogre"), ("Теневой охотник", "wolf")], "Матриарх тьмы",
     "Паутина оплела деревья до самых верхушек, воздух густой от яда.", "Матриарх убита, но реальность вокруг дрожит и расползается."),
    ("chaos", "👁 Измерение хаоса", 135, [("Искажённый", "goblin"), ("Пожиратель разума", "ogre"), ("Страж хаоса", "skeleton")], "Повелитель хаоса",
     "Здесь нет верха и низа, а стены шепчут твоё имя.", "Хаос обуздан. Остался последний враг на троне бездны."),
    ("throne", "💀 Трон бездны", 165, [("Падший рыцарь", "skeleton"), ("Демон-палач", "ogre"), ("Тёмный маг", "goblin")], "Император бездны",
     "Последний рубеж: император ждёт тех, кто дошёл так далеко.", "Император бездны повержен! Но за его троном открылась настоящая Бездна."),
]
# Параметры каждой локации считаются от требуемого уровня, поэтому кампания растёт вместе с героем
LOCS = [{"key": k, "name": n, "lvl": lv, "mon": mon, "boss": (bn, "boss"), "intro": intro, "end": end,
         "hp": 70 + lv * 14, "atk": 10 + int(lv * 1.4), "mult": round(1.35 ** i, 2), "need": 5 + i}
        for i, (k, n, lv, mon, bn, intro, end) in enumerate(_LOC_DATA)]
ABYSS = {"key": "abyss", "name": "🌌 Бездна", "lvl": 180, "endless": True, "need": 0,
         "mon": [("Тень бездны", "skeleton"), ("Пожиратель миров", "ogre"), ("Безликий", "goblin"), ("Страж пустоты", "wolf")],
         "boss": ("Хранитель бездны", "boss"), "hp": 70 + 180 * 14, "atk": 10 + int(180 * 1.4), "mult": round(1.35 ** 11, 2),
         "intro": "Бесконечная тьма: чем глубже, тем сильнее враги и богаче награда. Каждые 25 побед выходит Хранитель.", "end": ""}
ALL_LOCS = LOCS + [ABYSS]
ABYSS_BOSS_EVERY = 25
GPUS = [("GTX 1050", 300, 3), ("GTX 1660", 900, 9), ("RTX 3060", 2500, 24), ("RTX 4070", 7000, 60), ("RTX 4090", 20000, 130),
        ("RTX 5090", 60000, 360), ("Серверная стойка", 180000, 1000), ("ASIC S19", 550000, 3000),
        ("ASIC S21", 1700000, 9000), ("Квантовый майнер", 5000000, 26000)]
FARM_BASE_CAP = 12     # сколько часов дохода влезает в накопитель на старте
FARM_MAX_SLOTS = 500
FARM_MAX_LVL = 500
TRANSFER_DAILY = 2000  # сколько € можно передать другим игрокам за сутки
TRANSFER_MIN = 10
TRANSFER_MIN_LEVEL = 3
GIVE_MAX = 10 ** 18

B_CPREV, B_CNEXT, B_CFIGHT = "◀️ Локация", "Локация ▶️", "⚔️ В бой"
B_FARM_COLLECT, B_GPUS, B_SLOT, B_FARMUP = "💸 Собрать доход", "🖥 Видеокарты", "➕ Слот", "⚙️ Улучшить ферму"
B_Q1, B_Q10, B_Q100, B_QMAX = "×1", "×10", "×100", "МАКС"
B_GPU = [f"🖥 {g[0]}" for g in GPUS]
CAMP_KB = ReplyKeyboardMarkup([[B_CPREV, B_CNEXT], [B_CFIGHT], [B_BACK]], resize_keyboard=True)
FARM_KB = ReplyKeyboardMarkup([[B_FARM_COLLECT, B_GPUS], [B_SLOT, B_FARMUP], [B_Q1, B_Q10, B_Q100, B_QMAX], [B_BACK]], resize_keyboard=True)
GPU_KB = ReplyKeyboardMarkup([B_GPU[i:i + 2] for i in range(0, len(B_GPU), 2)] + [[B_Q1, B_Q10, B_Q100, B_QMAX], [B_SLOT, B_BACK]], resize_keyboard=True)
SCREEN_KB.update({"camp": CAMP_KB, "farm": FARM_KB, "gpu": GPU_KB})
SCREEN_WORDS.update({"кампания": "camp", "ферма": "farm"})
BUTTON_ALIASES.update({_norm(k): v for k, v in {
    B_CAMP: "кампания", B_FARM: "ферма", B_CPREV: "локация назад", B_CNEXT: "локация вперёд", B_CFIGHT: "в бой",
    B_FARM_COLLECT: "собрать доход", B_GPUS: "видеокарты", B_SLOT: "купить слот", B_FARMUP: "улучшить ферму",
    B_Q1: "количество 1", B_Q10: "количество 10", B_Q100: "количество 100", B_QMAX: "количество макс",
    B_BUY_BOOST: "купить разгон",
    **{B_GPU[i]: f"карта {i + 1}" for i in range(len(GPUS))},
}.items()})


def today_s() -> str:
    return time.strftime("%Y-%m-%d")

def fmt_left(sec) -> str:
    sec = max(0, int(sec))
    h, m = sec // 3600, sec % 3600 // 60
    return f"{h} ч {m} мин" if h else f"{m} мин"

def attack_limit(data: dict) -> int:
    """Дневной лимит атак: базовый плюс купленные энергетики за сегодня."""
    extra = data.get("att_extra", 0) if data.get("att_extra_day") == today_s() else 0
    return DAILY_ATTACKS + extra

ACH["camp_1"] = ("Охотник", "Пройди Тёмный лес", lambda d: "forest" in d.get("camp", {}).get("done", []), 100)
ACH["camp_all"] = ("Герой кампании", "Пройди все локации кампании", lambda d: len(d.get("camp", {}).get("done", [])) >= len(LOCS), 400)
ACH["farm_1"] = ("Майнер", "Купи первую видеокарту", lambda d: sum((d.get("farm") or {}).get("cards", [])) >= 1, 80)


# ---------------- кампания ----------------
def camp_state(data: dict) -> dict:
    c = data.setdefault("camp", {})
    c.setdefault("kills", {})
    c.setdefault("done", [])
    return c

def camp_unlocked(data: dict, i: int) -> bool:
    return data["level"] >= ALL_LOCS[i]["lvl"] and (i == 0 or ALL_LOCS[i - 1]["key"] in camp_state(data)["done"])

def camp_score(d: dict) -> int:
    c = d.get("camp") or {}
    return len(c.get("done", [])) * 100000 + sum(c.get("kills", {}).values())

def camp_default(data: dict) -> int:
    """Текущий рубеж кампании: первая открытая локация, которую ещё не прошли (или Бездна)."""
    c = camp_state(data)
    last = 0
    for i, loc in enumerate(ALL_LOCS):
        if camp_unlocked(data, i):
            last = i
            if loc.get("endless") or loc["key"] not in c["done"]:
                return i
    return last

def camp_sel(uid, data: dict) -> int:
    st = active_games.get(f"scr_{uid}")
    if st is None:
        return camp_default(data)
    if "loc" not in st:
        st["loc"] = camp_default(data)
    return st["loc"]

def camp_text(data: dict, uid=None) -> str:
    c = camp_state(data)
    i = camp_sel(uid, data) if uid is not None else camp_default(data)
    loc, key = ALL_LOCS[i], ALL_LOCS[i]["key"]
    done_n = sum(1 for l in LOCS if l["key"] in c["done"])
    lines = [f"🗺 Кампания · локация {i + 1}/{len(ALL_LOCS)} · пройдено {done_n}/{len(LOCS)}", "", loc["name"], loc["intro"], ""]
    if not camp_unlocked(data, i):
        prev = f" и победа над «{ALL_LOCS[i - 1]['boss'][0]}»" if i else ""
        lines.append(f"🔒 Закрыто: нужен {loc['lvl']} уровень{prev}.")
    elif loc.get("endless"):
        depth = c["kills"].get(key, 0)
        lines.append(f"🔓 Глубина: {depth} побед · следующий Хранитель через {ABYSS_BOSS_EVERY - depth % ABYSS_BOSS_EVERY}")
        lines.append("Враги и награды растут с глубиной, конца нет.")
    elif key in c["done"]:
        lines.append(f"✅ Пройдена · монстров побеждено: {c['kills'].get(key, 0)}. Можно фармить дальше.")
    else:
        k = min(c["kills"].get(key, 0), loc["need"])
        lines.append(f"🔓 Монстры: {k}/{loc['need']}" + (" · БОСС ждёт!" if k >= loc["need"] else ""))
    lines.append(f"\n⚡ Атак сегодня: {attacks_used(data)}/{attack_limit(data)}")
    lines.append("◀️ ▶️ листать локации · ⚔️ В бой")
    return "\n".join(lines)

async def camp_start(update: Update, user_id: int, data: dict, i: int):
    loc = ALL_LOCS[i]
    c = camp_state(data)
    if not camp_unlocked(data, i):
        prev = f" и победа над боссом «{ALL_LOCS[i - 1]['boss'][0]}»" if i else ""
        await reply(update, f"🔒 Локация закрыта: нужен {loc['lvl']} уровень{prev}.")
        return
    if data["hp"] <= 0:
        await reply(update, "🩸 У тебя 0 HP. Подожди лечения (+15 HP каждую минуту).")
        return
    if attacks_used(data) >= attack_limit(data):
        await reply(update, f"⚡ Лимит атак на сегодня исчерпан ({attacks_used(data)}/{attack_limit(data)}). Новые атаки появятся завтра.")
        return
    key = loc["key"]
    depth = c["kills"].get(key, 0)
    if loc.get("endless"):
        boss = (depth + 1) % ABYSS_BOSS_EVERY == 0
        s_hp, s_atk = 1 + depth * 0.03, 1 + depth * 0.02
    else:
        boss = depth >= loc["need"] and key not in c["done"]
        s_hp = s_atk = 1.0
    if boss:
        name, pic = loc["boss"]
        hp, atk = int(loc["hp"] * 3 * s_hp), int(loc["atk"] * 1.4 * s_atk)
    else:
        name, pic = random.choice(loc["mon"])
        hp, atk = int(loc["hp"] * random.uniform(0.85, 1.15) * s_hp), int(loc["atk"] * s_atk)
    active_games[user_id] = {"game": "duel", "mode": "camp", "loc": i, "boss": boss, "depth": depth, "player_hp": data["hp"],
                             "bot_hp": hp, "bot_attack": atk, "round": 1, "opponent": name, "cd": 0}
    where = f"глубина {depth + 1}" if loc.get("endless") else f"монстры {min(depth, loc['need'])}/{loc['need']}"
    intro = f"\n{loc['intro']}" if depth == 0 and not boss and not loc.get("endless") else ""
    await reply_pic(update, pic, f"{loc['name']}{intro}\n{'☠️ БОСС' if boss else 'Противник'}: {name} (HP {hp}, урон ~{atk})\n{where}\nВыбирай действие.")

async def camp_win(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict, game: dict, log: str):
    i = game["loc"]
    loc, key, boss = ALL_LOCS[i], ALL_LOCS[i]["key"], game.get("boss")
    endless = loc.get("endless")
    mult = loc["mult"] * ((1 + game.get("depth", 0) * 0.02) if endless else 1) * (4 if boss else 1)
    xp_gain = int(30 * mult)
    coin_gain = int(15 * mult * (1 + equip_bonus(data)[2] / 100))
    data["coins"] += coin_gain
    shards = random.randint(15, 25) + 2 * i if boss else random.randint(2, 5) + i // 2
    data["shards"] = data.get("shards", 0) + shards
    data["wins"] = data.get("wins", 0) + 1
    data["hp"] = min(data["max_hp"], game["player_hp"] + data["max_hp"] // 4)
    levels = add_xp(data, xp_gain)
    if levels:
        data["hp"] = data["max_hp"]
    c = camp_state(data)
    story = ""
    min_r = min(3, 1 + i // 4)
    if endless:
        c["kills"][key] = c["kills"].get(key, 0) + 1
        story = f"\n\n🌌 Глубина бездны: {c['kills'][key]}" + (f"\n☠️ Хранитель побеждён! Ждёт следующий через {ABYSS_BOSS_EVERY} побед." if boss else "")
        loot = loot_reward(data, boost=6) if boss else loot_reward(data, boost=min(3, i // 4))
    elif boss:
        if key not in c["done"]:
            c["done"].append(key)
        story = f"\n\n🏆 {loc['end']}"
        if i + 1 < len(ALL_LOCS):
            nxt = ALL_LOCS[i + 1]
            story += f"\n🔓 Следующая локация: {nxt['name']}" + (f" (откроется на {nxt['lvl']} уровне)" if data["level"] < nxt["lvl"] else "")
        loot = loot_reward(data, boost=5)
    else:
        c["kills"][key] = c["kills"].get(key, 0) + 1
        loot = loot_reward(data, boost=min(3, i // 4))
        if c["kills"][key] == loc["need"] and key not in c["done"]:
            story = "\n\n☠️ Босс локации вышел из логова! Нажми «⚔️ В бой», чтобы сразиться с ним."
    notes = quest_event(data, "win") + (quest_event(data, "loot") if loot else "")
    clan_points(data, 2 if boss else 1)
    notes += check_ach(data)
    del active_games[user_id]
    update_user_data(user_id, data)
    await reply_pic(update, "win", f"{log}🎉 Победа! +{xp_gain} XP, +{coin_gain} €, +{shards} 🔩.\n{xp_status(data, levels)}{notes}{story}")
    if loot:
        await reply_pic(update, loot[0], loot[1])

async def act_camp(update, context, user_id, data, text, orig) -> bool:
    st = active_games.get(f"scr_{user_id}")
    if st is None:
        return False
    if text in ("локация назад", "локация вперёд", "локация вперед"):
        st["loc"] = max(0, min(len(ALL_LOCS) - 1, camp_sel(user_id, data) + (-1 if text.endswith("назад") else 1)))
        await reply_pic(update, "redzone", camp_text(data, user_id))
        return True
    m = re.fullmatch(r"локация (\d+)", text)
    if m and 1 <= int(m.group(1)) <= len(ALL_LOCS):
        st["loc"] = int(m.group(1)) - 1
        await reply_pic(update, "redzone", camp_text(data, user_id))
        return True
    if text == "в бой":
        await camp_start(update, user_id, data, camp_sel(user_id, data))
        return True
    return False


# ---------------- ферма ----------------
QTY_WORDS = {"1": 1, "10": 10, "100": 100, "макс": 0}

def farm_mult(lvl: int) -> float:
    return 1 + 0.02 * lvl            # +2% дохода за каждый уровень фермы (до 500 уровня: ×11)

def farm_hours(lvl: int) -> int:
    return FARM_BASE_CAP + lvl // 5  # накопитель растёт вместе с уровнем

def farm_get(d: dict) -> dict:
    f = d.setdefault("farm", {})
    cards = f.setdefault("cards", [0] * len(GPUS))
    if len(cards) < len(GPUS):       # у старых ферм добавились новые видеокарты
        cards.extend([0] * (len(GPUS) - len(cards)))
    f.setdefault("slots", 3)
    f.setdefault("lvl", 0)
    f.setdefault("t", time.time())
    f.setdefault("stock", 0.0)
    return f

def farm_rate(d: dict) -> float:
    f = farm_get(d)
    rate = sum(c * g[2] for c, g in zip(f["cards"], GPUS)) * farm_mult(f["lvl"])
    return rate * (1.5 if d.get("farm_boost", 0) > time.time() else 1)

def farm_cap(d: dict) -> float:
    return farm_rate(d) * farm_hours(farm_get(d)["lvl"])

def farm_tick(d: dict):
    """Начисляет накопленный доход (до лимита накопителя)."""
    f = farm_get(d)
    now = time.time()
    f["stock"] = min(farm_cap(d), f["stock"] + farm_rate(d) * (now - f["t"]) / 3600)
    f["t"] = now

def farm_income(d: dict) -> int:
    f = d.get("farm") or {}
    return int(sum(c * g[2] for c, g in zip(f.get("cards", []), GPUS)) * farm_mult(f.get("lvl", 0)))

def farm_qty(d: dict) -> int:
    return d.get("farm_qty", 1)      # 0 означает «максимум»

def qty_label(d: dict) -> str:
    return "МАКС" if farm_qty(d) == 0 else f"×{farm_qty(d)}"

def afford(coins: int, want: int, limit: int, cost_n) -> int:
    """Сколько штук можно купить: не больше want и limit, и чтобы хватило монет (cost_n(n) — цена n штук)."""
    lo, hi = 0, max(0, min(want, limit))
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if cost_n(mid) <= coins:
            lo = mid
        else:
            hi = mid - 1
    return lo

def farm_text(d: dict) -> str:
    farm_tick(d)
    f = farm_get(d)
    cards = [f"{n}× {g[0]}" for n, g in zip(f["cards"], GPUS) if n]
    lines = ["🌾 Ферма", f"⚙️ Уровень фермы: {f['lvl']}/{FARM_MAX_LVL} · слотов занято: {sum(f['cards'])}/{f['slots']} (максимум {FARM_MAX_SLOTS})",
             f"💶 Доход: {farm_rate(d):.0f} €/ч · накоплено: {int(f['stock'])}/{int(farm_cap(d))} €",
             "🖥 Видеокарты: " + (", ".join(cards) or "пока нет, купи первую!")]
    if d.get("farm_boost", 0) > time.time():
        lines.append(f"🚀 Разгон ещё {fmt_left(d['farm_boost'] - time.time())}")
    lines.append(f"\nДоход копится сам, но не дольше {farm_hours(f['lvl'])} ч подряд. Каждый уровень фермы: +2% дохода и больше накопитель.")
    lines.append(f"Покупка слотов и улучшений: {qty_label(d)} (кнопки ×1, ×10, ×100, МАКС).")
    return "\n".join(lines)

def gpu_text(d: dict) -> str:
    f = farm_get(d)
    lines = [f"🖥 Видеокарты · свободных слотов: {f['slots'] - sum(f['cards'])} · баланс {d['coins']} € · покупка {qty_label(d)}", ""]
    lines += [f"{i}. {g[0]} — {g[1]} €, {g[2]} €/ч (у тебя {f['cards'][i - 1]})" for i, g in enumerate(GPUS, 1)]
    lines.append("\nНажми на видеокарту, чтобы купить. Слоты: кнопка «➕ Слот».")
    return "\n".join(lines)

async def act_farm(update, context, user_id, data, text, orig) -> bool:
    farm_tick(data)
    f = farm_get(data)
    want = 10 ** 9 if farm_qty(data) == 0 else farm_qty(data)
    m = re.fullmatch(r"количество (1|10|100|макс)", text)
    if m:
        data["farm_qty"] = QTY_WORDS[m.group(1)]
        update_user_data(user_id, data)
        on_gpu = (active_games.get(f"scr_{user_id}") or {}).get("kind") == "gpu"
        await reply_pic(update, "balance", gpu_text(data) if on_gpu else farm_text(data))
        return True
    if text == "собрать доход":
        amount = int(f["stock"])
        if amount < 1:
            await reply(update, "ℹ️ Пока нечего собирать, доход ещё копится.")
            return True
        data["coins"] += amount
        f["stock"] -= amount
        update_user_data(user_id, data)
        await reply_pic(update, "balance", f"💸 Собрано: {amount} €\n\n{farm_text(data)}")
        return True
    if text == "видеокарты":
        await open_screen(update, "gpu", user_id, data)
        return True
    if text == "купить слот":
        s0 = f["slots"]
        n = afford(data["coins"], want, FARM_MAX_SLOTS - s0, lambda k: 400 * (k * s0 + k * (k - 1) // 2))
        if s0 >= FARM_MAX_SLOTS:
            await reply(update, f"ℹ️ Больше {FARM_MAX_SLOTS} слотов не бывает.")
        elif n == 0:
            await reply(update, f"❌ Не хватает монет: слот стоит {400 * s0} €, у тебя {data['coins']} €.")
        else:
            cost = 400 * (n * s0 + n * (n - 1) // 2)
            data["coins"] -= cost
            f["slots"] += n
            update_user_data(user_id, data)
            await reply_pic(update, "balance", f"✅ Слотов куплено: {n} за {cost} €.\n\n{farm_text(data)}")
        return True
    if text == "улучшить ферму":
        l0 = f["lvl"]
        n = afford(data["coins"], want, FARM_MAX_LVL - l0, lambda k: 1000 * (k * (l0 + 1) + k * (k - 1) // 2))
        if l0 >= FARM_MAX_LVL:
            await reply(update, "ℹ️ Ферма уже улучшена до максимума.")
        elif n == 0:
            await reply(update, f"❌ Не хватает монет: улучшение стоит {1000 * (l0 + 1)} €, у тебя {data['coins']} €.")
        else:
            cost = 1000 * (n * (l0 + 1) + n * (n - 1) // 2)
            data["coins"] -= cost
            f["lvl"] += n
            update_user_data(user_id, data)
            await reply_pic(update, "balance", f"✅ Уровней фермы: +{n} за {cost} € (теперь {f['lvl']}).\n\n{farm_text(data)}")
        return True
    return False

async def act_gpu(update, context, user_id, data, text, orig) -> bool:
    m = re.fullmatch(r"карта ([0-9]+)", text)
    if not m and (text in ("купить слот", "собрать доход", "улучшить ферму") or text.startswith("количество ")):
        return await act_farm(update, context, user_id, data, text, orig)   # слот, улучшение и количество доступны и тут
    if not m or not 1 <= int(m.group(1)) <= len(GPUS):
        return False
    farm_tick(data)
    f = farm_get(data)
    i = int(m.group(1)) - 1
    name, price, rate = GPUS[i]
    free = f["slots"] - sum(f["cards"])
    want = 10 ** 9 if farm_qty(data) == 0 else farm_qty(data)
    n = afford(data["coins"], want, free, lambda k: price * k)
    if free <= 0:
        await reply(update, "❌ Свободных слотов нет. Купи слоты кнопкой «➕ Слот».")
    elif n == 0:
        await reply(update, f"❌ Не хватает монет: нужно {price} €, у тебя {data['coins']} €.")
    else:
        data["coins"] -= price * n
        f["cards"][i] += n
        notes = check_ach(data)
        update_user_data(user_id, data)
        await reply_pic(update, "balance", f"✅ Куплено {n}× {name} за {price * n} €, +{rate * n} €/ч.{notes}\n\n{gpu_text(data)}")
    return True

async def farm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_user:
        uid = update.effective_user.id
        data = get_user_data_safe(uid)
        if is_private(update) and not (uid in active_games and active_games[uid].get("game") == "duel"):
            await open_screen(update, "farm", uid, data)
        else:
            await reply(update, farm_text(data))

async def camp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_user:
        uid = update.effective_user.id
        data = get_user_data_safe(uid)
        if is_private(update) and not (uid in active_games and active_games[uid].get("game") == "duel"):
            await open_screen(update, "camp", uid, data)
        else:
            await reply(update, camp_text(data))


# ---------------- экраны и переходы ----------------
SCREEN_RENDER = {
    "camp": lambda uid, d: ("redzone", camp_text(d, uid)),
    "farm": lambda uid, d: ("balance", farm_text(d)),
    "gpu": lambda uid, d: ("balance", gpu_text(d)),
}
ACTS = {"camp": act_camp, "farm": act_farm, "gpu": act_gpu}

async def screens2(update, context, user_id, data, text, scr, orig, fighting) -> bool:
    fn = ACTS.get(scr)
    if fn and not fighting:
        return await fn(update, context, user_id, data, text, orig)
    return False


# ---------------- переводы € между игроками ----------------
def transfer_left(d: dict) -> int:
    sent = d.get("tr_sent", 0) if d.get("tr_day") == today_s() else 0
    return max(0, TRANSFER_DAILY - sent)

def resolve_player(query: str):
    q = query.strip().lstrip("@").lower()
    if not q:
        return None
    if q.isdigit():
        return int(q) if int(q) in user_data else None
    exact = [u for u, d in user_data.items() if q in (str(d.get("nick", "")).lower(), str(d.get("username", "")).lower(), str(d.get("name", "")).lower())]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return None
    part = find_players(q)
    return part[0] if len(part) == 1 else None

async def limit_show(update: Update, data: dict):
    await reply(update, f"💸 Лимит передачи € на сегодня: осталось {transfer_left(data)} из {TRANSFER_DAILY}.\n"
                        f"Минимальная сумма: {TRANSFER_MIN} €. Передавать можно с {TRANSFER_MIN_LEVEL} уровня.\n"
                        "Как передать: /pay ник сумма (или «передать ник сумма»). Лимит обновляется каждый день.")

async def pay_apply(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict, who: str, amount_s: str):
    if not amount_s.isdigit() or int(amount_s) <= 0:
        await reply(update, "Пример: /pay Вася 100 (ник или ID и сумма цифрами).")
        return
    amount = int(amount_s)
    target = resolve_player(who)
    if data["level"] < TRANSFER_MIN_LEVEL:
        await reply(update, f"🔒 Передавать € можно с {TRANSFER_MIN_LEVEL} уровня.")
    elif target is None:
        await reply(update, "❌ Игрок не найден (или таких несколько). Укажи точный ник или ID.")
    elif target == user_id:
        await reply(update, "❌ Нельзя передавать самому себе.")
    elif user_data[target].get("banned"):
        await reply(update, "❌ Этому игроку передавать нельзя.")
    elif amount < TRANSFER_MIN:
        await reply(update, f"❌ Минимальная сумма: {TRANSFER_MIN} €.")
    elif amount > transfer_left(data):
        await reply(update, f"❌ Превышен лимит передачи: сегодня осталось {transfer_left(data)} €. Посмотреть: /limit")
    elif amount > data["coins"]:
        await reply(update, f"❌ Не хватает монет: у тебя {data['coins']} €.")
    else:
        data["coins"] -= amount
        data["tr_sent"] = (data.get("tr_sent", 0) if data.get("tr_day") == today_s() else 0) + amount
        data["tr_day"] = today_s()
        tr = data.setdefault("tr_to", {})
        tr[str(target)] = tr.get(str(target), 0) + 1
        update_user_data(user_id, data)
        give(target, amount)
        await reply(update, f"✅ Передано {amount} € игроку {pname(target)}. Остаток лимита на сегодня: {transfer_left(data)} €.")
        try:
            await send_msg(context.bot, chat_id=target, text=f"💸 {pname(user_id)} передал тебе {amount} €!")
        except Exception:
            pass

async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    args = context.args or []
    data = get_user_data_safe(update.effective_user.id)
    if len(args) < 2:
        await reply(update, "Пример: /pay Вася 100 (ник или ID и сумма). Лимит: /limit")
        return
    await pay_apply(update, context, update.effective_user.id, data, " ".join(args[:-1]), args[-1])

async def pay_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict, orig: str):
    parts = orig.split()
    if len(parts) < 3:
        await reply(update, "Пример: передать Вася 100 (ник или ID и сумма). Лимит: «лимит»")
        return
    await pay_apply(update, context, user_id, data, " ".join(parts[1:-1]), parts[-1])

async def limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_user:
        await limit_show(update, get_user_data_safe(update.effective_user.id))

# ---------------- рейтинги игроков (обычный и админский) ----------------
def m_arena(d): return d.get("rating", 1000)
def m_level(d): return d["level"] * 1000000 + d.get("xp", 0)
def m_tower(d): return d.get("tower_best", 0)
def m_camp(d): return camp_score(d)
def m_farm(d): return farm_income(d)
def m_rich(d): return d.get("coins", 0)

LEADER_BOARDS = [
    ("⚔️ Арена", m_arena, lambda v: str(v)),
    ("👤 Уровень", m_level, lambda v: f"ур. {v // 1000000}"),
    ("🗼 Башня", m_tower, lambda v: f"этаж {v}"),
    ("🗺 Кампания", m_camp, lambda v: f"локаций {v // 100000}, побед {v % 100000}"),
    ("🌾 Ферма", m_farm, lambda v: f"{v} €/ч"),
    ("💶 Богатые", m_rich, lambda v: f"{v} €"),
]

def top_rows(fn, n, public=True):
    """Топ игроков. Владелец бота скрыт только в списке «Богатые» (ему можно выдавать €), везде остальные видны."""
    rows = sorted(((fn(d), u) for u, d in user_data.items()
                   if not d.get("banned") and fn(d) >= 1 and not (public and fn is m_rich and u == ADMIN_ID)), reverse=True)
    return rows[:n], rows

def leader_lines(who, n=3, n_first=5, public=True) -> list:
    lines = []
    for idx, (title, fn, fmt) in enumerate(LEADER_BOARDS):
        top, _ = top_rows(fn, n_first if idx == 0 else n, public)
        if top:
            lines.append(title)
            lines += [f"{i}. {who(u)} — {fmt(v)}" for i, (v, u) in enumerate(top, 1)]
            lines.append("")
    return lines

# =====================================================================
#   ОБНОВЛЕНИЕ 15: общий рейтинг всех игроков, хаб «Герой», подтверждения в инвентаре
# =====================================================================
B_UP, B_DOWN, B_BOARDS = "⏪ Выше", "⏩ Ниже", "📊 По разделам"
B_YES, B_NO = "✅ Да, подтверждаю", "❌ Отмена"
HERO_KB = ReplyKeyboardMarkup([[B_INV, B_CLASS], [B_QUESTS, B_ACH], [B_CLAN, B_REF], [B_STATS, B_BACK]], resize_keyboard=True)
RATING_KB = ReplyKeyboardMarkup([[B_UP, B_DOWN], [B_BOARDS, B_BACK]], resize_keyboard=True)
CONFIRM_KB = ReplyKeyboardMarkup([[B_YES, B_NO]], resize_keyboard=True)
SCREEN_KB.update({"hero": HERO_KB, "rating": RATING_KB})
SCREEN_WORDS.update({"герой": "hero"})
BUTTON_ALIASES.update({_norm(k): v for k, v in {
    B_HERO: "герой", B_UP: "рейтинг выше", B_DOWN: "рейтинг ниже", B_BOARDS: "рейтинг разделы", B_YES: "да", B_NO: "нет",
}.items()})


# ---------------- общий рейтинг: в нём ВСЕ игроки бота ----------------
def total_score(d: dict) -> int:
    c = d.get("camp") or {}
    arena = max(0, d.get("rating", 1000) - 1000) if d.get("pvp_games", 0) > 0 else 0
    return (d["level"] * 100 + d.get("xp", 0) // 10 + d.get("wins", 0) * 2 + d.get("tower_best", 0) * 15
            + len(c.get("done", [])) * 250 + sum(c.get("kills", {}).values()) * 5 + arena // 2 + d.get("boss_kills", 0) * 50)

def rating_rows() -> list:
    """Все игроки, кроме забаненных. Новый игрок попадает сюда сразу, как только бот его увидел."""
    return sorted(((total_score(d), d["level"], u) for u, d in user_data.items() if not d.get("banned")), reverse=True)

def rank_text(uid: int) -> str:
    rows = rating_rows()
    rank = next((i for i, (_, _, u) in enumerate(rows, 1) if u == uid), None)
    return f"{rank} из {len(rows)}" if rank else "—"

def rating_text(uid: int, page: int = 0) -> str:
    rows = rating_rows()
    total = len(rows)
    pages = max(1, (total + 9) // 10)
    page = max(0, min(pages - 1, page))
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = [f"🏆 Рейтинг игроков · всего {total} · стр. {page + 1}/{pages}", ""]
    for i, (sc, lv, u) in enumerate(rows[page * 10:(page + 1) * 10], page * 10 + 1):
        lines.append(f"{medals.get(i, '')}{i}. {pname(u)} — {sc} оч. (ур. {lv})" + (" ← ты" if u == uid else ""))
    mine = user_data.get(uid)
    lines += ["", f"Твоё место: {rank_text(uid)}" + (f" · {total_score(mine)} оч." if mine and not mine.get("banned") else ""),
              "В рейтинге все игроки бота. Очки: уровень, победы, башня, кампания, арена, боссы.",
              "⏪ ⏩ листать · 📊 по разделам"]
    return "\n".join(lines)

def admin_rating_all() -> str:
    rows = rating_rows()
    banned = sum(1 for d in user_data.values() if d.get("banned"))
    lines = [f"🏆 В рейтинге {len(rows)} из {len(user_data)} игроков в базе (в бане: {banned})", ""]
    lines += [f"{i}. {label(u)} — {sc} оч., ур. {lv}" for i, (sc, lv, u) in enumerate(rows[:40], 1)]
    if len(rows) > 40:
        lines.append(f"…и ещё {len(rows) - 40}")
    return "\n".join(lines)

def admin_rating_lines() -> list:
    total = sum(d.get("coins", 0) for d in user_data.values())
    refs = sum(d.get("refs", 0) for d in user_data.values())
    banned = sum(1 for d in user_data.values() if d.get("banned"))
    return (["", f"🏆 В рейтинге: {len(rating_rows())} из {len(user_data)} игроков (в бане: {banned})", "", "📈 Рейтинги по разделам:", ""]
            + leader_lines(label, 5, 5, public=False) + [f"💶 Всего € у игроков: {total} · приглашений по ссылкам: {refs}"])

async def act_rating(update, context, user_id, data, text, orig) -> bool:
    st = active_games.get(f"scr_{user_id}")
    if text in ("рейтинг выше", "рейтинг ниже") and st:
        st["page"] = max(0, st.get("page", 0) + (-1 if text.endswith("выше") else 1))
        pages = max(1, (len(rating_rows()) + 9) // 10)
        st["page"] = min(st["page"], pages - 1)
        await reply_pic(update, "rating", rating_text(user_id, st["page"]))
        return True
    if text == "рейтинг разделы":
        await reply(update, "\n".join(["📊 Рейтинги по разделам", ""] + leader_lines(pname)))
        return True
    return False


# ---------------- хаб «Герой» ----------------
def hero_text(uid: int, d: dict) -> str:
    cls = CLASSES.get(d.get("class", ""), ("не выбран",))[0]
    return (f"🎒 Герой: {pname(uid)}\n⭐ Уровень {d['level']} · XP {d['xp']}/{xp_needed(d['level'])} · 🧙 {cls}\n"
            f"💶 {d['coins']} € · 🏆 место {rank_text(uid)}\n\n"
            "🎒 Инвентарь: предметы и экипировка\n🧙 Класс: навыки в бою\n📅 Задания и 🏅 достижения: награды\n"
            "👥 Клан и 🎁 Друзья\n📊 Статистика: все цифры героя\n\n⬅️ Назад: в главное меню")

SCREEN_RENDER.update({
    "hero": lambda uid, d: ("inventory", hero_text(uid, d)),
    "rating": lambda uid, d: ("rating", rating_text(uid, (active_games.get(f"scr_{uid}") or {}).get("page", 0))),
})

async def hero_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_user:
        uid = update.effective_user.id
        data = get_user_data_safe(uid)
        if is_private(update) and not (uid in active_games and active_games[uid].get("game") == "duel"):
            await open_screen(update, "hero", uid, data)
        else:
            await reply(update, hero_text(uid, data))

async def rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_user:
        uid = update.effective_user.id
        data = get_user_data_safe(uid)
        if is_private(update) and not (uid in active_games and active_games[uid].get("game") == "duel"):
            await open_screen(update, "rating", uid, data)
        else:
            await reply(update, rating_text(uid))


# ---------------- подтверждение продажи и выброса предметов ----------------
async def act_inv(update, context, user_id, data, text, orig) -> bool:
    st = active_games.get(f"scr_{user_id}")
    if not st:
        return False
    conf = st.get("confirm")
    if conf:
        if text == "да":
            st.pop("confirm", None)
            st["confirmed"] = True
            return await screens_dispatch(update, context, user_id, data, conf["cmd"])   # выполняем то, что подтвердили
        if text in ("нет", "отмена"):
            st.pop("confirm", None)
            await reply_pic(update, "inventory", "↩️ Отменено, всё осталось на месте.\n\n" + inv_text(data))
            return True
        await reply(update, "Подтверди действие кнопками: «✅ Да, подтверждаю» или «❌ Отмена».")
        return True
    inv = data.get("inv", [])
    if st.pop("confirmed", False):
        m = re.fullmatch(r"выбросить (\d+)", text)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(inv):
                it = inv.pop(idx)
                update_user_data(user_id, data)
                await reply_pic(update, "inventory", f"🗑 Выброшено: {item_line(it)}\n\n{inv_text(data)}")
            else:
                await reply(update, "❌ Нет предмета с таким номером.")
            return True
        return False   # продажа и «хлам» выполнятся обычным обработчиком
    m = re.fullmatch(r"(продать|выбросить) (\d+)", text)
    if m:
        idx = int(m.group(2)) - 1
        if not 0 <= idx < len(inv):
            await reply(update, "❌ Нет предмета с таким номером.")
            return True
        it = inv[idx]
        ask = (f"Продать {item_line(it)} за {sell_price(it, data)} €?" if m.group(1) == "продать"
               else f"Выбросить {item_line(it)} без оплаты? Вернуть его будет нельзя.")
        st["confirm"] = {"cmd": text}
        await reply(update, f"❓ {ask}")
        return True
    if text in ("продать хлам", "разобрать хлам"):
        junk = [it for it in inv if it["r"] <= 1]
        if not junk:
            await reply(update, "ℹ️ Хлама нет: обычные и редкие предметы в рюкзаке закончились.")
            return True
        st["confirm"] = {"cmd": text}
        if text == "продать хлам":
            ask = f"Продать {len(junk)} предметов (обычные и редкие) за {sum(sell_price(it, data) for it in junk)} €?"
        else:
            ask = f"Разобрать {len(junk)} предметов (обычные и редкие) на {sum(DISMANTLE[it['r']] for it in junk)} осколков?"
        await reply(update, f"❓ {ask} Эпические и легендарные останутся.")
        return True
    return False

ACTS.update({"inv": act_inv, "rating": act_rating})


# ---------------- самопроверка меню при запуске ----------------
def check_menu_sync() -> list:
    """У каждой кнопки должна быть команда. Если после обновления что-то забыли, бот напишет об этом при запуске."""
    problems = []
    for name, obj in list(globals().items()):
        if isinstance(obj, ReplyKeyboardMarkup):
            for row in obj.keyboard:
                for b in row:
                    label_text = getattr(b, "text", b)
                    if _norm(label_text) not in BUTTON_ALIASES:
                        problems.append(f"Меню: кнопка «{label_text}» ({name}) не привязана к команде")
    for kind in SCREEN_KB:
        if kind not in SCREEN_RENDER and kind not in ("boss", "pvp", "inv", "class", "clan", "quests", "ach", "rating", "redzone", "ref"):
            problems.append(f"Меню: у раздела «{kind}» нет описания экрана")
    return problems

# =====================================================================
#   ОБНОВЛЕНИЕ 16: инструменты владельца в админ-панели
# =====================================================================
AMOUNT_RE = re.compile(r"^(-?\d+(?:[.,]\d+)?)(ккк|kkk|млрд|кк|kk|млн|к|k|м|m|b)?$", re.I)
AMOUNT_MULT = {"к": 10 ** 3, "k": 10 ** 3, "кк": 10 ** 6, "kk": 10 ** 6, "млн": 10 ** 6, "м": 10 ** 6, "m": 10 ** 6,
               "ккк": 10 ** 9, "kkk": 10 ** 9, "млрд": 10 ** 9, "b": 10 ** 9}
RARITY_WORDS = {"обычный": 0, "обычная": 0, "обычное": 0, "редкий": 1, "редкая": 1, "редкое": 1,
                "эпический": 2, "эпическая": 2, "эпическое": 2, "легендарный": 3, "легендарная": 3, "легендарное": 3}
SLOT_WORDS = {"оружие": "weapon", "меч": "weapon", "броня": "armor", "доспех": "armor", "амулет": "amulet"}
PENDING_BC = {}

GIVE_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("+1 000 мне", callback_data="adm_g_1000"),
     InlineKeyboardButton("+1 000 000 мне", callback_data="adm_g_1000000")],
    [InlineKeyboardButton("+1 000 000 000 мне", callback_data="adm_g_1000000000")],
    [InlineKeyboardButton("⬅️ Панель", callback_data="adm_home")]])
BACK_ADM_KB = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Панель", callback_data="adm_home")]])
BC_KB = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Отправить всем", callback_data="adm_bc_yes"),
                               InlineKeyboardButton("❌ Отмена", callback_data="adm_bc_no")]])


def parse_amount(s: str):
    """Сумма с сокращениями: 1000, 5к, 2кк (млн), 3ккк (млрд), 2.5кк, -100. Возвращает int или None."""
    m = AMOUNT_RE.match(s.strip().replace(" ", ""))
    if not m:
        return None
    num, suf = m.group(1).replace(",", "."), (m.group(2) or "").lower()
    mult = AMOUNT_MULT.get(suf, 1)
    return int(num) * mult if "." not in num else int(round(float(num) * mult))

def calc_power(slot: str, r: int, lvl: int) -> int:
    mult = RARITY[r][2]
    if slot == "amulet":
        return max(1, round(2 * mult + lvl * 0.1))
    if slot == "weapon":
        return max(1, round((1 + lvl * 0.4) * mult))
    return max(1, round((0.5 + lvl * 0.25) * mult))

def admin_log(text: str):
    log = world.setdefault("admin_log", [])
    log.append([int(time.time()), text])
    del log[:-100]
    touch()

def admin_log_text() -> str:
    log = world.get("admin_log", [])[-15:]
    return "📜 Журнал действий владельца (последние 15)\n\n" + ("\n".join(f"{fmt_time(t)} · {x}" for t, x in reversed(log)) or "Пока пусто.")

def add_coins(target: int, amount: int) -> int:
    get_user_data_safe(target)
    rec = user_data[target]
    rec["coins"] = max(0, rec.get("coins", 0) + amount)
    touch()
    return rec["coins"]

def admin_target(who: str):
    return ADMIN_ID if who.strip().lower() in ("я", "me", "себе") else resolve_player(who)

async def notify_player(context, uid: int, text: str):
    if uid != ADMIN_ID:
        try:
            await send_msg(context.bot, chat_id=uid, text=text)
        except Exception:
            pass

async def give_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/give кому сумма. Кому: я, ID или ник. Сумма: 1000, 5к, 2кк, 3ккк, минус забирает. Количество выдач не ограничено."""
    if not is_admin(update) or not update.message:
        return
    args = context.args or []
    amount = parse_amount(args[-1]) if len(args) >= 2 else None
    if amount is None:
        await update.message.reply_text("Пример: /give я 1кк · /give 12345 500 · /give Вася 5ккк · /give Вася -100\n"
                                        "Сокращения: к = тысяча, кк = миллион, ккк = миллиард.")
        return
    target = admin_target(" ".join(args[:-1]))
    if target is None or abs(amount) > GIVE_MAX:
        await update.message.reply_text("Не нашёл игрока (или таких несколько) либо сумма больше 10^18.")
        return
    total = add_coins(target, amount)
    admin_log(f"give {label(target)}: {amount:+d} €")
    await update.message.reply_text(f"✅ {label(target)}: {amount:+d} €, теперь {total} €")
    if amount > 0:
        await notify_player(context, target, f"🎁 Администратор выдал тебе {amount} €!")

async def giveall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/giveall сумма да: выдать всем игрокам (кроме забаненных)."""
    if not is_admin(update) or not update.message:
        return
    args = context.args or []
    amount = parse_amount(args[0]) if args else None
    if amount is None or not 0 < amount <= GIVE_MAX:
        await update.message.reply_text("Пример: /giveall 1000 да (без слова «да» бот только покажет, сколько игроков получат).")
        return
    ids = [u for u, d in user_data.items() if not d.get("banned")]
    if len(args) < 2 or args[-1].lower() not in ("да", "yes"):
        await update.message.reply_text(f"❓ Выдать по {amount} € каждому из {len(ids)} игроков? Подтверди: /giveall {args[0]} да")
        return
    for u in ids:
        add_coins(u, amount)
    admin_log(f"giveall: +{amount} € × {len(ids)} игроков")
    await update.message.reply_text(f"✅ Выдано по {amount} € игрокам: {len(ids)}")
    for u in ids[:300]:
        await notify_player(context, u, f"🎁 Администратор выдал всем игрокам по {amount} €!")
        await asyncio.sleep(0.04)

async def giveitem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/giveitem кому слот редкость: слот оружие|броня|амулет, редкость обычный|редкий|эпический|легендарный."""
    if not is_admin(update) or not update.message:
        return
    args = context.args or []
    slot = SLOT_WORDS.get(args[-2].lower()) if len(args) >= 3 else None
    r = RARITY_WORDS.get(args[-1].lower()) if len(args) >= 3 else None
    target = admin_target(" ".join(args[:-2])) if slot and r is not None else None
    if target is None:
        await update.message.reply_text("Пример: /giveitem я оружие легендарный · /giveitem Вася броня эпический\n"
                                        "Слоты: оружие, броня, амулет. Редкости: обычный, редкий, эпический, легендарный.")
        return
    get_user_data_safe(target)
    rec = user_data[target]
    it = {"n": gear_name(slot, rec.get("class", "")), "s": slot, "r": r, "p": calc_power(slot, r, rec["level"])}
    if rec.get("class"):
        it["c"] = rec["class"]
    how = add_item(rec, it)
    touch()
    admin_log(f"giveitem {label(target)}: {item_line(it)}")
    await update.message.reply_text(f"✅ {label(target)}: {item_line(it)} → {how}")
    await notify_player(context, target, f"🎁 Администратор выдал тебе предмет!\n{item_line(it)}\n→ {how}")

async def setlevel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setlevel кому уровень (1-1000)."""
    if not is_admin(update) or not update.message:
        return
    args = context.args or []
    lvl = int(args[-1]) if len(args) >= 2 and args[-1].isdigit() else 0
    target = admin_target(" ".join(args[:-1])) if 1 <= lvl <= 1000 else None
    if target is None:
        await update.message.reply_text("Пример: /setlevel я 50 · /setlevel Вася 10 (уровень от 1 до 1000)")
        return
    get_user_data_safe(target)
    rec = user_data[target]
    rec["level"], rec["xp"] = lvl, 0
    rec["max_hp"] = 100 + 20 * (lvl - 1)
    rec["hp"] = rec["max_hp"]
    touch()
    admin_log(f"setlevel {label(target)}: {lvl}")
    await update.message.reply_text(f"✅ {label(target)}: уровень {lvl}, макс. HP {rec['max_hp']}")
    await notify_player(context, target, f"⭐ Администратор установил тебе {lvl} уровень!")

async def resetlimits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/resetlimits кому|все: сбросить дневные лимиты атак, арены и передач."""
    if not is_admin(update) or not update.message:
        return
    who = " ".join(context.args or []).strip()
    if not who:
        await update.message.reply_text("Пример: /resetlimits я · /resetlimits Вася · /resetlimits все")
        return
    ids = list(user_data) if who.lower() in ("все", "всем", "all") else [admin_target(who)]
    if ids == [None]:
        await update.message.reply_text("Не нашёл игрока (или таких несколько).")
        return
    for u in ids:
        d = user_data[u]
        d["att_used"], d["att_extra"], d["pvp_used"], d["tr_sent"] = 0, 0, 0, 0
    touch()
    admin_log(f"resetlimits: {'все' if len(ids) > 1 else label(ids[0])}")
    await update.message.reply_text(f"✅ Дневные лимиты сброшены, игроков: {len(ids)}")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast текст: показывает предпросмотр, отправка по кнопке."""
    if not is_admin(update) or not update.message:
        return
    text = update.message.text.partition(" ")[2].strip()
    if not text:
        await update.message.reply_text("Пример: /broadcast Завтра в 20:00 босс мира с двойной наградой! (сначала будет предпросмотр)")
        return
    PENDING_BC["text"] = text
    n = sum(1 for u, d in user_data.items() if not d.get("banned") and u > 0)
    await update.message.reply_text(f"📢 Предпросмотр рассылки ({n} игроков):\n\n{text}", reply_markup=BC_KB)

async def admin_extra(data: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Дополнительные кнопки админ-панели. Возвращает (текст, кнопки) или None."""
    if data == "adm_give":
        return ("💶 Выдать €\n\n/give кому сумма\nКому: я, ID или ник. Сумма: 1000, 5к, 2кк (млн), 3ккк (млрд); минус забирает.\n"
                "Выдавать можно сколько угодно раз и любые суммы (до 10^18 за раз).\n/giveall сумма да — всем игрокам\n\n"
                "Быстро себе:", GIVE_KB)
    if data.startswith("adm_g_") and data[6:].isdigit():
        amount = int(data[6:])
        total = add_coins(ADMIN_ID, amount)
        admin_log(f"give я: +{amount} €")
        return (f"✅ Тебе выдано {amount} €, теперь {total} €\n\nЕщё раз:", GIVE_KB)
    if data == "adm_item":
        return ("🎁 Предметы и уровни\n\n/giveitem кому слот редкость — выдать предмет\n  слоты: оружие, броня, амулет\n"
                "  редкости: обычный, редкий, эпический, легендарный\n/setlevel кому уровень — установить уровень (1–1000)\n"
                "/resetlimits кому|все — сбросить дневные лимиты атак, арены и передач", BACK_ADM_KB)
    if data == "adm_bc":
        return ("📢 Рассылка\n\n/broadcast текст — бот покажет предпросмотр, а отправит всем только после кнопки «Отправить».", BACK_ADM_KB)
    if data == "adm_log":
        return (admin_log_text(), BACK_ADM_KB)
    if data == "adm_bc_no":
        PENDING_BC.clear()
        return ("❌ Рассылка отменена.", BACK_ADM_KB)
    if data == "adm_bc_yes":
        text = PENDING_BC.pop("text", None)
        if not text:
            return ("Нет рассылки для отправки. Используй /broadcast текст.", BACK_ADM_KB)
        ids = [u for u, d in user_data.items() if not d.get("banned") and u > 0]
        ok = 0
        for u in ids[:500]:
            try:
                await context.bot.send_message(chat_id=u, text=text)
                ok += 1
            except Exception:
                pass
            await asyncio.sleep(0.05)
        admin_log(f"broadcast: доставлено {ok} из {len(ids)}")
        return (f"📢 Рассылка отправлена: доставлено {ok} из {len(ids)}.", BACK_ADM_KB)
    if data == "adm_boss":
        b = world.get("boss") or {}
        state = "повержен" if b.get("dead") else f"HP {b.get('hp', 0)}/{b.get('max', 0)}"
        return (f"🐉 Запустить мирового босса сейчас?\n\nСейчас: «{b.get('name', '—')}» ({state}).\n"
                "Текущий босс будет заменён, тем, кто его бил, начислится утешительная награда, а все игроки получат уведомление.\n\n"
                "Свои название и HP: /spawnboss Название 5кк", BOSS_SPAWN_KB)
    if data == "adm_boss_no":
        return ("❌ Запуск босса отменён.", BACK_ADM_KB)
    if data == "adm_boss_yes":
        await send_notes(context.bot, spawn_boss_now())
        sent = await announce_boss(context)
        b = world["boss"]
        return (f"✅ Мировой босс «{b['name']}» запущен: HP {b['max']}. Уведомлено игроков: {sent}.", BACK_ADM_KB)
    return None

# ---------------- запуск мирового босса раньше срока (для владельца) ----------------
def spawn_boss_now(name=None, hp=None) -> list:
    """Заменяет текущего мирового босса новым прямо сейчас. Тем, кто бил старого, начисляется утешительная награда."""
    notes = []
    old = world.get("boss") or {}
    if old and not old.get("dead"):
        for u, dm in old.get("dmg", {}).items():
            coins = min(200, dm // 20)
            if coins:
                give(u, coins)
                notes.append((u, f"🐉 «{old['name']}» заменён новым боссом. Твой урон {dm} принёс {coins} €."))
    new_boss(week_id())
    nb = world["boss"]
    nb["name"] = name or random.choice([n for n in BOSS_NAMES if n != old.get("name")] or BOSS_NAMES)
    if hp:
        nb["max"] = nb["hp"] = int(hp)
    nb["manual"] = True
    admin_log(f"spawnboss: «{nb['name']}», HP {nb['max']}")
    touch()
    return notes

async def announce_boss(context) -> int:
    b = world["boss"]
    text = f"🐉 Появился мировой босс «{b['name']}»! HP {b['max']}. Заходи: 🔴 Красная точка → 🐉 Босс мира."
    ok = 0
    for u in [u for u, d in user_data.items() if not d.get("banned") and u > 0][:500]:
        try:
            await context.bot.send_message(chat_id=u, text=text)
            ok += 1
        except Exception:
            pass
        await asyncio.sleep(0.04)
    return ok

async def spawnboss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/spawnboss [Название] [HP]: запустить мирового босса сейчас (HP можно задать, например 5кк)."""
    if not is_admin(update) or not update.message:
        return
    args = list(context.args or [])
    hp = None
    if args and parse_amount(args[-1]) and parse_amount(args[-1]) >= 1000:
        hp = parse_amount(args.pop())
    notes = spawn_boss_now(" ".join(args) or None, hp)
    await send_notes(context.bot, notes)
    sent = await announce_boss(context)
    b = world["boss"]
    await update.message.reply_text(f"✅ Мировой босс «{b['name']}» запущен: HP {b['max']}. Уведомлено игроков: {sent}.")

ACH["abyss_50"] = ("Хозяин бездны", "Достигни глубины 50 в Бездне", lambda d: d.get("camp", {}).get("kills", {}).get("abyss", 0) >= 50, 500)
BOSS_SPAWN_KB = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Запустить", callback_data="adm_boss_yes"),
                                 InlineKeyboardButton("❌ Отмена", callback_data="adm_boss_no")]])


# =====================================================================
#   ОБНОВЛЕНИЕ 19: дуэль с боссом и охота на существ, осколки и ковка, защита от двойного запуска
# =====================================================================
PID_FILE = "game_bot.pid"
BOSS_TITLES = ["Костяной король", "Тёмный страж", "Повелитель клинков", "Хозяин подземелий", "Теневой палач"]
HUNT_TIERS = [("⚪ Обычное", 1.0, 70), ("🔵 Редкое", 1.6, 25), ("🟣 Элитное", 2.5, 5)]   # название, сила, шанс в %
FORGE_COST = [40, 150, 500]                      # осколков за предмет: обычный, редкий, эпический
TEMPER_COST = [30, 45, 70, 100, 150, 220, 320, 450, 650, 900]   # осколков за закалку с уровня u до u+1
DISMANTLE = [3, 10, 35, 100]                     # осколков за разбор предмета по редкости
B_FT = ["⚪ Ковка: обычный", "🔵 Ковка: редкий", "🟣 Ковка: эпический"]
B_FORGE_CRAFT = ["⚒ Ковать оружие", "⚒ Ковать броню", "⚒ Ковать амулет"]
B_FORGE_TEMPER = ["🔥 Закалить оружие", "🔥 Закалить броню", "🔥 Закалить амулет"]
FORGE_KB = ReplyKeyboardMarkup([B_FT, B_FORGE_CRAFT, B_FORGE_TEMPER, [B_BACK]], resize_keyboard=True)
SCREEN_KB["forge"] = FORGE_KB
SCREEN_WORDS["ковка"] = "forge"
BUTTON_ALIASES.update({_norm(k): v for k, v in {
    B_FORGE: "ковка", B_DISM: "разобрать хлам",
    **{B_FT[i]: f"ковка уровень {i + 1}" for i in range(3)},
    **{B_FORGE_CRAFT[i]: f"ковать {w}" for i, w in enumerate(("оружие", "броню", "амулет"))},
    **{B_FORGE_TEMPER[i]: f"закалить {w}" for i, w in enumerate(("оружие", "броню", "амулет"))},
}.items()})
FORGE_SLOTS = {"оружие": "weapon", "броню": "armor", "амулет": "amulet"}


# ---------------- защита от двойного запуска ----------------
def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

def find_other_instances() -> list:
    """Другие запущенные копии этого же файла бота (по списку процессов и по pid-файлу)."""
    me, parent, script, found = os.getpid(), os.getppid(), os.path.basename(__file__), set()
    try:
        for name in os.listdir("/proc"):
            if not name.isdigit() or int(name) in (me, parent):
                continue
            try:
                with open(f"/proc/{name}/cmdline", "rb") as f:
                    args = f.read().split(b"\0")
            except OSError:
                continue
            if args and b"python" in os.path.basename(args[0]) and any(os.path.basename(a.decode(errors="ignore")) == script for a in args[1:]):
                found.add(int(name))
    except OSError:
        pass
    try:
        with open(PID_FILE) as f:
            old = int(f.read().strip())
        if old not in (me, parent) and _alive(old):
            found.add(old)
    except (OSError, ValueError):
        pass
    return sorted(found)

def ensure_single_instance(wait: float = 20.0) -> int:
    """Останавливает старые копии бота, чтобы работала ровно одна. Иначе ответы дублируются, а данные затирают друг друга."""
    others = find_other_instances()
    for pid in others:
        try:
            os.kill(pid, signal.SIGTERM)    # мягко: старая копия успеет сохранить данные
        except OSError:
            pass
    deadline = time.time() + wait
    while others and time.time() < deadline and any(_alive(p) for p in others):
        time.sleep(0.3)
    for pid in others:
        if _alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass
    atexit.register(lambda: os.path.exists(PID_FILE) and open(PID_FILE).read().strip() == str(os.getpid()) and os.remove(PID_FILE))
    if others:
        logger.warning(f"Остановлено старых копий бота: {len(others)} ({', '.join(map(str, others))}). Теперь работает одна.")
    return len(others)

async def on_error(update, context):
    try:
        from telegram.error import Conflict
        conflict = isinstance(context.error, Conflict)
    except ImportError:
        conflict = False
    if conflict:
        logger.error("Telegram: с этим токеном уже запущена другая копия бота. Останови лишние: pkill -f game_bot.py, затем запусти бота заново.")
    else:
        logger.error("Ошибка в обработчике: %s", context.error, exc_info=context.error)


# ---------------- дуэль с боссом и охота на существ ----------------
async def fight_ready(update: Update, user_id: int, data: dict) -> bool:
    if user_id in active_games and active_games[user_id].get("game") == "duel":
        await reply(update, "⚠️ Бой уже идёт.")
        return False
    if data["hp"] <= 0:
        await reply(update, "🩸 У тебя 0 HP. Подожди лечения (+15 HP каждую минуту).")
        return False
    if attacks_used(data) >= attack_limit(data):
        await reply(update, f"⚡ Лимит атак на сегодня исчерпан ({attacks_used(data)}/{attack_limit(data)}). Новые атаки появятся завтра.")
        return False
    return True

async def start_boss_duel(update: Update, user_id: int, data: dict):
    """Дуэль с боссом: ярость на половине HP и мощный удар каждый 4-й ход (его можно переждать защитой)."""
    if not await fight_ready(update, user_id, data):
        return
    title = BOSS_TITLES[int(time.strftime("%j")) % len(BOSS_TITLES)]
    hp, atk = 120 + data["level"] * 15, 12 + data["level"] * 3
    active_games[user_id] = {"game": "duel", "mode": "duel", "boss": True, "tier": 0, "player_hp": data["hp"], "bot_hp": hp,
                             "bot_attack": atk, "round": 1, "opponent": f"Босс «{title}»", "cd": 0}
    await reply_pic(update, "boss", f"⚔️ ДУЭЛЬ С БОССОМ\n{title}\nТвоё HP: {data['hp']}/{data['max_hp']} · HP босса: {hp} · урон ~{atk}\n"
                                    "🔥 На половине HP босс впадает в ярость, а каждый 4-й ход бьёт мощным ударом: перед ним прикройся защитой.\n"
                                    "Награда: больше XP, € и осколков, небольшой шанс на снаряжение.\nВыбирай действие.")

async def start_hunt(update: Update, user_id: int, data: dict):
    """Охота: существо бывает обычным, редким или элитным. Чем сильнее, тем богаче награда."""
    if not await fight_ready(update, user_id, data):
        return
    tier = random.choices(range(3), weights=[t[2] for t in HUNT_TIERS])[0]
    name = random.choice(list(CREATURES))
    c, mult = CREATURES[name], HUNT_TIERS[tier][1]
    hp, atk = int((c["hp"] + data["level"] * 10) * mult), int((c["attack"] + data["level"] * 2) * mult)
    active_games[user_id] = {"game": "duel", "mode": "duel", "boss": False, "tier": tier, "player_hp": data["hp"], "bot_hp": hp,
                             "bot_attack": atk, "round": 1, "opponent": name, "cd": 0}
    await reply_pic(update, CREATURE_PIC[name], f"👹 ОХОТА: {HUNT_TIERS[tier][0]} существо {name}\nТвоё HP: {data['hp']}/{data['max_hp']} · "
                                                f"HP врага: {hp} · урон ~{atk}\nВыбирай действие.")


# ---------------- осколки и ковка (путь к снаряжению без магазина и без удачи) ----------------
def dismantle_junk(data: dict):
    inv = data.setdefault("inv", [])
    keep, n, total = [], 0, 0
    for it in inv:
        if it["r"] <= 1:
            total += DISMANTLE[it["r"]]
            n += 1
        else:
            keep.append(it)
    data["inv"] = keep
    data["shards"] = data.get("shards", 0) + total
    return n, total

def forge_text(d: dict) -> str:
    tier = d.get("forge_tier", 0)
    cls = CLASSES.get(d.get("class", ""), ("не выбран",))[0]
    lines = [f"🔨 Ковка · 🔩 осколков: {d.get('shards', 0)} · класс: {cls}", "",
             f"Выбрано: {RARITY[tier][0]} {RARITY[tier][1]} предмет — {FORGE_COST[tier]} осколков",
             "Куётся снаряжение твоего класса. Легендарное только из добычи и сундуков.", "",
             f"🔥 Закалка надетого снаряжения (до {GEAR_MAX_LVL} уровня):"]
    for slot, name in (("weapon", "Оружие"), ("armor", "Броня"), ("amulet", "Амулет")):
        it = d.get("eq", {}).get(slot)
        u = it.get("u", 0) if it else 0
        if not it:
            lines.append(f"{SLOTS[slot][0]} {name}: слот пуст")
        elif u >= GEAR_MAX_LVL:
            lines.append(f"{SLOTS[slot][0]} {name}: максимум ({u}/{GEAR_MAX_LVL})")
        else:
            lines.append(f"{SLOTS[slot][0]} {name} {u}→{u + 1}: {TEMPER_COST[u]} осколков")
    lines += ["", "Осколки падают после боёв (больше с боссов и элитных существ) и выходят из разобранного хлама."]
    return "\n".join(lines)

SCREEN_RENDER["forge"] = lambda uid, d: ("inventory", forge_text(d))

async def act_forge(update, context, user_id, data, text, orig) -> bool:
    m = re.fullmatch(r"ковка уровень ([123])", text)
    if m:
        data["forge_tier"] = int(m.group(1)) - 1
        update_user_data(user_id, data)
        await reply_pic(update, "inventory", forge_text(data))
        return True
    m = re.fullmatch(r"ковать (оружие|броню|амулет)", text)
    if m:
        slot, tier, cls = FORGE_SLOTS[m.group(1)], data.get("forge_tier", 0), data.get("class", "")
        cost = FORGE_COST[tier]
        if not cls:
            await reply(update, "🚫 Сначала выбери класс: «🎒 Герой» → «🧙 Класс». Куётся снаряжение твоего класса.")
        elif data.get("shards", 0) < cost:
            await reply(update, f"❌ Не хватает осколков: нужно {cost}, у тебя {data.get('shards', 0)}.")
        elif slot in data.get("eq", {}) and len(data.get("inv", [])) >= inv_capacity(data):
            await reply(update, "❌ Рюкзак полон. Продай или разбери лишнее, либо расширь рюкзак в магазине.")
        else:
            data["shards"] -= cost
            it = {"n": gear_name(slot, cls), "s": slot, "r": tier, "p": calc_power(slot, tier, data["level"]), "c": cls}
            how = add_item(data, it)
            update_user_data(user_id, data)
            await reply_pic(update, f"loot_{RARITY_KEY[tier]}", f"🔨 Выковано!\n{item_line(it)}\n→ {how}\n🔩 Осталось осколков: {data['shards']}")
        return True
    m = re.fullmatch(r"закалить (оружие|броню|амулет)", text)
    if m:
        it = data.get("eq", {}).get(FORGE_SLOTS[m.group(1)])
        u = it.get("u", 0) if it else 0
        if not it:
            await reply(update, "ℹ️ В этом слоте ничего не надето. Сначала надень предмет.")
        elif not gear_ok(it, data):
            await reply(update, gear_mismatch_text(it, data))
        elif u >= GEAR_MAX_LVL:
            await reply(update, f"ℹ️ Предмет уже на максимальном уровне ({GEAR_MAX_LVL}/{GEAR_MAX_LVL}).")
        elif data.get("shards", 0) < TEMPER_COST[u]:
            await reply(update, f"❌ Не хватает осколков: нужно {TEMPER_COST[u]}, у тебя {data.get('shards', 0)}.")
        else:
            data["shards"] -= TEMPER_COST[u]
            it["u"] = u + 1
            update_user_data(user_id, data)
            await reply_pic(update, "inventory", f"🔥 Закалено: {item_line(it)} (уровень {u + 1}/{GEAR_MAX_LVL})\n🔩 Осталось осколков: {data['shards']}")
        return True
    return False

ACTS["forge"] = act_forge

async def autosave(context: ContextTypes.DEFAULT_TYPE):
    if dirty:
        save_data()

async def on_shutdown(application: Application):
    save_data()

BOT_COMMANDS = [
    BotCommand("start", "Главное меню"),
    BotCommand("menu", "Выйти в меню"),
    BotCommand("hero", "Герой: инвентарь, класс, задания"),
    BotCommand("rating", "Рейтинг всех игроков"),
    BotCommand("balance", "Мой баланс"),
    BotCommand("b", "Баланс (коротко)"),
    BotCommand("farm", "Ферма: до 500 слотов и уровней"),
    BotCommand("camp", "Кампания: 12 локаций и Бездна"),
    BotCommand("shop", "Магазин"),
    BotCommand("pay", "Передать €: /pay ник сумма"),
    BotCommand("limit", "Лимит передачи € на сегодня"),
    BotCommand("stats", "Моя статистика"),
    BotCommand("nick", "Сменить ник"),
    BotCommand("ref", "Пригласить друзей"),
    BotCommand("help", "Помощь: коротко и по делу"),
    BotCommand("help_what", "Что это за бот"),
    BotCommand("help_how", "Как пользоваться"),
    BotCommand("help_where", "Где что искать"),
    BotCommand("leave", "Выйти из игры"),
]

async def on_startup(application: Application):
    """Список команд, который Telegram показывает, когда набираешь «/»."""
    global BOT_USERNAME
    BOT_USERNAME = getattr(application.bot, "username", None) or BOT_USERNAME
    try:
        await application.bot.set_my_commands(BOT_COMMANDS)
    except Exception as e:
        logger.error(f"Не удалось установить меню команд: {e}")
    if ADMIN_ID:   # владелец видит дополнительные команды, остальные нет
        try:
            await application.bot.set_my_commands(BOT_COMMANDS + ADMIN_COMMANDS, scope=BotCommandScopeChat(ADMIN_ID))
        except Exception as e:
            logger.error(f"Не удалось установить команды админа: {e}")

# --- КОМАНДЫ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await handle_referral(update, context)
    if not (user_id in active_games and active_games[user_id].get("game") == "duel"):
        active_games.pop(f"scr_{user_id}", None)   # /start всегда возвращает в главное меню
    data = get_user_data_safe(user_id)

    if user_id in active_games and active_games[user_id].get("game") == "duel":
        game = active_games[user_id]
        await reply(update, 
            f"⚔️ Вы в дуэли с {game['opponent']}. \nHP: {game['player_hp']}/{data['max_hp']}. \nВыбирай действие кнопками."
        )
        return
    
    if f"solo_{user_id}" in active_games:
        await reply(update, "🎲 Вы в игре 'Угадай число'.")
        return

    if f"tod_{user_id}" in active_games:
        await reply(update, "🎭 Вы в игре 'Правда или действие'. Пиши 'правда' или 'действие'. Выйти: 'стоп' или /leave.")
        return
        
    await reply_pic(update, "start", f"Привет, {pname(update.effective_user.id)}! \n"
        f"Уровень: {data['level']} (XP: {data['xp']}/{xp_needed(data['level'])}), HP: {data['hp']}/{data['max_hp']}\n\n"
        f"📖 Пиши /help, чтобы увидеть все команды."
    )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if f"tod_{user_id}" in active_games:
        del active_games[f"tod_{user_id}"]
        await reply_pic(update, "menu", "✅ Вы вышли из игры (Правда или действие). /start для меню.")
        return
    if f"solo_{user_id}" in active_games:
        del active_games[f"solo_{user_id}"]
        await reply_pic(update, "menu", "✅ Вы вышли из игры (угадай число). /start для меню.")
        return
    if f"shop_{user_id}" in active_games:
        del active_games[f"shop_{user_id}"]
        await reply_pic(update, "menu", "✅ Вы вышли из магазина. /start для меню.")
        return
    if f"scr_{user_id}" in active_games and user_id not in active_games and not in_duo_room(user_id):
        await scr_back(update, user_id, "menu")
        return
    if user_id in active_games:
        game_type = active_games[user_id].get("game")
        del active_games[user_id]
        await reply_pic(update, "menu", f"✅ Вы вышли из игры ({game_type}). /start для меню.")
    else:
        await reply_pic(update, "menu", "ℹ️ Нет активных игр. /start для выбора.")

async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if f"tod_{user_id}" in active_games:
        del active_games[f"tod_{user_id}"]
        await reply_pic(update, "leave", "✅ Вы вышли из игры (Правда или действие).")
        return
    if f"solo_{user_id}" in active_games:
        del active_games[f"solo_{user_id}"]
        await reply_pic(update, "leave", "✅ Вы вышли из игры (угадай число).")
        return
    if f"shop_{user_id}" in active_games:
        del active_games[f"shop_{user_id}"]
        await reply_pic(update, "leave", "✅ Вы вышли из магазина.")
        return
    if f"scr_{user_id}" in active_games and user_id not in active_games and not in_duo_room(user_id):
        await scr_back(update, user_id, "leave")
        return
    if user_id in active_games:
        game_type = active_games[user_id].get("game")
        del active_games[user_id]
        await reply_pic(update, "leave", f"✅ Вы вышли из игры ({game_type}).")
    else:
        left = False
        keys_to_del = []
        for gid, gdata in active_games.items():
            if gdata.get("type") == "guess_duo" and user_id in [gdata.get("creator"), gdata.get("partner")]:
                keys_to_del.append(gid)
                left = True
        notices = []  # (куда написать, текст)
        for k in keys_to_del:
            g = active_games.pop(k)
            other = g['partner'] if user_id == g['creator'] else g['creator']
            if g.get("private", True):
                if other: notices.append((other, "ℹ️ Соперник вышел из игры."))
            elif update.effective_chat is None or update.effective_chat.id != g.get("chat_id"):
                notices.append((g["chat_id"], f"ℹ️ {pname(update.effective_user.id)} вышел из игры, комната закрыта."))
        if left:
            await reply_pic(update, "leave", "✅ Вышел из дуэли на угадывание.")
            for chat, msg in notices:
                try:
                    await send_msg(context.bot, chat_id=chat, text=msg)
                except Exception:
                    pass
        else:
            await reply_pic(update, "leave", "ℹ️ Нет активных игр.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    uid = update.effective_user.id
    data = get_user_data_safe(uid)
    a, dfn, c = equip_bonus(data)
    cls = CLASSES.get(data.get("class", ""), ("не выбран",))[0]
    title = f"\n🎖 Титул: {data['title']}" if data.get("title") else ""
    await reply_pic(update, "stats",
        f"📊 Статистика: {pname(uid)}{title}\n👤 Уровень: {data['level']} · ⭐ XP: {data['xp']}/{xp_needed(data['level'])}\n"
        f"⚔️ Атака: {data['attack'] + a} (база {data['attack']} + предметы {a})\n🛡 Броня: −{dfn} урона и −{int(armor_pct(data) * 100)}% от каждого удара\n"
        f"📿 Амулет: +{c}% € и +{c // 2}% XP\n❤️ HP: {data['hp']}/{data['max_hp']}\n"
        f"🧙 Класс: {cls}\n€ Монеты: {data['coins']}\n🏆 Рейтинг: {data.get('rating', 1000)} · 🗼 Башня: этаж {data.get('tower_best', 0)}\n"
        f"👥 Клан: {data.get('clan') or '—'}\n⚡ Атак сегодня: {attacks_used(data)}/{attack_limit(data)}\n"
        f"🏆 Место в рейтинге: {rank_text(uid)}")

HELP_TEXTS = {
    "home": ("📖 Помощь\n\nВыбери, что нужно узнать: нажми кнопку или набери команду.\n\n"
             "/help_what — что это за бот\n/help_how — как пользоваться\n/help_where — где что искать\n/help_cmds — главные команды"),
    "what": ("🎮 Что это за бот\n\nЭто игра прямо в Telegram. Ты растишь героя: сражаешься с монстрами и боссами, "
             "собираешь снаряжение и зарабатываешь €.\n\nЗа победы растут уровень и опыт. Редкие вещи выпадают иногда: "
             "это приятная находка, а не награда за каждый бой. Зато после боёв падают осколки: из них делают снаряжение твоего класса. "
             "Играть можно одному и вместе с друзьями."),
    "how": ("🧭 Как пользоваться\n\n1. Нажми /start: появится меню с кнопками.\n2. Писать ничего не нужно, управляй кнопками внизу.\n"
            "3. Начни с «🔴 Красная точка» и нажми «Дуэль».\n4. В «🎒 Герой» выбери класс: от него зависит снаряжение.\n"
            "5. € зарабатывай в боях и на «🌾 Ферме», трать в «🛒 Магазине».\n\n"
            "В день можно сделать 100 атак, потом лимит обновится.\n«⬅️ Назад» возвращает на шаг назад, /menu открывает главное меню."),
    "where": ("🔎 Где что искать\n\n⚔️ Бои, кампания, башня, арена, босс — «🔴 Красная точка»\n"
              "🎒 Инвентарь, класс, задания, клан — «🎒 Герой»\n🔨 Ковка и закалка за осколки — «🎒 Герой» → «Инвентарь» → «Ковка»\n💶 Покупки и улучшения — «🛒 Магазин»\n"
              "🌾 Пассивный доход — «🌾 Ферма»\n🏆 Места игроков — «🏆 Рейтинг»\n🎁 Приглашения и награды — «🎒 Герой» → «Друзья»\n\n"
              "Не нашёл нужное? Набери / в строке ввода: там все команды."),
    "cmds": ("⌨️ Главные команды\n\n/start — главное меню\n/menu — выйти в меню\n/b — мой баланс\n/shop — магазин\n"
             "/hero — герой\n/rating — рейтинг игроков\n/help — помощь\n\nОстальные команды видны, если набрать / в строке ввода."),
}
HELP_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎮 Что это", callback_data="help_what"), InlineKeyboardButton("🧭 Как пользоваться", callback_data="help_how")],
    [InlineKeyboardButton("🔎 Где что искать", callback_data="help_where"), InlineKeyboardButton("⌨️ Команды", callback_data="help_cmds")]])

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_pic(update, "help", "📖 Помощь")
    await update.message.reply_text(HELP_TEXTS["home"], reply_markup=HELP_KB)

def _help_cmd(key):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text(HELP_TEXTS[key], reply_markup=HELP_KB)
    return handler

help_what_command, help_how_command, help_where_command, help_cmds_command = (_help_cmd(k) for k in ("what", "how", "where", "cmds"))

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    try:
        await q.edit_message_text(HELP_TEXTS.get(q.data[5:], HELP_TEXTS["home"]), reply_markup=HELP_KB)
    except Exception:
        pass  # текст не изменился

BUTTON_ALIASES.update({_norm(k): v for k, v in {
    B_UP_W: "купить улучшение оружия", B_UP_A: "купить улучшение брони", B_UP_M: "купить улучшение амулета", B_BUY_BAG: "купить рюкзак",
}.items()})


# --- ТРИГГЕРЫ ---

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip().lower()
    text = BUTTON_ALIASES.get(_norm(text), text)
    data = get_user_data_safe(user_id)

    # --- КОМАНДЫ ---
    if text.startswith("/join_"):
        raw = text.replace("/join_", "").split("@")[0].strip()
        game_id = raw if raw.startswith("duo_") else f"duo_{raw}"
        if game_id not in active_games: await reply(update, "❌ Комната не найдена."); return
        game = active_games[game_id]
        if game.get("type") != "guess_duo" or game["status"] != "waiting": await reply(update, "❌ Комната закрыта."); return
        if not room_in_this_chat(game, update): await reply(update, "❌ Эта комната создана в другом чате."); return
        if game["creator"] == user_id: await reply(update, "❌ Нельзя в свою."); return
        game["partner"] = user_id; game["status"] = "active"
        game.setdefault("names", {})[user_id] = pname(update.effective_user.id)
        record_pair(game["creator"], user_id)

        if game.get("private", True):
            await send_msg(context.bot,
                chat_id=game["creator"],
                text=f"🎉 Твой напарник {pname(update.effective_user.id)} зашел в комнату!\nИгра началась. Жди его хода."
            )
            await reply(update, f"🤝 Игра началась! Число от 1 до {game['secret']+5}.")
        else:
            await reply(update,
                f"🤝 {pname(update.effective_user.id)} зашёл в комнату! Игра началась.\n"
                f"Число от 1 до {game['secret']+5}. Пишите числа прямо в этот чат."
            )
        return

    if text == "/leave": await leave_command(update, context); return
    if text == "статистика": await stats_command(update, context); return
    if text == "помощь": await help_command(update, context); return
    if text == "ник" or text.startswith("ник "): await nick_apply(update, update.message.text.strip()[3:]); return
    if text in ("баланс", "б", "/б", "/b"): await balance_show(update, data); return
    if text in ("лимит", "лимит передачи"): await limit_show(update, data); return
    if text.startswith("передать "): await pay_text(update, context, user_id, data, update.message.text.strip()); return
    if await screens_dispatch(update, context, user_id, data, text): return
    if text == "магазин": await open_shop(update, data); return
    if text.startswith("купить "):
        item = SHOP_ALIASES.get(text[7:].strip().replace("hp", "хп"))
        if item:
            await buy_item(update, user_id, data, item)
            return

    # --- ТРИГГЕРЫ НАЧАЛА ---
    if text == "дуэль":
        await start_boss_duel(update, user_id, data)
        return

    if text == "существо":
        await start_hunt(update, user_id, data)
        return

    if text == "угадай":
        if f"solo_{user_id}" in active_games: await reply(update, "⚠️ Игра уже есть."); return
        secret = random.randint(1, 10 + (data['level'] - 1) * 5)
        active_games[f"solo_{user_id}"] = {"game": "guess", "secret": secret, "owner": user_id}
        await reply_pic(update, "guess", f"🎲 Угадай число от 1 до {secret + 5}.")
        return

    if text == "друг":
        for gid, gdata in active_games.items():
            if gdata.get("creator") == user_id and gdata.get("type") == "guess_duo" and gdata.get("status") == "waiting":
                await reply(update, "⚠️ У тебя уже есть открытая комната."); return
        game_id = new_duo_id(); secret = random.randint(1, 20 + (data['level'] * 5))
        active_games[game_id] = {"type": "guess_duo", "secret": secret, "creator": user_id, "partner": None, "status": "waiting",
                                 "private": is_private(update),
                                 "chat_id": update.effective_chat.id if update.effective_chat else user_id,
                                 "names": {user_id: pname(update.effective_user.id)}}
        await reply_pic(update, "duo", f"✨ Комната: {game_id}\nЧисло от 1 до {secret+5}.\nДруг: /join_{game_id.split('_')[1]}")
        return

    # --- ПРАВДА ИЛИ ДЕЙСТВИЕ: начало ---
    if text in ["пд", "правда или действие"]:
        if f"tod_{user_id}" in active_games:
            await reply(update, "⚠️ Игра уже идёт. Пиши 'правда' или 'действие'.")
            return
        active_games[f"tod_{user_id}"] = {"game": "tod"}
        await reply_pic(update, "tod", "🎭 ПРАВДА ИЛИ ДЕЙСТВИЕ\n\n"
            "Правда или действие?\n"
            "Выбирай кнопкой: «🔮 Правда» или «🔥 Действие». Закончить: «🛑 Стоп»."
        )
        return

    # --- ПРАВДА ИЛИ ДЕЙСТВИЕ: ход игры ---
    tod = active_games.get(f"tod_{user_id}")
    if tod:
        if text == "правда":
            question = pick_no_repeat(tod, "truths_left", TRUTHS)
            await reply(update, f"🔮 Правда:\n{question}\n\nПравда или действие?")
        elif text == "действие":
            task = pick_no_repeat(tod, "dares_left", DARES)
            await reply(update, f"🔥 Действие:\n{task}\n\nПравда или действие?")
        elif text in ["стоп", "хватит", "выход"]:
            del active_games[f"tod_{user_id}"]
            await reply(update, "✅ Игра закончена. /start для меню.")
        else:
            if is_private(update): await reply(update, "Правда или действие? Выбери кнопкой: «🔮 Правда» или «🔥 Действие».")
        return

    # --- БОЙ ---
    game = active_games.get(user_id)
    if game and game.get("game") == "duel":
        if text in ["атака", "сбей", "навык", "защита"]:
            await fight_action(update, context, user_id, data, game, "атака" if text == "сбей" else text)
            return
        if text in ["уйти", "сбежал", "сбегаю"]:
            if game.get("mode") == "tower":
                data["hp"] = max(0, game["player_hp"])
                update_user_data(user_id, data)
                del active_games[user_id]
                await reply_pic(update, "leave", f"🚪 Ты покинул башню на этаже {game['floor']}. Рекорд: {data.get('tower_best', 0)}. /menu.")
            else:
                del active_games[user_id]
                await reply(update, "🏃 Сбежал. /menu.")
            return

    # --- УГАДАЙ ЧИСЛО (СОЛО) ---
    solo = active_games.get(f"solo_{user_id}")
    if solo:
        try:
            guess = int(text)
        except ValueError:
            if is_private(update): await reply(update, "Только цифры! (/leave — выйти)")
            return
        if guess == solo["secret"]:
            levels = add_xp(data, 25); data['attack'] += 2; data['coins'] += 10; qn = quest_event(data, 'guess') + check_ach(data); update_user_data(user_id, data)
            del active_games[f"solo_{user_id}"]
            await reply_pic(update, "win_guess", f"🎉 Вы угадали число {guess}! Заработано 25 XP, 10 € и +2 к атаке.\n{xp_status(data, levels)}{qn}")
        elif guess < solo["secret"]:
            await reply(update, "🔼 Больше.")
        else:
            await reply(update, "🔽 Меньше.")
        return

    # --- УГАДАЙ ЧИСЛО (ДУО) ---
    my_duo_game = None
    for gid, gdata in active_games.items():
        if gdata.get("type") == "guess_duo" and gdata.get("status") == "active" \
                and user_id in [gdata.get("creator"), gdata.get("partner")] and room_in_this_chat(gdata, update):
            my_duo_game = (gid, gdata); break

    if my_duo_game:
        gid, game = my_duo_game
        in_private = game.get("private", True)
        try:
            guess = int(text)
        except ValueError:
            if in_private:
                await send_msg(context.bot, chat_id=user_id, text="Только цифры!")
            return  # в группе обычную болтовню игроков не трогаем

        secret = game["secret"]
        first_name = pname(user_id)
        partner_id = game["creator"] if user_id == game["partner"] else game["partner"]

        if guess == secret:
            data = get_user_data_safe(user_id)
            levels = add_xp(data, 40); data['attack'] += 3; data['coins'] += 20; update_user_data(user_id, data); del active_games[gid]

            if in_private:
                await send_pic(context.bot, "win_duo", chat_id=user_id, text=f"🔥 Ты угадал число {secret} и победил в дуэли! Заработано 40 XP, 20 € и +3 к атаке.\n{xp_status(data, levels)}"
                )
                await send_pic(context.bot, "lose", chat_id=partner_id, text=f"💀 Твой соперник {first_name} угадал число {secret}. Ты проиграл эту дуэль."
                )
            else:
                loser = game.get("names", {}).get(partner_id, "Соперник")
                await reply_pic(update, "win_duo", f"🔥 {first_name} угадал число {secret} и победил в дуэли! Заработано 40 XP, 20 € и +3 к атаке.\n"
                    f"{xp_status(data, levels)}\n💀 {loser} проиграл эту дуэль."
                )
        else:
            if in_private:
                await send_msg(context.bot,
                    chat_id=user_id,
                    text=f"🧙‍♂️ Неверно."
                )
                await send_msg(context.bot,
                    chat_id=partner_id,
                    text=f"🧙‍♂️ Твой соперник {first_name} не угадал число. Старайтесь дальше!"
                )
            else:
                await reply(update, f"🧙‍♂️ {first_name} не угадал число. Пробуйте дальше!")
        return

    # --- Нажата кнопка боя или игры, а самой игры уже нет ---
    if is_private(update) and keyboard_for(user_id) is MAIN_KB and text in ["атака", "сбей", "уйти", "правда", "действие", "стоп", "навык", "защита", "ударить босса", "обновить",
                                                                         "найти соперника", "надеть лучшее", "продать хлам", "воин", "маг", "лучник",
                                                                         "топ кланов", "покинуть клан"]:
        await reply(update, "ℹ️ Сейчас нет активной игры. Выбери игру кнопкой ниже.")

# --- ЗАПУСК ---

def main():
    global user_data
    ensure_single_instance()   # старые копии бота останавливаются, остаётся одна
    user_data = load_data()
    world.update(load_world())
    for problem in check_menu_sync():
        logger.warning(problem)
    application = Application.builder().token(TOKEN).post_init(on_startup).post_shutdown(on_shutdown).build()
    application.add_error_handler(on_error)
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("leave", leave_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("help_what", help_what_command))
    application.add_handler(CommandHandler("help_how", help_how_command))
    application.add_handler(CommandHandler("help_where", help_where_command))
    application.add_handler(CommandHandler("help_cmds", help_cmds_command))
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help_"))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(TypeHandler(Update, track), group=-1)
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("nick", nick_command))
    application.add_handler(CommandHandler("b", balance_command))
    application.add_handler(CommandHandler("farm", farm_command))
    application.add_handler(CommandHandler("hero", hero_command))
    application.add_handler(CommandHandler("rating", rating_command))
    application.add_handler(CommandHandler("camp", camp_command))
    application.add_handler(CommandHandler("pay", pay_command))
    application.add_handler(CommandHandler("limit", limit_command))
    application.add_handler(CommandHandler("give", give_command))
    application.add_handler(CommandHandler("giveall", giveall_command))
    application.add_handler(CommandHandler("giveitem", giveitem_command))
    application.add_handler(CommandHandler("setlevel", setlevel_command))
    application.add_handler(CommandHandler("resetlimits", resetlimits_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("spawnboss", spawnboss_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("ref", ref_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("user", user_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^adm_"))
    if not ADMIN_ID:
        logger.warning("ADMIN_ID не задан: админ-панель отключена. Свой ID покажет команда /myid.")
    
    application.add_handler(MessageHandler(filters.TEXT, message_handler))

    application.job_queue.run_repeating(auto_heal, interval=HEAL_INTERVAL, first=HEAL_INTERVAL)
    application.job_queue.run_repeating(autosave, interval=AUTOSAVE_INTERVAL, first=AUTOSAVE_INTERVAL)
    print("Бот запущен. Дуэль без подсказок.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
