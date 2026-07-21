#!/usr/bin/env python3
"""Generate JSQKV talk audio via OpenRouter -> MiniMax speech-2.8-hd.

Reuses the validated per-slide text from gen_audio.py (SLIDES).
Writes one MP3 per slide, then stitches a full-talk MP3.
API key is read ONLY from env var OPENROUTER_API_KEY (never hardcoded).
"""
import os
import sys
import time
import subprocess
import requests

from gen_audio import SLIDES, FFMPEG  # reuse validated text + bundled ffmpeg

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
URL = "https://openrouter.ai/api/v1/audio/speech"
MODEL = "minimax/speech-2.8-hd"
VOICE = os.environ.get("TTS_VOICE", "alloy")


def synth(text, retries=4):
    key = os.environ["OPENROUTER_API_KEY"]
    for attempt in range(retries):
        try:
            r = requests.post(
                URL,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json={"model": MODEL, "input": text, "voice": VOICE,
                      "response_format": "mp3"},
                timeout=300,
            )
            ctype = r.headers.get("content-type") or ""
            if r.status_code == 200 and "json" not in ctype:
                return r.content
            # error: show body, retry on 429/5xx
            print(f"    ! HTTP {r.status_code}: {r.text[:160]}")
            if r.status_code not in (429, 500, 502, 503, 529):
                raise SystemExit("  Non-retryable error; aborting.")
        except requests.RequestException as e:
            print(f"    ! {type(e).__name__}: {str(e)[:120]}")
        wait = 5 * (attempt + 1)
        print(f"    retrying in {wait}s ...")
        time.sleep(wait)
    raise SystemExit("  Gave up after retries.")


def mp3_seconds(path):
    """Duration in seconds via ffprobe-less ffmpeg (parse stderr)."""
    p = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    for line in p.stderr.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("Set OPENROUTER_API_KEY in the environment first.")
    os.makedirs(OUT, exist_ok=True)

    only = os.environ.get("RUN_ONLY")
    only_set = set(only.split(",")) if only else None

    for num, text in SLIDES:
        if only_set and num not in only_set:
            continue
        mp3 = os.path.join(OUT, f"slide_{num}.mp3")
        print(f"[{num}] synth ({len(text)} chars, voice={VOICE}) ...")
        data = synth(text)
        with open(mp3, "wb") as f:
            f.write(data)
        print(f"[{num}] ok -> {os.path.basename(mp3)}  ({mp3_seconds(mp3):0.1f}s)")
        time.sleep(int(os.environ.get("SLEEP_BETWEEN", "2")))

    # stitch full talk from all 14 slides present on disk
    present = [os.path.join(OUT, f"slide_{n}.mp3") for n, _ in SLIDES
               if os.path.exists(os.path.join(OUT, f"slide_{n}.mp3"))]
    if len(present) == len(SLIDES):
        concat_txt = os.path.join(OUT, "_concat.txt")
        with open(concat_txt, "w") as f:
            for m in present:
                f.write(f"file '{os.path.basename(m)}'\n")
        full = os.path.join(OUT, "JSQKV_full_talk.mp3")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat",
                        "-safe", "0", "-i", concat_txt, "-codec:a", "libmp3lame",
                        "-b:a", "192k", full], check=True, cwd=OUT)
        total = sum(mp3_seconds(m) for m in present)
        print(f"\nStitched full talk -> {full}")
        print(f"Total: {int(total//60)}m {int(total%60)}s")
    else:
        print(f"\nOnly {len(present)}/{len(SLIDES)} slides present; skipping stitch.")


if __name__ == "__main__":
    main()
