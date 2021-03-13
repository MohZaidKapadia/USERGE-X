# Copyright (C) 2021 BY - GitHub.com/code-rgb [TG - @deleteduser420]
# All rights reserved.

"""Module that handles Bot PM"""

import asyncio
from collections import defaultdict
from datetime import date, datetime, timedelta
from re import compile as comp_regex
from typing import Optional, Union

from pyrogram import StopPropagation, filters
from pyrogram.errors import BadRequest, FloodWait, UserIsBlocked
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    User,
)

from userge import Config, Message, get_collection, pool, userge
from userge.utils import check_owner, get_file_id

from .bot_forwards import ban_from_bot_pm

# Load from DB
SAVED_SETTINGS = get_collection("CONFIGS")
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


class FloodConfig:
    BANNED_USERS = filters.user()
    USERS = defaultdict(list)
    MESSAGES = 3
    SECONDS = 6
    OWNER = filters.user(list(Config.OWNER_ID))
    ALERT = defaultdict(dict)


if userge.has_bot:

    async def _init() -> None:
        s_o = await SAVED_SETTINGS.find_one({"_id": "BOT_ANTIFLOOD"})
        if s_o:
            Config.BOT_ANTIFLOOD = s_o["data"]
        await get_bot_pm_media()
        await get_bot_info()

    async def get_bot_pm_media() -> None:
        global _BOT_PM_MEDIA
        if not Config.BOT_MEDIA:
            _BOT_PM_MEDIA = get_file_id(await userge.bot.get_messages("useless_x", 2))
            return
        if Config.BOT_MEDIA.strip().lower() != "false":
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
            finally:
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
        if Config.BOT_MEDIA and Config.BOT_MEDIA.strip().lower() == "false":
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
        if user_.id in Config.OWNER_ID or user_.id in Config.SUDO_USERS:
            found = True
        else:
            found = await BOT_START.find_one({"user_id": user_.id})
            if not found:
                start_date = str(date.today().strftime("%B %d, %Y")).replace(",", "")
                bot_start_msg = (
                    "A <b>New User</b> Started your Bot.\n"
                    f"  ┌─ ID: <code>{user_.id}</code>\n"
                    f"  ├─ Name: {user_.flname}\n"
                    f"  └─ 👤: {user_.mention}"
                )
                await asyncio.gather(
                    BOT_START.insert_one(
                        {
                            "firstname": user_.flname,
                            "user_id": user_.id,
                            "date": start_date,
                        }
                    ),
                    CHANNEL.log(bot_start_msg),
                )
        return not bool(found)

    def default_owner_start(from_user):
        start_msg = f"Hello Master **{from_user.flname}** !\n"
        btns = [
            [InlineKeyboardButton("➕  ADD TO GROUP", callback_data="add_to_grp")],
            
        ]
        return start_msg, btns

    @userge.bot.on_message(filters.private & filters.regex(pattern=f"(?i)^/start(@{_CACHED_INFO['bot'].uname})?([\s]+|$)"))
    async def start_bot(_, message: Message):
        c_info = await get_bot_info()
        bot_ = c_info.get("bot")
        owner_ = c_info.get("owner")
        from_user = await userge.bot.get_user_dict(message.from_user, attr_dict=True)
        if from_user.id in Config.OWNER_ID:
            start_msg, btns = default_owner_start(from_user)
        else:
            start_msg = f"""
👋  Hello {from_user.fname},
Nice To Meet You !, I'm <b>{bot_.fname}</b> A Bot.

        <b><i>Powered by</i> [USERGE-X](https://t.me/x_xtests)

My Master is : {owner_.flname}</b>
"""
            if Config.BOT_FORWARDS:
                start_msg += "<b>\n📌 NOTE:</b>\n  • You can 📨 <b>Send Message</b> here to contact my <b>Master.</b>"
            contact_url = (
                f"https://t.me/{owner_.uname}"
                if owner_.uname
                else f"tg://user?id={owner_.id}"
            )
            btns = [
                [
                    InlineKeyboardButton("👤  CONTACT", url=contact_url),
                    InlineKeyboardButton("⭐️  REPO", url=Config.UPSTREAM_REPO),
                ]
            ]
        try:
            await send_bot_media(message, start_msg, InlineKeyboardMarkup(btns))
        except FloodWait as e:
            await asyncio.sleep(e.x + 10)
        except Exception as bpm_e:
            await CHANNEL.log(
                f"**ERROR**: {str(bpm_e)}\n\nFatal Error occured while sending Bot Pm Media"
            )
        if not from_user.id in Config.OWNER_ID:
            await check_new_bot_user(message.from_user)


    @userge.bot.on_callback_query(filters.regex(pattern=r"^add_to_grp$"))
    @check_owner
    async def add_to_grp(c_q: CallbackQuery):
        await c_q.answer()
        msg = "<b>🤖 Add Your Bot to Group</b> \n\n <u>Note:</u>  <i>Admin Privilege Required !</i>"
        add_bot = f"http://t.me/{(await get_bot_info())['bot'].uname}?startgroup=start"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("➕ PRESS TO ADD", url=add_bot)],
            [InlineKeyboardButton("BACK", callback_data="back_bot_pm")]]
        )
        await c_q.edit_message_text(msg, reply_markup=buttons)

    @userge.bot.on_callback_query(filters.regex(pattern=r"^back_bot_pm$"))
    @check_owner
    async def back_bot_pm_(c_q: CallbackQuery):
        await c_q.answer()
        start_msg, btns = default_owner_start((await userge.bot.get_user_dict(c_q.from_user)))
        await c_q.edit_message_text(start_msg, reply_markup=InlineKeyboardMarkup(btns))
    
    
        ##############| USERGE-X Bot Antiflood |##############
    if Config.BOT_ANTIFLOOD:
        async def send_flood_alert(user_id: Union[int, User]) -> None:
            user_ = await userge.bot.get_user_dict(user_id, attr_dict=True)
            if user_.id in FloodConfig.BANNED_USERS:
                return
            if user_.id in FloodConfig.ALERT:
                flood_count = FloodConfig.ALERT[user_.id]["count"]
                if flood_count > 10:
                    if user_.id in Config.SUDO_USERS:
                        sudo_spam = (f"**Sudo User** {user_.mention}:\n  ID: {user_.id}\n\n"
                        "Is Flooding your bot !, Check `.help delsudo` to remove the user from Sudo.")
                        await userge.bot.send_message(
                            Config.LOG_CHANNEL_ID, sudo_spam
                        )
                        return
                    await ban_from_bot_pm(user_.id, "Automated Ban for Flooding bot [10 times]", log=__name__)
                    return
                else:
                    FloodConfig.ALERT[user_.id]["count"] = flood_count + 1
            else:
                flood_count = 1
                FloodConfig.ALERT[user_.id]["count"] = flood_count

            flood_msg = (
                r"⚠️ <b>\\#Flood_Warning//</b>"
                "\n\n"
                f"  ┌─ ID: <code>{user_.id}</code>\n"
                f"  ├─ Name: {user_.flname}\n"
                f"  └─ 👤: {user_.mention}"
                f"\n\n**Is spamming your bot !** ->  [ Flood Count **({flood_count})** ]\n"
                "__Quick Action__: Ignored from bot for a while."
            )
            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🚫  BAN", callback_data=f"bot_pm_ban_{user_.id}"
                        ),
                        InlineKeyboardButton(
                            "➖ Bot Antiflood [OFF]", callback_data=f"toggle_bot-antiflood_off"
                        ),
                    ]
                ]
            )
            if flood_count == 1:
                fa_msg = await userge.bot.send_message(
                    Config.LOG_CHANNEL_ID, flood_msg, reply_markup=buttons
                )
            else:
                fa_msg = await userge.bot.edit_message_text(
                    Config.LOG_CHANNEL_ID, FloodConfig.ALERT[user_.id]["fa_id"], flood_msg, reply_markup=buttons
                )
            FloodConfig.ALERT[user_.id]["fa_id"] = fa_msg.message_id
            try:
                await userge.bot.send_message(
                    Config.OWNER_ID[0], f"⚠️  [**Flood Notification**]({fa_msg.link})", disable_web_page_preview=True
                )
            except UserIsBlocked:
                await CHANNEL.log("**Unblock your bot !**")

        @userge.bot.on_callback_query(filters.regex(pattern=r"^bot_pm_ban_([0-9]+)"))
        @check_owner
        async def bot_pm_ban_cb(c_q: CallbackQuery):
            user_id = int(c_q.matches[0].group(1))
            await asyncio.gather(
                c_q.answer(f"Banning UserID -> {user_id} ...", show_alert=False),
                ban_from_bot_pm(user_id, "Spamming Bot", log=__name__),
                c_q.edit_message_text(f"✅ **Successfully Banned**  User ID: {user_id}"),
            )

        def time_now() -> Union[float, int]:
            return datetime.timestamp(datetime.now())

        @pool.run_in_thread
        def is_flood(uid: int) -> Optional[bool]:
            """Checks if a user is flooding"""
            FloodConfig.USERS[uid].append(time_now())
            if (
                len(
                    list(
                        filter(
                            lambda x: time_now() - int(x) < FloodConfig.SECONDS,
                            FloodConfig.USERS[uid],
                        )
                    )
                )
                > FloodConfig.MESSAGES
            ):
                FloodConfig.USERS[uid] = list(
                    filter(
                        lambda x: time_now() - int(x) < FloodConfig.SECONDS,
                        FloodConfig.USERS[uid],
                    )
                )
                return True

        @userge.bot.on_message(filters.private & ~FloodConfig.OWNER, group=-100)
        async def antif_on_msg(_, msg: Message):
            user_id = msg.from_user.id
            if await BOT_BAN.find_one({"user_id": user_id}):
                # LOGGER.info(
                #     r"<b>\\#Bot_PM//</b>" f"\n\nBanned UserID: {user_id} ignored from bot."
                # )
                await msg.stop_propagation()
            elif await is_flood(user_id):
                await send_flood_alert(msg.from_user)
                FloodConfig.BANNED_USERS.add(user_id)
                await msg.stop_propagation()
            elif user_id in FloodConfig.BANNED_USERS:
                FloodConfig.BANNED_USERS.remove(user_id)

        @userge.bot.on_callback_query(~FloodConfig.OWNER, group=-100)
        async def antif_on_cb(_, c_q: CallbackQuery):
            user_id = c_q.from_user.id
            if await BOT_BAN.find_one({"user_id": user_id}):
                await c_q.answer("You are banned from this bot !")
                # LOGGER.info(
                #     r"<b>\\#Callback//</b>"
                #     f"\n\nBanned UserID: {user_id} ignored from bot."
                # )
                raise StopPropagation
            elif await is_flood(user_id):
                await c_q.answer("Wooh, Mate Chill ! go slow")
                await send_flood_alert(c_q.from_user)
                FloodConfig.BANNED_USERS.add(user_id)
                raise StopPropagation
            elif user_id in FloodConfig.BANNED_USERS:
                FloodConfig.BANNED_USERS.remove(user_id)

        ########################################################

    @userge.bot.on_callback_query(filters.regex(pattern=r"^toggle_bot-antiflood_off$"))
    @check_owner
    async def settings_toggle(c_q: CallbackQuery):
        Config.BOT_ANTIFLOOD = False
        await asyncio.gather(
            c_q.answer(),
            SAVED_SETTINGS.update_one(
                {"_id": "BOT_ANTIFLOOD"}, {"$set": {"data": Config.BOT_ANTIFLOOD}}, upsert=True
            ),
            c_q.edit_message_text("BOT_ANTIFLOOD is now disabled !")
        )



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


@userge.on_cmd(
    "bot_antiflood",
    about={
        "header": "enable / disable Bot Antiflood",
        "description": "Get Notified if a user spams your bot and even autobans",
    },
    allow_channels=False,
)
async def bot_antiflood_(message: Message):
    """ enable / disable Bot Antiflood """
    if Config.BOT_ANTIFLOOD:
        Config.BOT_ANTIFLOOD = False
        await message.edit("`Bot Antiflood disabled !`", del_in=3)
    else:
        Config.BOT_ANTIFLOOD = True
        await message.edit("`Bot Antiflood enabled !`", del_in=3)
    await SAVED_SETTINGS.update_one(
        {"_id": "BOT_ANTIFLOOD"},
        {"$set": {"data": Config.BOT_ANTIFLOOD}},
        upsert=True,
    )