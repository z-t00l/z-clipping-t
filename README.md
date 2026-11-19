# Zubi AI Clipping Tool — Free

Long YouTube video / stream -> best viral Shorts / Reels / TikTok / Facebook Reels clips.
Bilkul free, open source. Koi paid API nahi.

## Features
- **Face tracking**: OpenCV face detection, smooth crop following the speaker. No face? Center fallback or Blur mode.
- **Auto subtitles**: YouTube captions if available (har language), warna faster-whisper (base, int8) word timestamps. 3-word pop captions, ASS burn-in.
- **Auto emoji**: Keyword-based emoji in captions (money 💰, secret 🤫, fire 🔥, love ❤️, etc, English + Roman Urdu words).
- **Viral score**: Hook 40% + Pacing 35% + Engagement 25%, har clip ka breakdown.
- **Clips quantity input**: 1, 2, 3, 4, 5, 10 ya jitni chahiye — web UI mein chips + number input, CLI mein `--clips N`.
- **Har language**: `--language auto` (Whisper 99 languages auto-detect) ya specific code `ur/en/hi/ar/es/fr/de/pt/tr/id/bn/pa`. `--translate-to-english` se subtitles English mein bhi ho sakti hain.
- **Subtitles language khud select karo**: `--subtitle-language auto|none|en|ur|hi|ar|es|fr|de|pt|tr|id|bn|pa|ru|ja|ko|zh`. `auto` = video wali language, `none` = **without subtitles** saaf clips (ya `--no-subtitles`). Dusri language select karne par subtitles YouTube captions se ya auto-translate (Google/MyMemory) se bante hain — translation kabhi kabhi perfect nahi hoti. Web UI aur GitHub Actions mein bhi yehi select option hai.
- **Extra best features**: Hook title pehle 3 sec, loudness normalize (-14 LUFS), auto thumbnail, title + hashtags, 9:16 export, Blur mode.
- **Download qualities (without watermark)**: Har clip ki alag files — HD 720p (720x1280), Full HD 1080p (1080x1920), 2K (1440x2560), 4K (2160x3840). `--qualities 720p,1080p,2k,4k`. Koi watermark nahi lagta.
  - Sach: Source 720p hai to 4K file sirf upscale hogi, real detail nahi barhegi, file bari aur slow hogi. Best result ke liye source bhi HD/4K ho.
- **Copyright check**: Tool YouTube license check karke `clips.json` mein warning deta hai. **Clip karne se copyrighted video copyright-free NAHI banti.** Sirf apni, Creative Commons, public domain, ya permission wali video safe hai. `--i-own-this` se confirm kar sakte ho ke video tumhari hai / permission hai.

## Free GitHub par chalana (paisay nahi lagtay)
1. GitHub account banao (github.com, free).
2. Is repo ko apnay GitHub par push karo (public repo par Actions zyada free milta hai).
3. **Web UI free**: Settings → Pages → Source: `web/` folder (ya root se `web/index.html` publish karo). Page free host ho jayegi.
4. **Clips free banana**: Repo mein **Actions → Make Clips (Free) → Run workflow** → YouTube link, clips quantity (1..jitni chahiye), language (auto), fit (face/blur) dalo → Run. Clips **Artifacts** mein download hongi.
5. **APK free banana**: **Actions → Build APK (Free) → Run workflow** → APK artifact `zubi-clip-tool-apk` download karke phone mein install karo.

> Note: GitHub Actions ke free minutes ki limit hoti hai (public repo par aam tor par zyada miltay hain). Lambi video = zyada time. YouTube ki apni terms ka khayal rakho, sirf apni ya permission wali videos clip karo.

## Computer par chalana
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python clipper.py --url "https://www.youtube.com/watch?v=XXXX" --clips 10 --language auto --fit face --qualities 720p,1080p,2k,4k
.venv/bin/python clipper.py --url "https://www.youtube.com/watch?v=XXXX" --clips 5 --subtitle-language ur
.venv/bin/python clipper.py --url "https://www.youtube.com/watch?v=XXXX" --clips 5 --no-subtitles
.venv/bin/python clipper.py --file video.mp4 --clips 1 --fit blur --language ur
```
Output: `output/clips.json`, har clip `output/clip_01/clip_01_9x16.mp4` + `thumbnail.jpg`

## APK
`android/` mein simple WebView APK project hai jo `web/index.html` ko phone par chalata hai (link, clips quantity, language, face/blur, emoji).
Phone par Whisper + face tracking heavy hai, is liye asli processing GitHub Actions (free) ya computer/Muse par hoti hai, APK UI/job ke liye hai.
APK build: GitHub Actions `Build APK (Free)` workflow, ya Android Studio se `android/` khol kar Build.

## Requirements
- ffmpeg, Python 3.12
- yt-dlp, opencv-python-headless==4.10.0.84, faster-whisper (sab free/open source)

## Limits (MVP)
- Face tracking Haar cascade hai, side face / crowd mein kamzor ho sakta hai. Agla step YuNet/MediaPipe.
- Whisper base CPU par slow hai, lambi video mein time lagega. YouTube captions hon to fast hai.
- Viral score heuristic hai, ScaleReach jaisa trained model nahi. Transcript ke hook/emotion/pace par based hai.
- APK abhi WebView UI hai, on-phone full processing nahi. Processing free backend (GitHub Actions) par hai.
