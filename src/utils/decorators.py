"""
Decorators for access control and other common functionality
"""
import logging

try:
    from pyrogram import Client, types, enums
except ImportError:
    from kurigram import Client, types, enums

from .access_control import check_full_user_access, get_access_denied_message


def private_use(func):
    """Decorator for message handlers with access control"""
    async def wrapper(client: Client, message: types.Message):
        chat_id = getattr(message.from_user, "id", None)

        # Only allow private chats for this bot now
        if message.chat.type != enums.ChatType.PRIVATE:
            logging.debug("Ignoring group/channel message: %s", message.text)
            return

        # Access control check
        if chat_id:
            try:
                access_result = await check_full_user_access(client, chat_id)
                if not access_result['has_access']:
                    denial_message = get_access_denied_message(access_result)
                    await message.reply_text(denial_message, quote=True)
                    logging.info(f"Access denied for user {chat_id}: {access_result['reason']}")
                    return
                
                # Log successful access
                logging.info(f"Access granted for user {chat_id}: {access_result['reason']}")
                
            except Exception as e:
                logging.error(f"Error checking access for user {chat_id}: {e}")
                await message.reply_text("❌ **Access Check Failed**\n\nThere was an error verifying your access. Please try again later.", quote=True)
                return

        return await func(client, message)

    return wrapper


def private_use_callback(func):
    """Decorator for callback query handlers with access control"""
    async def wrapper(client: Client, callback_query: types.CallbackQuery):
        chat_id = getattr(callback_query.from_user, "id", None)

        # Only allow private chats for this bot now
        if callback_query.message.chat.type != enums.ChatType.PRIVATE:
            logging.debug("Ignoring group/channel callback query")
            await callback_query.answer("❌ This bot only works in private chats", show_alert=True)
            return

        # Access control check
        if chat_id:
            try:
                access_result = await check_full_user_access(client, chat_id)
                if not access_result['has_access']:
                    denial_message = get_access_denied_message(access_result)
                    await callback_query.answer("❌ Access denied", show_alert=True)
                    logging.info(f"Access denied for user {chat_id}: {access_result['reason']}")
                    return
                
                # Log successful access
                logging.info(f"Access granted for user {chat_id}: {access_result['reason']}")
                
            except Exception as e:
                logging.error(f"Error checking access for user {chat_id}: {e}")
                await callback_query.answer("❌ Access check failed", show_alert=True)
                return

        return await func(client, callback_query)

    return wrapper
