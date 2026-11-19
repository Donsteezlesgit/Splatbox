"""Download the five TripoSplat weight files (about 3.8 GB) from Hugging Face into a folder.
Usage: get_weights.py <folder>"""
import os, sys

REPO_ID = "VAST-AI/TripoSplat"
FILES = [
    "diffusion_models/triposplat_fp16.safetensors",
    "vae/triposplat_vae_decoder_fp16.safetensors",
    "clip_vision/dino_v3_vit_h.safetensors",
    "vae/flux2-vae.safetensors",
    "background_removal/birefnet.safetensors",
]


def main():
    dest = sys.argv[1]
    from huggingface_hub import snapshot_download
    os.makedirs(dest, exist_ok=True)
    print("Downloading %d files from %s" % (len(FILES), REPO_ID), flush=True)
    snapshot_download(repo_id=REPO_ID, local_dir=dest, allow_patterns=FILES)
    missing = [f for f in FILES if not os.path.isfile(os.path.join(dest, *f.split("/")))]
    if missing:
        print("Missing after download: " + ", ".join(missing), file=sys.stderr)
        return 2
    for f in FILES:
        print("OK %s %d bytes" % (f, os.path.getsize(os.path.join(dest, *f.split("/")))), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
