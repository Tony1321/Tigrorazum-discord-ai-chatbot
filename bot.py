import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import requests
from datetime import datetime, timezone

# ==========================
#  Настройка окружения
# ==========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL")

USERS_FILE = "users.json"
INSTRUCTIONS_FILE = "instructions.json"
MEMORY_FILE = "memory.json"
SERVER_PROMPTS_FILE = "server_prompts.json"
AUTHORIZED_USERS_FILE = "authorized_users.json"  # Новый файл для доверенных пользователей
VERSION_FILE = "version.txt"


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================
#  Базовые функции JSON
# ==========================
def load_json_file(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else {}

def save_json_file(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    else:
        return "unknown"

# ==========================
#  Память по серверам и пользователям
# ==========================
MEMORY_DIR = "server_memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

def get_server_memory_file(guild_id: int) -> str:
    return os.path.join(MEMORY_DIR, f"server_{guild_id}.json")

def load_server_memory(guild_id: int) -> dict:
    path = get_server_memory_file(guild_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_server_memory(guild_id: int, data: dict):
    path = get_server_memory_file(guild_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_recent_memory(guild_id: int, user_id: int, limit=5):
    data = load_server_memory(guild_id)
    memory = data.get(str(user_id), [])
    return memory[-limit:]

def update_memory(guild_id: int, user_id: int, user_prompt: str, bot_reply: str):
    data = load_server_memory(guild_id)
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = []
    data[user_id].append({"user": user_prompt, "bot": bot_reply})
    if len(data[user_id]) > 50:
        data[user_id] = data[user_id][-50:]
    save_server_memory(guild_id, data)

def forget_user_memory(guild_id: int, user_id: int):
    data = load_server_memory(guild_id)
    if str(user_id) in data:
        del data[str(user_id)]
        save_server_memory(guild_id, data)
        return True
    return False

# ==========================
#  Промпты серверов
# ==========================
def load_server_prompts():
    return load_json_file(SERVER_PROMPTS_FILE)

def save_server_prompts(data):
    save_json_file(data, SERVER_PROMPTS_FILE)

def get_server_prompt(guild_id):
    prompts = load_server_prompts()
    guild_data = prompts.get(str(guild_id), {})
    return guild_data.get("system_prompt", "")

def set_server_prompt(guild_id, prompt, updated_by="Unknown"):
    prompts = load_server_prompts()
    prompts[str(guild_id)] = {
        "system_prompt": prompt,
        "updated_by": updated_by,
        "updated_at": str(datetime.now(timezone.utc))
    }
    save_server_prompts(prompts)

# ==========================
#  Запрос к OpenRouter
# ==========================
def ask_ai(prompt, system_prompt="", user_instruction="", user_info=""):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [
        {"role": "system",
         "content": f"{system_prompt}\nИнструкция администратора: {user_instruction}\nИнформация о пользователе: {user_info}"},
        {"role": "user", "content": prompt}
    ]
    data = {
        "model": MODEL,
        "messages": messages
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Ошибка: {response.text}"

def extract_info_from_response(response):
    if "<info>" in response and "</info>" in response:
        start = response.find("<info>") + len("<info>")
        end = response.find("</info>")
        info_text = response[start:end].strip()
        try:
            return json.loads(info_text)
        except json.JSONDecodeError:
            return {}
    return {}

# ==========================
#  События
# ==========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    version = load_version()
    print(f"✅ Бот запущен как {bot.user} | Версия: {version}")


# ==========================
#  Команда !tigr
# ==========================
@bot.command(name="tigr", aliases=["t"])
async def tigr_command(ctx, *, prompt: str):
    users = load_json_file(USERS_FILE)
    user_id = str(ctx.author.id)
    user_name = ctx.author.display_name
    user_data = users.get(user_id, {})

    if not user_data:
        user_data = {
            "name": user_name,
            "joined_at": str(datetime.now(timezone.utc)),
            "instruction": "",
            "info": {}
        }

    user_instruction = user_data.get("instruction", "")
    user_info = json.dumps(user_data.get("info", {}), ensure_ascii=False)
    system_prompt = get_server_prompt(ctx.guild.id)

    memory_context = get_recent_memory(ctx.guild.id, user_id)
    memory_text = "\n".join([f"Пользователь: {m['user']}\nБот: {m['bot']}" for m in memory_context])

    try:
        reply = ask_ai(f"{memory_text}\n\nТекущий запрос: {prompt}", system_prompt, user_instruction, user_info)
        clean_reply = reply.split("<info>")[0].strip()
        await ctx.send(clean_reply)

        update_memory(ctx.guild.id, user_id, prompt, clean_reply)

        new_info = extract_info_from_response(reply)
        if new_info:
            user_data["info"].update(new_info)
            users[user_id] = user_data
            save_json_file(users, USERS_FILE)

    except Exception as e:
        await ctx.send(f"Произошла ошибка: {e}")

# ==========================
# ️ Установка инструкции пользователю
# ==========================
@bot.tree.command(name="set_instruction", description="Установить инструкцию для пользователя")
@app_commands.describe(user="Упомянутый пользователь", instruction="Инструкция для ИИ")
async def set_instruction(interaction: discord.Interaction, user: discord.User, instruction: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ У вас нет прав администратора.", ephemeral=True)
        return

    users = load_json_file(USERS_FILE)
    user_id = str(user.id)
    if user_id not in users:
        users[user_id] = {
            "name": user.display_name,
            "joined_at": str(datetime.now(timezone.utc)),
            "instruction": instruction,
            "info": {}
        }
    else:
        users[user_id]["instruction"] = instruction

    save_json_file(users, USERS_FILE)
    await interaction.response.send_message(f"✅ Инструкция для {user.name} обновлена.")

# ==========================
#  Установка серверного промпта
# ==========================
@bot.tree.command(name="set_server_prompt", description="Установить системный промпт для этого сервера")
@app_commands.describe(prompt="Новый системный промпт для сервера")
async def set_server_prompt_cmd(interaction: discord.Interaction, prompt: str):
    user = interaction.user

    # Проверяем права: админ или в списке авторизованных
    if not (user.guild_permissions.administrator or is_user_authorized(user.id)):
        await interaction.response.send_message("❌ У вас нет прав на изменение системного промпта.", ephemeral=True)
        return

    set_server_prompt(interaction.guild.id, prompt, user.display_name)
    await interaction.response.send_message("✅ Системный промпт для сервера успешно обновлён.")


# ==========================
#  Авторизованные пользователи
# ==========================
def load_authorized_users():
    data = load_json_file(AUTHORIZED_USERS_FILE)
    return data.get("users", [])

def save_authorized_users(user_list):
    save_json_file({"users": user_list}, AUTHORIZED_USERS_FILE)

def is_user_authorized(user_id):
    authorized = load_authorized_users()
    return str(user_id) in authorized

# ==========================
#  Добавление авторизованных пользователей
# ==========================
@bot.tree.command(name="add_authorized_user", description="Добавить пользователя, которому разрешено менять промпт")
@app_commands.describe(user="Пользователь, которому дать доступ")
async def add_authorized_user(interaction: discord.Interaction, user: discord.User):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Только администраторы могут выдавать права.", ephemeral=True)
        return

    authorized = load_authorized_users()
    if str(user.id) not in authorized:
        authorized.append(str(user.id))
        save_authorized_users(authorized)
        await interaction.response.send_message(f"✅ {user.display_name} теперь может изменять промпты.")
    else:
        await interaction.response.send_message("⚠ Этот пользователь уже имеет права.")

@bot.tree.command(name="remove_authorized_user", description="Убрать пользователя из списка разрешённых")
@app_commands.describe(user="Пользователь, у которого забрать доступ")
async def remove_authorized_user(interaction: discord.Interaction, user: discord.User):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Только администраторы могут убирать права.", ephemeral=True)
        return

    authorized = load_authorized_users()
    if str(user.id) in authorized:
        authorized.remove(str(user.id))
        save_authorized_users(authorized)
        await interaction.response.send_message(f"✅ {user.display_name} больше не может изменять промпты.")
    else:
        await interaction.response.send_message("⚠ Этого пользователя нет в списке.")

# ==========================
#  Очистка памяти (для админов и доверенных)
# ==========================

@bot.tree.command(name="forget", description="Очистить память пользователя или всего сервера")
@app_commands.describe(
    user="Пользователь, чью память нужно очистить (оставь пустым, чтобы стереть память всего сервера)"
)
async def forget_command(interaction: discord.Interaction, user: discord.User = None):
    executor = interaction.user
    guild_id = interaction.guild.id

    # Проверка прав: администратор или доверенный пользователь
    if not (executor.guild_permissions.administrator or is_user_authorized(executor.id)):
        await interaction.response.send_message("❌ У вас нет прав на использование этой команды.", ephemeral=True)
        return

    if user:  # очистка памяти конкретного пользователя
        if forget_user_memory(guild_id, user.id):
            await interaction.response.send_message(f"🧠 Память пользователя {user.display_name} успешно очищена.")
        else:
            await interaction.response.send_message("⚠ Память этого пользователя пуста или не найдена.")
    else:  # очистка всей памяти сервера
        path = get_server_memory_file(guild_id)
        if os.path.exists(path):
            os.remove(path)
            await interaction.response.send_message("💾 Вся память этого сервера полностью очищена.")
        else:
            await interaction.response.send_message("⚠ У этого сервера нет сохранённой памяти.")

# ==========================
#  Запуск бота
# ==========================
bot.run(TOKEN)