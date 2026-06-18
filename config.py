import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Не найден токен бота. Установите BOT_TOKEN")

# База данных - теперь в папке data
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_FILE = os.getenv("DB_FILE", "orders.json")
DB_PATH = DATA_DIR / DB_FILE

ADMIN_URL = os.getenv("ADMIN_URL", "http://localhost:8000")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Статусы заказа
ORDER_STATUSES = [
    {"id": "new", "name": "Новый", "emoji": "🟡"},
    {"id": "collecting", "name": "Собирается", "emoji": "🔵"},
    {"id": "ready", "name": "Готов", "emoji": "🟢"},
    {"id": "delivering", "name": "В доставке", "emoji": "🟠"},
    {"id": "delivered", "name": "Доставлен", "emoji": "✅"},
]

STATUS_MAP = {s["id"]: s for s in ORDER_STATUSES}
STATUS_NAMES = {s["id"]: s["name"] for s in ORDER_STATUSES}
STATUS_EMOJIS = {s["id"]: s["emoji"] for s in ORDER_STATUSES}