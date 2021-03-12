from random import randint, sample
from typing import List, Optional, Union

from pyrogram.errors import PeerIdInvalid, Forbidden
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.messages import GetFullChat
from pyrogram.raw.functions.phone import (
    CreateGroupCall,
    DiscardGroupCall,
    InviteToGroupCall,
)
from pyrogram.raw.types import (
    InputGroupCall,
    InputPeerChannel,
    InputPeerChat,
    InputPeerUser,
)

from userge import Message, userge


@userge.on_cmd(
    "startvc",
    about={
        "header": "Create a voice chat",
        "examples": "{tr}startvc",
    },
    allow_channels=False,
    allow_private=False,
    allow_via_bot=False,
    only_admins=True,
)
async def start_vc_(message: Message):
    chat_id = message.chat.id
    await userge.send(
        CreateGroupCall(
            peer=(await userge.resolve_peer(chat_id)),
            random_id=randint(10000, 999999999),
        )
    )
    await message.edit(
        f"Started Voice Chat in **Chat ID** : `{chat_id}`", del_in=5, log=__name__
    )


@userge.on_cmd(
    "endvc",
    about={
        "header": "End a voice chat",
        "examples": "{tr}endvc",
    },
    allow_channels=False,
    allow_private=False,
    allow_via_bot=False,
    only_admins=True,
)
async def end_vc_(message: Message):
    chat_id = message.chat.id
    group_call = await get_group_call(chat_id)
    if not group_call:
        await message.edit("**No Voice Chat Found** !, Voice Chat already ended", del_in=8)
        return
    await userge.send(DiscardGroupCall(call=group_call))
    await message.edit(
        f"Ended Voice Chat in **Chat ID** : `{chat_id}`", del_in=5, log=__name__
    )


@userge.on_cmd(
    "invvc",
    about={
        "header": "Invite to a voice chat",
        "examples": "{tr}invvc",
        "flags": {"-l": "randomly invite members"},
    },
    allow_channels=False,
    allow_private=False,
    allow_via_bot=False,
)
async def inv_vc_(message: Message):
    peer_list = None
    reply = message.reply_to_message
    limit_ = int(message.flags.get("-l", 0))
    await message.edit("`Inviting Members to Voice Chat ...`")
    if limit_ != 0:
        peer_list = (
            await get_peer_list(message, limit_)
            if limit_ > 0
            else await get_peer_list(message)
        )
    elif message.input_str:
        if "," in message.input_str:
            peer_list = await append_peer_user(
                [_.strip() for _ in message.input_str.split(",")]
            )
        else:
            peer_list = await append_peer_user([message.input_str.split()[0]])
    elif reply and reply.from_user and not reply.from_user.is_bot:
        peer_list = await append_peer_user([reply.from_user.id])
    if not peer_list:
        return
    group_call = await get_group_call(message.chat.id)
    if not group_call:
        await message.edit("**No Voice Chat Found** !, first start by .startvc", del_in=8)
        return
    try:
        await userge.send(
            InviteToGroupCall(call=group_call, users=peer_list)
        )
    except Forbidden:
        await message.err("Join Voice Chat First !", del_in=8)
    else:
        await message.edit("✅ Invited Successfully !", del_in=5)


async def get_group_call(chat_id: Union[int, str]) -> Optional[InputGroupCall]:
    chat_peer = await userge.resolve_peer(chat_id)
    if not isinstance(chat_peer, (InputPeerChannel, InputPeerChat)):
        return
    if isinstance(chat_peer, InputPeerChannel):
        full_chat = (await userge.send(GetFullChannel(channel=chat_peer))).full_chat
    elif isinstance(chat_peer, InputPeerChat):
        full_chat = (
            await userge.send(GetFullChat(chat_id=chat_peer.chat_id))
        ).full_chat
    if full_chat is not None:
        return full_chat.call


async def get_peer_list(message: Message, limit: int = 10) -> Optional[List]:
    chat_id = message.chat.id
    user_ids = [
        member.user.id
        async for member in userge.iter_chat_members(chat_id, limit=100)
        if not (
            member.user.is_bot
            or member.user.is_deleted
            or member.user.id == message.from_user.id
        )
    ]
    return await append_peer_user(user_ids, limit)


async def append_peer_user(user_ids: List, limit: int = None) -> Optional[List]:
    peer_list = []
    for uid in user_ids:
        try:
            peer_ = await userge.resolve_peer(uid)
        except PeerIdInvalid:
            pass
        else:
            if isinstance(peer_, InputPeerUser):
                peer_list.append(peer_)
    if len(peer_list) != 0:
        return sample(peer_list, min(len(peer_list), limit)) if limit else peer_list
