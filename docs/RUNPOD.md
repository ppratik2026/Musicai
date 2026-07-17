# Running MusicAI on a RunPod GPU

RunPod rents you a real GPU by the hour — the fastest way to generate
full-length songs. An RTX 4090 renders a 3-minute ACE-Step song in
roughly a minute, and you only pay while the pod runs.

## 1. Create an account and add credit

1. Sign up at https://runpod.io
2. **Billing** → add credit ($10 is plenty to start; unused credit stays).

## 2. Deploy a pod

1. **Pods → Deploy** (Secure Cloud is fine).
2. Pick a GPU — recommendations:

   | GPU | VRAM | Approx. price | Notes |
   |---|---|---|---|
   | **RTX 4090** | 24 GB | ~$0.35–0.70/hr | Best value, bfloat16 ✅ |
   | RTX 3090 | 24 GB | ~$0.25–0.45/hr | Cheaper, still great |
   | A100 80GB | 80 GB | ~$1.2–2/hr | Overkill for this |

3. Template: **RunPod PyTorch** (any recent version).
4. Click **Edit Template**:
   - **Expose HTTP Ports**: add `8000`
   - Container/Volume disk: at least **40 GB** (model weights ~7 GB + OS + deps)
5. **Deploy On-Demand**.

## 3. Install MusicAI

Open the pod's **Web Terminal** (Connect → Start Web Terminal) and run:

```bash
apt update && apt install -y ffmpeg git
git clone https://github.com/ppratik2026/Musicai.git
cd Musicai
pip install -r requirements.txt
pip install -r requirements-models.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 4. Open the app

Pod page → **Connect** → under *HTTP Services*, click port **8000**
(URL looks like `https://<pod-id>-8000.proxy.runpod.net`).

- Engine: **ACE-Step** (24 GB VRAM = default bfloat16, no offload needed — fast)
- Lyrics filled = vocals; empty = instrumental
- Duration up to 4:00

First generation downloads the ~7 GB checkpoints once; they persist as
long as the pod exists.

## 5. IMPORTANT — stop the meter

Billing runs while the pod is up, even idle.

- **Stop** the pod when done (you keep the disk, pay only a small storage
  fee, and can restart later without re-downloading anything).
- **Terminate** deletes everything and stops all charges.

## Cost math

A 3-minute song ≈ 1–2 minutes of 4090 time ≈ **$0.01–0.02 (₹1–2) per song**.
A 2-hour session of making an album: ~$1 (₹80–90).

## Tips

- Generation queue is serialized — fire several prompts and they render
  one after another; download the WAVs before terminating the pod.
- Keep the web terminal tab open (closing it doesn't kill the server,
  but reconnecting is easier).
- To run the server in the background instead:
  `nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > musicai.log 2>&1 &`
- For a permanent public studio, see [DEPLOYMENT.md](DEPLOYMENT.md)
  (Hostinger VPS + Replicate) — RunPod pods are for sessions, not 24×7
  hosting (a 24×7 4090 would be ~$250-500/month).
