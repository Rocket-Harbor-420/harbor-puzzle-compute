# Harbor Puzzle Compute

An opt-in GitHub Actions worker for one bounded, public puzzle-search lead. It does not mine, scan arbitrary wallets, or claim that compute equals income.

## Current search: Guntis 10 ETH challenge, alternative paths

The public challenge asks solvers to reconstruct a 12-word BIP-39 phrase from its video and companion post. The upstream analysis reports five additional video-side words from the portfolio display: `atom`, `link`, `basic`, `token`, and `dash`. The default MetaMask path was already searched for these words and reported negative. This worker crosses that same reading-order model and those five words with the six listed non-default paths only:

- `m/44'/60'/0'/0/1` through `m/44'/60'/0'/0/4`
- `m/44'/60'/1'/0/0`
- `m/44'/60'/2'/0/0`

The upstream issue records 1,741,140,000 arrangements and 108,817,960 checksum-valid candidates for the five-word default-path sweep. This extension checks those valid candidates on six additional paths (652,907,760 address derivations). It is a specific hypothesis, not a claim that the complete puzzle has been searched.

Sources: [challenge record and rules](https://github.com/floflo777/open-crypto-puzzles/blob/main/1-big-prizes/guntis-vitolins-metamask-8-6eth/README.md), [on-screen word report and earlier default-path negatives](https://github.com/floflo777/open-crypto-puzzles/issues/18), [upstream scripts pinned at `4c980f0707aecd915b908b5c751abd80e5d380f3`](https://github.com/floflo777/open-crypto-puzzles/tree/4c980f0707aecd915b908b5c751abd80e5d380f3/1-big-prizes/guntis-vitolins-metamask-8-6eth/tools).

## Run

1. Open the **Actions** tab and choose **Guntis alternative-path puzzle workers**.
2. Run `selftest` first. It checks the upstream witness and compares the six-path derivation with the upstream oracle.
3. Run `search` to launch 40 deterministic shards. The workflow checks the live target balance before compute, caps parallelism at 20 jobs, and stops each hosted job at 350 minutes. Re-running the complete workflow repeats the search; shard assignment is deterministic.
4. Open the **summarize** job. It reports completed shard count, arrangements, checksum-valid candidates, and any matched derivation path.

The workflow uses standard hosted runners in this public repository, which GitHub currently lists as free for public repos. GitHub still applies plan-based concurrency limits and a six-hour maximum per hosted job; this workflow caps itself at 20 concurrent jobs and under six hours per job. It does not create paid resources or use local CPU.

## Result handling

The worker never prints or uploads a plaintext mnemonic. If it finds a match, it encrypts the phrase with the public key in `config/operator-hit-public.pem` and uploads only `encrypted_hit.bin`. The matching derivation path and coverage counts are logged. The corresponding private decryption key is held only in the operator's local WorkMap folder; it is not in this repository or GitHub secrets. Do not publish that private key or decrypted phrase.

A match still needs a live balance check and human review before any transfer. The challenge wallet has prior outgoing transactions, so its balance is not a fixed escrow. Only a confirmed transfer to the operator wallet counts as income. Do not transmit a transaction automatically from this workflow.

## Scope and limits

- Search starts only after a manual dispatch; there are no scheduled or push-triggered jobs.
- The workflow has read-only repository permissions. It needs no wallet, RPC, exchange, or cloud credentials.
- Candidate source, wordlist, and dependencies are pinned or checksum-verified.
- This run does not test different word-selection rules, passphrases, or arbitrary derivation paths beyond the six above.
- No x402 integration is used.

## License

This worker and workflow are MIT-licensed. At runtime they check out the upstream puzzle repository at the pinned revision and retain its notices and attribution.
