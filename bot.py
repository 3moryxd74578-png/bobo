import os
import requests
import xml.etree.ElementTree as ET
from telegram import Bot

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = "@hghjgfhjg"

RSS_URL = (
    "https://api.gamebanana.com/Rss/New"
    "?gameid=8694&itemtype=Mod&perpage=50"
)

def get_mods():
    r = requests.get(RSS_URL, timeout=30)
    r.raise_for_status()

    root = ET.fromstring(r.content)
    mods = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "بدون اسم")
        link = item.findtext("link", "")
        image = item.findtext("image", "")

        if link:
            mods.append({
                "title": title.strip(),
                "link": link.strip(),
                "image": image.strip()
            })

    return mods


def main():
    bot = Bot(TOKEN)
    mods = get_mods()[:15]

    for mod in mods:
        text = (
            "🎮 <b>مود FNF جديد!</b>\n\n"
            f"📦 <b>اسم المود:</b> {mod['title']}\n"
            "🔧 <b>المحرك:</b> غير محدد\n"
            "💻 <b>المنصة:</b> PC\n"
            "🔢 <b>الإصدار:</b> غير محدد\n"
            "📏 <b>الحجم:</b> غير محدد\n\n"
            f"🔗 <a href=\"{mod['link']}\">صفحة المود على GameBanana</a>\n\n"
            "🧁 <b>Gummy Mods | FNF</b>"
        )

        try:
            if mod["image"]:
                bot.send_photo(
                    chat_id=CHANNEL,
                    photo=mod["image"],
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=CHANNEL,
                    text=text,
                    parse_mode="HTML"
                )

            print("تم نشر:", mod["title"])

        except Exception as e:
            print("خطأ:", e)


if __name__ == "__main__":
    main()
