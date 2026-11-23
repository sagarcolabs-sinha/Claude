import sys, json, soundfile as sf
from kokoro_onnx import Kokoro
tts, lines, out = sys.argv[1], sys.argv[2], sys.argv[3]
k = Kokoro(tts + "/kokoro-v1.0.onnx", tts + "/voices-v1.0.bin")
for L in json.load(open(lines)):
    a, sr = k.create(L["text"], voice=L["voice"], speed=1.12, lang="en-us")
    sf.write(f"{out}/{L['id']}.wav", a, sr); print(L["id"], round(len(a) / sr, 2), sr)
