#!/usr/bin/env python3
"""
Batch process mockup images through B&W pipeline and save to Ground_Truth folder.
"""
import os
import sys
from pathlib import Path
from PIL import Image
import io

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from v8_generate import generate_bw

def process_mockups():
    mockups_dir = Path(__file__).parent / "Mockups"
    gt_dir = Path(__file__).parent / "Ground_Truth"
    
    # Ensure Ground_Truth directory exists
    gt_dir.mkdir(exist_ok=True)
    
    # Get all PNG files in Mockups folder
    mockup_files = sorted([f for f in mockups_dir.iterdir() if f.suffix.lower() == '.png'])
    
    print(f"Found {len(mockup_files)} mockup images to process")
    print(f"Results will be saved to: {gt_dir}")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i, mockup_path in enumerate(mockup_files, 1):
        print(f"\n[{i}/{len(mockup_files)}] Processing: {mockup_path.name}")
        
        try:
            # Read the mockup image
            with open(mockup_path, 'rb') as f:
                mockup_bytes = f.read()
            
            if not mockup_bytes:
                print(f"  [WARN] Empty file, skipping")
                fail_count += 1
                continue
            
            # Process through B&W pipeline
            print(f"  [WORK] Converting to B&W...")
            bw_bytes = generate_bw(mockup_bytes, "image/png")
            
            # Save to Ground_Truth with same filename
            output_path = gt_dir / mockup_path.name
            with open(output_path, 'wb') as f:
                f.write(bw_bytes)
            
            print(f"  [OK] Saved: {output_path.name}")
            success_count += 1
            
        except Exception as e:
            print(f"  [FAIL] {str(e)}")
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"Batch processing complete!")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {fail_count}")
    print(f"  Total:   {len(mockup_files)}")

if __name__ == "__main__":
    process_mockups()