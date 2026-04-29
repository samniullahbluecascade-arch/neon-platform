import re

def parse_results(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    start_parsing = False
    results = []
    
    for line in lines:
        # print(f"DEBUG: checking line: {repr(line)}")
        if '--------------------------------------------------------------------------------------' in line:
            if not start_parsing:
                start_parsing = True
                print("DEBUG: start_parsing = True")
                continue
            else:
                print("DEBUG: break")
                break
        
        if start_parsing:
            match_file = re.search(r'^(.+?\.png)', line)
            if not match_file:
                print(f"DEBUG: match_file failed for: {repr(line)}")
                continue
                
            filename = match_file.group(1).strip()
            
            match_err = re.search(r'([+-]?\d+\.\d+)%', line)
            if match_err:
                err_pct = float(match_err.group(1))
            elif 'N/A%' in line:
                err_pct = 100.0
            else:
                print(f"DEBUG: match_err failed for: {repr(line)}")
                continue
            
            accuracy = max(0, 100 - abs(err_pct))
            results.append((filename, accuracy))
            print(f"DEBUG: added {filename} with accuracy {accuracy}")
            
    return results

if __name__ == "__main__":
    res = parse_results('batch_results_v8.txt')
    print(f"Total results: {len(res)}")
