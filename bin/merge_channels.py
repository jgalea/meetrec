#!/usr/bin/env python3
"""Merge whisper.cpp JSON output into a timestamped, speaker-labelled transcript.

  merge_channels.py them.json me.json   -> two-speaker transcript
  merge_channels.py mono.json           -> single-track transcript
"""
import json
import sys
from pathlib import Path

GAP_MS = 1500  # merge consecutive segments from one speaker within this gap


def load(path, speaker):
    data = json.loads(Path(path).read_text())
    segments = data.get("transcription") or []
    out = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        offsets = seg.get("offsets") or {}
        out.append(
            {
                "start": offsets.get("from", 0),
                "end": offsets.get("to", 0),
                "text": text,
                "speaker": speaker,
            }
        )
    return out


def stamp(ms):
    m, s = divmod(int(ms) // 1000, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: merge_channels.py <them.json> [me.json]")

    if len(args) == 1:
        segments = load(args[0], None)
    else:
        segments = load(args[0], "THEM") + load(args[1], "ME")
    segments.sort(key=lambda s: s["start"])

    blocks = []
    for seg in segments:
        if (
            blocks
            and blocks[-1]["speaker"] == seg["speaker"]
            and seg["start"] - blocks[-1]["end"] <= GAP_MS
        ):
            blocks[-1]["text"] += " " + seg["text"]
            blocks[-1]["end"] = seg["end"]
        else:
            blocks.append(dict(seg))

    for b in blocks:
        label = f"**{b['speaker']}:** " if b["speaker"] else ""
        print(f"[{stamp(b['start'])}] {label}{b['text']}\n")


if __name__ == "__main__":
    main()
