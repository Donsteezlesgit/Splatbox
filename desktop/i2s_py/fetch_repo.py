"""Download the TripoSplat source (one pinned commit) from GitHub and unpack it into a folder.
Usage: fetch_repo.py <commit> <folder>"""
import io, os, shutil, sys, urllib.request, zipfile

OWNER_REPO = "VAST-AI-Research/TripoSplat"


def main():
    sha, dest = sys.argv[1], sys.argv[2]
    url = "https://github.com/%s/archive/%s.zip" % (OWNER_REPO, sha)
    print("Downloading " + url, flush=True)
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    print("Downloaded %d bytes" % len(data), flush=True)
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    top = names[0].split("/")[0] + "/"
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    for n in names:
        if not n.startswith(top) or n.endswith("/"):
            continue
        rel = n[len(top):]
        out = os.path.join(dest, *rel.split("/"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with z.open(n) as src, open(out, "wb") as dst:
            shutil.copyfileobj(src, dst)
    for need in ("triposplat.py", "model.py"):
        if not os.path.isfile(os.path.join(dest, need)):
            print("Missing " + need + " after unpacking", file=sys.stderr)
            return 2
    print("Unpacked into " + dest, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
