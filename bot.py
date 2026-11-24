import os

import wave

import array

import random

import subprocess

import telebot

import imageio_ffmpeg

 

# Вставьте сюда токен вашего бота от @BotFather

BOT_TOKEN = "9174803226:AAH4d-aHWVTFZdcGoXIUD0GfxCLmUvXW4hk"

 

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

 

def prepare_slowed_audio(input_audio, output_audio):

    """Делает атмосферный Slowed + Reverb."""

    subprocess.run([

        FFMPEG_PATH, "-y", "-i", input_audio,

        "-af", "asetrate=44100*0.88,aresample=44100,aecho=0.8:0.88:60:0.4",

        output_audio

    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

 

def analyze_music_beats(audio_path, num_images):

    """Анализирует басы и находит дроп на чистом Python."""

    wav_path = audio_path + ".wav"

    subprocess.run([

        FFMPEG_PATH, "-y", "-i", audio_path,

        "-af", "lowpass=f=150",

        "-ac", "1", "-ar", "1000", wav_path

    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

   

    with wave.open(wav_path, 'rb') as wf:

        rate = wf.getframerate()

        n_frames = wf.getnframes()

        raw_bytes = wf.readframes(n_frames)

    os.remove(wav_path)

   

    samples = array.array('h', raw_bytes)

    step = int(rate * 0.05)

    energies = []

    for i in range(0, len(samples) - step, step):

        chunk = samples[i:i+step]

        energy = sum(abs(x) for x in chunk) / step

        energies.append(energy)

       

    if not energies:

        return 0.0, [0.75] * num_images, [0.5] * num_images

 

    max_e = max(energies) or 1.0

    threshold = max_e * 0.45

   

    peaks = []

    last_peak = -10

    for i in range(1, len(energies) - 1):

        if energies[i] > threshold and energies[i] >= energies[i-1] and energies[i] >= energies[i+1]:

            if i - last_peak >= 9:

                peaks.append((i * 0.05, energies[i]))

                last_peak = i

               

    if len(peaks) < num_images + 1:

        return 0.0, [0.75] * num_images, [0.6] * num_images

 

    best_idx = 0

    max_sum = -1

    for i in range(len(peaks) - num_images):

        s = sum(p for p in peaks[i : i + num_images])

        if s > max_sum:

            max_sum = s

            best_idx = i

           

    selected = peaks[best_idx : best_idx + num_images + 1]

    strengths = [p for p in selected[:-1]]

    min_s, max_s = min(strengths), max(strengths)

   

    if max_s > min_s:

        intensities = [(s - min_s) / (max_s - min_s) for s in strengths]

    else:

        intensities = [0.7] * num_images

       

    start_time = round(selected, 3)

    durations = []

    for i in range(num_images):

        dur = selected[i+1] - selected[i]

        dur = max(0.35, min(1.5, dur))

        durations.append(round(dur, 3))

       

    return start_time, durations, intensities

 

def build_music_synced_fx(frames, intensity):

    """Подбирает комбинацию из 20 эффектов строго под силу баса."""

    if intensity >= 0.75:

        motions = [

            ("1.4 - 0.4*(on/duration)", "iw/2-(iw/zoom/2)+if(lt(on,10),sin(on*3.5)*42,0)", "ih/2-(ih/zoom/2)+if(lt(on,10),cos(on*3.5)*42,0)"),

            ("1.0 + 0.35*(on/duration)", "iw/2-(iw/zoom/2)+sin(on*10)*15", "ih/2-(ih/zoom/2)+cos(on*10)*15"),

            ("1.35 - 0.25*(on/duration)", "iw/2-(iw/zoom/2) - 100*(1 - on/duration)", "ih/2-(ih/zoom/2)")

        ]

        flashes = ["fade=t=in:st=0:d=0.15:color=white", "negate=enable='lt(n,3)'", "eq=brightness='if(lt(mod(n,3),1),0.22,-0.05)'"]

        styles = [

            "rgbashift=rh=-16:bh=16:rv=8:bv=-8",

            "rgbashift=rh=-10:bh=10,eq=contrast=1.4:saturation=1.4",

            "tmix=frames=3:weights='1 3 1',rgbashift=rh=12:bh=-12"

        ]

    elif intensity >= 0.4:

        motions = [

            ("1.25 - 0.25*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),

            ("1.0 + 0.22*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),

            ("1.22", "iw/2-(iw/zoom/2) + 75*(1 - on/duration)", "ih/2-(iw/zoom/2)"),

            ("1.22", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2) - 75*(1 - on/duration)")

        ]

        flashes = ["fade=t=in:st=0:d=0.12:color=white", "fade=t=in:st=0:d=0.12:color=black"]

        styles = [

            "hue=h=sin(2*PI*t)*35:s=1.3",

            "eq=contrast=1.3:brightness=-0.04:saturation=0.9",

            "rgbashift=rh=-7:bh=7"

        ]

    else:

        motions = [

            ("1.0 + 0.14*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),

            ("1.16 - 0.16*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)")

        ]

        flashes = ["fade=t=in:st=0:d=0.18:color=black"]

        styles = [

            "gblur=sigma=1.1,eq=contrast=1.2:brightness=0.05:saturation=1.3",

            "noise=alls=16:allf=t+u,eq=contrast=1.15"

        ]

 

    z_expr, x_expr, y_expr = random.choice(motions)

    filters = [

        "scale=1350:2400:force_original_aspect_ratio=increase,crop=1350:2400",

        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s=1080x1920:fps=30"

    ]

   

    if intensity >= 0.4 and random.random() > 0.5:

        filters.append(random.choice(["hflip", "rotate=0.04*sin(t*3):fillcolor=black", "rotate=-0.04*sin(t*3):fillcolor=black"]))

 

    filters.append(random.choice(flashes))

    filters.append(random.choice(styles))

    filters.append("vignette=PI/4")

   

    return ",".join(filters)

 

@bot.message_handler(commands=['start'])

def send_welcome(message):

    user_data[message.chat.id] = {'photos': [], 'audio': None}

    bot.reply_to(

        message,

        "🎧 Умная синхронизация с музыкой включена!\n"

        "∙ Сам нахожу самый мощный ДРОП в треке\n"

        "∙ Выделяю низкие частоты (бас/бочку)\n"

        "∙ Сила тряски, вспышек и RGB-глитчей зависит от громкости каждого удара!\n\n"

        "Скинь от 4 до 15 картинок и музыку, затем жми /make"

    )

 

@bot.message_handler(content_types=['photo'])

def handle_photo(message):

    chat_id = message.chat.id

    if chat_id not in user_data:

        user_data[chat_id] = {'photos': [], 'audio': None}

   

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

    audio_path = f"temp_{chat_id}/raw_music.mp3"

   

    with open(audio_path, 'wb') as new_file:

        new_file.write(downloaded_file)

       

    user_data[chat_id]['audio'] = audio_path

    bot.reply_to(message, "🎵 Музыка загружена! Жми /make — найду дроп и подстрою эффекты под бас!")

 

@bot.message_handler(commands=['make'])

def make_edit(message):

    chat_id = message.chat.id

    data = user_data.get(chat_id)

   

    if not data or len(data['photos']) < 3 or not data['audio']:

        bot.reply_to(message, "❌ Нужно минимум 3 картинки и 1 трек!")

        return

 

    msg = bot.reply_to(message, "🔊 Выделяю басы, ищу дроп в треке и синхронизирую эффекты...")

   

    folder = f"temp_{chat_id}"

    slowed_audio = f"{folder}/slowed.mp3"

    output_video = f"{folder}/edit.mp4"

    photos = data['photos']

   

    try:

        prepare_slowed_audio(data['audio'], slowed_audio)

        start_time, durations, intensities = analyze_music_beats(slowed_audio, len(photos))

        clip_files = []

       

        for i, (img, dur, intensity) in enumerate(zip(photos, durations, intensities)):

            clip_out = f"{folder}/clip_{i:03d}.mp4"

            frames = int(dur * 30)

            vf = build_music_synced_fx(frames, intensity)

           

            cmd_clip = [

                FFMPEG_PATH, "-y",

                "-loop", "1", "-i", img,

                "-vf", vf,

                "-t", str(dur),

                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",

                clip_out

            ]

            subprocess.run(cmd_clip, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            clip_files.append(clip_out)

           

        list_file = f"{folder}/clips.txt"

        with open(list_file, "w") as f:

            for c in clip_files:

                f.write(f"file '{os.path.basename(c)}'\n")

               

        total_dur = sum(durations)

       

        cmd_concat = [

            FFMPEG_PATH, "-y",

            "-f", "concat", "-safe", "0", "-i", list_file,

            "-ss", str(start_time), "-i", slowed_audio,

            "-c:v", "copy",

            "-c:a", "aac", "-b:a", "192k",

            "-t", str(total_dur),

            output_video

        ]

        subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

       

        with open(output_video, 'rb') as video:

            bot.send_video(chat_id, video, caption="🔥 Эдит, синхронизированный с басом и дропом, готов!")

        bot.delete_message(chat_id, msg.message_id)

       

    except Exception as e:

        bot.reply_to(message, f"Ошибка при монтаже: {e}")

    finally:

        if os.path.exists(folder):

            for f in os.listdir(folder):

                os.remove(os.path.join(folder, f))

            os.rmdir(folder)

        user_data[chat_id] = {'photos': [], 'audio': None}

 

bot.polling(none_stop=True)
