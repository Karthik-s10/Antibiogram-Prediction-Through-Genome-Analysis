import requests  # type: ignore
import json
import sys
import time

url = 'http://localhost:8001/api/predict'
print(f'Sending POST request to {url} ...')

try:
    with open('e:/Antibiogram-Prediction-Through-Genome-Analysis/DATA/AP011121_random.fasta', 'rb') as f:
        files = {'genome_file': ('AP011121_random.fasta', f)}
        data = {'model_mode': 'both', 'enable_blast': 'true'}
        
        start_time = time.time()
        response = requests.post(url, files=files, data=data, timeout=600)
        elapsed = time.time() - start_time
        
        print(f'Status Code: {response.status_code} (took {elapsed:.2f}s)')
        if response.status_code == 200:
            print('Successfully received data!')
            resp_json = response.json()
            predictions = resp_json.get('predictions', [])
            
            xgb_total = 0
            tr_total = 0
            blast_annotated = 0
            
            for pred in predictions:
                ab = pred.get('antibiotic')
                xgb_markers = pred.get('xgboost_markers', [])
                if xgb_markers:
                    print(f'\n{ab} has {len(xgb_markers)} XGBoost features (SHAP values):')
                    for m in xgb_markers[:3]:
                        print(f"  - Feature: {m.get('feature_name')} | Importance: {round(m.get('importance', 0), 4)} | K-mer: {m.get('kmer_sequence', 'N/A')}")
                    xgb_total += int(len(xgb_markers))  # type: ignore
                    
                tr_markers = pred.get('transformer_markers', [])
                if tr_markers:
                    print(f'\n{ab} has {len(tr_markers)} Transformer markers:')
                    for m in tr_markers[:3]:
                        title = m.get('best_hit_title', 'None')
                        identity = m.get('best_hit_identity')
                        identity_str = f"{identity*100:.1f}%" if identity is not None else "N/A"
                        print(f"  - Gene {m.get('gene_index')} | Importance: {round(m.get('importance', 0), 4)} | BLAST: '{title[:50]}...' ({identity_str})")
                        if 'best_hit_title' in m:
                            blast_annotated += 1  # type: ignore
                    tr_total += int(len(tr_markers))  # type: ignore
                    
            print(f'\nTotal XGBoost markers found: {xgb_total}')
            print(f'Total Transformer markers found: {tr_total}')
            print(f'Total markers annotated with BLAST hits: {blast_annotated}')
            
            with open('test_response.json', 'w') as f2:
                json.dump(resp_json, f2, indent=2)
            print("Saved full response to test_response.json")
        else:
            print(f'Error: {response.text}')

except Exception as e:
    print('Exception occurred during request:', e)
