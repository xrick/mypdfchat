#!/usr/bin/env python3
"""
Download a SentenceTransformer/Hugging Face model to disk.

Examples
  - SentenceTransformers format (recommended for sentence-transformers):
      python scripts/download_model.py -m sentence-transformers/all-MiniLM-L6-v2 \
        -o ./models/all-MiniLM-L6-v2 --method st

  - Exact repo snapshot (mirrors HF files):
      python scripts/download_model.py -m sentence-transformers/all-MiniLM-L6-v2 \
        -o ./models/all-MiniLM-L6-v2 --method snapshot

After download, point your app to the directory:
  export EMBEDDING_MODEL=$(pwd)/models/all-MiniLM-L6-v2
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _default_out_dir(model_id: str) -> str:
    safe = model_id.replace(":", "-").replace("/", "-").replace("@", "-")
    return str(Path("models") / safe)


def download_with_sentence_transformers(model_id: str, out_dir: str) -> None:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        print(
            "[ERROR] sentence-transformers not installed. Run: pip install -U sentence-transformers",
            file=sys.stderr,
        )
        raise

    print(f"[INFO] Downloading with sentence-transformers: {model_id}")
    model = SentenceTransformer(model_id)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    model.save(out_dir)
    print(f"[OK] Saved to: {out_dir}")


def download_with_snapshot(
    model_id: str,
    out_dir: str,
    *,
    local_files_only: bool = False,
    revision: str | None = None,
    use_symlinks: bool = False,
) -> None:
    try:
        from huggingface_hub import snapshot_download
    except Exception:
        print(
            "[ERROR] huggingface_hub not installed. Run: pip install -U huggingface_hub",
            file=sys.stderr,
        )
        raise

    print(
        f"[INFO] Snapshotting repo: {model_id} -> {out_dir} (local_only={local_files_only}, revision={revision})"
    )
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=model_id,
        local_dir=out_dir,
        local_dir_use_symlinks=use_symlinks,
        local_files_only=local_files_only,
        revision=revision,
    )
    print(f"[OK] Downloaded to: {out_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download HF/SentenceTransformer models to disk")
    parser.add_argument(
        "-m",
        "--model",
        required=True,
        help="Model ID on Hugging Face Hub or local path",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        help="Output directory (default: ./models/<model-id>)",
    )
    parser.add_argument(
        "--method",
        choices=["st", "snapshot"],
        default="st",
        help="Download method: 'st' (SentenceTransformer.save) or 'snapshot' (huggingface_hub)",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Do not attempt to download; use local cache only (snapshot mode)",
    )
    parser.add_argument(
        "--revision",
        help="Specific revision/commit/tag to download (snapshot mode)",
    )
    parser.add_argument(
        "--use-symlinks",
        action="store_true",
        help="Use symlinks in local_dir (snapshot mode). Default is to copy files.",
    )
    parser.add_argument(
        "--hf-token",
        help="Hugging Face token (optional). If set, overrides HF_TOKEN env var during run.",
    )
    parser.add_argument(
        "--hf-home",
        help="Cache directory for Hugging Face (sets HF_HOME for this process)",
    )

    args = parser.parse_args(argv)

    model_id: str = args.model
    out_dir: str = args.out_dir or _default_out_dir(model_id)

    # Optional environment configuration for this run
    if args.hf_home:
        os.environ["HF_HOME"] = args.hf_home
        print(f"[INFO] HF_HOME set to: {args.hf_home}")
    if args.hf_token:
        os.environ["HF_TOKEN"] = args.hf_token
        print("[INFO] HF_TOKEN set for this process.")

    try:
        if args.method == "st":
            download_with_sentence_transformers(model_id, out_dir)
        else:
            download_with_snapshot(
                model_id,
                out_dir,
                local_files_only=args.local_files_only,
                revision=args.revision,
                use_symlinks=args.use_symlinks,
            )
    except KeyboardInterrupt:
        print("[WARN] Interrupted by user.")
        return 130
    except Exception as e:
        print(f"[ERROR] Download failed: {e}", file=sys.stderr)
        return 1

    # Print a convenient export hint
    abs_path = str(Path(out_dir).resolve())
    print("\n[HINT] Point your app to the local model directory:")
    print(f"export EMBEDDING_MODEL={abs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

