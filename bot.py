# -*- coding: utf-8 -*-

import asyncio
import os
import sqlite3
import random
import emoji
import base64
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import openai
import torch
import whisper
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters import Command
from aiogram.types import ParseMode
from aiogram.utils.markdown import hbold, hcode
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import Message

from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import filters

from aiogram.types import ParseMode, ReplyKeyboardRemove
from aiogram.utils.markdown import hbold, hcode, text

from aiogram.types import CallbackQuery

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.dispatcher import Dispatcher
from aiogram import types

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = ""
OPENAI_API_KEY = ""

openai.api_key = OPENAI_API_KEY

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

class Form(StatesGroup):
    sleep_quality = State()  # Will be represented in storage as 'Form:sleep_quality'
    hours_slept = State()  # Will be represented in storage as 'Form:hours_slept'
    bedtime = State()  # Will be represented in storage as 'Form:bedtime'
    wake_time = State()  # Will be represented in storage as 'Form:wake_time'
# Database functions
def create_connection():
    conn = sqlite3.connect('mindtalk.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    bot_response TEXT DEFAULT '')''')
    conn.commit()
    return conn


def save_message(conn, user_id, message, bot_response):
    c = conn.cursor()
    c.execute("INSERT INTO messages (user_id, message, bot_response) VALUES (?, ?, ?)", (user_id, message, bot_response))
    conn.commit()

...


def get_messages(conn, user_id):
    c = conn.cursor()
    c.execute("SELECT message FROM messages WHERE user_id=?", (user_id,))
    return c.fetchall()

def clear_journal(conn, user_id):
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE user_id=?", (user_id,))
    conn.commit()


# Analysis and response functions
async def analyze_journal(journal_text: str) -> str:
    model_engine = "text-davinci-003"
    max_tokens = 1024
    temperature = 0.3

    response = openai.Completion.create(
        engine=model_engine,
        prompt='Вы - умный журнал-терапевт по имени MindTalk. Проанализируйте мою запись в дневнике, дайте советы и рекомендации для улучшения самочувствия или решения проблем. Выводы представляйте в диалоговом формате. Анализируйте все области, зависящие от запроса пользователя. Запись для анализа: ' '\n' + journal_text + '\n Сделай выводы и давай рекомендации, используй смайлики в диалоге, если возможо так же добавь ключевые слова в фломате #ключевоеслово',
        max_tokens=max_tokens,
        temperature=temperature,
    )

    analysis = response.choices[0].text.strip()
    return analysis

async def analyze_sleep(prompt: str) -> str:
    model_engine = "text-davinci-002"
    max_tokens = 1024
    temperature = 0.5

    response = openai.Completion.create(
        engine=model_engine,
        prompt=prompt +'Предствь что ты специалист по сну. Твоя задача дать рекомендацию на основе моих данных. Данные в среднем за трое суток.',
        max_tokens=max_tokens,
        temperature=temperature,
    )

    analysis = response.choices[0].text.strip()
    recommendations = (analysis)

    return "\n".join(recommendations)

async def generate_openai_response(prompt: str) -> str:
    model_engine = "text-davinci-003"
    max_tokens = 1024
    temperature = 0.5

    response = openai.Completion.create(
        engine=model_engine,
        prompt='Вы - умный журнал-терапевт по имени MindTalk. Ведите себя как дружелюбный психотерапевт на отпуске. Помогите пользователям решать различные проблемы и вопросы, предоставляя расслабленные советы и рекомендации. Используйте случайные эмодзи в своих ответах для создания более увлекательного взаимодействия. Опирайтесь на предыдущие ответы пользователя и свои рекомендации, а также отслеживайте эмоциональное состояние пользователя на основе их сообщений.. Первое сообщение пользователя: ' + '\n' + prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    answerai = response.choices[0].text.strip()
    return answerai

# Command handlers
@dp.message_handler(Command("start"))
async def start_message(message: types.Message):
    await message.answer("👋 Я умный дневник MindTalk. Расскажите мне о своем дне, так же я могу проанализировать ваши записи и сделать выводы. Используйте команду /help, чтобы увидеть мои функции!")

@dp.message_handler(Command("help"))
async def help_command(message: types.Message):
    help_text = '''Я - MindTalk. Вот мои функции:
🚀 /start - Начать работу с ботом.
📊 /analyz - Проанализировать ваш дневник и дать рекомендации.
❓ /agenda - Напишу расспорядок дня и цели на основе ваших записей.
🗑️ /clear - удаления всех записей из дневника. 
💤 /sleep_analyz - получить рекомендации по улучшению качества сна на основе информации о вашем сне.
🎙️ Записивый голосовое сообщения чтобы не писать вручную!'''

    await message.answer(help_text)

@dp.message_handler(Command("analyz"))
async def analyze_journal_command(message: types.Message):
    # Get user's messages from the database
    user_id = message.from_user.id
    conn = create_connection()
    messages = get_messages(conn, user_id)
    journal_text = '\n'.join([m[0] for m in messages])

    # Analyze journal
    analysis = await analyze_journal(journal_text)

    # Send result to the user
    await message.answer(analysis)

@dp.message_handler(Command("sleep_analyz"))
async def sleep_analyze_command(message: types.Message):
    # Set state
    await Form.sleep_quality.set()

    # Запрашиваем информацию о сне у пользователя
    await message.answer("Я могу помочь вам анализировать ваш сон. Давайте начнем с ваших последних трех ночей. Как вы спали за это время? 🤔" + '\n' + "<Ответьте на это сообщение, для этого зажмите 'Cообщение' и выбирите функцию 'Ответить'>")
    

@dp.message_handler(state=Form.sleep_quality)
async def process_sleep_quality(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['sleep_quality'] = message.text

    await Form.next()
    await message.answer("По сколько часов в среднем вы спите каждый день?")


@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.hours_slept)
async def process_hours_slept_invalid(message: types.Message):
    """
    If hours slept is invalid
    """
    return await message.reply("Количество часов должно быть числом. Сколько часов вы проспали?")


@dp.message_handler(lambda message: message.text.isdigit(), state=Form.hours_slept)
async def process_hours_slept(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['hours_slept'] = message.text

    await Form.next()
    await message.answer("Во сколько вы ложитесь спать?(Укажите 24 часовом формате, например в 23:00)")


@dp.message_handler(state=Form.bedtime)
async def process_bedtime(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['bedtime'] = message.text

    await Form.next()
    await message.answer("Во сколько вы просыпаетесь?")


@dp.message_handler(state=Form.wake_time)
async def process_wake_time(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['wake_time'] = message.text

        # Combine all user data into a single string and send it to the model for analysis
        full_prompt = f"Как спалось: {data['sleep_quality']}\nСпал {data['hours_slept']} часов, лег спать в {data['bedtime']}, проснулся в {data['wake_time']}."
        sleep_analysis = await analyze_sleep(full_prompt)

        # Send the result back to the user
        await message.answer(sleep_analysis)

    # Finish conversation
    await state.finish()

@dp.message_handler(Command("clear"))
async def clear_command(message: types.Message):
    user_id = message.from_user.id
    conn = create_connection()
    clear_journal(conn, user_id)
    conn.close()
    await message.answer("🧹Ваш дневник был успешно очищен!")


@dp.message_handler(content_types=['voice'])
async def recognize_voice(message: types.Message):
    import whisper # import whisper module here
    import torch
    # download voice message
    voice_file_id = message.voice.file_id
    voice_file = await bot.get_file(voice_file_id)
    voice_file_path = voice_file.file_path
    await bot.download_file(voice_file_path,'voice.ogg')

    # recognize voice
    model = whisper.load_model('medium')
    audio = whisper.load_audio('voice.ogg')
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    options = whisper.DecodingOptions(language = 'ru')
    result = whisper.decode(model, mel, options)
    recognized_voice_text = result.text
    await message.answer(f'Ваш запрос выглядит так:{recognized_voice_text}')
    # Save user's message to the database
    conn = create_connection()
    save_message(conn, message.from_user.id ,result.text, None)
    conn.close()
    # Generate response
    response_voice_to_text = await generate_openai_response(result.text)
    # Send response to the user
    await message.answer(response_voice_to_text)


@dp.message_handler(content_types=['text'])
async def answer_message(message: types.Message):
    # Generate response
    response_text = await generate_openai_response(message.text)

    conn = create_connection()
    save_message(conn, message.from_user.id, message.text, response_text)
    conn.close()
    # Send response to the user
    await message.answer(response_text)

# Agenda and resources functions
async def recommend_resources(analysis: str) -> str:
    model_engine = "text-davinci-003"
    max_tokens = 1024
    temperature = 0.5

    response = openai.Completion.create(
        engine=model_engine,
        prompt='Представьте, что вы - умный журнал-терапевт по имени MindTalk, проанализируй мой дневник и дай рекомендации и выжимку.\n' + analysis,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    response_text = response.choices[0].text.strip()
    return response_text

async def generate_agenda(analysis) -> str:
    model_engine = "text-davinci-003"
    max_tokens = 1024
    temperature = 0.5

    response = openai.Completion.create(
        engine=model_engine,
        prompt='Представьте, что вы - умный журнал-терапевт по имени MindTalk, вот мой распорядок дня, цели и мысли' + analysis + '\n Пожалуйста, скажите мне мои цели и расписание на сегодня',
        max_tokens=max_tokens,
        temperature=temperature,
    )

    response_agenda = response.choices[0].text.strip()
    return response_agenda

@dp.message_handler(Command("agenda"))
async def agenda_command(message: types.Message):

    user_id = message.from_user.id
    conn = create_connection()
    messages = get_messages(conn, user_id)
    analysis = '\n'.join([m[0] for m in messages])
    agenda = await generate_agenda(analysis)
    await message.answer(agenda)


# Error handler
@dp.errors_handler(exception=Exception)
async def error_handler(update, exception):
    # Log the error
    if isinstance(exception, openai.error.InvalidRequestError):
        message = exception.args[0]['error']['message']
    else:
        message = str(exception)
    error_msg = f"Error handling the update {update}. \n{message}"
    print(error_msg)

    # Send error message to user
    await bot.send_message(chat_id=update.message.chat.id, text="Извините, что-то пошло не так. Пожалуйста, повторите попытку позже.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
