from __future__ import annotations

import argparse
import secrets
import sys

from torrent_stats.db.models import WorkerKey
from torrent_stats.db.repository import WorkerKeyRepository


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m torrent_stats",
        description="Torrent Stats CLI",
    )
    subparsers = parser.add_subparsers(dest="group", required=True)

    workers_parser = subparsers.add_parser("workers", help="Manage worker keys")
    workers_subparsers = workers_parser.add_subparsers(dest="action", required=True)

    # create
    create_parser = workers_subparsers.add_parser("create", help="Create a worker key")
    create_parser.add_argument(
        "--description", default="", help="Description for the worker key"
    )

    # list
    workers_subparsers.add_parser("list", help="List all worker keys")

    # delete
    delete_parser = workers_subparsers.add_parser("delete", help="Delete a worker key")
    delete_parser.add_argument("id", help="Worker key ID or hash")

    args = parser.parse_args()
    repo = WorkerKeyRepository()

    if args.group == "workers":
        if args.action == "create":
            raw_key = secrets.token_hex(32)
            wk = repo.save_key(raw_key, description=args.description)
            print("Worker key created successfully!")
            print(f"ID/Hash: {wk.id}")
            print(f"Description: {wk.description}")
            print(f"Raw Key (save this now, it cannot be recovered): {raw_key}")
            return 0
        elif args.action == "list":
            db = repo.client.get_db()
            docs = [db.get(doc_id) for doc_id in db if not doc_id.startswith("_")]
            keys = [WorkerKey.model_validate(d) for d in docs if d and "key_hash" in d]
            if not keys:
                print("No worker keys found.")
                return 0
            print(f"{'ID / Hash':<65} | {'Created At':<25} | Description")
            print("-" * 115)
            for k in keys:
                print(f"{k.id:<65} | {k.created_at:<25} | {k.description}")
            return 0
        elif args.action == "delete":
            db = repo.client.get_db()
            doc_id = args.id
            if doc_id in db:
                doc = db.get(doc_id)
                db.delete(doc)
                print(f"Worker key {doc_id} deleted successfully.")
                return 0
            else:
                print(f"Error: Worker key {doc_id} not found.", file=sys.stderr)
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
