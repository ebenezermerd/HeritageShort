"""Writes the Kaggle notebooks as .ipynb files. Run: python notebooks/build_notebooks.py

The notebooks are generated from this one file so the code is easy to review as text.
Nothing here has been run on Kaggle yet; see notebooks/README.md for the order to try them in.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip().splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip().splitlines(keepends=True)}


def save(name, cells):
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                                      "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}
    (HERE / f"{name}.ipynb").write_text(json.dumps(nb, indent=1))


BUNDLE = 'BUNDLE = next(p.parent for p in Path("/kaggle/input").rglob("storyboard.json"))  # the dataset from `make kaggle-bundle`, wherever Kaggle mounts it'

# ---------------------------------------------------------------- 00 smoke
save("00_smoke", [
    md("# 00 Smoke test\nSettings: Accelerator GPU T4 x2, Internet on. Run all cells, then write the GPU "
       "name, VRAM, free disk and the weekly GPU quota shown in Kaggle's sidebar into COSTS.md."),
    code("!nvidia-smi"),
    code("""
import shutil, torch
print("cuda:", torch.cuda.is_available())
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(i, p.name, round(p.total_memory / 1e9, 1), "GB")
print("free disk GB:", round(shutil.disk_usage("/kaggle/working").free / 1e9, 1))
"""),
])

# ---------------------------------------------------------------- 10 ace-step
ACE_SCRIPT = '''
import json, os, time
from pathlib import Path
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music

BUNDLE = next(p.parent for p in Path("/kaggle/input").rglob("storyboard.json"))  # the dataset from `make kaggle-bundle`, wherever Kaggle mounts it
OUT = Path("/kaggle/working/music")
OUT.mkdir(exist_ok=True)
LOG = Path("/kaggle/working/notebook_log.jsonl")
DONE = OUT / "done.json"
if DONE.exists():
    print("candidates already generated, nothing to do")
    raise SystemExit

music = json.loads((BUNDLE / "storyboard.json").read_text())["music"]
dit = AceStepHandler()
llm = LLMHandler()
root = os.getcwd()
dit.initialize_service(project_root=root, config_path="acestep-v15-turbo", device="cuda")
for backend in ("vllm", "pt"):
    try:
        llm.initialize(checkpoint_dir=os.path.join(root, "checkpoints"), lm_model_path="acestep-5Hz-lm-0.6B",
                       backend=backend, device="cuda")
        break
    except Exception as e:
        print("LLM backend", backend, "failed:", e)

params = GenerationParams(caption=music["caption"], bpm=music["bpm"], keyscale=music["key"],
                          duration=music["duration_s"], instrumental=True, seed=-1, lyrics="")
config = GenerationConfig(batch_size=3, audio_format="flac")
start = time.time()
result = generate_music(dit, llm, params, config, save_dir=str(OUT))
seconds = time.time() - start
if not result.success:
    raise SystemExit(f"ACE-Step failed: {result.error}")
paths = [a["path"] for a in result.audios]
with LOG.open("a") as f:
    f.write(json.dumps({"stage": "music", "model": "ace-step-1.5-turbo", "seconds": round(seconds, 1),
                        "candidates": paths, "seeds": [a["params"]["seed"] for a in result.audios]}) + "\\n")
DONE.write_text(json.dumps(paths))
print("done in", round(seconds), "s:", paths)
'''

save("10_acestep", [
    md("# 10 ACE-Step: three score candidates\nSettings: GPU on, Internet on. Add the dataset "
       "`heritage-short-bundle` (from `make kaggle-bundle`). Download `/kaggle/working/music/` and "
       "`notebook_log.jsonl` when it finishes."),
    code("""
!pip install -q uv
!git clone -q https://github.com/ACE-Step/ACE-Step-1.5.git /kaggle/working/ace
!cd /kaggle/working/ace && uv sync
"""),
    code("%%writefile /kaggle/working/gen_music.py\n" + ACE_SCRIPT.strip()),
    # Kaggle sets MPLBACKEND to its inline backend, which ACE-Step's own venv does not have (FAILURES #9).
    code("!cd /kaggle/working/ace && MPLBACKEND=Agg uv run python /kaggle/working/gen_music.py"),
])

# ---------------------------------------------------------------- 15 keyframes
KEYFRAME_SCRIPT = '''
import json, shutil, time
from pathlib import Path
import torch
from PIL import Image
from diffusers import Flux2KleinPipeline

JOBS = next(Path("/kaggle/input").rglob("image_jobs.json"))  # from `python -m pipeline.kaggle_images`
OUT = Path("/kaggle/working/images")
LOG = Path("/kaggle/working/notebook_log.jsonl")
jobs = json.loads(JOBS.read_text())
print(len(jobs), "jobs,", sum((OUT / j["out"]).exists() for j in jobs), "already done")

MODEL = "black-forest-labs/FLUX.2-klein-4B"  # Apache 2.0, not gated
try:  # two T4s: spread the text encoder and the transformer over both GPUs
    pipe = Flux2KleinPipeline.from_pretrained(MODEL, torch_dtype=torch.bfloat16, device_map="balanced")
    placement = "balanced"
except Exception as e:
    print("balanced placement failed, using CPU offload:", e)
    pipe = Flux2KleinPipeline.from_pretrained(MODEL, torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    placement = "cpu_offload"
try:  # the VAE decode ran out of memory on a T4 at full size (FAILURES #12): decode in tiles
    pipe.vae.enable_tiling()
except Exception as e:
    print("no vae tiling:", e)

for job in jobs:
    torch.cuda.empty_cache()
    out = OUT / job["out"]
    if out.exists():
        continue
    kwargs = dict(prompt=job["prompt"], width=job["width"], height=job["height"], guidance_scale=1.0,
                  num_inference_steps=4, generator=torch.Generator("cuda").manual_seed(job["seed"]))
    if job["refs"]:
        kwargs["image"] = [Image.open(OUT / r).convert("RGB") for r in job["refs"]]
    start = time.time()
    image = pipe(**kwargs).images[0]
    seconds = time.time() - start
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    with LOG.open("a") as f:
        f.write(json.dumps({"stage": "keyframes", "model": MODEL, "out": job["out"], "seed": job["seed"],
                            "seconds": round(seconds, 1), "placement": placement}) + "\\n")
    print(job["out"], round(seconds, 1), "s")

shutil.make_archive("/kaggle/working/images_out", "zip", OUT)
print("done: download /kaggle/working/images_out.zip and notebook_log.jsonl")
'''

save("15_keyframes", [
    md("# 15 Keyframes: FLUX.2 klein 4B on a Kaggle T4\nUsed when Cloudflare's daily image quota is spent. "
       "Settings: GPU T4 x2, Internet on, Persistence Files only. Add the dataset that holds "
       "`image_jobs.json` (from `python -m pipeline.kaggle_images`). It saves each image as it goes and "
       "skips finished ones, so after a timeout just run it again."),
    code("!pip install -q -U diffusers transformers accelerate"),
    code("%%writefile /kaggle/working/gen_keyframes.py\n" + KEYFRAME_SCRIPT.strip()),
    code("!PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python /kaggle/working/gen_keyframes.py"),
])

# ---------------------------------------------------------------- 20 wan
save("20_wan", [
    md("# 20 Wan 2.2: moving shots from keyframes\nSettings: GPU T4 x2, Internet on. Add the dataset "
       "`heritage-short-bundle`. Each clip is saved the moment it is made, and clips already saved are "
       "skipped, so a timeout loses nothing: just run it again. Download `/kaggle/working/shots/` and "
       "`notebook_log.jsonl`.\n\n**Untested.** The TI2V-5B image-to-video call below follows the diffusers "
       "docs (`WanImageToVideoPipeline` with `image=`) and the model card, but has not been run."),
    code("!pip install -q -U diffusers transformers accelerate imageio imageio-ffmpeg ftfy sentencepiece"),
    code(f"""
import json, time
from pathlib import Path
import torch
from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
from diffusers.utils import export_to_video, load_image

{BUNDLE}
OUT = Path("/kaggle/working/shots"); OUT.mkdir(exist_ok=True)
LOG = Path("/kaggle/working/notebook_log.jsonl")
jobs = json.loads((BUNDLE / "wan_jobs.json").read_text())

MODEL = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
vae = AutoencoderKLWan.from_pretrained(MODEL, subfolder="vae", torch_dtype=torch.float32)
pipe = WanImageToVideoPipeline.from_pretrained(MODEL, vae=vae, torch_dtype=torch.float16)  # T4 has no bfloat16
pipe.enable_model_cpu_offload()

NEGATIVE = "blurry, low quality, distorted face, extra fingers, deformed, static, text, watermark"
for job in jobs:
    out = OUT / f"{{job['id']}}.mp4"
    if out.exists():
        print(job["id"], "already done"); continue
    image = load_image(str(BUNDLE / job["keyframe"])).resize((480, 832))
    start = time.time()
    frames = pipe(image=image, prompt=job["prompt"], negative_prompt=NEGATIVE, height=832, width=480,
                  num_frames=81, guidance_scale=5.0, num_inference_steps=30,
                  generator=torch.Generator("cpu").manual_seed(job["seed"])).frames[0]
    export_to_video(frames, str(out), fps=24)
    # the job hash lets the pipeline tell a stale clip (older keyframe, prompt or seed) from a current one
    (OUT / f"{{job['id']}}.json").write_text(json.dumps({{"hash": job["hash"]}}))
    seconds = time.time() - start
    with LOG.open("a") as f:
        f.write(json.dumps({{"stage": "shots", "model": MODEL, "shot_id": job["id"], "seconds": round(seconds, 1),
                            "seed": job["seed"], "hash": job["hash"], "width": 480, "height": 832,
                            "frames": 81}}) + "\\n")
    print(job["id"], round(seconds), "s")
"""),
])

# ---------------------------------------------------------------- 30 likeness
save("30_likeness", [
    md("# 30 Likeness test (only after both brothers' written yes to photo upload)\n"
       "Compares shot 8 painted from text only against shot 8 painted with a portrait as a reference, same "
       "seed, so Tesfa and Beki can pick blind which looks more like them.\n\n"
       "**The generation code is deliberately not written yet.** The exact FLUX.2 klein reference-image "
       "pipeline has to be checked against its model card first, and the portraits must not be uploaded to "
       "Kaggle until `ETHICS.md` holds both brothers' exact messages."),
    code("""
CONSENT_RECORDED = False  # set True only once ETHICS.md holds both brothers' exact photo-upload messages
assert CONSENT_RECORDED, "Stop: no recorded consent to upload photos. See ETHICS.md."
"""),
])
print("notebooks written")
