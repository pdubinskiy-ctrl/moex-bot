import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

OWNER_ID = 878761279

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN отсутствует в .env")

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Хранилище для уведомлений, чтобы отправлять 1 раз
notified_index = False
notified_usd = False


# ============================
#     MOEX API FUNCTIONS
# ============================

async def fetch_json(url):
    """Загрузка JSON с MOEX."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


async def get_imoex():
    """Получение индекса Мосбиржи."""
    url = "https://iss.moex.com/iss/engines/stock/markets/index/boards/SNDX/securities/IMOEX.json"
    data = await fetch_json(url)

    marketdata = data["marketdata"]["data"][0]
    columns = data["marketdata"]["columns"]

    idx_last = marketdata[columns.index("LAST")]
    idx_open = marketdata[columns.index("OPEN")]

    pct = ((idx_last - idx_open) / idx_open) * 100

    return idx_last, idx_open, pct


async def get_usd_rub():
    """Получение курса USD/RUB."""
    url = "https://iss.moex.com/iss/engines/currency/markets/selt/securities/USD000UTSTOM.json"
    data = await fetch_json(url)

    marketdata = data["marketdata"]["data"][0]
    columns = data["marketdata"]["columns"]

    last = marketdata[columns.index("LAST")]
    open_ = marketdata[columns.index("OPEN")]

    pct = ((last - open_) / open_) * 100

    return last, open_, pct


# ============================
#        COMMANDS
# ============================

@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    await msg.answer(
        "📈 <b>Бот мониторинга Мосбиржи</b>\n\n"
        "Доступные команды:\n"
        "• /index — Индекс Мосбиржи (IMOEX)\n"
        "• /usd — Курс USD/RUB\n"
        "Бот также отправит уведомление, если движение превысит 1%."
    )


@dp.message(Command("index"))
async def index_cmd(msg: types.Message):
    last, open_, pct = await get_imoex()
    arrow = "🔺" if pct > 0 else "🔻"
    await msg.answer(
        f"📊 <b>Индекс Мосбиржи (IMOEX)</b>\n"
        f"Текущая цена: <b>{last:.2f}</b>\n"
        f"Цена открытия: {open_:.2f}\n"
        f"Изменение: {arrow} <b>{pct:.2f}%</b>"
    )


@dp.message(Command("usd"))
async def usd_cmd(msg: types.Message):
    last, open_, pct = await get_usd_rub()
    arrow = "🔺" if pct > 0 else "🔻"
    await msg.answer(
        f"💵 <b>Курс USD/RUB</b>\n"
        f"Текущий курс: <b>{last:.2f}</b>\n"
        f"Цена открытия: {open_:.2f}\n"
        f"Изменение: {arrow} <b>{pct:.2f}%</b>"
    )


# ============================
#     BACKGROUND MONITOR
# ============================

async def monitor_markets():
    global notified_index, notified_usd

    await asyncio.sleep(3)

    while True:
        try:
            # ===== IMOEX =====
            last_i, open_i, pct_i = await get_imoex()
            if abs(pct_i) >= 1 and not notified_index:
                arrow = "🔺" if pct_i > 0 else "🔻"
                await bot.send_message(
                    OWNER_ID,
                    f"📢 <b>Движение индекса Мосбиржи!</b>\n"
                    f"IMOEX изменился на {arrow} <b>{pct_i:.2f}%</b> от открытия."
                )
                notified_index = True

            # ===== USD/RUB =====
            last_u, open_u, pct_u = await get_usd_rub()
            if abs(pct_u) >= 1 and not notified_usd:
                arrow = "🔺" if pct_u > 0 else "🔻"
                await bot.send_message(
                    OWNER_ID,
                    f"📢 <b>Движение курса USD/RUB!</b>\n"
                    f"Доллар изменился на {arrow} <b>{pct_u:.2f}%</b> от открытия."
                )
                notified_usd = True

        except Exception as e:
            print("Monitor error:", e)

        await asyncio.sleep(60)


# ============================
#   RUN BOT
# ============================

async def main():
    asyncio.create_task(monitor_markets())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
