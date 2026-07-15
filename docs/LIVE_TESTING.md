# Testing MusicAI live — three ways

## Option 1 — 2-minute test on your laptop (no GPU)

Verifies the whole app: UI, generation queue, playback, WAV/MP3/FLAC
downloads, metadata, cover art. Uses the built-in demo synth engine
(placeholder music, not real AI).

```bash
git clone https://github.com/ppratik2026/Musicai.git
cd Musicai
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Open http://localhost:8000, click a style preset, hit **⚡ Generate** — a
track appears in the library within seconds. Download the MP3 and check the
title/artist metadata shows up in your music player.

> MP3/FLAC export needs `ffmpeg` (`sudo apt install ffmpeg` /
> `brew install ffmpeg` / `winget install ffmpeg`). WAV works without it.

## Option 2 — real AI songs on a FREE Google Colab GPU

The repo ships a ready-made notebook: [`colab/MusicAI_Colab.ipynb`](../colab/MusicAI_Colab.ipynb)

1. Open https://colab.research.google.com → **File → Open notebook →
   GitHub** → paste `ppratik2026/Musicai` → open `colab/MusicAI_Colab.ipynb`.
   (Or use the badge in the README.)
2. **Runtime → Change runtime type → T4 GPU** (free).
3. **Runtime → Run all.** Setup takes ~5–10 minutes.
4. The last cell prints a public `https://….trycloudflare.com` URL — open it
   on any device and generate real songs with vocals via ACE-Step.

Notes for the free T4:
- The first generation downloads ~7 GB of ACE-Step weights — one-time wait.
- T4 runs in float32 (auto-detected), so generation is slower; start with
  30–60 second tracks.
- Colab Pro's A100/L4 GPUs run bfloat16 and are several times faster.

## Option 3 — rented GPU for serious use (~$0.25–0.50/hour)

For full-length songs at good speed, rent an RTX 4090 / A100 machine on
[RunPod](https://runpod.io), [Vast.ai](https://vast.ai) or
[Lightning AI](https://lightning.ai):

```bash
git clone https://github.com/ppratik2026/Musicai.git
cd Musicai
pip install -r requirements.txt -r requirements-models.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Expose port 8000 through the provider's dashboard (they all support HTTP
port forwarding) and open the URL. Generate, download the WAV masters, then
shut the machine down — you only pay for the hours you use.

## What to check during a live test

- [ ] Generate with **ACE-Step**: style tags + `[verse]`/`[chorus]` lyrics →
      full song with vocals
- [ ] Play the track in the browser
- [ ] Set title + artist, upload cover art, download **MP3** → verify
      metadata and artwork appear in a music player
- [ ] Download the **WAV** master → this is the file you'd upload to a
      distributor (see [DISTRIBUTION.md](DISTRIBUTION.md))
