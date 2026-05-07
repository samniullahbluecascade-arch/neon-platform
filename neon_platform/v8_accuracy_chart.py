import re
import matplotlib.pyplot as plt
import numpy as np

def parse_results(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    start_parsing = False
    results = []
    
    for line in lines:
        if '--------------------------------------------------------------------------------------' in line:
            if not start_parsing:
                start_parsing = True
                continue
            else:
                break
        
        if start_parsing:
            # Match filename and ERR%
            # Example: 12 0.94.png                  0.94   0.932   -0.86% GLASS_CUT       7    5  37   0  15.8s
            # Example: 80 12.87.png                12.87   0.000     N/A% FAIL            0    0   0   0   0.0s [PHYS]
            
            # Match the filename (up to .png)
            match_file = re.search(r'^(.+?\.png)', line)
            if not match_file:
                continue
                
            filename = match_file.group(1).strip()
            
            # Match the error percentage (signed float followed by %) or N/A%
            match_err = re.search(r'([+-]?\d+\.\d+)%', line)
            if match_err:
                err_pct = float(match_err.group(1))
            elif 'N/A%' in line:
                err_pct = 100.0 # Treat N/A as 100% error (0% accuracy)
            else:
                continue
            
            accuracy = max(0, 100 - abs(err_pct))
            results.append((filename, accuracy))
            
    return results

def create_chart(results):
    if not results:
        print("No results found to plot.")
        return

    # Sort by accuracy for better visualization
    results.sort(key=lambda x: x[1], reverse=True)
    
    filenames = [r[0] for r in results]
    accuracies = [r[1] for r in results]
    
    plt.figure(figsize=(20, 10))
    bars = plt.bar(range(len(accuracies)), accuracies, color='skyblue', edgecolor='navy')
    
    plt.xlabel('Images', fontsize=12)
    plt.ylabel('Accuracy (%)', fontsize=12)
    plt.title(f'Full Batch Accuracy Results ({len(results)} images)', fontsize=16)
    plt.ylim(0, 105)
    
    # Add horizontal lines for Tiers
    plt.axhline(y=95, color='green', linestyle='--', alpha=0.5, label='GLASS_CUT (95%)')
    plt.axhline(y=90, color='blue', linestyle='--', alpha=0.5, label='QUOTE (90%)')
    plt.axhline(y=80, color='orange', linestyle='--', alpha=0.5, label='ESTIMATE (80%)')
    plt.axhline(y=65, color='red', linestyle='--', alpha=0.5, label='MARGINAL (65%)')
    
    plt.xticks(range(len(filenames)), filenames, rotation=90, fontsize=8)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('batch_accuracy_chart.png')
    print(f"Chart saved as batch_accuracy_chart.png with {len(results)} images.")

if __name__ == "__main__":
    results = parse_results('batch_results_v8.txt')
    create_chart(results)
