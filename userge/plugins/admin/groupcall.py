from random import randint, sample
from pyrogram.raw.types import InputGroupCall, InputPeerChannel, InputPeerChat, InputPeerUser
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import CreateGroupCall, DiscardGroupCall, InviteToGroupCall
from typing import Optional, Union, List
from userge import Message, userge
from pyrogram.errors import PeerIdInvalid
from pyrogram.raw.functions.messages import GetFullChat

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
    await userge.send(
        CreateGroupCall(
            peer=(await userge.resolve_peer(message.chat.id)),
            random_id=randint(10000, 999999999),
        )
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
    await userge.send(
        DiscardGroupCall(
            call=(await get_group_call(message.chat.id))
        )
    )

@userge.on_cmd(
    "invvc",
    about={
        "header": "Invite to a voice chat",
        "examples": "{tr}invvc",
        "flags" {"-l": "randomly invite members"}
    },
    allow_channels=False,
    allow_private=False,
    allow_via_bot=False
)
async def inv_vc_(message: Message):
    peer_list = None
    limit_ = message.flags.get("-l", 0)
    if limit_ != 0:
        peer_list = await get_peer_list(message.chat.id, limit_) if limit_ > 0 else await get_peer_list(message.chat.id)
    elif "," in message.input_str:
        peer_list = await append_peer_user([_.strip() for _ in message.input_str.split(",")])
    if not peer_list:
        return
    await userge.send(
        InviteToGroupCall(
            call=(await get_group_call(message.chat.id)),
            users=peer_list
        )
    )


async def get_group_call(chat_id: Union[int, str]) -> Optional[InputGroupCall]:
    chat_peer = await userge.resolve_peer(chat_id)
    if not isinstance(chat_peer, (InputPeerChannel, InputPeerChat)):
        return
    if isinstance(chat_peer, InputPeerChannel):
        full_chat = (await userge.send(GetFullChannel(
            channel=chat_peer
        ))).full_chat
    elif isinstance(chat_peer, InputPeerChat):
        full_chat = (await userge.send(GetFullChat(
            chat_id=chat_peer.chat_id
        ))).full_chat
    if full_chat is not None:
        return full_chat.call


async def get_peer_list(chat_id: Union[str, int], limit: int=10) -> Optional[List]:
    user_ids = [member.user.id async for member in userge.iter_chat_members(chat_id, limit=100) if not (member.user.is_bot or member.user.is_deleted or member.user.id == message.from_user.id)]
    return await append_peer_user(user_ids, limit)

async def append_peer_user(user_ids: List, limit: int) -> Optional[List]:
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

