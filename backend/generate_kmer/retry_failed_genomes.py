import argparse
import os
import time
import requests
import io
import zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

NCBI_DATASETS_BASE_URL = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha"

def get_any_assembly(taxon_id, api_key=None):
    url = f"{NCBI_DATASETS_BASE_URL}/genome/dataset_report"
    
    # We remove "Complete Genome" and "RefSeq" restrictions 
    # to catch any published assembly for this taxon.
    request_data = {
        "taxons": [str(taxon_id)],
        "page_size": 20,
    }

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key: headers["api-key"] = api_key

    try:
        resp = requests.post(url, json=request_data, headers=headers, timeout=60)
        if resp.status_code != 200: return None
        
        data = resp.json()
        reports = []
        if isinstance(data, dict):
            if "reports" in data and isinstance(data["reports"], list):
                reports = data["reports"]
            elif "assemblies" in data and isinstance(data["assemblies"], list):
                reports = data["assemblies"]
            elif "assemblies_by_taxid" in data:
                assemblies_data = list((data.get("assemblies_by_taxid") or {}).values())
                for tax_data in assemblies_data:
                    reports.extend(tax_data.get("assemblies", []))
            elif "assemblies_by_accession" in data:
                reports = list((data.get("assemblies_by_accession") or {}).values())

        if not reports: return None
        
        # Simple heuristic: try to find a RefSeq first, else GenBank.
        for rep in reports:
            acc = rep.get("accession") or rep.get("current_accession")
            if acc and acc.startswith("GCF_"): return acc
        
        for rep in reports:
            acc = rep.get("accession") or rep.get("current_accession")
            if acc: return acc
            
        return None
    except Exception as e:
        return None

def download_assembly(taxon_id, accession, output_dir, api_key=None):
    output_file = output_dir / f"{taxon_id}.fna"
    url = f"{NCBI_DATASETS_BASE_URL}/genome/download"
    request_data = {
        "accessions": [accession],
        "include_annotation_type": ["GENOME_FASTA"],
        "format": "fasta",
    }
    headers = {"Content-Type": "application/json"}
    if api_key: headers["api-key"] = api_key

    for attempt in range(3):
        try:
            resp = requests.post(url, json=request_data, headers=headers, timeout=120)
            if resp.status_code == 200:
                if "zip" in resp.headers.get("content-type", "").lower():
                    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                        fastas = [n for n in zf.namelist() if n.endswith((".fna", ".fasta", ".fa"))]
                        if fastas:
                            with zf.open(fastas[0]) as f_in, open(output_file, "wb") as f_out:
                                f_out.write(f_in.read())
                            return True
                else:
                    with open(output_file, "wb") as f_out:
                        f_out.write(resp.content)
                    return True
        except:
            time.sleep(2)
    return False

def main():
    failed_file = Path("backend/downloaded_genomes/failed_downloads.txt")
    output_dir = Path("backend/downloaded_genomes")
    api_key = os.environ.get("NCBI_API_KEY", "db02801bb154bcee21414e7ab86cec9a0508")
    
    if not failed_file.exists():
        print("No failed downloads file found.")
        return

    with open(failed_file) as f:
        lines = f.readlines()[1:] # skip header
    taxons = [line.split("\t")[0].strip() for line in lines if line.strip()]

    print(f"Retrying {len(taxons)} failed taxons with relaxed filters...")
    
    def process(tid):
        acc = get_any_assembly(tid, api_key)
        if acc:
            success = download_assembly(tid, acc, output_dir, api_key)
            return tid, success
        return tid, False

    success_count = 0
    with ThreadPoolExecutor(10) as ex:
        futures = {ex.submit(process, t): t for t in taxons}
        for i, fut in enumerate(as_completed(futures), 1):
            tid, success = fut.result()
            if success:
                success_count += 1
                print(f"[{i}/{len(taxons)}] Taxon {tid} SUCCESS")
            else:
                print(f"[{i}/{len(taxons)}] Taxon {tid} FAILED again")
                
    print(f"\nRecovered {success_count} / {len(taxons)} genomes.")

if __name__ == "__main__":
    main()
