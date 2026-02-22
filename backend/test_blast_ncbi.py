import sys
import os

# Set up path so imports work
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from api.prediction_routes import _run_blast_ncbi

# Example blaCTX-M-15 gene segment (commonly associated with Ceftriaxone resistance)
# length ~ 200bp
sample_gene = (
    "ATGGTTCAAAACTCGCCACAGGTTACCATGTGTGCCAATCAAATTGGAACGGTCTTTGTT"
    "CAGCTGTCCCGTAAGCGCTACACGGAAGATGAAAACAACAAATTGCAGTAG"
)

print(f"Testing real NCBI BLAST lookup for sequence: {sample_gene}")
try:
    hits = _run_blast_ncbi(sample_gene, max_hits=1)
    print(f"Hits: {hits}")
except Exception as e:
    print(f"Error: {e}")
