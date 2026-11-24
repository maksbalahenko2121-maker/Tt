import os

import wave

import array

import random

import subprocess

import imageio_ffmpeg

 

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

 

def prepare_slowed_audio(input_audio, output_audio):

    subprocess.run([

        FFMPEG_PATH, "-y", "-i", input_audio,

        "-af", "asetrate=44100*0.88,aresample=44100,aecho=0.8:0.88:60:0.4",

        output_audio

    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

 

def get_media_duration(file_path):

    res = subprocess.run(

        [FFMPEG_PATH, "-i", file_path],

        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True

    )

    for line in res.stderr.splitlines():

        if "Duration:" in line:

            parts = line.split("Duration:").split(",").strip().split(":")

            if len(parts) == 3:

                return float(parts) * 3600 + float(parts) * 60 + float(parts)

    return 3.0

 

def analyze_music_beats(audio_path, target_duration=15.0):

    """

    Высокоточное распознавание ударов бочки (Beat Attack / Onset Detection):

    Выделяет только саб-бас (35-130 Гц) с шагом 0.025 сек и ищет резкие скачки энергии.

    """

    wav_path = audio_path + ".wav"

    subprocess.run([

        FFMPEG_PATH, "-y", "-i", audio_path,

        "-af", "highpass=f=35,lowpass=f=130",

        "-ac", "1", "-ar", "2000", wav_path

    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

   

    with wave.open(wav_path, 'rb') as wf:

        rate = wf.getframerate()

        raw_bytes = wf.readframes(wf.getnframes())

    os.remove(wav_path)

   

    samples = array.array('h', raw_bytes)

    # Шаг 0.025 сек (40 замеров в секунду для высокой точности)

    step = int(rate * 0.025)

    energies = [sum(abs(x) for x in samples[i:i+step]) / step for i in range(0, len(samples) - step, step)]

       

    if len(energies) < 20:

        return 0.0, [0.75] * 20, [0.6] * 20

 

    # Считаем Onset (резкий прирост громкости баса по сравнению с предыдущим окном)

    onsets = [0.0]

    for i in range(1, len(energies)):

        diff = energies[i] - energies[i - 1]

        onsets.append(max(0.0, diff))

 

    max_onset = max(onsets) or 1.0

    threshold = max_onset * 0.28

   

    peak_times, peak_strengths = [], []

    last_peak = -14 # Минимум 0.35 сек (14 * 0.025) между сменами кадров

   

    for i in range(1, len(onsets) - 1):

        curr_o = onsets[i]

        if curr_o > threshold and curr_o >= onsets[i - 1] and curr_o >= onsets[i + 1]:

            if i - last_peak >= 14:

                peak_times.append(round(i * 0.025, 3))

                # Учитываем и резкость удара, и общую мощь баса в этот момент

                peak_strengths.append(curr_o * 0.6 + energies[i] * 0.4)

                last_peak = i

               

    if len(peak_times) < 6:

        return 0.0, [0.75] * 20, [0.6] * 20

 

    # Находим 15-секундный отрезок (ДРОП) с максимальной плотностью и силой битов

    best_start, best_end, max_score = 0, len(peak_times) - 1, -1.0

    for i in range(len(peak_times) - 2):

        curr_sum = 0.0

        for j in range(i + 1, len(peak_times)):

            curr_sum += peak_strengths[j - 1]

            if peak_times[j] - peak_times[i] >= target_duration:

                if curr_sum > max_score:

                    max_score, best_start, best_end = curr_sum, i, j

                break

 

    sel_times = peak_times[best_start : best_end + 1]

    sel_strengths = peak_strengths[best_start : best_end]

    min_s, max_s = min(sel_strengths), max(sel_strengths)

   

    intensities = [(s - min_s) / (max_s - min_s) for s in sel_strengths] if max_s > min_s else [0.7] * len(sel_strengths)

    start_time = next(iter(sel_times))

    durations = [round(max(0.35, min(1.5, b - a)), 3) for a, b in zip(sel_times[:-1], sel_times[1:])]

       

    return start_time, durations, intensities

 

def generate_150_fx(frames, intensity, is_video=False):

    """

    Аккуратная камера без сильного кропа лиц (зум 1.0 - 1.16) + 150+ эффектов под бит.

    """

    filters = []

    if is_video:

        # Для видео: плавное замедление + легкий безопасный импульс без обрезки краев

        filters.extend(["setpts=1.3*PTS", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"])

        if intensity >= 0.75:

            filters.append("scale=1150:2044,crop=1080:1920:x='35+sin(n*3.5)*18':y='62+cos(n*3.5)*18'")

        elif intensity >= 0.45:

            filters.append("scale=1130:2008,crop=1080:1920:x='25*(1-t)':y='44'")

    else:

        # Для фото: мягкий зум (не больше 1.16x), чтобы персонажи и лица оставались в кадре

        if intensity >= 0.75:

            motions = [

                ("1.16 - 0.16*(on/duration)", "iw/2-(iw/zoom/2)+if(lt(on,8),sin(on*3.5)*22,0)", "ih/2.2-(ih/zoom/2)+if(lt(on,8),cos(on*3.5)*22,0)"),

                ("1.0 + 0.15*(on/duration)", "iw/2-(iw/zoom/2)+sin(on*10)*10", "ih/2.2-(ih/zoom/2)+cos(on*10)*10"),

                ("1.14 - 0.14*(on/duration)", "iw/2-(iw/zoom/2)-35*(1-on/duration)", "ih/2.2-(ih/zoom/2)"),

                ("1.14 - 0.14*(on/duration)", "iw/2-(iw/zoom/2)+35*(1-on/duration)", "ih/2.2-(ih/zoom/2)")

            ]

        elif intensity >= 0.45:

            motions = [

                ("1.12 - 0.12*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2.2-(ih/zoom/2)"),

                ("1.0 + 0.11*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2.2-(ih/zoom/2)"),

                ("1.10", "iw/2-(iw/zoom/2)+25*(1-on/duration)", "ih/2.2-(ih/zoom/2)")

            ]

        else:

            motions = [

                ("1.0 + 0.08*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2.2-(ih/zoom/2)"),

                ("1.09 - 0.09*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2.2-(ih/zoom/2)")

            ]

        z_e, x_e, y_e = random.choice(motions)

        filters.extend([

            "scale=1180:2098:force_original_aspect_ratio=increase,crop=1180:2098",

            f"zoompan=z='{z_e}':x='{x_e}':y='{y_e}':d={frames}:s=1080x1920:fps=30"

        ])

 

    # Геометрия: убрали переворот вверх ногами (vflip), оставили только зеркало и легкий наклон

    geo = random.choice([None, None, "hflip", "rotate=0.025*sin(t*4):fillcolor=black", "rotate=-0.025*sin(t*4):fillcolor=black"])

    if geo and intensity >= 0.45:

        filters.append(geo)

 

    flashes = [

        "fade=t=in:st=0:d=0.12:color=white",

        "fade=t=in:st=0:d=0.12:color=red",

        "negate=enable='lt(n,2)'",

        "eq=brightness='if(lt(mod(n,3),1),0.2,-0.04)'"

    ] if intensity >= 0.75 else [

        "fade=t=in:st=0:d=0.10:color=white",

        "fade=t=in:st=0:d=0.12:color=black",

        None

    ]

    flash = random.choice(flashes)

    if flash:

        filters.append(flash)

 

    styles = [

        "rgbashift=rh=-14:bh=14:rv=6:bv=-6",

        "rgbashift=rh=11:bh=-11:gh=-4:gv=4",

        "rgbashift=rh=-7:bh=7,eq=contrast=1.3:saturation=1.4",

        "hue=h=sin(2*PI*t)*40:s=1.35",

        "hue=h=180:s=1.25,eq=contrast=1.25",

        "eq=contrast=1.4:brightness=-0.06:saturation=0.8",

        "eq=contrast=1.3:brightness=0.05:saturation=1.45",

        "eq=saturation=0.0:contrast=1.5",

        "colorbalance=rs=0.22:bs=-0.18:rm=0.12",

        "colorbalance=bs=0.25:gs=0.08:rs=-0.12",

        "gblur=sigma=1.1,eq=contrast=1.22:brightness=0.05:saturation=1.3",

        "noise=alls=18:allf=t+u,rgbashift=rh=-5:bh=5,eq=contrast=1.18"

    ]

    filters.extend([random.choice(styles), "vignette=PI/4"])

    return ",".join(filters)
