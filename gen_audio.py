#!/usr/bin/env python3
"""Generate JSQKV talk audio with Gemini TTS.

Per-slide WAV -> per-slide MP3 -> one stitched full MP3.
API key is read ONLY from env var GEMINI_API_KEY (never hardcoded).
Requires: google-genai, imageio-ffmpeg (both in .ppt_venv).
"""
import os
import sys
import time
import wave
import subprocess
from google import genai
from google.genai import types
import imageio_ffmpeg

VOICE = os.environ.get("TTS_VOICE", "Charon")
MODEL = "gemini-3.1-flash-tts-preview"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Per-slide text, tuned for spoken TTS: acronyms spaced so they're read as
# letters, numbers spelled the way they should sound, no SSML tags.
SLIDES = [
    ("01", """Good morning, everyone. Thank you for being here. My name is Hao Zhang, from the College of Computer Science at Nankai University. Today I'll present our work, J S Q K V, a joint sparsification and quantization framework for K V cache compression and decode acceleration. This is joint work with my collaborators at Nankai University, the National University of Defense Technology, and the Qian Xuesen Laboratory."""),

    ("02", """Let me start with the problem. As context windows keep growing, the real bottleneck of autoregressive decoding is no longer computation. It's the K V cache. The K V cache grows linearly with context length, and it is re-read at every single decode step. So in long-context serving, it dominates memory footprint and memory bandwidth, and it caps throughput, batch size, and deployment efficiency. The key point: decoding is memory-bound. Bandwidth, not floating-point operations, is the true limiter. To address this, the community has two mainstream directions: sparsification, evicting or pruning less useful K V states, and low-bit quantization, reducing the numerical precision of what's kept."""),

    ("03", """Both directions work well on their own. The natural idea is to simply combine them: sparsify, then quantize. But that naive chaining does not work, for two reasons. First, a representation and execution gap. Sparsification changes not just how much K V you keep, but the retained token and feature layout. That shifts quantization granularity, the compressed data layout, and the decode kernel, so algorithmic compression gains don't automatically become lower memory traffic. Second, an online decision gap. Token-differential compression is easy in prefill, where future attention is observable. But during decoding, a token must be cached before we know how important it will be. So the real challenge: preserve model quality under aggressive compression, and keep the compressed representation directly executable for real speedup."""),

    ("04", """Our answer is J S Q K V, a unified sparse-quant decode pipeline. Instead of treating sparsity and quantization as separate post-processing steps, we co-design three things together: the compression policy, the compressed format, and the execution path. Concretely, there are four contributions, and I'll walk through each: differential sparsity, a budgeted three-level token policy; a dual-window mechanism that makes it work online; Per-Token-Tile quantization with Hadamard rotation; and a bitmap-based sparse-quant kernel that loads compressed but computes dense."""),

    ("05", """First module: budgeted differential sparsity. The idea is simple. Not all tokens deserve the same compression. A fixed sparsity ratio wastes budget on unimportant tokens and over-compresses important ones. So we estimate token importance from prefill attention: each token's score is the average attention it receives from the last few observation-window queries, in the SnapKV style, length-normalized. Then we assign every token to one of three levels. Level zero, the most important, stays dense. Level one keeps only the top-magnitude features in its key and value vectors. Level two, the least important, is evicted entirely. Two percentile thresholds split the tokens under a target average budget B, and a small calibration search picks the best allocation at that fixed budget. As we'll see, this matters most when the budget is tight."""),

    ("06", """But that policy needs future attention, which we don't have when a token is first generated. That's the second module: the dual-window mechanism. The trick is to delay compression until enough future evidence accumulates. We keep two windows. Window A holds tokens waiting to be compressed. Window B holds newly generated tokens, and their queries observe Window A, supplying the missing future attention. Three steps: we accumulate each new query's attention to Window A; we normalize by the number of observations, since earlier tokens are seen by more queries; and we classify and slide, comparing against the same thresholds, compressing Window A into history, and Window B becomes the new Window A. Importantly, each token is observed before it's compressed, and the number of uncompressed tokens stays bounded. We also show these prefill thresholds are stable enough to reuse."""),

    ("07", """Third module: quantizing what remains. We use Per-Token-Tile quantization, splitting each key or value vector into small tiles, and quantizing each tile independently with its own scale and zero-point. This aligns the quantization unit with our token-level decisions and the tile-based decode path. The problem is that key states carry outliers that wreck aggressive low-bit quantization. Our fix is an orthogonal Hadamard rotation applied to queries and keys before quantizing. It suppresses the heavy tails you can see in the figure, and because it's orthogonal, it exactly preserves attention scores. The effect is dramatic. Look at the two-bit column: plain round-to-nearest blows up to a perplexity of one hundred fifteen, while Hadamard rotation brings it down to five point three five, and it stays compatible with the sparsification that follows."""),

    ("08", """The final module is where compression turns into real speedup. We co-design the storage format and the decode kernel. Each one-by-sixty-four tile stores a bitmap of nonzero positions, the packed low-bit values, a per-tile offset, and the quantization metadata, scales and zero-points. The kernel follows a load-as-compressed, compute-as-dense strategy: it loads the compact tiles from memory, unpacks and dequantizes them into dense shared-memory tiles, and then runs a standard Tensor-Core matrix-vector product. So sparsity is handled entirely on the loading path, where the memory savings are, while the compute stage stays dense and regular. That avoids the irregular memory access and control-flow divergence that usually kill sparse execution. This is exactly what a memory-bound decode stage needs."""),

    ("09", """Now to the evaluation. Everything runs on a single A one hundred, eighty gigabyte GPU, with custom CUDA and Triton kernels. For accuracy, we use the official LongBench pipeline on six representative tasks, with Llama 3, 8 B Instruct as the main model, plus Llama 2, Mistral, and Qwen 2.5. For efficiency, we measure end-to-end throughput and compression cost at batch sizes one through eight. Our baselines are dense decoding, a matched-budget uniform-sparsity baseline based on MUSTAFAR, and the sequential MUSTAFAR plus KIVI pipeline, which I'll call M plus K. We test both sparse-only and joint sparse-quant settings at fifty and seventy percent."""),

    ("10", """First, sparsity alone, to isolate the effect of budget allocation. No quantization yet. The takeaway is on the right. Our differential policy is greater than or equal to uniform sparsity in every setting. It never hurts. And the gain is larger at the tighter seventy percent budget than at fifty percent. That confirms the intuition from the method: token-level budget allocation matters most exactly when the budget is scarce."""),

    ("11", """Now the main result: the full joint sparse-quant pipeline against the sequential M plus K baseline, averaged over the six tasks. J S Q K V wins in all four settings, and, this is the key pattern, the gap widens as compression gets more aggressive. At the most aggressive setting, seventy seventy with two-bit, the average score jumps from thirty-nine point eight three, to forty-three point one two, a gain of over three points. Why does J S Q K V win? Because jointly aligning sparsity, quantization, and execution beats stacking two methods that were never designed to work together. The cross-model results tell the same story: favorable overall, and strongest under tight budgets."""),

    ("12", """And crucially, this quality holds up while delivering real speedup. On the left, end-to-end throughput versus batch size: the compressed paths pull ahead of dense decoding, with the clearest advantage in the small-to-medium batch regime. Overall, J S Q K V improves end-to-end throughput by up to forty-four percent over dense decoding. On the right, compression statistics. Compared to sparse-only MUSTAFAR seventy, our sparse-quant path pushes the compression ratio from two point zero nine times, up to three point four eight times. And notably, it also lowers the compression time, from about five thousand four hundred, down to four thousand three hundred milliseconds. So the more compact representation even cuts the write-back cost. Better compression and faster. Not a trade-off."""),

    ("13", """To conclude. Our central message is that K V cache compression should be treated as a systems-and-algorithms co-design problem, not a simple composition of independent post-processing steps. J S Q K V brings together four pieces: differential sparsity, the dual-window online mechanism, Hadamard-stabilized Per-Token-Tile quantization, and the sparse-quant kernel that turns compression into speedup. And the headline numbers, on Llama 3, 8 B: the average score improves from thirty-nine point eight three, to forty-three point one two, throughput improves by forty-four percent, and the K V cache is compressed by three point four eight times, all at the same time."""),

    ("14", """That's J S Q K V. Thank you very much for your attention. I'd be happy to take your questions."""),
]


def wave_file(fn, pcm, ch=1, rate=24000, sw=2):
    with wave.open(fn, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(sw)
        w.setframerate(rate)
        w.writeframes(pcm)


def synth(client, text, retries=4):
    for attempt in range(retries):
        try:
            r = client.models.generate_content(
                model=MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=VOICE)
                        )
                    ),
                ),
            )
            return r.candidates[0].content.parts[0].inline_data.data
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"    ! {type(e).__name__}: {str(e)[:120]} -- retry in {wait}s")
            time.sleep(wait)
    raise SystemExit("  Gave up after retries.")


def to_mp3(wav_path, mp3_path):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", wav_path,
                    "-codec:a", "libmp3lame", "-b:a", "192k", mp3_path], check=True)


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY in the environment first.")
    os.makedirs(OUT, exist_ok=True)
    client = genai.Client()

    # optional: only run a subset, e.g. RUN_ONLY="01,02"
    only = os.environ.get("RUN_ONLY")
    only_set = set(only.split(",")) if only else None

    mp3_list = []
    for num, text in SLIDES:
        if only_set and num not in only_set:
            continue
        wav = os.path.join(OUT, f"slide_{num}.wav")
        mp3 = os.path.join(OUT, f"slide_{num}.mp3")
        print(f"[{num}] synth ({len(text)} chars, voice={VOICE}) ...")
        pcm = synth(client, text)
        wave_file(wav, pcm)
        to_mp3(wav, mp3)
        dur = len(pcm) / (24000 * 2)
        print(f"[{num}] ok -> {os.path.basename(mp3)}  ({dur:0.1f}s)")
        mp3_list.append(mp3)
        time.sleep(int(os.environ.get("SLEEP_BETWEEN", "8")))

    # stitch all per-slide mp3s into one full talk (only when doing the full run)
    if not only_set:
        concat_txt = os.path.join(OUT, "_concat.txt")
        with open(concat_txt, "w") as f:
            for m in mp3_list:
                f.write(f"file '{os.path.basename(m)}'\n")
        full = os.path.join(OUT, "JSQKV_full_talk.mp3")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat",
                        "-safe", "0", "-i", concat_txt, "-codec:a", "libmp3lame",
                        "-b:a", "192k", full], check=True, cwd=OUT)
        # total duration
        total = 0.0
        for num, _ in SLIDES:
            w = os.path.join(OUT, f"slide_{num}.wav")
            if os.path.exists(w):
                with wave.open(w) as wf:
                    total += wf.getnframes() / wf.getframerate()
        print(f"\nStitched full talk -> {full}")
        print(f"Total duration: {int(total//60)}m {int(total%60)}s")


if __name__ == "__main__":
    main()
