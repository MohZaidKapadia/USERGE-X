"Imprisoning this sticker...",
    "Mr.Steal Your Sticker is stealing this sticker... ",
    "Udhar Dekho Sir... Mujhe apka sticker churane dijiye 😁😁",
    "Dekho pikachu hai vaha..",
    "Please gussa mat hoiye sticker chori kar raha hu",
    "Aree upar dekho!!! UFO ",
    "Ye Sticker Tu muje dede😠",
)


# Based on:
# https://github.com/AnimeKaizoku/SaitamaRobot/blob/10291ba0fc27f920e00f49bc61fcd52af0808e14/SaitamaRobot/modules/stickers.py#L42
@userge.on_cmd(
    "sticker",
    about={
        "header": "Search Sticker Packs",
        "usage": "Reply {tr}sticker or " "{tr}sticker text]",
    },
)
async def sticker_search(message: Message):
    # search sticker packs
    reply = message.reply_to_message
    query_ = None
    if message.input_str:
        query_ = message.input_str
    elif reply and reply.from_user:
        query_ = reply.from_user.username or reply.from_user.id

    if not query_:
        return message.err(
            "reply to a user or provide text to search sticker packs", del_in=3
        )

    await message.edit(f'🔎 Searching for sticker packs for "{query_}"...')
    titlex = f'<b>Sticker Packs For:</b> "<u>{query_}</u>"\n'
    sticker_pack = ""
    try:
        text = await get_response.text(
            f"https://combot.org/telegram/stickers?q={query_}"
        )
    except ValueError:
        return await message.err(
            "Response was not 200!, Api is having some issues\n Please try again later.",
            del_in=5,
        )
    soup = bs(text, "lxml")
    results = soup.find_all("div", {"class": "sticker-pack__header"})
    for pack in results:
        if pack.button:
            title_ = (pack.find("div", {"class": "sticker-pack__title"})).text
            link_ = (pack.a).get("href")
            sticker_pack += f"\n• [{title_}"
    if not sticker_pack:
        sticker_pack = "❌ Not Found!"
    await message.edit((titlex + sticker_pack), disable_web_page_preview=True)
