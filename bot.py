import os
from datetime import datetime
from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from telegram.request import HTTPXRequest

from config import BOT_TOKEN, VPN_NAME
from database import (
    init_db,
    create_user,
    get_user,
    update_username,
    format_bytes,
)
from github import upload_subscription


def read_nodes():
    try:
        with open("nodes.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    nodes = []

    for line in lines:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if (
            line.startswith("vless://")
            or line.startswith("vmess://")
            or line.startswith("trojan://")
            or line.startswith("ss://")
            or line.startswith("socks://")
            or line.startswith("hy2://")
            or line.startswith("hysteria2://")
        ):
            nodes.append(line)

    return nodes


def build_subscription(user):
    (
        user_id,
        telegram_id,
        username,
        token,
        used_bytes,
        total_bytes,
        expires_at,
        active,
        created_at,
    ) = user

    nodes = read_nodes()

    if not nodes:
        raise RuntimeError(
            "В nodes.txt нет ни одной VPN-ноды"
        )

    expires_timestamp = 0

    try:
        expires_timestamp = int(
            datetime.fromisoformat(expires_at).timestamp()
        )
    except Exception:
        pass

    text = (
        f"#profile-title: {VPN_NAME}\n"
        "#profile-update-interval: 60\n"
        f"#subscription-userinfo: "
        f"upload=0;"
        f"download={used_bytes};"
        f"total={total_bytes};"
        f"expire={expires_timestamp}\n"
        "#profile-status: active\n"
        "\n"
    )

    text += "\n".join(nodes)

    return text


def happ_link(subscription_url):
    return "happ://add/" + quote(
        subscription_url,
        safe=":/?=&%#"
    )


def subscription_buttons(url):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🍑 Добавить в Happ",
                url=happ_link(url)
            )
        ],
        [
            InlineKeyboardButton(
                "🔗 Скопировать ссылку",
                callback_data="copy_info"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Обновить подписку",
                callback_data="refresh"
            )
        ],
    ])


def user_info_text(user):
    (
        user_id,
        telegram_id,
        username,
        token,
        used_bytes,
        total_bytes,
        expires_at,
        active,
        created_at,
    ) = user

    status = "🟢 Активна" if active else "🔴 Отключена"

    return (
        f"🍑 <b>{VPN_NAME}</b>\n\n"
        f"Статус: {status}\n"
        f"Трафик: <b>{format_bytes(used_bytes)}</b> / "
        f"<b>{format_bytes(total_bytes)}</b>\n"
        f"До: <code>{expires_at[:10]}</code>"
    )


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📱 Моя подписка",
                callback_data="subscription"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Статистика",
                callback_data="stats"
            ),
            InlineKeyboardButton(
                "🔄 Обновить",
                callback_data="refresh"
            )
        ],
        [
            InlineKeyboardButton(
                "❓ Помощь",
                callback_data="help"
            )
        ],
    ])


def make_subscription(user):
    content = build_subscription(user)

    filename = f"{user[3]}.txt"

    return upload_subscription(
        filename,
        content
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    db_user = get_user(user.id)

    if not db_user:
        db_user = create_user(
            user.id,
            user.username
        )
    else:
        update_username(
            user.id,
            user.username
        )
        db_user = get_user(user.id)

    await update.message.reply_text(
        (
            f"🍑 <b>{VPN_NAME}</b>\n\n"
            "Добро пожаловать!\n\n"
            "Я создам для тебя персональную "
            "VPN-подписку на GitHub.\n\n"
            "Нажми кнопку ниже 👇"
        ),
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


async def button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    db_user = get_user(user.id)

    if not db_user:
        db_user = create_user(
            user.id,
            user.username
        )

    if query.data == "subscription":
        try:
            url = make_subscription(db_user)

            await query.message.reply_text(
                (
                    "🍑 <b>Твоя подписка готова!</b>\n\n"
                    "Нажми кнопку ниже — Happ откроется "
                    "и добавит подписку автоматически.\n\n"
                    "Или скопируй ссылку вручную:\n"
                    f"<code>{url}</code>\n\n"
                    "⚠️ Не передавай эту ссылку другим."
                ),
                parse_mode="HTML",
                reply_markup=subscription_buttons(url)
            )

        except Exception as e:
            await query.message.reply_text(
                (
                    "❌ Не удалось создать подписку:\n"
                    f"<code>{str(e)}</code>"
                ),
                parse_mode="HTML"
            )

    elif query.data == "stats":
        db_user = get_user(user.id)

        await query.message.reply_text(
            user_info_text(db_user),
            parse_mode="HTML"
        )

    elif query.data == "refresh":
        db_user = get_user(user.id)

        try:
            url = make_subscription(db_user)

            await query.message.reply_text(
                (
                    "🔄 <b>Подписка обновлена!</b>\n\n"
                    "Новые ноды уже находятся "
                    "в твоей GitHub-подписке."
                ),
                parse_mode="HTML",
                reply_markup=subscription_buttons(url)
            )

        except Exception as e:
            await query.message.reply_text(
                (
                    "❌ Ошибка обновления:\n"
                    f"<code>{str(e)}</code>"
                ),
                parse_mode="HTML"
            )

    elif query.data == "copy_info":
        await query.message.reply_text(
            (
                "📋 Telegram не позволяет боту "
                "напрямую положить ссылку в буфер обмена.\n\n"
                "Зажми ссылку в предыдущем сообщении "
                "и выбери «Копировать»."
            ),
            parse_mode="HTML"
        )

    elif query.data == "help":
        await query.message.reply_text(
            (
                "❓ <b>Как пользоваться</b>\n\n"
                "1️⃣ Нажми «Моя подписка».\n"
                "2️⃣ Открой ссылку подписки.\n"
                "3️⃣ Добавь её в Happ.\n"
                "4️⃣ Выбери сервер.\n"
                "5️⃣ Подключись.\n\n"
                "🔄 При изменении nodes.txt нажми "
                "«Обновить подписку»."
            ),
            parse_mode="HTML"
        )


def run():
    if not BOT_TOKEN:
        raise RuntimeError(
            "Не задан PEACH_BOT_TOKEN"
        )

    if not os.getenv("GITHUB_TOKEN"):
        raise RuntimeError(
            "Не задан GITHUB_TOKEN"
        )

    init_db()

    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )

    get_updates_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(get_updates_request)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(button)
    )

    print("🍑 PeachVPN Bot 1.3 запущен")
    print("📦 GitHub subscription mode: ON")
    print("🌐 Telegram timeout: 30 seconds")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    run()
