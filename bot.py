import os

import random

import threading

import subprocess

import telebot

from effects import FFMPEG_PATH, prepare_slowed_audio, get_media_duration, analyze_music_beats, generate_150_fx

 

# Вставьте сюда токен вашего бота от @BotFather

BOT_TOKEN = "9174803226:AAH4d-aHWVTFZdcGoXIUD0GfxCLmUvXW4hk"

 

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

data_lock = threading.Lock()

 

@bot.message_handler(commands=['start', 'clear'])

def send_welcome(message):

    with data_lock:

        user_data[message.chat.id] = {'media': [], 'audio': None}

    bot.reply_to(

        message,

        "🎬 Умный монтажер эдитов (Видео + Фото + Музыка) готов!\n"

        "∙ Видит ВСЕ фотки и видео (даже если кинуть альбомом по 10 штук)\n"

        "∙ Вырезает исходный звук из видео и делает Slow-Mo\n"

        "∙ Делает мощный эдит до 25 секунд с 1000+ эффектами под басы\n\n"

        "Скидывай сколько угодно фото/видео, затем трек и жми /make\n"

        "(Очистить список файлов: /clear)"

    )

 

@bot.message_handler(content_types=['photo'])

def handle_photo(message):

    chat_id = message.chat.id

    file_info = bot.get_file(message.photo[-1].file_id)

    downloaded = bot.download_file(file_info.file_path)

   

    os.makedirs(f"temp_{chat_id}", exist_ok=True)

    # Используем уникальный message_id, чтобы файлы из альбома не перезаписывали друг друга

    path = f"temp_{chat_id}/photo_{message.message_id}_{random.randint(100,999)}.jpg"

    with open(path, 'wb') as f:

        f.write(downloaded)

       

    with data_lock:

        user_data.setdefault(chat_id, {'media': [], 'audio': None})

        user_data[chat_id]['media'].append(('photo', path))

 

@bot.message_handler(content_types=['video', 'animation'])

def handle_video(message):

    chat_id = message.chat.id

    vid = message.video or message.animation

    if vid.file_size and vid.file_size > 20 * 1024 * 1024:

        bot.reply_to(message, "⚠️ Это видео тяжелее 20 МБ, скинь отрезок покороче!")

        return

       

    file_info = bot.get_file(vid.file_id)

    downloaded = bot.download_file(file_info.file_path)

   

    os.makedirs(f"temp_{chat_id}", exist_ok=True)

    path = f"temp_{chat_id}/video_{message.message_id}_{random.randint(100,999)}.mp4"

    with open(path, 'wb') as f:

        f.write(downloaded)

       

    with data_lock:

        user_data.setdefault(chat_id, {'media': [], 'audio': None})

        user_data[chat_id]['media'].append(('video', path))

        total = len(user_data[chat_id]['media'])

    bot.reply_to(message, f"🎞 Видео принято! Всего файлов в очереди: {total}")

 

@bot.message_handler(content_types=['audio', 'voice'])

def handle_audio(message):

    chat_id = message.chat.id

    file_id = message.audio.file_id if message.audio else message.voice.file_id

    file_info = bot.get_file(file_id)

    downloaded = bot.download_file(file_info.file_path)

   

    os.makedirs(f"temp_{chat_id}", exist_ok=True)

    path = f"temp_{chat_id}/raw_music.mp3"

    with open(path, 'wb') as f:

        f.write(downloaded)

       

    with data_lock:

        user_data.setdefault(chat_id, {'media': [], 'audio': None})

        user_data[chat_id]['audio'] = path

        total = len(user_data[chat_id]['media'])

    bot.reply_to(message, f"🎵 Музыка загружена! Загружено фото/видео: {total} шт.\nЖми /make для сборки эдита до 25 сек!")

 

@bot.message_handler(commands=['make'])

def make_edit(message):

    chat_id = message.chat.id

    with data_lock:

        data = user_data.get(chat_id)

        if not data or len(data['media']) < 2 or not data['audio']:

            bot.reply_to(message, "❌ Скинь минимум 2 файла (видео или фото) и 1 трек!")

            return

        media_list = list(data['media'])

        audio_in = data['audio']

 

    msg = bot.reply_to(message, f"🧠 Взял в работу {len(media_list)} файлов! Анализирую басы, убираю звук из видео и собираю эдит на ~25 сек (подожди 40-70 сек)...")

    folder = f"temp_{chat_id}"

    slowed_audio, output_video = f"{folder}/slowed.mp3", f"{folder}/edit.mp4"

   

    try:

        prepare_slowed_audio(audio_in, slowed_audio)

        start_time, durations, intensities = analyze_music_beats(slowed_audio, target_duration=25.0)

        video_durations = {p: get_media_duration(p) for t, p in media_list if t == 'video'}

        clip_files = []

       

        for i, (dur, intensity) in enumerate(zip(durations, intensities)):

            m_type, m_path = media_list[i % len(media_list)]

            clip_out = f"{folder}/clip_{i:03d}.mp4"

            frames = int(dur * 30)

           

            if m_type == 'video':

                vf = generate_150_fx(frames, intensity, is_video=True)

                max_off = max(0.0, video_durations.get(m_path, 3.0) - dur - 0.2)

                off = round(random.uniform(0.0, max_off), 2) if max_off > 0 else 0.0

                cmd = [FFMPEG_PATH, "-y", "-ss", str(off), "-i", m_path, "-an", "-vf", vf, "-r", "30", "-t", str(dur), "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", clip_out]

            else:

                vf = generate_150_fx(frames, intensity, is_video=False)

                cmd = [FFMPEG_PATH, "-y", "-loop", "1", "-i", m_path, "-vf", vf, "-t", str(dur), "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", clip_out]

               

            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            clip_files.append(clip_out)

           

        list_file = f"{folder}/clips.txt"

        with open(list_file, "w") as f:

            for c in clip_files:

                f.write(f"file '{os.path.basename(c)}'\n")

               

        cmd_concat = [FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-ss", str(start_time), "-i", slowed_audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(sum(durations)), output_video]

        subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

       

        with open(output_video, 'rb') as video:

            bot.send_video(chat_id, video, caption=f"🔥 25-секундный эдит из {len(media_list)} файлов готов!")

        bot.delete_message(chat_id, msg.message_id)

    except Exception as e:

        bot.reply_to(message, f"Ошибка при монтаже: {e}")

    finally:

        if os.path.exists(folder):

            for f in os.listdir(folder):

                os.remove(os.path.join(folder, f))

            os.rmdir(folder)

        with data_lock:

            user_data[chat_id] = {'media': [], 'audio': None}

 

bot.polling(none_stop=True)
