#!/usr/bin/env python3
"""
Zubi AI Clipping Tool - MVP pipeline
Long YouTube / stream -> viral Shorts / Reels / TikTok clips
Features: face tracking, auto subtitles (word chunks), auto emoji,
viral scoring (hook/pacing/engagement), hook title, loudness normalize,
thumbnail, title+hashtags.

Usage:
  .venv/bin/python clipper.py --url "https://youtube.com/watch?v=..." --clips 5
  .venv/bin/python clipper.py --url "https://youtube.com/watch?v=..." --clips 10 --language auto
  .venv/bin/python clipper.py --file video.mp4 --clips 1 --fit face --language ur
  .venv/bin/python clipper.py --url "https://youtube.com/watch?v=..." --clips 5 --subtitle-language ur
  # --clips: 1, 2, 3, 4, 5, 10 ya jitnay chahiye (koi upper limit code mein nahi, video ki length par depend hai)
  # --language: video ki language, auto (default, Whisper khud pehchanta hai) ya en/ur/hi/ar/es/fr/de/pt/tr/id/bn/pa waghera
  # --subtitle-language: clip ke subtitles ki language khud select karo, auto (video wali) ya en/ur/hi/ar/es/fr/de/pt/tr/id/bn/pa/ru/ja/ko/zh
"""
import argparse, json, math, os, re, subprocess, sys
from pathlib import Path

EMOJI_MAP = {
    "money": "💰", "paisa": "💰", "rich": "💰", "ameer": "💰",
    "love": "❤️", "mohabbat": "❤️", "dil": "❤️",
    "fire": "🔥", "viral": "🔥", "best": "🔥",
    "laugh": "😂", "hansi": "😂", "funny": "😂",
    "shock": "😱", "shocking": "😱", "hairan": "😱",
    "secret": "🤫", "raaz": "🤫",
    "success": "🏆", "kamyaab": "🏆", "win": "🏆",
    "never": "🚫", "kabhi": "🚫", "stop": "🛑",
    "how": "🤔", "kaise": "🤔", "kyun": "🤔", "why": "🤔",
    "think": "🧠", "mind": "🧠", "dimaag": "🧠",
    "time": "⏰", "waqt": "⏰",
    "power": "💪", "taqat": "💪", "strong": "💪",
    "sad": "😢", "dukhi": "😢", "cry": "😢",
    "happy": "😊", "khush": "😊",
    "danger": "⚠️", "khatra": "⚠️",
    "wow": "🤯", "amazing": "🤯", "zabardast": "🤯",
    "learn": "📚", "seekho": "📚", "education": "📚",
    "business": "💼", "karobar": "💼",
    "god": "🙏", "allah": "🙏",
}

HOOK_WORDS = ["never","secret","how","why","stop","listen","truth","mistake","shocking",
              "kaise","kyun","kabhi","raaz","suno","galti","sach","hairan","zabardast","best",
              "cómo","por qué","nunca","secreto","comment","pourquoi","jamais","como","nunca",
              "كيف","لماذا","سر","कैसे","क्यों","कभी","রহস্য","কীভাবে"]
EMOTION_WORDS = ["love","hate","amazing","wow","sad","happy","angry","fear","excited",
                 "mohabbat","khush","dukhi","gussa","dar","hairan",
                 "amor","feliz","triste","amour","heureux","حب","سعيد","प्यार","खुश"]

def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"command failed: {cmd[0]}")
    return r

def yt_dlp_cmd(*args):
    """yt-dlp command. Kuch environments (proxy wale) mein certificate verify
    fail hota hai; wahan CLIPPER_NO_CHECK_CERTIFICATES=1 set karne se
    --no-check-certificates lag jata hai. Default secure hai."""
    cmd = [sys.executable, "-m", "yt_dlp"]
    if os.environ.get("CLIPPER_NO_CHECK_CERTIFICATES") == "1":
        cmd.append("--no-check-certificates")
    return cmd + list(args)

# Vertical export qualities. Source se zyada quality real detail nahi deti, sirf upscale hoti hai.
QUALITIES = {
    "720p": (720, 1280),    # HD
    "1080p": (1080, 1920),  # Full HD
    "2k": (1440, 2560),     # 2K / QHD vertical
    "4k": (2160, 3840),     # 4K / UHD vertical
}

# Subtitles ki language user khud select kar sakta hai (video ki language se alag).
# "auto" = video wali original language ke subtitles.
SUBTITLE_LANGUAGES = {
    "auto": "Auto (video wali language)",
    "none": "Without Subtitles (koi subtitles nahi)",
    "en": "English", "ur": "Urdu", "hi": "Hindi", "ar": "Arabic",
    "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese",
    "tr": "Turkish", "id": "Indonesian", "bn": "Bengali", "pa": "Punjabi",
    "ru": "Russian", "ja": "Japanese", "ko": "Korean", "zh": "Chinese",
}

def get_video_info(url):
    """License / copyright check. Clip karne se copyright khatam NAHI hota."""
    try:
        r = subprocess.run(yt_dlp_cmd("--dump-single-json", "--no-download", url),
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return {"license": "unknown", "copyright_status": "License check nahi ho saka. Sirf apni / CC / permission wali video use karo."}
        info = json.loads(r.stdout)
        lic = info.get("license") or "Standard YouTube License"
        is_cc = "creative commons" in lic.lower()
        status = ("Creative Commons license mili hai. Terms ke hisab se attribution de kar use kar sakte ho, phir bhi license parho."
                  if is_cc else
                  "WARNING: Ye video copyright-free NAHI hai (Standard License). Clip, captions, face tracking se copyright khatam nahi hota. "
                  "Sirf apni video, Creative Commons, public domain, ya owner ki permission wali video post karo, warna Content ID / strike ka risk hai.")
        return {"title": info.get("title"), "uploader": info.get("uploader"), "license": lic,
                "is_creative_commons": is_cc, "copyright_status": status,
                "webpage_url": info.get("webpage_url"), "height": info.get("height")}
    except Exception as e:
        return {"license": "unknown", "copyright_status": f"License check fail: {e}. Sirf apni / CC / permission wali video use karo."}

def download(url, outdir: Path, max_height=1080, language=None, subtitle_language=None):
    outdir.mkdir(parents=True, exist_ok=True)
    tmpl = str(outdir / "source.%(ext)s")
    fmt = f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={max_height}]"
    # Pehle sirf video download karo. Subtitles alag step mein hain taake
    # subtitle rate-limit (HTTP 429) poori video download ko fail na kare.
    run(yt_dlp_cmd("-f", fmt,
         "--merge-output-format", "mp4", "-o", tmpl, url))
    # Phir limited languages mein subtitles try karo. "all" languages
    # mangne se YouTube 429 de deta hai, is liye sirf zaroori languages.
    # User ne subtitles language select ki hai to wo sab se pehle mango.
    langs = []
    if subtitle_language and subtitle_language not in ("auto", "none"):
        langs += [subtitle_language, f".*-{subtitle_language}"]
    if language:
        langs += [language, f"{language}-orig", "en"]
    else:
        langs += ["en", "ur", "hi", "hi-orig", "ar", "es", "fr", "de", "pt", "tr", "id", "bn", "pa"]
    sub_langs = ",".join(dict.fromkeys(langs))
    try:
        run(yt_dlp_cmd("--skip-download",
             "--write-subs", "--write-auto-subs", "--sub-langs", sub_langs,
             "--convert-subs", "vtt", "--ignore-errors", "-o", tmpl, url))
    except Exception as e:
        print(f"Subtitles download nahi ho sakay ({e}), Whisper use hoga.")
    mp4 = list(outdir.glob("source.mp4"))
    if not mp4:
        mp4 = [p for p in outdir.glob("source.*") if p.suffix not in (".vtt", ".srt")]
    return mp4[0]

def parse_vtt(path: Path):
    words = []
    text = path.read_text(errors="ignore")
    blocks = re.split(r"\n\n+", text)
    for b in blocks:
        m = re.search(r"(\d+):(\d+):(\d+\.\d+) --> (\d+):(\d+):(\d+\.\d+)", b)
        if not m: continue
        start = int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))
        end = int(m.group(4))*3600+int(m.group(5))*60+float(m.group(6))
        lines = [l for l in b.splitlines() if "-->" not in l and not l.strip().isdigit() and "WEBVTT" not in l]
        txt = re.sub(r"<[^>]+>", "", " ".join(lines)).strip()
        if not txt: continue
        ws = txt.split()
        if not ws: continue
        step = (end-start)/len(ws)
        for i,w in enumerate(ws):
            words.append({"word": w, "start": start+i*step, "end": start+(i+1)*step})
    return words

def transcribe_whisper(video: Path, outdir: Path, language=None, translate=False):
    # extract audio
    wav = outdir / "audio.wav"
    run(["ffmpeg","-y","-i",str(video),"-vn","-ar","16000","-ac","1",str(wav)])
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    # language=None -> auto-detect (Whisper 99 languages). translate=True -> subtitles English mein.
    segments, info = model.transcribe(str(wav), language=language, task="translate" if translate else "transcribe",
                                      word_timestamps=True, vad_filter=True)
    words = []
    for seg in segments:
        for w in (seg.words or []):
            words.append({"word": w.word.strip(), "start": float(w.start), "end": float(w.end)})
    print(f"Whisper language={info.language} (p={info.language_probability:.2f}) words={len(words)}")
    return words

MYMEMORY_CODES = {
    "en": "en-GB", "ur": "ur-PK", "hi": "hi-IN", "ar": "ar-SA", "es": "es-ES",
    "fr": "fr-FR", "de": "de-DE", "pt": "pt-PT", "tr": "tr-TR", "id": "id-ID",
    "bn": "bn-IN", "pa": "pa-IN", "ru": "ru-RU", "ja": "ja-JP", "ko": "ko-KR", "zh": "zh-CN",
}

def _translate_text(text, target_language, source_language=None):
    """Ek text chunk translate karo. Pehle Google, fail ho to MyMemory."""
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source="auto", target=target_language).translate(text)
        if result:
            return result
    except Exception as e:
        print(f"Google translate fail ({str(e)[:120]}), MyMemory try kar raha hun.")
    try:
        from deep_translator import MyMemoryTranslator
        src = MYMEMORY_CODES.get(source_language or "en", "en-GB")
        tgt = MYMEMORY_CODES.get(target_language, target_language)
        result = MyMemoryTranslator(source=src, target=tgt).translate(text)
        if result:
            return result
    except Exception as e:
        print(f"MyMemory translate fail ({str(e)[:120]}), original text rakha gaya.")
    return text

def translate_words(words, target_language, source_language=None):
    """Transcript ko user ki select ki hui subtitle language mein translate karo.

    Words ko chhote chunks (lagbhag 12 words) mein translate karke har chunk
    ki timing usi chunk ke start/end par rakhi jati hai, taake subtitles
    audio ke saath sync rahen. Translation fail ho to original words wapas
    de diye jate hain (clip phir bhi ban jayegi).
    """
    if not words or not target_language or target_language in ("auto", "none"):
        return words
    out = []
    chunk_size = 12
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i + chunk_size]
        text = " ".join(w["word"] for w in chunk).strip()
        if not text:
            continue
        translated = _translate_text(text, target_language, source_language=source_language)
        tw = translated.split()
        if not tw:
            tw = [text]
        start, end = chunk[0]["start"], chunk[-1]["end"]
        step = max(0.01, (end - start) / len(tw))
        for j, w in enumerate(tw):
            out.append({"word": w, "start": start + j * step, "end": start + (j + 1) * step})
    print(f"Subtitles translated to '{target_language}': {len(out)} words")
    return out

def _pick_vtt(vtts, language=None, subtitle_language=None):
    """Sab se munasib caption file choose karo."""
    if not vtts:
        return None
    # 1) User ki select ki hui subtitle language ki file sab se pehle.
    if subtitle_language and subtitle_language not in ("auto", "none"):
        match = [v for v in vtts if f".{subtitle_language}." in v.name or f"-{subtitle_language}." in v.name
                 or f".{subtitle_language}-" in v.name]
        if match:
            return match[0]
    # 2) Video ki specific language.
    if language:
        match = [v for v in vtts if f".{language}" in v.name or f"-{language}" in v.name]
        if match:
            return match[0]
    # 3) Auto: en, phir original, phir ur/hi/ar.
    for pref in (".en.", "-orig", ".ur.", ".hi.", ".ar."):
        match = [v for v in vtts if pref in v.name]
        if match:
            return match[0]
    return vtts[0]

def _vtt_source_language(name):
    """Caption file name se source language guess karo, masalan source.en.vtt -> en."""
    m = re.search(r"source\.([a-z]{2,3})(?:-|_|\.)", name)
    return m.group(1) if m else None

def get_words(video: Path, outdir: Path, language=None, translate=False, subtitle_language=None):
    # subtitle_language: user ki select ki hui subtitles language.
    # "auto"/None = video wali language. "none" = without subtitles (transcript
    # sirf best clips choose karne ke liye use hoga, clip par nahi lagega).
    # "en" = English (purana --translate-to-english bhi yahi hai).
    if translate and not subtitle_language:
        subtitle_language = "en"
    vtts = list(outdir.glob("source*.vtt"))
    # English chahiye aur en captions mojood hain to wahi best hain.
    # Kisi aur language ki captions mojood hain to wahi use karo.
    if vtts:
        chosen = _pick_vtt(vtts, language=language, subtitle_language=subtitle_language)
        words = parse_vtt(chosen)
        if len(words) > 20:
            print(f"Using YouTube captions ({chosen.name}): {len(words)} words")
            # Agar chosen file user ki subtitle language ki nahi hai, to
            # usi transcript ko us language mein translate kar do.
            if subtitle_language and subtitle_language not in ("auto", "none") and \
               f".{subtitle_language}." not in chosen.name and f"-{subtitle_language}." not in chosen.name:
                words = translate_words(words, subtitle_language,
                                        source_language=language or _vtt_source_language(chosen.name))
            return words
    # Captions nahi mile: Whisper. English subtitles ke liye Whisper ka
    # apna translate task use karo, baaki languages ke liye pehle original
    # transcript, phir translate_words.
    if subtitle_language == "en":
        return transcribe_whisper(video, outdir, language=language, translate=True)
    words = transcribe_whisper(video, outdir, language=language, translate=False)
    if subtitle_language and subtitle_language not in ("auto", "none"):
        words = translate_words(words, subtitle_language, source_language=language)
    return words

def score_segment(words_seg):
    text = " ".join(w["word"] for w in words_seg).lower()
    duration = max(1.0, words_seg[-1]["end"]-words_seg[0]["start"])
    wpm = len(words_seg)/duration*60
    first = " ".join(w["word"] for w in words_seg[:8]).lower()
    hook = 0
    if "?" in first or any(h in first for h in HOOK_WORDS): hook += 60
    if re.search(r"\d+", first): hook += 20
    if any(h in text for h in HOOK_WORDS): hook += 20
    hook = min(100, hook)
    # pacing: ideal 130-180 wpm
    pacing = 100 - min(100, abs(wpm-155)/1.2)
    engagement = 30
    if any(e in text for e in EMOTION_WORDS): engagement += 30
    if "you" in text or "tum" in text or "aap" in text: engagement += 20
    if "!" in text: engagement += 10
    engagement = min(100, engagement)
    overall = round(hook*0.40 + pacing*0.35 + engagement*0.25)
    return {"overall": overall, "hook": round(hook), "pacing": round(pacing), "engagement": round(engagement), "wpm": round(wpm)}

def find_candidates(words, max_clips=5, min_sec=25, max_sec=60):
    if not words: return []
    cands = []
    # sliding windows at word boundaries every ~5 sec
    i = 0
    while i < len(words):
        start = words[i]["start"]
        j = i
        while j < len(words) and words[j]["end"]-start < max_sec:
            j += 1
        if j > i:
            seg = words[i:j]
            dur = seg[-1]["end"]-seg[0]["start"]
            if dur >= min_sec:
                s = score_segment(seg)
                cands.append({"start": seg[0]["start"], "end": seg[-1]["end"], "words": seg, "score": s,
                              "text": " ".join(w["word"] for w in seg)})
        # advance ~10 sec
        target = start + 10
        while i < len(words) and words[i]["start"] < target:
            i += 1
    cands.sort(key=lambda c: c["score"]["overall"], reverse=True)
    # non-overlapping top clips
    picked = []
    for c in cands:
        if any(not (c["end"] < p["start"] or c["start"] > p["end"]) for p in picked):
            continue
        picked.append(c)
        if len(picked) >= max_clips: break
    picked.sort(key=lambda c: c["start"])
    return picked

def emoji_for(text):
    low = text.lower()
    for k,v in EMOJI_MAP.items():
        if k in low:
            return v
    return ""

def make_ass(words_seg, clip_start, out_path: Path, use_emoji=True, width=720, height=1280):
    def ts(t):
        t = max(0, t-clip_start)
        h = int(t//3600); m = int((t%3600)//60); s = t%60
        return f"{h}:{m:02d}:{s:05.2f}"
    fontsize = max(32, int(58 * width / 720))
    margin_v = int(140 * height / 1280)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,Noto Sans,{fontsize},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,30,30,{margin_v},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    # 3 words per chunk
    for i in range(0, len(words_seg), 3):
        chunk = words_seg[i:i+3]
        txt = " ".join(w["word"] for w in chunk).upper()
        if use_emoji:
            e = emoji_for(txt)
            if e: txt += " " + e
        lines.append(f"Dialogue: 0,{ts(chunk[0]['start'])},{ts(chunk[-1]['end'])},Pop,,0,0,0,,{txt}")
    out_path.write_text("\n".join(lines), encoding="utf-8")

def render_face_tracked(video: Path, start, end, out_silent: Path, fit="face"):
    """9:16 crop jo face ko smoothly follow kare.

    Smoothness ke liye:
    - Face har 5 frames par detect hota hai (chhoti frame par, fast).
    - Wahi face follow hota hai jo pichli position ke qareeb ho (sab se bada
      face har bar nahi uthate, warna do logon ke darmiyan crop uchhalta hai).
    - Crop ek target ki taraf ahista pan karta hai (max speed limit), is liye
      video idhar udhar nahi bhagti.
    - Scene cut detect ho to crop foran nayi position par snap ho jata hai
      (cut ke paar pan karna sab se zyada kharab lagta hai).
    - Chhoti movements (dead zone) ignore hoti hain.
    """
    import cv2
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_MSEC, start*1000)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    profile = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_silent), fourcc, fps, (720,1280))
    cx = None          # current crop center (source pixels)
    target = None      # jahan crop ko jana hai
    prev_small = None  # scene-cut detection ke liye
    frames = 0; face_frames = 0
    total = int((end-start)*fps)
    for n in range(total):
        ok, frame = cap.read()
        if not ok: break
        h, w = frame.shape[:2]
        crop_w = int(h*9/16)
        if fit == "blur":
            bg = cv2.resize(frame, (720,1280))
            bg = cv2.GaussianBlur(bg, (51,51), 0)
            fg_h = int(720 * h / w)
            fg = cv2.resize(frame, (720, fg_h))
            y = (1280-fg_h)//2
            bg[y:y+fg_h] = fg
            writer.write(bg); frames+=1; continue
        # --- scene cut detection (chhoti gray frame ka farq) ---
        small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 36))
        scene_cut = False
        if prev_small is not None:
            diff = float(cv2.absdiff(small, prev_small).mean())
            scene_cut = diff > 28
        prev_small = small
        # --- face detection har 5 frames par ---
        if n % 5 == 0 or scene_cut:
            scale = 640 / w
            det = cv2.resize(frame, (640, int(h*scale)))
            gray = cv2.cvtColor(det, cv2.COLOR_BGR2GRAY)
            faces = list(cascade.detectMultiScale(gray, 1.15, 5, minSize=(40,40)))
            if not len(faces):
                faces = list(profile.detectMultiScale(gray, 1.15, 5, minSize=(40,40)))
            if len(faces):
                face_frames += 5
                centers = [((x+fw/2)/scale, fw/scale) for x, y, fw, fh in faces]
                if target is None or scene_cut:
                    # sab se bada face
                    new_target = max(centers, key=lambda c: c[1])[0]
                else:
                    # pichle target ke sab se qareeb wala face (wahi banda)
                    near = min(centers, key=lambda c: abs(c[0]-target))
                    # do face qareeb hon to darmiyan mein center karo
                    close = [c for c in centers if abs(c[0]-near[0]) < crop_w*0.8]
                    new_target = sum(c[0] for c in close)/len(close) if len(close) > 1 else near[0]
                if scene_cut or target is None:
                    target = new_target
                    cx = new_target  # cut par foran snap, pan nahi
                elif abs(new_target - target) > w*0.02:  # dead zone
                    target = 0.6*target + 0.4*new_target
        if cx is None:
            cx = target = w/2
        if target is None:
            target = cx
        # --- smooth pan: har frame target ki taraf limited speed se ---
        max_step = max(2.0, w*0.004)  # ~0.4% width per frame
        delta = target - cx
        if abs(delta) > max_step:
            cx += max_step if delta > 0 else -max_step
        else:
            cx = target
        x1 = int(max(0, min(w-crop_w, cx-crop_w/2)))
        cropped = frame[:, x1:x1+crop_w]
        writer.write(cv2.resize(cropped, (720,1280)))
        frames+=1
    cap.release(); writer.release()
    face_pct = round(100*min(face_frames, frames)/max(1,frames))
    print(f"Rendered {frames} frames, face in ~{face_pct}%")
    return face_pct

def make_title_hashtags(text):
    clean = re.sub(r"\s+", " ", text).strip()
    title = (clean[:60] + ("..." if len(clean)>60 else ""))
    tags = ["#shorts","#reels","#viral","#tiktok"]
    low = clean.lower()
    if "money" in low or "business" in low: tags.append("#business")
    if "love" in low: tags.append("#love")
    if "learn" in low or "seekho" in low: tags.append("#learning")
    return title, " ".join(tags)

def process(url=None, file=None, max_clips=5, fit="face", use_emoji=True, out_root="output",
            language=None, translate=False, subtitle_language=None, min_sec=25, max_sec=60,
            qualities=("720p","1080p"), i_own_this=False):
    if max_clips < 1:
        raise SystemExit("--clips kam az kam 1 hona chahiye")
    qualities = [q.lower() for q in qualities if q.lower() in QUALITIES] or ["720p"]
    outdir = Path(out_root); outdir.mkdir(parents=True, exist_ok=True)
    work = outdir / "work"; work.mkdir(exist_ok=True)
    # Copyright / license check (clip karne se copyright khatam nahi hota)
    info = {"license": "local file", "copyright_status": "Local file: sirf apni ya permission wali video use karo."}
    if url and not file:
        info = get_video_info(url)
        if i_own_this:
            info["copyright_status"] = "User ne confirm kiya ke ye unki apni video hai ya unke paas permission hai. Phir bhi platform rules check karo."
        print("COPYRIGHT CHECK:", info.get("license"), "-", info.get("copyright_status"))
    max_h = 2160 if any(q in ("2k","4k") for q in qualities) else 1080
    video = Path(file) if file else download(url, work, max_height=max_h, language=language, subtitle_language=subtitle_language)
    words = get_words(video, work, language=language, translate=translate, subtitle_language=subtitle_language)
    (work/"transcript.json").write_text(json.dumps(words, ensure_ascii=False, indent=2))
    cands = find_candidates(words, max_clips=max_clips, min_sec=min_sec, max_sec=max_sec)
    print(f"Found {len(cands)} candidate clips")
    results = []
    for idx, c in enumerate(cands, 1):
        clip_dir = outdir / f"clip_{idx:02d}"; clip_dir.mkdir(exist_ok=True)
        silent = clip_dir/"silent.mp4"
        face_pct = render_face_tracked(video, c["start"], c["end"], silent, fit=fit)
        audio = clip_dir/"audio.m4a"
        run(["ffmpeg","-y","-ss",str(c["start"]),"-to",str(c["end"]),"-i",str(video),"-vn","-c:a","aac",str(audio)])
        hook_title = " ".join(w["word"] for w in c["words"][:7]).upper().replace("'","").replace(":","").replace("\\","")
        downloads = {}
        final = None
        # Har quality ke liye alag file, WITHOUT watermark (koi watermark filter nahi hai)
        no_subs = (subtitle_language == "none")
        for q in qualities:
            qw, qh = QUALITIES[q]
            out_file = clip_dir/f"clip_{idx:02d}_{q}.mp4"
            if no_subs:
                # Without subtitles: saaf clip, na captions na hook title text.
                vf = f"scale={qw}:{qh}:flags=lanczos"
            else:
                ass = clip_dir/f"subs_{q}.ass"; make_ass(c["words"], c["start"], ass, use_emoji=use_emoji, width=qw, height=qh)
                hook_size = max(24, int(38 * qw / 720))
                hook_y = int(80 * qh / 1280)
                vf = (f"scale={qw}:{qh}:flags=lanczos,ass={ass},"
                      f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{hook_title}':fontcolor=white:fontsize={hook_size}:borderw=3:bordercolor=black:x=(w-text_w)/2:y={hook_y}:enable='lt(t,3)'")
            run(["ffmpeg","-y","-i",str(silent),"-i",str(audio),"-vf",vf,"-af","loudnorm=I=-14:TP=-1:LRA=11",
                 "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(out_file)])
            downloads[q] = {"file": str(out_file), "width": qw, "height": qh,
                            "label": {"720p":"HD 720p","1080p":"Full HD 1080p","2k":"2K","4k":"4K"}[q],
                            "watermark": False}
            if final is None: final = out_file
        # thumbnail at 1 sec
        thumb = clip_dir/"thumbnail.jpg"
        run(["ffmpeg","-y","-ss","1","-i",str(final),"-frames:v","1",str(thumb)])
        title, tags = make_title_hashtags(c["text"])
        c["score"]["face_pct"] = face_pct
        results.append({"clip": idx, "file": str(final), "downloads": downloads, "thumbnail": str(thumb),
                        "watermark": False,
                        "subtitle_language": subtitle_language or ("en" if translate else "auto"),
                        "subtitle_language_name": SUBTITLE_LANGUAGES.get(subtitle_language or ("en" if translate else "auto"), subtitle_language),
                        "video_language": language or "auto",
                        "start": round(c["start"],2), "end": round(c["end"],2),
                        "duration": round(c["end"]-c["start"],2), "viral_score": c["score"],
                        "title": title, "hashtags": tags, "text": c["text"][:500],
                        "source_license": info.get("license"), "copyright_status": info.get("copyright_status"),
                        "source_title": info.get("title"), "source_uploader": info.get("uploader")})
    (outdir/"clips.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return results

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url"); ap.add_argument("--file")
    ap.add_argument("--clips", type=int, default=5, help="Kitni clips chahiye: 1, 2, 3, 4, 5, 10 ya jitni chahiye")
    ap.add_argument("--fit", choices=["face","blur"], default="face")
    ap.add_argument("--language", default="auto", help="Video ki language: auto ya language code: en ur hi ar es fr de pt tr id bn pa ... (Whisper 99 languages)")
    ap.add_argument("--subtitle-language", default="auto", choices=list(SUBTITLE_LANGUAGES.keys()),
                    help="Clip ke subtitles ki language khud select karo: auto (video wali), none (without subtitles), ya en/ur/hi/ar/es/fr/de/pt/tr/id/bn/pa/ru/ja/ko/zh")
    ap.add_argument("--no-subtitles", action="store_true", help="Without subtitles clips banao (saaf clip, koi captions nahi)")
    ap.add_argument("--translate-to-english", action="store_true", help="Subtitles ko English mein translate kar do (purana option, --subtitle-language en ke barabar)")
    ap.add_argument("--min-sec", type=int, default=25)
    ap.add_argument("--max-sec", type=int, default=60)
    ap.add_argument("--no-emoji", action="store_true")
    ap.add_argument("--qualities", default="720p,1080p", help="Download qualities, comma se alag: 720p,1080p,2k,4k (har ek ki alag file, without watermark)")
    ap.add_argument("--i-own-this", action="store_true", help="Confirm karo ke ye meri apni video hai ya mere paas permission hai")
    ap.add_argument("--out", default="output")
    a = ap.parse_args()
    if not a.url and not a.file:
        ap.error("--url ya --file lazmi hai")
    lang = None if a.language.lower() == "auto" else a.language.lower()
    sub_lang = a.subtitle_language.lower()
    if a.no_subtitles:
        sub_lang = "none"
    elif a.translate_to_english and sub_lang == "auto":
        sub_lang = "en"
    quals = tuple(q.strip() for q in a.qualities.split(",") if q.strip())
    process(url=a.url, file=a.file, max_clips=a.clips, fit=a.fit, use_emoji=not a.no_emoji, out_root=a.out,
            language=lang, translate=a.translate_to_english, subtitle_language=sub_lang,
            min_sec=a.min_sec, max_sec=a.max_sec,
            qualities=quals, i_own_this=a.i_own_this)
