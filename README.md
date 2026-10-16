<h1 align="center">meetrec</h1>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/LICENSE-MIT-5C9E31?style=for-the-badge" alt="License"></a>
  <img src="https://img.shields.io/badge/PLATFORM-MACOS-000000?style=for-the-badge&logo=apple&logoColor=white" alt="macOS">
  <img src="https://img.shields.io/badge/100%25-LOCAL-brightgreen?style=for-the-badge" alt="Local only">
  <img src="https://img.shields.io/badge/NO-CLOUD%20ACCOUNT-8A2BE2?style=for-the-badge" alt="No cloud account">
</p>

<p align="center"><strong>Record meetings on macOS and transcribe them locally. Keeps the audio, so a bad summary is never the end of the road.</strong></p>

---

## Overview

Meeting-notes services summarize and throw the recording away. When the summary is wrong, and on room audio it often is, there's nothing to go back to.

`meetrec` records to disk first and treats the transcript as a derived artifact you can regenerate with a better model, a different language, or more patience. Recording is `ffmpeg`, transcription is `whisper.cpp` on Metal. Nothing is uploaded and no account is involved.

It's macOS-only: recording relies on Core Audio process taps, ffmpeg's AVFoundation input and macOS audio routing, none of which exist on Linux or Windows.

There's no integration with Teams, Meet or Zoom, and no bot joins the call. It captures whatever plays out of the speakers plus your mic, so the meeting platform is irrelevant. A phone on speaker next to the laptop works the same way.

## Install

```bash
brew install ffmpeg whisper-cpp switchaudio-osx

# system audio: audiotee uses Core Audio process taps (macOS 14.2+), no virtual device
git clone https://github.com/makeusabrew/audiotee.git
(cd audiotee && swift build -c release) && cp audiotee/.build/release/audiotee ~/.local/bin/

git clone https://github.com/jgalea/meetrec.git
ln -sf "$PWD/meetrec/bin/meetrec" ~/.local/bin/meetrec

meetrec fetch-model large   # 3,1 GB, for meetings that matter
meetrec fetch-model turbo   # 1,5 GB, ~3x faster, for quick internal calls
meetrec fetch-model vad     # 865 KB, required
meetrec check               # verifies the lot, including a live capture test
```

Your terminal needs Microphone permission and System Audio Recording permission (System Settings > Privacy & Security). macOS asks for the second one the first time `audiotee` runs.

Without `audiotee`, `call` falls back to the [Background Music](https://github.com/kyleneideck/BackgroundMusic) virtual device (`brew install --cask background-music`), which needs every app's audio routed through it. On macOS 26 it garbled playback and its capture device hung, so treat it as a last resort. `MEETREC_BGM=1` forces it.

## Video calls

```bash
meetrec check                # once, before the first call of the day
meetrec call acme-kickoff    # start this, then join the meeting
# ... meeting ...
meetrec stop
meetrec transcribe acme-kickoff --model large --lang es
```

`call` taps whatever the Mac plays, before it reaches your speakers or headphones. Nothing in the output path changes, so the meeting app can use any speaker, including AirPods.

Two files come out: `*.them.wav` (system audio, everyone else) and `*.me.wav` (your mic). They're written by separate `ffmpeg` processes, so a device dropping out mid-meeting can't take the other side of the conversation with it. Separate tracks also give speaker labels for free, with no diarization model. `stop` reports a peak level per track and says outright if one captured nothing.

Things worth knowing before your first real call:

**Set the meeting app's mic to the built-in one or "System default", never a wireless headset.** Teams, Zoom and the WhatsApp desktop app each have their own mic picker, and that choice never shows up in the system settings.

**Wear headphones.** On speakers the far end bleeds into your mic and both tracks transcribe the same words twice.

**Wireless headsets can't be both speaker and mic.** Opening an AirPods mic drops the headset into headset mode: output falls from 48 kHz to 24 kHz and the call stutters. When the mic and speaker resolve to the same wireless device, `call` records from the built-in mic instead. Override with `MEETREC_MIC`. A guard checks every 10 seconds, logging to a `.guard.log` beside the recording. It moves the system mic back off the headset, and when an app opens the headset mic through its own settings, it spots the sample-rate drop and raises a notification.

**A capture can stall without exiting.** When Core Audio hiccups, ffmpeg can keep running while its file stops growing, so one side of the call records nothing. The guard checks both files every 10 seconds and raises a notification on a stall. `stop` force-kills a hung capture so it can't keep holding the device into the next recording.

## In-person meetings

Room audio is what kills transcripts. A laptop mic across a table, two or more speakers, cross-talk, and any summarizer produces mush. No transcription model rescues this; the microphone has to be better.

Best option is a clip-on wireless mic recording internally (a DJI Mic Mini or similar), placed near whoever talks most, then:

```bash
meetrec import ~/Downloads/DJI_01.WAV acme-office
meetrec transcribe acme-office --model large --lang es
```

Two transmitters is better still, because you get real speaker separation. Import them as `<base>.them.wav` and `<base>.me.wav` and `transcribe` labels the speakers.

Fallback, built-in mic:

```bash
meetrec room acme-office        # MEETREC_ROOM_DEVICE=<n> to pick another input
```

## Transcription

```bash
meetrec transcribe <file|base|slug> [--model turbo|large] [--lang es]
```

Writes `<base>.transcript.md`: timestamped, with `**THEM:**` / `**ME:**` labels on two-track sources. Re-run it with different settings as often as you like, the audio doesn't go anywhere.

`large` is meaningfully better on accented speech, overlapping speakers and room audio. `turbo` is fine for clean solo recordings.

Silero VAD is always on. Without it Whisper hallucinates filler into stretches where a channel is silent, and on a two-track call that's most of the file. The usual tells are a polite closing line the speaker never said, or a repeated phrase filling a gap.

## Commands

```
meetrec check                 pre-flight: tools, models, and a live 3s capture test
meetrec call <slug>           record a video call (system audio + your mic)
meetrec room <slug>           record in person from a mic device
meetrec stop                  stop and finalize, restore audio devices
meetrec status                is anything recording
meetrec import <file> [slug]  bring in an external recording
meetrec transcribe <target>   transcribe to markdown
meetrec fetch-model <name>    turbo | large | vad
meetrec devices               list audio inputs
meetrec list                  recordings, newest first
```

Env: `MEETREC_DIR` (default `~/Recordings/meetings`), `MEETREC_LANG` (default `es`), `MEETREC_MIC`, `MEETREC_ROOM_DEVICE`.

## Notes

- WAV, 48 kHz, mono per track, roughly 350 MB per hour per track. Crash-tolerant, unlike a half-written compressed file.
- `caffeinate` holds off sleep while recording.
- A per-track `.log` sits next to the audio if a capture misbehaves.
- The transcript is plain markdown, so handing it to an LLM for a write-up is the obvious next step. Give it the whole file rather than a summary of a summary, and make it state how good the audio was before it writes anything, so bad audio doesn't get laundered into confident notes.

## Consent

Recording laws differ by country and some require every participant's consent. Check your own jurisdiction. Telling people you're recording is the right call regardless, and it makes asking for the file later normal rather than awkward.

## License

MIT
