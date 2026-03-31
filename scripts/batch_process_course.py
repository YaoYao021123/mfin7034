#!/usr/bin/env python3
"""
Batch process PDFs for a course.
Usage: python3 scripts/batch_process_course.py <course_id>
"""

import os
import sys
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/batch_process_course.py <course_id>")
        print("Example: python3 scripts/batch_process_course.py mfin7049")
        sys.exit(1)
    
    course_id = sys.argv[1]
    pdf_dir = f"data/{course_id}/pdfs"
    html_dir = f"data/{course_id}/html"
    extracted_base = f"extracted/{course_id}"
    
    if not os.path.isdir(pdf_dir):
        print(f"[ERROR] PDF directory not found: {pdf_dir}")
        sys.exit(1)
    
    # Get all PDFs
    pdfs = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')])
    print(f"[INFO] Found {len(pdfs)} PDFs in {pdf_dir}")
    print("="*60)
    
    success = 0
    failed = []
    
    for i, pdf_name in enumerate(pdfs, 1):
        pdf_path = os.path.join(pdf_dir, pdf_name)
        base_name = os.path.splitext(pdf_name)[0]
        extracted_dir = os.path.join(extracted_base, base_name)
        
        print(f"\n[{i}/{len(pdfs)}] Processing: {pdf_name}")
        print("-"*50)
        
        # Step 1: Extract PDF
        try:
            result = subprocess.run(
                ['python3', 'extract_pdf.py', pdf_path, extracted_dir],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                print(f"  [ERROR] Extraction failed: {result.stderr[:200]}")
                failed.append((pdf_name, "extraction"))
                continue
            print("  [OK] Extracted content")
        except subprocess.TimeoutExpired:
            print("  [ERROR] Extraction timed out")
            failed.append((pdf_name, "extraction timeout"))
            continue
        except Exception as e:
            print(f"  [ERROR] Extraction error: {e}")
            failed.append((pdf_name, str(e)))
            continue
        
        # Step 2: Generate HTML
        try:
            result = subprocess.run(
                ['python3', 'generate_html.py', extracted_dir, '--output', html_dir],
                capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                print(f"  [ERROR] HTML generation failed: {result.stderr[:200]}")
                failed.append((pdf_name, "html generation"))
                continue
            print("  [OK] Generated HTML")
            success += 1
        except subprocess.TimeoutExpired:
            print("  [ERROR] HTML generation timed out")
            failed.append((pdf_name, "html timeout"))
            continue
        except Exception as e:
            print(f"  [ERROR] HTML generation error: {e}")
            failed.append((pdf_name, str(e)))
            continue
    
    # Summary
    print("\n" + "="*60)
    print("[SUMMARY]")
    print(f"  Total PDFs: {len(pdfs)}")
    print(f"  Successful: {success}")
    print(f"  Failed: {len(failed)}")
    
    if failed:
        print("\n  Failed files:")
        for name, reason in failed:
            print(f"    - {name}: {reason}")
    
    print("="*60)
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
