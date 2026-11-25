"""Motion stage: a Ken Burns pass over each keyframe, or a Wan clip from Kaggle where one exists."""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

from pipeline import common, media, timeline
from pipeline.common import Manifest, input_hash, log_run
from pipeline.keyframes import ratio_dir

STAGE = "shots"
FPS = 24
FINAL_SIZES = {"9:16": (720, 1280), "16:9": (1280, 720)}
MIN_WAN_SECONDS = 3.0


def kenburns(frame: Path, camera: str, seconds: float, out: Path, size: tuple[int, int]) -> Path:
    """Slow pan or zoom over a still, made with FFmpeg's zoompan."""
    n = max(1, int(round(seconds * FPS)))
    centre_y = "ih/2-(ih/zoom/2)"
    z, x, y = {
        "push_in": (f"1.0+0.15*on/{n}", "iw/2-(iw/zoom/2)", centre_y),
        "pull_out": (f"1.15-0.15*on/{n}", "iw/2-(iw/zoom/2)", centre_y),
        "pan_right": ("1.12", f"(iw-iw/zoom)*on/{n}", centre_y),
        "pan_left": ("1.12", f"(iw-iw/zoom)*(1-on/{n})", centre_y),
    }[camera]
    vf = (f"scale=iw*2:ih*2,zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={size[0]}x{size[1]}:fps={FPS},"
          "format=yuv420p")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(frame), "-vf", vf,
                    "-frames:v", str(n), "-c:v", "libx264", "-r", str(FPS), str(out)], check=True)
    return out


def fit_clip(clip: Path, seconds: float, out: Path, size: tuple[int, int]) -> Path:
    """Scale and crop a Wan clip to the final frame and hold its last frame if the shot is longer."""
    w, h = size
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},"
          f"tpad=stop_mode=clone:stop_duration={seconds:.3f},format=yuv420p")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-vf", vf, "-t", f"{seconds:.3f}",
                    "-c:v", "libx264", "-r", str(FPS), str(out)], check=True)
    return out


def _raw_dir() -> Path:
    return common.ROOT / "outputs" / "shots" / "raw"


def _valid_wan(path: Path) -> bool:
    """Decodes cleanly to the end and is at least three seconds. Reading the header is not enough:
    a clip cut short after an intact header still reports its full length."""
    try:
        return path.exists() and media.duration(path) >= MIN_WAN_SECONDS and media.decodes_fully(path)
    except Exception:  # noqa: BLE001 - an unreadable or truncated download is simply not valid
        return False


def wan_job_hash(shot: dict) -> str:
    """What a Wan clip was made from: the 9:16 keyframe, the motion prompt and the seed."""
    frame = common.ROOT / "outputs" / "keyframes" / ratio_dir("9:16") / f"{shot['id']}.png"
    return input_hash(frame, shot["motion"]["prompt"], shot["seed"])


def _clip_matches_job(clip: Path, shot: dict) -> bool:
    """The notebook writes <id>.json with the job hash beside each clip. A clip whose hash is
    missing or different was made from an older keyframe, prompt or seed, so it is stale."""
    sidecar = clip.with_suffix(".json")
    try:
        return json.loads(sidecar.read_text())["hash"] == wan_job_hash(shot)
    except Exception:  # noqa: BLE001 - no readable sidecar means we cannot trust the clip
        return False


def export_wan_jobs(storyboard: dict) -> Path:
    """Write what the Kaggle notebook needs: 9:16 keyframes and motion prompts for the Wan shots."""
    jobs_dir = common.ROOT / "outputs" / "jobs"
    (jobs_dir / "keyframes").mkdir(parents=True, exist_ok=True)
    jobs = []
    for shot in storyboard["shots"]:
        if shot["motion"]["mode"] != "wan":
            continue
        src = common.ROOT / "outputs" / "keyframes" / ratio_dir("9:16") / f"{shot['id']}.png"
        dst = jobs_dir / "keyframes" / f"{shot['id']}.png"
        shutil.copyfile(src, dst)
        jobs.append({"id": shot["id"], "keyframe": f"keyframes/{shot['id']}.png",
                     "prompt": shot["motion"]["prompt"], "seed": shot["seed"],
                     "hash": wan_job_hash(shot)})
    path = jobs_dir / "wan_jobs.json"
    path.write_text(json.dumps(jobs, indent=2))
    return path


def import_wan(raw_dir: Path | None = None) -> list[str]:
    """Shot ids with a readable Wan clip of at least three seconds."""
    raw_dir = raw_dir or _raw_dir()
    return sorted(p.stem for p in raw_dir.glob("*.mp4") if _valid_wan(p))


def run(storyboard: dict, durations: dict[str, float]) -> dict[str, dict[str, Path]]:
    manifest = Manifest(STAGE)
    lengths = timeline.shot_lengths(storyboard, durations)
    result: dict[str, dict[str, Path]] = {}
    for shot in storyboard["shots"]:
        sid, motion = shot["id"], shot["motion"]
        for ratio in storyboard["ratios"]:
            size = FINAL_SIZES[ratio]
            frame = common.ROOT / "outputs" / "keyframes" / ratio_dir(ratio) / f"{sid}.png"
            out = common.ROOT / "outputs" / STAGE / ratio_dir(ratio) / f"{sid}.mp4"
            clip = _raw_dir() / f"{sid}.mp4"
            wanted_wan = motion["mode"] == "wan" and ratio == "9:16"
            clip_ok = wanted_wan and _valid_wan(clip)
            stale = clip_ok and not _clip_matches_job(clip, shot)
            use_wan = clip_ok and not stale
            length = lengths[sid]
            h = input_hash(frame, motion["camera"], round(length, 3), ratio, clip if use_wan else "kenburns")
            key = f"{sid}@{ratio}"
            if not manifest.is_fresh(key, h):
                start = time.time()
                if use_wan:
                    fit_clip(clip, length, out, size)
                else:
                    kenburns(frame, motion["camera"], length, out, size)
                status = "fallback" if wanted_wan and not use_wan else "ok"
                log_run(STAGE, sid, "wan" if use_wan else "ffmpeg", "wan2.2-ti2v-5b" if use_wan else "zoompan",
                        {"ratio": ratio, "camera": motion["camera"], "seconds": round(length, 2)},
                        shot["seed"], h, time.time() - start, status,
                        error=(("wan clip is stale: its job hash does not match the current keyframe, prompt "
                                "and seed (or it has no hash); used Ken Burns") if stale
                               else "wan clip missing or invalid, used Ken Burns") if status == "fallback" else None)
                manifest.put(key, h, str(out.relative_to(common.ROOT)))
            result.setdefault(sid, {})[ratio] = out
    return result


if __name__ == "__main__":
    from pipeline.validate import load_storyboard

    sb = load_storyboard()
    print(export_wan_jobs(sb))
