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

            parts = line.split("Duration:")[1].split(",")[0].strip().split(":")

            if len(parts) == 3:

                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

    return 3.0

 

def analyze_music_beats(audio_path, target_duration=15.0):

    wav_path = audio_path + ".wav"

    subprocess.run([

        FFMPEG_PATH, "-y", "-i", audio_path,

        "-af", "lowpass=f=150",

        "-ac", "1", "-ar", "1000", wav_path

    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

   

    with wave.open(wav_path, 'rb') as wf:

        rate = wf.getframerate()

        raw_bytes = wf.readframes(wf.getnframes())

    os.remove(wav_path)

   

    samples = array.array('h', raw_bytes)

    step = int(rate * 0.05)

    energies = [sum(abs(x) for x in samples[i:i+step]) / step for i in range(0, len(samples) - step, step)]

       

    if not energies:

        return 0.0, [0.75] * 20, [0.6] * 20

 

    threshold = (max(energies) or 1.0) * 0.42

    peak_times, peak_strengths = [], []

    last_peak = -8

   

    for i in range(1, len(energies) - 1):

        curr_e = energies[i]

        if curr_e > threshold and curr_e >= energies[i - 1] and curr_e >= energies[i + 1]:

            if i - last_peak >= 8:

                peak_times.append(i * 0.05)

                peak_strengths.append(curr_e)

                last_peak = i

               

    if len(peak_times) < 6:

        return 0.0, [0.75] * 20, [0.6] * 20

 

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

    start_time = round(sel_times[0], 3)

    durations = [round(max(0.35, min(1.4, b - a)), 3) for a, b in zip(sel_times[:-1], sel_times[1:])]

       

    return start_time, durations, intensities

 

def generate_150_fx(frames, intensity, is_video=False):

    filters = []

    if is_video:

        filters.extend(["setpts=1.35*PTS", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"])

        if intensity >= 0.7:

            filters.append("scale=1240:2204,crop=1080:1920:x='80+sin(n*3)*25':y='142+cos(n*3)*25'")

        elif intensity >= 0.4:

            filters.append("scale=1180:2098,crop=1080:1920:x='50*(1-t)':y='89'")

    else:

        if intensity >= 0.75:

            motions = [

                ("1.42 - 0.42*(on/duration)", "iw/2-(iw/zoom/2)+if(lt(on,10),sin(on*3.5)*45,0)", "ih/2-(ih/zoom/2)+if(lt(on,10),cos(on*3.5)*45,0)"),

                ("1.0 + 0.38*(on/duration)", "iw/2-(iw/zoom/2)+sin(on*11)*18", "ih/2-(ih/zoom/2)+cos(on*11)*18"),

                ("1.38 - 0.28*(on/duration)", "iw/2-(iw/zoom/2)-110*(1-on/duration)", "ih/2-(ih/zoom/2)"),

                ("1.38 - 0.28*(on/duration)", "iw/2-(iw/zoom/2)+110*(1-on/duration)", "ih/2-(ih/zoom/2)")

            ]

        elif intensity >= 0.4:

            motions = [

                ("1.26 - 0.26*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),

                ("1.0 + 0.24*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),

                ("1.24", "iw/2-(iw/zoom/2)+80*(1-on/duration)", "ih/2-(ih/zoom/2)")

            ]

        else:

            motions = [

                ("1.0 + 0.15*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),

                ("1.18 - 0.18*(on/duration)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)")

            ]

        z_e, x_e, y_e = random.choice(motions)

        filters.extend([

            "scale=1380:2454:force_original_aspect_ratio=increase,crop=1380:2454",

            f"zoompan=z='{z_e}':x='{x_e}':y='{y_e}':d={frames}:s=1080x1920:fps=30"

        ])

 

    geo = random.choice([None, None, "hflip", "vflip", "rotate=0.045*sin(t*4):fillcolor=black", "rotate=-0.045*sin(t*4):fillcolor=black"])

    if geo and intensity >= 0.35:

        filters.append(geo)

 

    flashes = ["fade=t=in:st=0:d=0.14:color=white", "fade=t=in:st=0:d=0.14:color=red", "negate=enable='lt(n,3)'", "eq=brightness='if(lt(mod(n,3),1),0.25,-0.06)'"] if intensity >= 0.7 else ["fade=t=in:st=0:d=0.12:color=white", "fade=t=in:st=0:d=0.15:color=black", None]

    flash = random.choice(flashes)

    if flash:

        filters.append(flash)

 

    styles = [

        "rgbashift=rh=-18:bh=18:rv=8:bv=-8", "rgbashift=rh=14:bh=-14:gh=-5:gv=5",

        "rgbashift=rh=-8:bh=8,eq=contrast=1.35:saturation=1.45", "hue=h=sin(2*PI*t)*50:s=1.4",

        "hue=h=180:s=1.3,eq=contrast=1.3", "eq=contrast=1.45:brightness=-0.08:saturation=0.75",

        "eq=contrast=1.35:brightness=0.06:saturation=1.5", "eq=saturation=0.0:contrast=1.55",

        "colorbalance=rs=0.25:bs=-0.2:rm=0.15", "colorbalance=bs=0.3:gs=0.1:rs=-0.15",

        "gblur=sigma=1.3,eq=contrast=1.25:brightness=0.06:saturation=1.35", "noise=alls=22:allf=t+u,rgbashift=rh=-6:bh=6,eq=contrast=1.2"

    ]

    filters.extend([random.choice(styles), "vignette=PI/4"])

    return ",".join(filters)
