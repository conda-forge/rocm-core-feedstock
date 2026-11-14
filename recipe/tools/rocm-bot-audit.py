#!/usr/bin/env python3
"""Audit conda-forge ROCm feedstocks against the version bot's data store.

For every feedstock it reports whether conda-forge.yml carries
``bot.version_updates.allowed_tag_globs`` and what the bot currently thinks
the newest version is, with the number of failed update attempts. A row is
flagged STUCK when the bot's current candidate version has failed update
attempts recorded against it, which is what happens when it picks up
hip-version_* build tags or therock-* tags from the monorepos and cannot
download the matching rocm-<version> URL.

Feedstocks come from three sources, merged: the conda-forge/rocm-core team
(needs a gh login that can read it), a GitHub name search, and EXTRA below.
Archived feedstocks (for example rocm-opencl-runtime, now an output of
hip-feedstock) are skipped; NOT_ROCM lists name-search hits that merely
contain "roc" or "hip".

Usage: python3 recipe/tools/rocm-bot-audit.py [extra-feedstock ...]

Needs only Python 3.9+; `gh` is optional and adds the rocm-core team's repositories.
"""

import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request

EXTRA = {
    "rocfft",
    "hipfft",
    "hipblas-common",
    "hipcc",
    "rocm-bandwidth-test",
    "roct-thunk-interface",
    "openmm-hip",
}
NOT_ROCM = {
    "ansys-rocky-core",
    "hipace",
    "hiphive",
    "hiplot",
    "hippynn",
    "hiproc",
    "hipscat",
    "hipscat-import",
    "hips",
    "python-rocksdb",
    "repo2rocrate",
    "r-loose.rock",
    "rockhound",
    "rockpool",
    "rocksdbdict",
    "rocksdb",
    "rocksdict",
    "rockstar-galaxies",
    "rockverse",
    "rocrate",
    "rocrate-inveniordm",
    "r-rocit",
    "r-rockchalk",
    "r-rocr",
    "r-rocs",
    "hippogriffe",
    "pyplif-hippos",
    "rocket-fft",
    "rocketpy",
    "rocketry",
}
LIVE = "select(.archived | not) | .name"


def gh(*args):
    try:
        return subprocess.run(
            ["gh", "api", *args], check=True, capture_output=True, text=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def feedstocks():
    names = set(EXTRA) | set(sys.argv[1:])
    names |= set(
        gh(
            "orgs/conda-forge/teams/rocm-core/repos?per_page=100",
            "--jq",
            f".[] | {LIVE}",
        ).split()
    )
    for q in ("roc", "hip", "amdsmi"):
        names |= set(
            gh(
                "-X",
                "GET",
                "search/repositories",
                "-f",
                f"q=org:conda-forge {q} in:name feedstock",
                "-f",
                "per_page=100",
                "--jq",
                f".items[] | {LIVE}",
            ).split()
        )
    names = {n.removesuffix("-feedstock") for n in names}
    return sorted(n for n in names if n not in NOT_ROCM)


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.read().decode()
    except (urllib.error.URLError, TimeoutError):
        return None


def bot_store(store, name):
    fn = f"{name}.json"
    hx = hashlib.sha1(fn.encode()).hexdigest()[:5]
    raw = fetch(
        f"https://github.com/conda-forge/conda-forge-bot-data-{store}"
        f"/raw/main/{'/'.join(hx)}/{fn}"
    )
    return json.loads(raw) if raw else None


def has_glob(name):
    raw = fetch(
        f"https://raw.githubusercontent.com/conda-forge/{name}-feedstock/main/conda-forge.yml"
    )
    return None if raw is None else "allowed_tag_globs" in raw


def main():
    print(f"{'feedstock':24} {'glob':5} {'bot new_version':16} {'errors':>6}  verdict")
    for name in feedstocks():
        cand = bot_store("versions", name) or {}
        info = bot_store("version_pr_info", name)
        glob = has_glob(name)
        if info is None:
            print(f"{name:24} {str(glob):5} {'(no bot data)':16}")
            continue
        nv = str(cand.get("new_version"))
        errs = info.get("new_version_errors") or {}
        if nv != "None" and nv in errs:
            verdict = "STUCK: cannot fetch candidate"
            if not glob:
                verdict += ", add allowed_tag_globs"
        else:
            verdict = "ok" if glob else "ok (no glob)"
        print(f"{name:24} {str(glob):5} {nv:16} {len(errs):6}  {verdict}")


if __name__ == "__main__":
    main()
