# Tigrorazum - Discord AI Chatbot
> Tigrorazum — это AI чатбот для Discord, который отвечает на сообщения пользователей с помощью модели OpenRouter, запоминает диалоги и позволяет настраивать поведение под сервер и конкретного пользователя.

# RU

## Что умеет бот

* Отвечает на сообщения AI с учётом истории диалогов.
* Хранит память пользователя и сервера (можно очищать).
* Позволяет задавать персональные инструкции для отдельных пользователей.
* Администраторы и доверенные пользователи могут менять системный промпт сервера.
* Управление доверенными пользователями для безопасного изменения промптов.

## Основные команды

### Чат с AI
```
!tigr <сообщение>
```
```
!t <сообщение>
```

### Персональная инструкция
```
/set_instruction user: <@user> instruction: <текст>
```

### Серверный промпт
```
/set_server_prompt prompt: <текст>
```

### Управление доверенными пользователями
```
/add_authorized_user user: <@user>
```
```
/remove_authorized_user user: <@user>
```

Очистка памяти
```
/forget [user: <@user>]
```

## Установка

### 1. Клонируйте репозиторий:

```
git clone <URL>
cd tigrorazum
```

### 2. Установите зависимости:

```
pip install -r requirements.txt
```

### 3. Создайте .env с токеном бота и ключом OpenRouter:

```
DISCORD_TOKEN=ваш_токен_бота
OPENROUTER_API_KEY=ваш_API_ключ
MODEL=название_модели
```

### 4. Запустите бота через ``` bot.bat ```

# EN

> Tigrorazum is an AI chatbot for Discord that responds to user messages using the OpenRouter model, remembers conversations, and allows customization for the server and individual users.

## Bot Capabilities

* Responds to messages using AI, taking conversation history into account.
* Stores user and server memory (can be cleared).
* Allows setting personal instructions for individual users.
* Administrators and trusted users can modify the server system prompt.
* Manage trusted users for safe prompt modifications.

## Main Commands

### Chat with AI
```
!tigr <message>
```
```
!t <message>
```

### Personal Instruction
```
/set_instruction user: <@user> instruction: <text>
```

### Server Prompt
```
/set_server_prompt prompt: <text>
```

### Manage Trusted Users
```
/add_authorized_user user: <@user>
```
```
/remove_authorized_user user: <@user>
```

### Clear Memory
```
/forget [user: <@user>]
```

## Installation

### 1. Clone the repository:
```
git clone <URL>
cd tigrorazum
```

### 2. Install dependencies:
```
pip install -r requirements.txt
```

### 3. Create a .env file with your bot token and OpenRouter key:
```
DISCORD_TOKEN=your_bot_token
OPENROUTER_API_KEY=your_API_key
MODEL=model_name
```

### 4. Run the bot using ``` bot.bat ```
