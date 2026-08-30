import os
import json
import re
import requests
import asyncio
from telegram import Bot

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = "@hghjgfhjg"

# GameBanana ID الخاص بـ Friday Night Funkin'
GAME_ID = 8694

POSTED_FILE = "posted.json"
MAX_POSTS = 15


def load_posted():
    if not os.path.exists(POSTED_FILE):
        return set()

    try:
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_posted(posted):
    # نحتفظ بآخر 1000 مود فقط
    data = list(posted)[-1000:]

    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_new_mod_ids():
    url = "https://api.gamebanana.com/Core/List/New"

    params = {
        "page": 1,
        "itemtype": "Mod",
        "gameid": GAME_ID,
        "max_age": 604800,
        "format": "json"
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    data = r.json()

    result = []

    for item in data:
        if isinstance(item, list) and len(item) >= 2:
            item_type = str(item[0])
            item_id = str(item[1])

            if item_type.lower() == "mod":
                result.append(item_id)

    return result


def get_mod_data(mod_id):
    url = "https://api.gamebanana.com/Core/Item/Data"

    fields = (
        "name,"
        "description,"
        "text,"
        "Files().aFiles(),"
        "Url().sDownloadUrl(),"
        "Preview().sStructuredDataFullsizeUrl(),"
        "Preview().sSubFeedImageUrl(),"
        "Game().name,"
        "Category().name,"
        "date,"
        "udate"
    )

    params = {
        "itemtype": "Mod",
        "itemid": mod_id,
        "fields": fields,
        "return_keys": "1",
        "format": "json"
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    return r.json()


def find_value(obj, names):
    """البحث عن قيمة داخل بيانات GameBanana مهما كان شكلها."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_low = str(key).lower()

            for name in names:
                if name.lower() in key_low:
                    if isinstance(value, (str, int, float)):
                        return value

            found = find_value(value, names)
            if found is not None:
                return found

    elif isinstance(obj, list):
        for value in obj:
            found = find_value(value, names)
            if found is not None:
                return found

    return None


def get_text(data):
    parts = []

    for key in ["description", "text", "name"]:
        value = data.get(key)

        if isinstance(value, str):
            parts.append(value)

    # لو البيانات رجعت بشكل مختلف
    if not parts:
        value = find_value(data, ["description", "text"])
        if value:
            parts.append(str(value))

    return " ".join(parts)


def detect_engine(text):
    text = text.lower()

    engines = []

    checks = [
        ("V-Slice", ["v-slice", "v slice", "vslice"]),
        ("Psych Engine", ["psych engine", "psychengine"]),
        ("P-Slice", ["p-slice", "p slice", "pslice"]),
        ("Codename Engine", ["codename engine", "codename"]),
        ("Kade Engine", ["kade engine", "kadeengine"]),
        ("NovaFNF", ["novafnf", "nova fnf"]),
        ("Leather Engine", ["leather engine"]),
        ("Forever Engine", ["forever engine"])
    ]

    for engine, keywords in checks:
        if any(keyword in text for keyword in keywords):
            engines.append(engine)

    if not engines:
        return "غير محدد"

    return " + ".join(engines)


def detect_version(text):
    # نتجنب اعتبار V-Slice رقم إصدار
    patterns = [
        r"(?:version|ver\.?|الإصدار)\s*[:\-]?\s*v?(\d+(?:\.\d+){0,3})",
        r"\bv(\d+\.\d+(?:\.\d+)?)\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(1)

    return "غير محدد"


def find_size(data):
    value = find_value(
        data,
        [
            "filesize",
            "size_bytes",
            "sizebytes",
            "nsize",
            "size"
        ]
    )

    if isinstance(value, (int, float)):
        mb = value / (1024 * 1024)

        if mb >= 0.01:
            return f"{mb:.2f} MB"

    return "غير محدد"


def find_image(data):
    for key in [
        "Preview().sStructuredDataFullsizeUrl()",
        "Preview().sSubFeedImageUrl()"
    ]:
        value = data.get(key)

        if isinstance(value, str) and value.startswith("http"):
            return value

    value = find_value(data, ["fullsizeurl", "subfeedimageurl"])

    if isinstance(value, str) and value.startswith("http"):
        return value

    return ""


def find_download(data):
    value = find_value(
        data,
        [
            "sdownloadurl",
            "downloadurl"
        ]
    )

    if isinstance(value, str) and value.startswith("http"):
        return value

    return ""


def create_message(mod_id, data):
    name = data.get("name")

    if not name:
        name = find_value(data, ["name"]) or f"FNF Mod #{mod_id}"

    description = get_text(data)

    # نستخدم الوصف لاكتشاف المحرك والإصدار
    engine = detect_engine(description)
    version = detect_version(description)

    size = find_size(data)

    download_url = find_download(data)

    page_url = f"https://gamebanana.com/mods/{mod_id}"

    text = (
        "🎮 <b>مود FNF جديد!</b>\n\n"
        f"📦 <b>اسم المود:</b> {name}\n"
        f"🔧 <b>المحرك:</b> {engine}\n"
        f"💻 <b>المنصة:</b> PC\n"
        f"🔢 <b>الإصدار:</b> {version}\n"
        f"📏 <b>الحجم:</b> {size}\n\n"
        f"🔗 <a href=\"{page_url}\">صفحة المود على GameBanana</a>"
    )

    if download_url:
        text += f'\n⬇️ <a href="{download_url}">تحميل المود</a>'

    text += "\n\n🧁 <b>Gummy Mods | FNF</b>"

    return text, find_image(data)


async def main():
    posted = load_posted()

    mod_ids = get_new_mod_ids()

    # الأحدث أولًا
    new_mods = [
        mod_id for mod_id in mod_ids
        if mod_id not in posted
    ]

    # بحد أقصى 15 مود في كل تشغيل
    new_mods = new_mods[:MAX_POSTS]

    print(f"وجدت {len(new_mods)} مود جديد.")

    if not new_mods:
        print("لا توجد مودات جديدة للنشر.")
        return

    bot = Bot(TOKEN)

    for mod_id in new_mods:

        try:
            data = get_mod_data(mod_id)

            text, image = create_message(mod_id, data)

            if image:
                await bot.send_photo(
                    chat_id=CHANNEL,
                    photo=image,
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=CHANNEL,
                    text=text,
                    parse_mode="HTML"
                )

            posted.add(mod_id)

            print(f"✅ تم نشر المود: {mod_id}")

            # فاصل بسيط بين المنشورات
            await asyncio.sleep(3)

        except Exception as e:
            print(f"❌ خطأ في المود {mod_id}: {e}")

    save_posted(posted)

    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
