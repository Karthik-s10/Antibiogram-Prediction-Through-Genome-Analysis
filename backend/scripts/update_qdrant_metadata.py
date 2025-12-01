"""Utility to update Qdrant payloads with genome name/organism/strain metadata.

This script reads the BVBRC AMR phenotype file and Rosetta mapping file
(BVBRC_genome.txt) via the existing DataPreprocessor and then attaches
assembly-level metadata (organism/genome name and strain) to any existing
Qdrant points keyed by Assembly Accession (GCA_...).

Run from the backend virtualenv, for example:

    python -m scripts.update_qdrant_metadata \
        --phenotype-file /path/to/BVBRC_genome_amr.txt \
        --rosetta-file /path/to/BVBRC_genome.txt

It will not retrain models or change vectors, only enrich the payload
for matching genome_ids.
"""

import argparse
import logging
from typing import Dict

from preprocessing.data_preprocessor import DataPreprocessor
from services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def build_assembly_metadata(phenotype_file: str, rosetta_file: str) -> Dict[str, Dict[str, str]]:
    """Load BVBRC phenotypes + Rosetta mapping and return assembly metadata.

    Returns a dict keyed by Assembly Accession (GCA_xxx) with fields like:
    {"genome_name": ..., "organism_name": ..., "strain": ...}.
    """
    pre = DataPreprocessor(rosetta_file=rosetta_file)
    id_mapping = pre.load_id_mapping()
    pre.load_and_map_phenotypes(phenotype_file, id_mapping)
    # DataPreprocessor.load_and_map_phenotypes populates pre.assembly_metadata
    return pre.assembly_metadata or {}


def update_qdrant_payloads(assembly_metadata: Dict[str, Dict[str, str]]) -> None:
    """Attach name/strain metadata to existing Qdrant points by genome_id.

    Uses the same point-id scheme as training (hash(genome_id) & 0x7FFFFFFF).
    Only updates payload for genome_ids that already exist in the collection.
    """
    qdrant = QdrantService()
    if not qdrant.client:
        logger.error("Qdrant client is not available; aborting.")
        return

    updated = 0
    skipped_missing = 0

    for assembly, meta in assembly_metadata.items():
        genome_id = assembly.strip()
        if not genome_id:
            continue

        point_id = hash(genome_id) & 0x7FFFFFFF

        # Check existence using the same helper as training jobs
        try:
            if not qdrant.genome_exists(genome_id):
                skipped_missing += 1
                continue
        except Exception as e:
            logger.warning(f"Failed to check existence for {genome_id}: {e}")

        species_name = meta.get("organism_name") or meta.get("genome_name")
        payload_update = {
            "species": species_name,
            "organism_name": meta.get("organism_name"),
            "genome_name": meta.get("genome_name"),
            "strain": meta.get("strain"),
        }

        try:
            # set_payload merges with existing payload for the point
            qdrant.client.set_payload(
                collection_name=qdrant.COLLECTION_NAME,
                payload=payload_update,
                points=[point_id],
            )
            updated += 1
        except Exception as e:
            logger.warning(f"Failed to update payload for {genome_id}: {e}")

    logger.info(
        "Updated payloads for %d genomes (skipped %d without existing points)",
        updated,
        skipped_missing,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Qdrant genome metadata from BVBRC/Rosetta files.")
    parser.add_argument(
        "--phenotype-file",
        required=True,
        help="Path to BVBRC_genome_amr.txt phenotype file",
    )
    parser.add_argument(
        "--rosetta-file",
        default="BVBRC_genome.txt",
        help="Path to BVBRC_genome.txt Rosetta mapping file (default: BVBRC_genome.txt)",
    )

    args = parser.parse_args()

    logger.info("Building assembly metadata from BVBRC files...")
    assembly_meta = build_assembly_metadata(args.phenotype_file, args.rosetta_file)
    logger.info("Loaded metadata for %d assemblies", len(assembly_meta))

    if not assembly_meta:
        logger.warning("No assembly metadata found; nothing to update.")
        return

    logger.info("Updating Qdrant payloads with genome names/strains...")
    update_qdrant_payloads(assembly_meta)


if __name__ == "__main__":
    main()
