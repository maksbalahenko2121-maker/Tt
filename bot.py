import os

import subprocess

import telebot

 

# Вставьте сюда токен вашего бота от @BotFather

BOT_TOKEN = "9174803226:AAH4d-aHWVTFZdcGoXIUD0GfxCLmUvXW4hk"

 

bot = telebot.TeleBot(BOT_TOKEN)

 

# Временное хранилище файлов пользователей

user_data = {}

 

@bot.message_handler(commands=['start'])

def send_welcome(message):

    user_data[message.chat.id] = {'photos': [], 'audio': None}

    bot.reply_to(

        message,

        "Привет! Скинь мне от 3 до 15 картинок (можно альбомом), а затем отправь аудиофайл (музыку).\n"

        "Когда всё загрузишь, нажми команду /make чтобы сделать эдит!"

    )

 

@bot.message_handler(content_types=['photo'])

def handle_photo(message):

    chat_id = message.chat.id

    if chat_id not in user_data:

        user_data[chat_id] = {'photos': [], 'audio': None}

   

    # Берем фото в самом лучшем качестве

    file_info = bot.get_file(message.photo[-1].file_id)

    downloaded_file = bot.download_file(file_info.file_path)

   

    os.makedirs(f"temp_{chat_id}", exist_ok=True)

    img_index = len(user_data[chat_id]['photos'])

    img_path = f"temp_{chat_id}/img_{img_index:03d}.jpg"

   

    with open(img_path, 'wb') as new_file:

        new_file.write(downloaded_file)

       

    user_data[chat_id]['photos'].append(img_path)

 

@bot.message_handler(content_types=['audio', 'voice'])

def handle_audio(message):

    chat_id = message.chat.id

    if chat_id not in user_data:

        user_data[chat_id] = {'photos': [], 'audio': None}

       

    file_id = message.audio.file_id if message.audio else message.voice.file_id

    file_info = bot.get_file(file_id)

    downloaded_file = bot.download_file(file_info.file_path)

   

    os.makedirs(f"temp_{chat_id}", exist_ok=True)

    audio_path = f"temp_{chat_id}/music.mp3"

   

    with open(audio_path, 'wb') as new_file:

        new_file.write(downloaded_file)

       

    user_data[chat_id]['audio'] = audio_path

    bot.reply_to(message, "🎵 Музыка загружена! Если картинки тоже скинуты, жми /make")

 

@bot.message_handler(commands=['make'])

def make_edit(message):

    chat_id = message.chat.id

    data = user_data.get(chat_id)

   

    if not data or len(data['photos']) < 2 or not data['audio']:

        bot.reply_to(message, "❌ Нужно скинуть минимум 2 картинки и 1 аудиофайл!")

        return

 

    msg = bot.reply_to(message, "⏳ Монтирую эдит, подожди 15-30 секунд...")

   

    folder = f"temp_{chat_id}"

    output_video = f"{folder}/edit.mp4"

   

    # Настройка длительности каждого кадра (например, 0.8 секунды на картинку для динамики)

    duration_per_img = 0.8

    total_duration = len(data['photos']) * duration_per_img

   

    # Формируем команду для FFmpeg: делаем размер 1080x1920, добавляем зум и накладываем музыку

    cmd = [

        "ffmpeg", "-y",

        "-framerate", str(1 / duration_per_img),

        "-i", f"{folder}/img_%03d.jpg",

        "-i", data['audio'],

        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.005,1.2)':d=25:s=1080x1920",

        "-c:v", "libx264",

        "-preset", "ultrafast",

        "-pix_fmt", "yuv420p",

        "-t", str(total_duration),

        "-shortest",

        output_video

    ]

   

    try:

        subprocess.run(cmd, check=True)

        with open(output_video, 'rb') as video:

            bot.send_video(chat_id, video, caption="🔥 Твой эдит готов!")

        bot.delete_message(chat_id, msg.message_id)

    except Exception as e:

        bot.reply_to(message, f"Ошибка при монтаже: {e}")

    finally:

        # Очищаем временные файлы, чтобы не забивать память хостинга

        for f in os.listdir(folder):

            os.remove(os.path.join(folder, f))

        os.rmdir(folder)

        user_data[chat_id] = {'photos': [], 'audio': None}

 

bot.polling(none_stop=True)
