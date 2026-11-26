"""Keyframes on a Kaggle GPU, for when Cloudflare's daily quota is spent (FAILURES #12).

The same model (FLUX.2 klein 4B, open weights, Apache 2.0) runs in notebooks/15_keyframes.ipynb.
Everything that decides an image is computed here and written to image_jobs.json, so the notebook
only executes: the prompts are exactly keyframes.build_prompt, references come first and are passed to
the shots that list them. The results come back as files and are imported with their provenance."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from pipeline import common
from pipeline.candidates import STAGE as CAND_STAGE, candidate_path
from pipeline.common import Manifest, input_hash, log_run
from pipeline.keyframes import MODEL, SIZES, build_prompt, ratio_dir

JOBS = "image_jobs.json"
KAGGLE_MODEL = "black-forest-labs/FLUX.2-klein-4B"


def _ref_prompt(storyboard: dict, ref: dict) -> str:
    return f"{storyboard['style_block'].rstrip('.')}. {ref['prompt']}"


N_PER_RATIO = {"9:16": 3, "16:9": 2}  # the phone cut is the main submission; about 95 s an image on a T4


def export_jobs(storyboard: dict, n: int | None = None) -> Path:
    jobs = []
    for ref in storyboard.get("references", []):
        w, h = ref["size"]
        jobs.append({"kind": "ref", "id": ref["id"], "seed": ref["seed"], "width": w, "height": h,
                     "prompt": _ref_prompt(storyboard, ref), "refs": [], "out": f"refs/{ref['id']}.png"})
    # 9:16 first for every shot, then 16:9, so a session that runs out of time still has the phone cut.
    for ratio in storyboard["ratios"]:
        w, h = SIZES[ratio]
        for shot in storyboard["shots"]:
            prompt = build_prompt(storyboard, shot)
            refs = [f"refs/{r}.png" for r in shot.get("refs", [])]
            for seed in range(shot["seed"], shot["seed"] + (n or N_PER_RATIO[ratio])):
                jobs.append({"kind": "shot", "id": shot["id"], "ratio": ratio, "seed": seed, "width": w,
                             "height": h, "prompt": prompt, "refs": refs,
                             "out": f"shots/{ratio_dir(ratio)}/{shot['id']}/{seed}.png"})
    out = common.ROOT / "outputs" / "kaggle_images" / JOBS
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(jobs, indent=2, ensure_ascii=False))
    return out


def import_results(storyboard: dict, results: Path) -> dict[str, int]:
    """Copy references into outputs/references (cached, so the pipeline will not call Cloudflare for
    them) and candidates to where candidates.pick looks. Each file is logged as imported from Kaggle."""
    counts = {"refs": 0, "shots": 0}
    manifest = Manifest("references")
    for ref in storyboard.get("references", []):
        src = results / "refs" / f"{ref['id']}.png"
        if not src.exists():
            continue
        dest = common.ROOT / "outputs" / "references" / f"{ref['id']}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        h = input_hash(_ref_prompt(storyboard, ref), ref["seed"], tuple(ref["size"]), MODEL)
        manifest.put(ref["id"], h, str(dest.relative_to(common.ROOT)))
        log_run("references", ref["id"], "kaggle", KAGGLE_MODEL, {"size": ref["size"]}, ref["seed"], h, 0.0,
                "imported", error="generated in notebooks/15_keyframes on a Kaggle T4")
        counts["refs"] += 1
    for ratio in storyboard["ratios"]:
        for src in sorted((results / "shots" / ratio_dir(ratio)).glob("*/*.png")):
            sid, seed = src.parent.name, int(src.stem)
            dest = candidate_path(sid, seed, ratio)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            log_run(CAND_STAGE, sid, "kaggle", KAGGLE_MODEL, {"ratio": ratio}, seed, "", 0.0, "imported",
                    error="generated in notebooks/15_keyframes on a Kaggle T4")
            counts["shots"] += 1
    return counts


if __name__ == "__main__":
    import argparse

    from pipeline.validate import load_storyboard

    ap = argparse.ArgumentParser()
    ap.add_argument("--import", dest="results", help="folder downloaded from the notebook's output")
    ap.add_argument("-n", type=int, default=None)
    a = ap.parse_args()
    sb = load_storyboard()
    print(import_results(sb, Path(a.results)) if a.results else export_jobs(sb, n=a.n))
