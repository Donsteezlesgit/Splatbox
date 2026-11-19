"""Splatbox "Image to splat": run TripoSplat on one image and write a .ply.
Runs inside the venv Splatbox made. Every progress or error line starts with @@ and is JSON, so the app can read it.
Everything else printed (warnings, tracebacks) goes to the error log as it is."""
import argparse, json, os, sys, time, traceback


def emit(**k):
    print("@@" + json.dumps(k), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ckpts", required=True)
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--count", type=int, default=131072)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    t0 = time.time()
    sys.path.insert(0, a.repo)
    os.chdir(a.repo)
    try:
        import torch
        cuda = torch.cuda.is_available()
        info = {"event": "env", "python": sys.version.split()[0], "torch": torch.__version__, "cuda": cuda}
        if cuda:
            p = torch.cuda.get_device_properties(0)
            info.update(gpu=p.name, vram_gb=round(p.total_memory / 2**30, 1), capability="%d.%d" % (p.major, p.minor))
        emit(**info)
        if not cuda:
            emit(event="error", kind="nocuda",
                 message="PyTorch can't see an NVIDIA graphics card with CUDA. Update the NVIDIA driver, or this PC can't run it.")
            return 3
        emit(event="stage", stage="loading", text="Loading the model into the graphics card")
        from triposplat import TripoSplatPipeline
        c = a.ckpts
        pipe = TripoSplatPipeline(
            ckpt_path=os.path.join(c, "diffusion_models", "triposplat_fp16.safetensors"),
            decoder_path=os.path.join(c, "vae", "triposplat_vae_decoder_fp16.safetensors"),
            dinov3_path=os.path.join(c, "clip_vision", "dino_v3_vit_h.safetensors"),
            flux2_vae_encoder_path=os.path.join(c, "vae", "flux2-vae.safetensors"),
            rmbg_path=os.path.join(c, "background_removal", "birefnet.safetensors"),
            device="cuda",
        )
        emit(event="stage", stage="running", text="Making the splat")
        gaussian, prepared = pipe.run(
            a.image, seed=a.seed, steps=a.steps, num_gaussians=a.count,
            callback=lambda i, n: emit(event="step", i=int(i), n=int(n)),
        )
        emit(event="stage", stage="saving", text="Saving the splat")
        prepared_path = os.path.splitext(a.out)[0] + "_prepared.png"
        try:
            prepared.save(prepared_path)
        except Exception:
            prepared_path = ""
        gaussian.save_ply(a.out)
        try:
            peak = round(torch.cuda.max_memory_allocated() / 2**30, 2)
        except Exception:
            peak = 0
        emit(event="done", ply=a.out, prepared=prepared_path, seconds=round(time.time() - t0, 1), peak_gb=peak)
        return 0
    except BaseException as e:
        traceback.print_exc()
        oom = e.__class__.__name__ == "OutOfMemoryError" or "out of memory" in str(e).lower()
        if oom:
            emit(event="error", kind="oom",
                 message="The graphics card ran out of memory. Close other programs that use the GPU (games, other AI tools), then try again, or pick a lower detail.")
        else:
            emit(event="error", kind="failed", message="%s: %s" % (e.__class__.__name__, str(e)[:300]))
        return 4 if oom else 1


if __name__ == "__main__":
    sys.exit(main())
