from random import randint

from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import CreateGroupCall, DiscardGroupCall

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
            call=(
                await userge.send(
                    GetFullChannel(channel=(await userge.resolve_peer(message.chat.id)))
                )
            ).full_chat.call
        )
    )
