#!/usr/bin/env python3
"""
Gather poem 释义 via Zhipu GLM into data/poem_explanations.json.

Default `--limit 10` keeps accidental runs cheap. Pass `--all` for the full corpus
(poems must have `id`; entries without id are skipped).

  uv run python scripts/gather_poem_explanations.py
  uv run python scripts/gather_poem_explanations.py --all --skip-existing --sleep 0.5


Stdout lines use a ``[i/N]`` prefix (candidate index in this run).

Use ``--no-progress-prefix`` for plain logs.
"""

from __future__ import annotations

import argparse
import sys
import time

from src.data_loader import load_poems_from_local, load_supplement_poems
from src.poem_explanations_store import get_explanation, upsert_explanation
from src.poem_web_supplement import fetch_poem_meaning_explanation
from src.zhipu_glm import DEFAULT_MODEL, get_api_key


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch poem explanations via Zhipu GLM and save to "
            "data/poem_explanations.json."
        )
    )
    parser.add_argument(
        "--character-set",
        choices=("simplified", "traditional"),
        default="simplified",
        help="Which local 唐诗 corpus file to merge with the supplement.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help=(
            "Process at most N poems (with ids), in corpus order. "
            "Ignored with --all. Default: 10."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every poem that has an id (merged base + supplement).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip poem ids already present in the local explanations store.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        metavar="SEC",
        help="Pause SEC seconds between API calls (rate limiting). Default: 0.",
    )
    parser.add_argument(
        "--quiet-timing",
        action="store_true",
        help="Suppress per-request timing lines on stderr from the GLM client.",
    )
    parser.add_argument(
        "--no-progress-prefix",
        action="store_true",
        help=('Do not print "[i/N]" progress prefixes on stdout (for logs or piping).'),
    )
    args = parser.parse_args()

    try:
        get_api_key()
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1

    timing_log = not args.quiet_timing

    base = load_poems_from_local(args.character_set) or []
    merged = [*base, *load_supplement_poems()]
    with_usable_ids: list[dict] = [
        p for p in merged if isinstance(p.get("id"), str) and str(p["id"]).strip()
    ]
    skipped_no_id = len(merged) - len(with_usable_ids)

    if not args.all:
        if args.limit < 1:
            print("--limit must be >= 1 (or use --all).", file=sys.stderr)
            return 1
        candidates = with_usable_ids[: args.limit]
    else:
        candidates = with_usable_ids

    fetched = 0
    skipped_disk = 0
    failures = 0

    total_candidates = len(candidates)
    print(f"Candidates this run: {total_candidates}", flush=True)

    for current_i, poem in enumerate(candidates, start=1):
        if total_candidates > 0 and not args.no_progress_prefix:
            pref = f"[{current_i}/{total_candidates}] "
        else:
            pref = ""

        poem_id = str(poem["id"]).strip()

        if args.skip_existing and get_explanation(poem_id) is not None:
            skipped_disk += 1
            if not args.no_progress_prefix:
                print(
                    f"{pref}skip (already on disk) {poem.get('title') or poem_id[:8]}",
                    flush=True,
                )
            continue

        title = poem.get("title") or poem_id[:8]
        did_call_api = False
        try:
            text = fetch_poem_meaning_explanation(
                poem,
                timing=timing_log,
            )
            upsert_explanation(
                poem_id,
                text,
                web_search=True,
                model=DEFAULT_MODEL,
            )
            fetched += 1
            did_call_api = True
            print(f"{pref}[ok] {title} ({poem_id[:8]}…)", flush=True)
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            break
        except Exception as exc:
            failures += 1
            did_call_api = True
            print(f"{pref}[fail] {title}: {exc}", file=sys.stderr, flush=True)

        if args.sleep > 0 and did_call_api:
            time.sleep(args.sleep)

    processed = fetched + skipped_disk + failures
    print(
        (
            "\nDone. "
            f"fetched={fetched} skipped_existing={skipped_disk} "
            f"failures={failures} "
            f"passes_through_loop={processed} "
            f"corpus_poems_without_usable_id={skipped_no_id}"
        ),
        flush=True,
    )

    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
