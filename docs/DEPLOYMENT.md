# Deploying MusicAI on a VPS (Hostinger, DigitalOcean, etc.)

Normal VPS servers have **no GPU**, so the app runs on your server while
generation runs on **Replicate's cloud GPUs** (same open-source ACE-Step
model — still watermark-free and commercially usable). You pay Replicate
per song (~$0.03–0.06, i.e. ₹3–5).

> **Hostinger note:** you need a **VPS plan** (KVM 1/2/4/8) with Ubuntu.
> Shared/web hosting plans cannot run a Python server.

## 1. Get a Replicate API token

1. Sign up at https://replicate.com and add a payment method.
2. Create a token at https://replicate.com/account/api-tokens (starts with `r8_`).

## 2. Set up the server

SSH into your VPS (Hostinger hPanel → VPS → SSH access):

```bash
ssh root@YOUR_SERVER_IP

apt update && apt install -y python3-venv python3-pip ffmpeg nginx git \
    apache2-utils certbot python3-certbot-nginx

git clone https://github.com/ppratik2026/Musicai.git /opt/musicai
cd /opt/musicai
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 3. Configure environment

```bash
cat > /etc/musicai.env <<'EOF'
MUSICAI_ENGINE=replicate
REPLICATE_API_TOKEN=r8_PASTE_YOUR_TOKEN_HERE
MUSICAI_DATA_DIR=/opt/musicai/data
EOF
chmod 600 /etc/musicai.env
```

## 4. Run as a systemd service

```bash
cat > /etc/systemd/system/musicai.service <<'EOF'
[Unit]
Description=MusicAI Studio
After=network.target

[Service]
WorkingDirectory=/opt/musicai
EnvironmentFile=/etc/musicai.env
ExecStart=/opt/musicai/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now musicai
systemctl status musicai   # should say "active (running)"
```

## 5. Point your domain

In Hostinger hPanel → Domains → DNS, add an **A record**:
`music.yourdomain.com → YOUR_SERVER_IP`

## 6. Nginx reverse proxy + password + HTTPS

**Password protection is essential** — every generation costs you money,
so don't leave the app open to the whole internet.

```bash
# Create a login (you'll be prompted for a password)
htpasswd -c /etc/nginx/.htpasswd yourname

cat > /etc/nginx/sites-available/musicai <<'EOF'
server {
    listen 80;
    server_name music.yourdomain.com;

    auth_basic "MusicAI Studio";
    auth_basic_user_file /etc/nginx/.htpasswd;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 900s;
    }
}
EOF

ln -s /etc/nginx/sites-available/musicai /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Free HTTPS certificate
certbot --nginx -d music.yourdomain.com
```

Open **https://music.yourdomain.com**, log in, and generate. 🎵

## Updating the app

```bash
cd /opt/musicai && git pull
.venv/bin/pip install -r requirements.txt
systemctl restart musicai
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `systemctl status musicai` shows failed | `journalctl -u musicai -n 50` for the error |
| Track errors with `Replicate API error 401` | Wrong/missing `REPLICATE_API_TOKEN` in `/etc/musicai.env` |
| Track errors with `Replicate API error 402` | Add billing/credit on replicate.com |
| Replicate rejects an input field | The hosted model's fields changed — set `MUSICAI_REPLICATE_MODEL` / `MUSICAI_REPLICATE_INPUT_MAP` (see `app/engines/replicate_engine.py`) |
| 413 on cover upload | `client_max_body_size` in the nginx config |

## Engine settings reference

| Env var | Default | Meaning |
|---|---|---|
| `REPLICATE_API_TOKEN` | — | Enables the Replicate engine |
| `MUSICAI_REPLICATE_MODEL` | `lucataco/ace-step` | Hosted model to call |
| `MUSICAI_REPLICATE_INPUT_MAP` | prompt→tags, lyrics→lyrics, … | JSON mapping of our fields to the model's input names |

## Alternative: your own GPU server

If you later rent a GPU VPS (RunPod, Vast.ai, Lightning), skip Replicate:
install `requirements-models.txt` and set `MUSICAI_ENGINE=ace_step` — same
app, generation happens locally, no per-song cost.
