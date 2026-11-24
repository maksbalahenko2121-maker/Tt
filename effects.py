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

 

def analyze_music_beats(audio_path, target_duration=25.0):

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

    step = int(rate * 0.025)

    energies = [sum(abs(x) for x in samples[i:i+step]) / step for i in range(0, len(samples) - step, step)]

       

    if len(energies) < 20:

        return 0.0, [0.75] * 32, [0.6] * 32

 

    onsets = [0.0] + [max(0.0, energies[i] - energies[i - 1]) for i in range(1, len(energies))]

    threshold = (max(onsets) or 1.0) * 0.25

   

    peak_times, peak_strengths = [], []

    last_peak = -14

   

    for i in range(1, len(onsets) - 1):

        curr_o = onsets[i]

        if curr_o > threshold and curr_o >= onsets[i - 1] and curr_o >= onsets[i + 1]:

            if i - last_peak >= 14:

                peak_times.append(round(i * 0.025, 3))

                peak_strengths.append(curr_o * 0.65 + energies[i] * 0.35)

                last_peak = i

               

    if len(peak_times) < 6:

        return 0.0, [0.75] * 32, [0.6] * 32

 

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

    durations = [round(max(0.35, min(1.4, b - a)), 3) for a, b in zip(sel_times[:-1], sel_times[1:])]

       

    return start_time, durations, intensities

 

def generate_150_fx(frames, intensity, is_video=False):

    """

    Современный стиль Alight Motion / After Effects:

    Экспоненциальное затухание скорости (Velocity Graphs), затухающий шейк,

    мягкий Motion Blur и современная цветокоррекция (CC).

    """

    filters = []

    if is_video:

        # Velocity Slow-Mo + плавный импульс на старте удара

        filters.extend(["setpts=1.35*PTS", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"])

        if intensity >= 0.7:

            filters.append("scale=1160:2062,crop=1080:1920:x='40+sin(n*3.2)*24*exp(-0.22*n)':y='71+cos(n*3.2)*24*exp(-0.22*n)'")

        elif intensity >= 0.4:

            filters.append("scale=1130:2008,crop=1080:1920:x='25*exp(-4*t)':y='44*exp(-4*t)'")

    else:

        # Графики скорости (Ease-Out Graphs): быстрый рывок в первые кадры и зависание

        if intensity >= 0.7:

            motions = [

                # 1. Alight Motion Elastic Punch + затухающая тряска

                ("1.0 + 0.18*exp(-0.18*on)", "iw/2-(iw/zoom/2)+sin(on*3.5)*28*exp(-0.25*on)", "ih/2.2-(ih/zoom/2)+cos(on*3.5)*28*exp(-0.25*on)"),

                # 2. Быстрый влет (Smooth Zoom In Ease-Out)

                ("1.16 - 0.14*exp(-0.15*on)", "iw/2-(iw/zoom/2)", "ih/2.2-(ih/zoom/2)"),

                # 3. Плавный слайд слева с торможением (Whip Slide Left)

                ("1.14", "iw/2-(iw/zoom/2) - 55*exp(-0.18*on)", "ih/2.2-(ih/zoom/2)"),

                # 4. Плавный слайд справа с торможением (Whip Slide Right)

                ("1.14", "iw/2-(iw/zoom/2) + 55*exp(-0.18*on)", "ih/2.2-(ih/zoom/2)"),

                # 5. Удар сверху вниз с пружиной (Drop Bounce)

                ("1.15", "iw/2-(iw/zoom/2)", "ih/2.2-(ih/zoom/2) - 50*exp(-0.18*on)")

            ]

        elif intensity >= 0.4:

            motions = [

                ("1.0 + 0.12*exp(-0.14*on)", "iw/2-(iw/zoom/2)", "ih/2.2-(ih/zoom/2)"),

                ("1.13 - 0.11*exp(-0.14*on)", "iw/2-(iw/zoom/2)", "ih/2.2-(ih/zoom/2)"),

                ("1.11", "iw/2-(iw/zoom/2) + 35*exp(-0.15*on)", "ih/2.2-(ih/zoom/2)")

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

 

    # Плавный Motion Blur (шлейф движения) при рывках на сильных битах

    if intensity >= 0.65:

        filters.append("tmix=frames=2:weights='1 2'")

 

    # Легкий киношный наклон с затуханием (Tilt Bounce) или зеркало

    geo = random.choice([None, None, "hflip", "rotate=0.035*exp(-4*t)*sin(t*12):fillcolor=black", "rotate=-0.035*exp(-4*t)*sin(t*12):fillcolor=black"])

    if geo and intensity >= 0.45:

        filters.append(geo)

 

    # Вспышки (Exposure Flash / White Flash) только в момент удара

    if intensity >= 0.7:

        flashes = [

            "fade=t=in:st=0:d=0.14:color=white",

            "eq=brightness='0.32*exp(-14*t)':contrast='1.25+0.4*exp(-12*t)'", # Настоящий Exposure Flash из CapCut

            "fade=t=in:st=0:d=0.12:color=black"

        ]

    else:

        flashes = [

            "eq=brightness='0.18*exp(-14*t)'",

            "fade=t=in:st=0:d=0.12:color=black",

            None

        ]

    flash = random.choice(flashes)

    if flash:

        filters.append(flash)

 

    # Современный CC (Color Correction — киношный цветокор + легкий RGB на ударе)

    cc_styles = [

        # 1. Холодный кибер-CC + легкий RGB-импульс

        "rgbashift=rh=-9:bh=9,colorbalance=bs=0.22:gs=0.06:rs=-0.12,eq=contrast=1.32:saturation=1.25",

        # 2. Теплый закатный аниме-CC (Golden Hour)

        "colorbalance=rs=0.22:gs=0.08:bs=-0.18:rm=0.1,eq=contrast=1.28:saturation=1.35",

        # 3. Мрачный Phonk CC (глубокий черный + холодные блики)

        "eq=contrast=1.42:brightness=-0.05:saturation=0.82,colorbalance=bs=0.15:rs=-0.08",

        # 4. Четкий HD-CC (резкость линий + сочные цвета как в Topaz)

        "unsharp=5:5:1.4:5:5:0.0,eq=contrast=1.3:brightness=0.03:saturation=1.38",

        # 5. Неоновый фиолетово-синий CC (Cyber Neon)

        "colorbalance=rs=0.18:bs=0.25:gs=-0.12,rgbashift=rh=7:bh=-7,eq=contrast=1.32",

        # 6. Мягкий Glow / Dreamy Anime CC

        "gblur=sigma=0.8,eq=contrast=1.24:brightness=0.05:saturation=1.32",

        # 7. Стильный Ч/Б с высоким контрастом

        "eq=saturation=0.0:contrast=1.48:brightness=-0.02"

    ]

    filters.extend([random.choice(cc_styles), "vignette=PI/4.5"])

    return ",".join(filters)
