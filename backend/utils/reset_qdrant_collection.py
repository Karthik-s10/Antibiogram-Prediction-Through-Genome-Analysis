"""Utility script to wipe and recreate the Qdrant bacterial_genomes collection.

Run from the project root (where backend/ is located):

    python -m backend.utils.reset_qdrant_collection

This will connect to Qdrant using the configured URL/API key and delete the
`bacterial_genomes` collection if it exists, then recreate it empty.
"""

from backend.services.qdrant_service import QdrantService


def main() -> None:
    service = QdrantService()
    ok = service.reset_collection()
    if ok:
        print("Qdrant collection 'bacterial_genomes' has been reset (all points deleted).")
    else:
        print("Failed to reset Qdrant collection. Check logs for details.")


if __name__ == "__main__":
    main()
