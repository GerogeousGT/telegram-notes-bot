from telegram import Update
from config import ADMIN_ID


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def check_admin_access(update: Update) -> bool:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "❌ Доступ запрещён. Этот бот доступен только администратору."
        )
        return False
    return True
