# Voyager 1: one light-day from Earth (41 s Short)

`voyager_one_light_day.mp4` is a 1080×1920, 30 fps vertical Short. It is 41.3 s long, with voiceover, word-by-word captions, music and sound effects. The audio is mixed to −14 LUFS.

## Why this topic

On **Nov 18, 2026** Voyager 1 became the first human-made object to reach one light-day (about 16 billion miles) from Earth. It is fresh news with a strong "wait, what?" angle: a message sent to it today arrives tomorrow. It is also safe to monetise, with no brands and no real-person quotes, and it suits the cartoon explainer style.

The runner-up topic was GTA VI's record $3.79B launch day (Nov 19). Thousands of channels are already covering it, and a cartoon would have to avoid showing the game at all.

## What the two retention graphs say

| | Video 1 (0:54) | Video 2 (0:57) |
|---|---|---|
| Stayed to watch | 57.5% | 53.3% |
| Avg view duration | 0:23 | 0:28 |
| Avg % viewed | 43.0% | 49.4% |

1. **The first 3–4 s work.** Both curves start above 100%, which means people rewatch the opening.
2. **The big loss is between 0:04 and 0:12.** Both videos drop from about 105–110% to about 50%. Whatever follows the hook loses half the audience. Typical causes are a setup or context beat, a slower scene, or a like/subscribe ask. (The cartoon-documentary skill puts its CTA right after the cold open, which would land exactly here.)
3. **After that, a slow, steady loss.** The curves fall from about 45% to 25–30% with no bumps, so nothing in the middle re-hooks people.
4. **The ending drops off instead of looping.** Video 1 ends at about 13%. Neither video sends viewers back to the start.
5. **About 45% swipe away immediately** (only 53–57% stayed to watch), so the first frame and first line need to be stronger.

## What this video changes

| Problem | Fix in this Short |
|---|---|
| Drop at 0:04–0:12 | No CTA, no intro, no backstory. The second beat raises the stakes: Nov 18, "first human-made object", 16 billion miles. |
| Swipe-aways | The first frame already shows the spacecraft and the caption "THIS SPACECRAFT IS…", and the first line is the whole hook. |
| Slow bleed | A new shot every 1.5–3 s, and a pop, stamp or tag with a sound on every key number. |
| Nothing pulling viewers forward | At 0:12 an open loop starts: "And it's running out of power," with a red battery. It pays off at 0:28–0:36 when the engineer switches instruments off ("Sorry, buddy."). |
| Abstract numbers | Each one is compared to something everyday: today vs. tomorrow, memory vs. one phone photo, the radio vs. a fridge bulb. |
| Drop at the end | It loops. The last line, "So if you ever want to say goodbye, remember:", runs straight into the first: "This spacecraft is so far away, a message you send it today arrives tomorrow." No fade at the end. |
| Too long | 41 s instead of 54–57 s. |

In YouTube Studio, compare the 0:04–0:12 segment against the earlier two. That's the number this video is designed to move.

## Upload copy

**Title:** Voyager 1 Is So Far Away, Your Text Arrives Tomorrow

**Description:**
On November 18, 2026, NASA's Voyager 1 became the first human-made object to reach one light-day from Earth, about 16 billion miles. A signal now takes a full day to reach it. It has been flying since 1977 on about 70 KB of memory, and it is slowly running out of power.

If you could send Voyager one message, what would it say? 👇

Figures as of November 2026, from NASA's announcement and reporting by NPR, CNN, EarthSky, Scientific American, NRAO and JPL.

#Voyager1 #NASA #Space #Shorts

**Pinned comment idea:** "What would you text Voyager 1? It would get it tomorrow."

**Thumbnail/cover frame:** the frame at about 0:04, with the phone, the "good morning!" bubble and the red TOMORROW stamp.

## Fact check (sources)

- One light-day reached on Nov 18, 2026; about 16 billion miles; one-way signal about 24 h, round trip about 48 h: [NASA release](https://www.nasa.gov/news-release/nasas-voyager-1-makes-history-reaching-one-light-day-from-earth/), [NPR](https://www.npr.org/2026/11/17/nx-s1-6043115/nasas-voyager-1-spacecraft-reaches-a-distance-of-1-light-day-from-earth), [EarthSky](https://earthsky.org/space/voyager-1-1-light-day-from-earth-november-17-18-2026/), [CNN](https://www.cnn.com/2025/12/09/science/voyager-1-light-day-earth), [Scientific American](https://www.scientificamerican.com/article/voyager-1-reaches-one-light-day-milestone/)
- Launched in 1977, about 38,000 mph: [NBC News](https://www.nbcnews.com/science/space/nasa-voyager-1-probe-light-day-from-earth-distance-rcna610005), [ScienceDaily](https://www.sciencedaily.com/releases/2026/11/261120075554.htm)
- About 69.63 KB of computer memory (shown as "70 KB"): [Scientific American, "Voyager Deconstructed"](https://www.scientificamerican.com/blog/life-unbounded/voyager-deconstructed/)
- Transmitter about 22 W, weaker than a fridge bulb: [MakeTechEasier](https://maketecheasier.com/voyager-1-signal-power-distance/), [19FortyFive](https://www.19fortyfive.com/2026/07/nasas-voyager-1-radio-transmitter-is-weaker-than-a-refrigerator-lightbulb-it-still-reaches-earth-from-15-billion-miles-away/)
- Under an attowatt (a billionth of a billionth of a watt) when it reaches Earth: [NRAO](https://public.nrao.edu/?p=13946)
- Power falls about 4 W a year; LECP switched off in April 2026, leaving 2 science instruments (magnetometer, plasma wave): [JPL](https://www.jpl.nasa.gov/news/nasa-shuts-off-instrument-on-voyager-1-to-keep-spacecraft-operating/), [Hypebeast](https://hypebeast.com/2026/7/nasa-voyager-1-nears-one-light-day-as-power-fades)

Simplifications: "one photo ≈ 3,000 KB" is a typical phone JPEG. The engineer's "Sorry, buddy." is an invented line for a generic cartoon character, not a quote.

## How it was made / rebuild

- **Script:** `lines.json`, one entry per voice line.
- **Voice:** Kokoro TTS (`kokoro-onnx`, Apache-2.0). The narrator is `af_heart`, chosen from Kokoro's published quality grades without listening to it here. The engineer is `am_michael`. Speed is 1.12.
- **Timing:** `assemble_vo.py` trims the lines, lays them on one timeline and writes `timeline.json` with per-word times.
- **Visuals:** `video.py`, built on the cartoon-documentary engine (`engine.py`, switched to vertical with a loop-friendly end). Everything is drawn in code.
- **Music/SFX:** synthesised by `engine.build_bed`, so they are royalty-free.

```bash
python -m venv venv && . venv/bin/activate && pip install pycairo numpy pillow kokoro-onnx soundfile
# kokoro-v1.0.onnx + voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0) -> TTS_DIR
python gen_vo.py TTS_DIR lines.json VO_DIR            # one wav per line (see below)
python assemble_vo.py VO_DIR lines.json .             # narration.wav + timeline.json
python video.py stills OUT_DIR 1 5 12                 # check frames
python video.py render part.mp4 0 99                  # or split into chunks and run them in parallel
python video.py bed bed.wav
ffmpeg -i narration.wav -i bed.wav -filter_complex "[0:a]aresample=44100,apad[v];[1:a]volume=0.5[b];[v][b]amix=inputs=2:duration=shortest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.89[a]" -map "[a]" -ar 44100 final_audio.wav
ffmpeg -i part.mp4 -i final_audio.wav -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart voyager_one_light_day.mp4
```
