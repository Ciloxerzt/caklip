# Caklip - AI Auto Clipper

## Singkatnya
Caklip merangkum video jadi klip pendek (TikTok/Shorts/Reels) pakai FFmpeg + AI opsional. **Tidak ada AI slop** — semua fitur either work atau tidak ada. Bisa dipakai dari file video lokal atau YouTube URL.

## Fitur (9/9 Sudah Jadi)

1. **Face Auto Tracker** — OpenCV mendeteksi wajah, crop mengikuti saat 9:16
2. **Zoom Otomatis** — FFmpeg zoompan effect, parameter `zoom-factor`
3. **Fade In/Out Audio** — Durasi configurable `fade-in` / `fade-out`
4. **Sound Effect** — 6 opsi: none, fade_in, fade_out, both, crossfade, reverb
5. **Audio Preset** — speech, music, voice dengan loudnorm normalization
6. **Font Options** — 8 gaya: clean, bold, podcast, viral, karaoke, news, educational, gaming
7. **Podcast Mode** — Layout 2 orang samping kiri-kanan
8. **Video Presets** — TikTok, YouTube Shorts, Ig Reels, Twitter, Custom
9. **AI Optional** — Auto-detect model dari API key (OpenAI/Gemini/Anthropic/bai-free), generate 1-10 clips dengan timestamp, hook, reason, score

## Instal

```bash
# Extract zip
unzip caklip-package.zip -d caklip

# Masuk directory
cd caklip

# Jalankan installer otomatis
bash caklip-installer.sh
```

## Cara Pakai

### Dari File Lokal (100% aman):

```bash
caklip video.mp4 --output ./clips --preset tiktok --face-tracking --start 0 --end 60
```

### Dengan AI (auto-detect model dari key):

```bash
caklip video.mp4 --output ./clips --preset tiktok \
  --face-tracking --start 0 --end 180
# AI akan auto-select model: gpt-4o-mini (OpenAI), gemini-1.5-flash (Google), dll
```

### Dari YouTube URL (coba extract):

```bash
caklip https://youtu.be/VIDEO_ID --output ./clips --preset tiktok --face-tracking --start 0 --end 60
# Kalau gagal → ke mode file lokal
```

## Kontribusi & Lisensi

**Copyright (c) 2026 xyclo. Semua hak tervar.**

Proyek ini dibuat untuk kebutuhan pribadi dan open source. Boleh di-modifikasi dan didistribusikan asal mencantumkan krediter.

---

**Bangun bergilir, jangan buat AI slop.**