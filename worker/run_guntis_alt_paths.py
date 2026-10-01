#!/usr/bin/env python3
"""Sharded worker for the public Guntis challenge's alternative-path lead."""
from __future__ import annotations
import argparse, itertools, json, multiprocessing as mp, os, subprocess, tempfile, time
from pathlib import Path
TARGET = "0x9c2f44efad0c1e852a09df9939e6daf061140caf"
SHARDS = 40
ZERO = "0x" + "0" * 40
W = {}
LAST_PATH = [None]

def load_upstream(root):
    import sys
    tools = root / "1-big-prizes/guntis-vitolins-metamask-8-6eth/tools"
    sys.path.insert(0, str(tools))
    import sweep_coins as coins
    import sweep_paths as paths
    return coins, paths

def alt_addresses(paths, mnemonic):
    """Match upstream addresses() but omit only the already-tested /0/0."""
    d = paths._i512(b"Bitcoin seed", paths.seed_of(mnemonic))
    k, c = int.from_bytes(d[:32], "big"), d[32:]
    k, c = paths._hard(k, c, 44)
    k, c = paths._hard(k, c, 60)
    out = []
    for account, indexes in paths.PATH_SPECS:
        indexes = tuple(i for i in indexes if not (account == 0 and i == 0))
        if not indexes:
            continue
        ka, ca = paths._hard(k, c, account)
        kc, cc = paths._soft(ka, paths._pub(ka), ca, 0)
        kcpub = paths._pub(kc)
        for index in indexes:
            child, _ = paths._soft(kc, kcpub, cc, index)
            out.append((f"m/44'/60'/{account}'/0/{index}", paths._addr(child)))
    return out

def derive_alt(mnemonic):
    for path, address in alt_addresses(W["paths"], mnemonic):
        if address.lower() == TARGET:
            LAST_PATH[0] = path
            return TARGET
    return ZERO

def init_worker(source_root, wordlist):
    root = Path(source_root)
    coins, paths = load_upstream(root)
    puzzle = root / "1-big-prizes/guntis-vitolins-metamask-8-6eth"
    state = coins._setup(wordlist, str(puzzle/"data/reading-order-pool.json"),
                         str(puzzle/"data/video-onscreen-words.json"), True, None)
    W.update(state, coins=coins, paths=paths, derive=derive_alt)

def scan_one(index):
    units = list(itertools.combinations(W["free"], 3))
    started = time.monotonic()
    n, valid, hit = W["coins"].scan_unit(
        units[index], W["index_of"], W["words"], W["lays"], W["coins_i"],
        W["order"], W["derive"], TARGET)
    return index, n, valid, hit, LAST_PATH[0] if hit else None, time.monotonic()-started

def encrypt_hit(phrase, public_key, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="puzzle-hit-", suffix=".txt")
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(phrase + "\n")
        subprocess.run(["openssl", "pkeyutl", "-encrypt", "-pubin", "-inkey", str(public_key),
                        "-in", str(tmp), "-out", str(output), "-pkeyopt", "rsa_padding_mode:oaep",
                        "-pkeyopt", "rsa_oaep_md:sha256"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    finally:
        tmp.unlink(missing_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--wordlist", required=True)
    ap.add_argument("--mode", choices=("selftest", "search"), required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--workers", type=int, choices=(1,2), default=2)
    ap.add_argument("--public-key", default="config/operator-hit-public.pem")
    ap.add_argument("--results", default="results")
    a = ap.parse_args()
    root = Path(a.source_root).resolve()
    puzzle = root / "1-big-prizes/guntis-vitolins-metamask-8-6eth"
    coins, paths = load_upstream(root)
    if a.mode == "selftest":
        ns = argparse.Namespace(wordlist=a.wordlist, pool=str(puzzle/"data/reading-order-pool.json"),
             coins=str(puzzle/"data/video-onscreen-words.json"), all_paths=False, words=None)
        if coins.cmd_selftest(ns):
            return 1
        vector = " ".join(["abandon"]*11+["about"])
        all_paths = paths.addresses(vector)
        alts = alt_addresses(paths, vector)
        if alts != all_paths[1:] or alts[0][0] != "m/44'/60'/0'/0/1":
            raise SystemExit("alternate-path derivations failed to match upstream oracle")
        print("Upstream witness and six-path differential check: OK")
        return 0
    if not 0 <= a.shard < SHARDS:
        raise SystemExit(f"shard must be 0..{SHARDS-1}")
    init_worker(a.source_root, a.wordlist)
    units = list(itertools.combinations(W["free"], 3))
    if len(units) != 816:
        raise SystemExit(f"expected 816 work units, got {len(units)}")
    start, stop = a.shard*len(units)//SHARDS, (a.shard+1)*len(units)//SHARDS
    indices = list(range(start, stop))
    out = Path(a.results)/f"shard-{a.shard:02d}"
    out.mkdir(parents=True, exist_ok=True)
    coverage = out/"coverage.tsv"
    coverage.write_text("", encoding="utf-8")
    arrangements = valid_total = 0
    hit_info = None
    t0 = time.monotonic()
    pool = mp.Pool(a.workers, initializer=init_worker, initargs=(a.source_root,a.wordlist))
    try:
        for idx, n, valid, phrase, path, seconds in pool.imap_unordered(scan_one, indices, chunksize=1):
            arrangements += n; valid_total += valid
            with coverage.open("a", encoding="utf-8") as f:
                f.write(f"{idx}\t{n}\t{valid}\t{seconds:.1f}\n"); f.flush()
            print(f"shard={a.shard} unit={idx} arrangements={n} checksum_valid={valid} seconds={seconds:.1f}")
            if phrase:
                encrypted = out/"encrypted_hit.bin"
                encrypt_hit(phrase, Path(a.public_key), encrypted)
                hit_info = {"found":True, "path":path, "encrypted_file":encrypted.name}
                pool.terminate()
                break
        else:
            pool.close()
    except Exception:
        pool.terminate()
        raise
    finally:
        pool.join()
    summary = {"puzzle":"guntis-vitolins-metamask-8-6eth",
      "hypothesis":"RO1 + five video coin words on six non-default paths",
      "target":TARGET,"shard":a.shard,"shard_count":SHARDS,"unit_start":start,
      "unit_stop_exclusive":stop,"units_completed":sum(1 for _ in coverage.open(encoding="utf-8")),
      "arrangements":arrangements,"checksum_valid_candidates":valid_total,
      "elapsed_seconds":round(time.monotonic()-t0,1),"found":bool(hit_info),
      "path":hit_info["path"] if hit_info else None,"plaintext_logged_or_uploaded":False}
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="target"},sort_keys=True))
    return 0

if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
