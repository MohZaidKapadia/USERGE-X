# Copyright (C) 2021 BY - GitHub.com/code-rgb [TG - @deleteduser420]
# All rights reserved.

"""Module that handles Bot PM"""

import asyncio
from datetime import date, datetime, timedelta
from re import compile as comp_regex
from typing import Union

from pyrogram import filters
from pyrogram.errors import BadRequest
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    User,
)

from userge import Config, Message, get_collection, userge
from userge.utils import check_owner, get_file_id

# Loggers
CHANNEL = userge.getCLogger(__name__)
LOGGER = userge.getLogger(__name__)
# User Checks
BOT_BAN = get_collection("BOT_BAN")
BOT_START = get_collection("BOT_START")
# Caches
_BOT_PM_MEDIA = None
_CACHED_INFO = {}
# Regex
TG_LINK_REGEX = comp_regex(r"http[s]?://[\w.]+/(?:[c|s]/)?(\w+)/([0-9]+)")


if userge.has_bot:

    async def _init() -> None:
        await get_bot_pm_media()

    async def get_bot_pm_media() -> None:
        global _BOT_PM_MEDIA
        if not Config.BOT_MEDIA:
            _BOT_PM_MEDIA = get_file_id(await userge.bot.get_messages("useless_x", 2))
        elif Config.BOT_MEDIA.strip().lower() != "false":
            match = TG_LINK_REGEX.search(Config.BOT_MEDIA)
            if match:
                from_chat = str(match.group(1))
                if from_chat.isdigit():
                    from_chat = int("-100" + from_chat)
                from_chat_msg = match.group(2)
                try:
                    bot_m_fid = get_file_id(
                        await userge.bot.get_messages(from_chat, from_chat_msg)
                    )
                except Exception as b_m_err:
                    LOGGER.error(b_m_err)
                else:
                    _BOT_PM_MEDIA = bot_m_fid

    async def get_bot_info():
        """ Caching Owner and bot info """
        global _CACHED_INFO
        t_now = datetime.now()
        if not (_CACHED_INFO and _CACHED_INFO["time"] > datetime.timestamp(t_now)):
            _CACHED_INFO["owner"]
            try:
                owner_info = await userge.bot.get_user_dict(
                    Config.OWNER_ID[0], attr_dict=True
                )
            except (BadRequest, IndexError):
                _CACHED_INFO["owner"] = Config.OWNER_ID[0]
                LOGGER.debug(
                    "Coudn't get Info about User in OWNER_ID !\n"
                    "Try /start in bot or check OWNER_ID var"
                )
            else:
                _CACHED_INFO["owner"] = owner_info
                _CACHED_INFO["bot"] = await userge.bot.get_user_dict(
                    "me", attr_dict=True
                )
                _CACHED_INFO["time"] = int(
                    datetime.timestamp(t_now + timedelta(days=1))
                )
        return _CACHED_INFO

    async def send_bot_media(
        message: Message, text: str, markup: InlineKeyboardMarkup
    ) -> None:
        if Config.BOT_MEDIA.strip().lower() == "false":
            await message.reply(
                text, disable_web_page_preview=True, reply_markup=markup
            )
        else:
            if not _BOT_PM_MEDIA:
                await get_bot_pm_media()
            await message.reply_cached_media(
                file_id=_BOT_PM_MEDIA, caption=text, reply_markup=markup
            )

    async def check_new_bot_user(user: Union[int, str, User]) -> bool:
        user_ = await userge.bot.get_user_dict(user, attr_dict=True)
        found = await BOT_START.find_one({"user_id": user_.id})
        if not found:
            start_date = str(date.today().strftime("%B %d, %Y")).replace(",", "")
            log_msg = (
                f"A <b>New User</b> Started your Bot \n\n• <i>ID</i>: <code>{user_.id}</code>\n"
                f"  👤 : {'@' + user_.uname if user_.uname else user_.mention}"
            )
            await asyncio.gather(
                BOT_START.insert_one(
                    {"firstname": user_.flname, "user_id": user_.id, "date": start_date}
                ),
                CHANNEL.log(log_msg),
            )
        return bool(found)

    @userge.bot.on_message(filters.private & filters.regex(pattern=r"^/start$"))
    async def start_bot(_, message: Message):
        c_info = await get_bot_info()
        from_user = await userge.bot.get_user_dict(message.from_user, attr_dict=True)
        if not (from_user.id in Config.OWNER_ID or from_user.id in Config.SUDO_USERS):
            if await BOT_BAN.find_one({"user_id": from_user.id}):
                LOGGER.info(f"Banned UserID: {from_user.id} ignored from bot.")
                return
        start_msg = f"""
    Hello {from_user.mention},
    Nice To Meet You! I'm <b>{c_info.bot.flname}</b> A Bot.

        <b><i>Powered by</i> <a href='https://t.me/x_xtests'>USERGE-X</a>

    My Master is: {c_info.master.flname}</b>
    <i>You can contact my <b>Master</b> and checkout the <b>Repo</b> For more info.</i>
    """
        if Config.BOT_FORWARDS:
            start_msg += (
                "\n<b>NOTE: "
                "Bot Forwarding is</b> :  ☑️ `Enabled`\n"
                "All your messages here will be forwarded to my <b>MASTER</b>"
            )
        contact_url = (
            f"https://t.me/{c_info.owner.uname}"
            if c_info.owner.uname
            else f"tg://user?id={c_info.owner.id}"
        )
        btns = [
            [
                InlineKeyboardButton("👋  CONTACT", url=contact_url),
                InlineKeyboardButton("⚡️  REPO", url=Config.UPSTREAM_REPO),
            ],
        ]
        if from_user.id in Config.OWNER_ID:
            btns += [InlineKeyboardButton("➕ ADD TO GROUP", callback_data="add_to_grp")]
        try:
            await send_bot_media(message, start_msg, InlineKeyboardMarkup(btns))
        except FloodWait as e:
            await asyncio.sleep(e.x + 10)
        except Exception as bpm_e:
            await CHANNEL.log(
                f"**ERROR**: {str(bpm_e)}\n\nFatal Error occured while sending Bot Pm Media"
            )
        await check_bot_user(from_user)

    @check_owner
    @userge.bot.on_callback_query(filters.regex(pattern=r"^add_to_grp$"))
    async def add_to_grp(c_q: CallbackQuery):
        await c_q.answer()
        msg = "<b>🤖 Add Your Bot to Group</b> \n\n <u>Note:</u>  <i>Admin Privilege Required !</i>"
        add_bot = f"http://t.me/{(await get_bot_info()).bot.uname}?startgroup=start"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("➕ PRESS TO ADD", url=add_bot)]]
        )
        await c_q.edit_message_text(msg, reply_markup=buttons)


@userge.on_cmd(
    "bot_users",
    about={
        "header": "Get a list Active Users Who started your Bot",
        "examples": "{tr}bot_users",
    },
    allow_channels=False,
)
async def bot_users_(message: Message):
    """Users Who Stated Your Bot by - /start"""
    msg = ""
    async for c in BOT_START.find():
        msg += (
            f"• <i>ID:</i> <code>{c['user_id']}</code>\n   "
            f"<b>Name:</b> {c['firstname']},  <b>Date:</b> `{c['date']}`\n"
        )
    await message.edit_or_send_as_file(
        f"<u><i><b>Bot PM Userlist</b></i></u>\n\n{msg}"
        if msg
        else "`Nobody Does it Better`"
    )
