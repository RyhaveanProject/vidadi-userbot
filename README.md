# Ryhavean Userbot

Telegram **userbot** (Pyrogram + py-tgcalls).
Hazırlanma: 2026 — Railway üçün optimallaşdırılıb.

## Komandalar

| Komanda | Yer | İş |
|---|---|---|
| `.play <mahnı adı>` | Qrup | YouTube-dan tapıb səsli söhbətdə oxuyur. |
| `.play` (audio reply-da) | Qrup | Reply olunmuş audionu səsli söhbətdə oxuyur. |
| `.end` / `.stop` / `.leave` | Qrup | Səsli söhbətdən çıxır. |
| `.pause` / `.resume` | Qrup | Pauza / davam. |
| `.song <mahnı adı>` | Qrup + Şəxsi | `@SongFastBot`-dan mahnını gətirib (cover = qara fon + ağ **R**, artist = **@Ryhavean**) reply ilə göndərir. |

> Kommandlar hər kəs tərəfindən işlədilə bilər (təhlükəsizliyi sevirsənsə, `modules/play.py` və `modules/song.py` içində `filters.me` əlavə edə bilərsən).
> Şəxsi söhbətlərdə yalnız `.song` cavab verir.
> Səsli söhbət yoxdursa və userbot-un “Manage Voice Chats” icazəsi varsa, `.play` özü açır.

## Tələblər (Railway avtomatik quraşdırır)

- Python 3.11
- ffmpeg
- DejaVu fontu (cover yazısı üçün)

## Quraşdırma adım-adım

### 1) Session string yaradın (lokal)

```bash
pip install pyrogram==2.0.106 TgCrypto==1.2.5
python generate_session.py
```

Çıxan uzun stringi yadda saxlayın.

### 2) Railway-də yeni proyekt

1. Bu repo-nu GitHub-a yükləyin (və ya ZIP-i Railway-də “Deploy from local” ilə açın).
2. **Variables** bölməsinə əlavə edin:

| Açar | Dəyər |
|---|---|
| `API_ID` | my.telegram.org-dan |
| `API_HASH` | my.telegram.org-dan |
| `SESSION_STRING` | yuxarıda generate etdiyiniz |
| `ARTIST_TAG` *(opsional)* | `@Ryhavean` (default) |
| `SONG_BOT` *(opsional)* | `SongFastBot` (default) |
| `COMMAND_PREFIXES` *(opsional)* | `.` (default) |

3. Deploy. Loglarda `Userbot started as @your_username` görəcəksiniz.

Railway həm `Dockerfile`-ı, həm də `nixpacks.toml`-u dəstəkləyir; layihədə hər ikisi var, **Dockerfile** üstünlük alır (railway.json).

## Faylların quruluşu

```
ryhavean-userbot/
├── main.py
├── app.py
├── config.py
├── modules/
│   ├── play.py     # .play, .end, .pause, .resume
│   └── song.py     # .song
├── utils/
│   ├── youtube.py  # yt-dlp wrapper
│   ├── cover.py    # qara fon + ağ R generator
│   └── metadata.py # mp3 tag/cover rewrite (mutagen)
├── requirements.txt
├── Dockerfile
├── Procfile
├── nixpacks.toml
├── railway.json
├── runtime.txt
├── generate_session.py
└── .env.example
```

## Performans qeydləri

- yt-dlp birbaşa stream URL-i çıxarır; ffmpeg `reconnect` flagları ilə (qoparsa yenidən bağlanır) py-tgcalls-a verilir → **donmasız, kəsintisiz**.
- `MediaStream(AudioQuality.HIGH)` 48 kHz / 2 ch.
- `@SongFastBot` qarşılıqlı işləməsi `asyncio.Lock` ilə serializə edilib ki, eyni anda iki sorğu bir-birinə qarışmasın.

## Tez-tez verilən suallar

**Sual:** `.play` deyir ki “Səsli söhbət aktiv deyil”
**Cavab:** Userbot-un qrupda admin və “Manage Voice Chats / Live streams” icazəsi olmalıdır ki, özü aça bilsin. Əks halda əvvəlcə əllə voice chat başladın.

**Sual:** `@SongFastBot` ban edib və ya başqa düymə formatı verir?
**Cavab:** `modules/song.py`-də `_wait_for_results` və düymə clickini öz bot variantınıza uyğunlaşdırın.

**Sual:** ffmpeg tapılmır.
**Cavab:** Dockerfile-da `ffmpeg` apt paketi var. Əgər nixpacks ilə deploy edirsinizsə, `nixpacks.toml`-dakı `ffmpeg` paketi mövcuddur.
