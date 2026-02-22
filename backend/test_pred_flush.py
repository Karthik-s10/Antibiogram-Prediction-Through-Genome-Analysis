import requests
import sys

print("Sending request...")
sys.stdout.flush()
try:
    with open('e:/Antibiogram-Prediction-Through-Genome-Analysis/DATA/AP011121_random.fasta', 'rb') as f:
        response = requests.post(
            'http://localhost:8001/api/predict',
            files={'genome_file': ('AP011121_random.fasta', f)},
            data={'model_mode': 'both'},
            timeout=120
        )
        print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Caught exception: {e}")
    with open('client_error_trace.log', 'w') as f2:
        f2.write(str(e))
print("Done!")
sys.stdout.flush()
