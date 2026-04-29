import subprocess
import os

output_file = 'batch_results_v8.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    subprocess.run(['python', 'v8_pipeline.py', '--batch', 'Ground_Truth'], stdout=f, stderr=subprocess.STDOUT)

print(f"Batch evaluation completed and saved to {output_file}")
