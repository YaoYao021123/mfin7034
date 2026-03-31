#!/usr/bin/env python3
"""
PDF Content Extractor for Interactive Learning Pages
Extracts text, images, tables, and formulas from PDF course materials
"""

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import json
import os
import re
import sys
from pathlib import Path


def _normalize_title_candidate(value):
    if not isinstance(value, str):
        return ""
    text = re.sub(r"\s+", " ", value).strip()
    text = re.sub(r"\.(pdf|pptx?)$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(microsoft powerpoint\s*-\s*)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(adobe acrobat\s*-\s*)", "", text, flags=re.IGNORECASE)
    return text.strip(" -_:")


def _extract_title_from_first_page(page):
    lines = []
    for raw_line in page.get_text("text").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        lines.append(line)

    if not lines:
        return ""

    skip_prefixes = ("prof.", "professor", "readings:", "reading:")
    filtered = [line for line in lines if not line.lower().startswith(skip_prefixes)]

    for index, line in enumerate(filtered):
        if re.fullmatch(r"lecture\s*\d+\s*[:\-]?", line, flags=re.IGNORECASE):
            next_line = filtered[index + 1] if index + 1 < len(filtered) else ""
            if next_line and len(next_line) >= 4:
                return f"{line.rstrip(': -')}: {next_line}"

    for line in filtered[:12]:
        if len(line) < 6 or len(line) > 120:
            continue
        if "|" in line:
            continue
        if re.search(r"(what to do|overview|contents?)$", line, flags=re.IGNORECASE):
            continue
        if re.search(r"[A-Za-z]{3,}", line):
            return line

    return ""


def derive_pdf_title(doc, pdf_path):
    file_title = Path(pdf_path).stem
    first_page_title = _normalize_title_candidate(_extract_title_from_first_page(doc[0])) if len(doc) else ""
    metadata_title = _normalize_title_candidate(doc.metadata.get("title", "")) if doc.metadata else ""

    for candidate in (first_page_title, metadata_title, file_title):
        if candidate:
            return candidate
    return file_title


def extract_pdf_comprehensive(pdf_path, output_dir):
    """
    Extract all content from PDF with rich structure preservation.
    Returns JSON with text, images, tables, formulas, and metadata.
    """
    
    print(f"\n[PDF] Processing: {pdf_path}")
    print("="*60)
    
    # Create output directories
    output_path = Path(output_dir)
    text_dir = output_path / 'text'
    image_dir = output_path / 'images'
    table_dir = output_path / 'tables'
    
    for dir_path in [text_dir, image_dir, table_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    extracted_data = {
        'title': '',
        'source_file': os.path.basename(pdf_path),
        'pages': [],
        'total_images': 0,
        'total_tables': 0,
        'total_formulas': 0
    }
    
    # Open PDF with PyMuPDF for images and text
    doc = fitz.open(pdf_path)
    
    # Extract a human-readable title from the PDF itself when possible.
    extracted_data['title'] = derive_pdf_title(doc, pdf_path)
    
    print(f"[INFO] Total pages: {len(doc)}")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"  Processing page {page_num + 1}...", end=' ')
        
        page_data = {
            'page_number': page_num + 1,
            'text_blocks': [],
            'images': [],
            'tables': [],
            'has_formulas': False
        }
        
        # Extract text blocks with position and style info
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block['type'] == 0:  # Text block
                for line in block.get('lines', []):
                    spans = line.get('spans', [])
                    if not spans:
                        continue
                    
                    text = ' '.join([span['text'] for span in spans])
                    if not text.strip():
                        continue
                    
                    # Detect headings by font size
                    font_size = spans[0]['size']
                    is_bold = 'bold' in spans[0].get('font', '').lower()
                    is_heading = font_size > 14 or (font_size > 12 and is_bold)
                    
                    # Detect potential formulas (contains math symbols)
                    math_pattern = r'[∫∑∏√∂∇∈∉⊂⊃∪∩±≤≥≠≈∞×÷]|[α-ωΑ-Ω]|[₀-₉]|[⁰-⁹]'
                    is_formula = bool(re.search(math_pattern, text))
                    
                    if is_formula:
                        page_data['has_formulas'] = True
                        extracted_data['total_formulas'] += 1
                    
                    # Determine block type
                    if is_heading:
                        block_type = 'heading'
                    elif is_formula:
                        block_type = 'formula'
                    elif text.strip().startswith('•') or text.strip().startswith('-'):
                        block_type = 'list_item'
                    else:
                        block_type = 'paragraph'
                    
                    page_data['text_blocks'].append({
                        'text': text.strip(),
                        'type': block_type,
                        'font_size': round(font_size, 1),
                        'is_bold': is_bold
                    })
        
        # Extract images
        image_list = page.get_images()
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Skip very small images (likely icons or decorations)
                if len(image_bytes) < 1000:
                    continue
                
                image_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                image_path = image_dir / image_filename
                
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                
                page_data['images'].append({
                    'filename': image_filename,
                    'path': f"images/{image_filename}",
                    'type': image_ext,
                    'size': len(image_bytes)
                })
                extracted_data['total_images'] += 1
            except Exception as e:
                print(f"\n    [WARN] Could not extract image {img_index + 1}: {e}")
        
        extracted_data['pages'].append(page_data)
        print(f"[OK] ({len(page_data['text_blocks'])} blocks, {len(page_data['images'])} images)")
    
    doc.close()
    
    # Use pdfplumber for better table extraction
    print("\n[INFO] Extracting tables...")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                if not tables:
                    continue
                
                for table_index, table in enumerate(tables):
                    if not table or len(table) < 2:  # Need at least header + 1 row
                        continue
                    
                    # Clean table data
                    cleaned_table = []
                    for row in table:
                        cleaned_row = [cell.strip() if cell else '' for cell in row]
                        if any(cleaned_row):  # Skip empty rows
                            cleaned_table.append(cleaned_row)
                    
                    if len(cleaned_table) < 2:
                        continue
                    
                    table_data = {
                        'headers': cleaned_table[0],
                        'rows': cleaned_table[1:],
                        'page': page_num + 1,
                        'row_count': len(cleaned_table) - 1,
                        'col_count': len(cleaned_table[0])
                    }
                    
                    # Save table as JSON
                    table_filename = f"page{page_num + 1}_table{table_index + 1}.json"
                    table_path = table_dir / table_filename
                    
                    with open(table_path, 'w', encoding='utf-8') as f:
                        json.dump(table_data, f, ensure_ascii=False, indent=2)
                    
                    extracted_data['pages'][page_num]['tables'].append({
                        'filename': table_filename,
                        'path': f"tables/{table_filename}",
                        'headers': table_data['headers'],
                        'row_count': table_data['row_count'],
                        'col_count': table_data['col_count']
                    })
                    extracted_data['total_tables'] += 1
                    print(f"  [OK] Page {page_num + 1}: Table with {table_data['row_count']} rows x {table_data['col_count']} cols")
    except Exception as e:
        print(f"  [WARN] Table extraction had issues: {e}")
    
    # Save comprehensive extraction data
    output_json = output_path / 'extracted_content.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)
    
    # Save plain text for easy reading and AI processing
    plain_text = []
    plain_text.append(f"# {extracted_data['title']}\n")
    plain_text.append(f"Source: {extracted_data['source_file']}\n")
    plain_text.append("="*60 + "\n")
    
    for page_data in extracted_data['pages']:
        plain_text.append(f"\n{'='*60}\n")
        plain_text.append(f"PAGE {page_data['page_number']}\n")
        plain_text.append(f"{'='*60}\n\n")
        
        current_section = []
        for block in page_data['text_blocks']:
            if block['type'] == 'heading':
                if current_section:
                    plain_text.append(' '.join(current_section) + '\n\n')
                    current_section = []
                plain_text.append(f"\n## {block['text']}\n\n")
            elif block['type'] == 'list_item':
                if current_section:
                    plain_text.append(' '.join(current_section) + '\n\n')
                    current_section = []
                plain_text.append(f"{block['text']}\n")
            elif block['type'] == 'formula':
                if current_section:
                    plain_text.append(' '.join(current_section) + '\n\n')
                    current_section = []
                plain_text.append(f"\n[FORMULA]: {block['text']}\n\n")
            else:
                current_section.append(block['text'])
        
        if current_section:
            plain_text.append(' '.join(current_section) + '\n\n')
        
        # Note images
        if page_data['images']:
            plain_text.append(f"\n[Images on this page: {', '.join([img['filename'] for img in page_data['images']])}]\n")
        
        # Note tables
        if page_data['tables']:
            plain_text.append(f"\n[Tables on this page: {len(page_data['tables'])}]\n")
    
    full_text_path = text_dir / 'full_text.txt'
    with open(full_text_path, 'w', encoding='utf-8') as f:
        f.write(''.join(plain_text))
    
    # Print summary
    print("\n" + "="*60)
    print("[OK] EXTRACTION COMPLETE")
    print("="*60)
    print(f"Title: {extracted_data['title']}")
    print(f"Pages: {len(extracted_data['pages'])}")
    print(f"Images: {extracted_data['total_images']} extracted")
    print(f"Tables: {extracted_data['total_tables']} extracted")
    print(f"Formulas: {extracted_data['total_formulas']} detected")
    print(f"\nOutput directory: {output_dir}")
    print(f"   - extracted_content.json")
    print(f"   - text/full_text.txt")
    if extracted_data['total_images'] > 0:
        print(f"   - images/ ({extracted_data['total_images']} files)")
    if extracted_data['total_tables'] > 0:
        print(f"   - tables/ ({extracted_data['total_tables']} files)")
    print("="*60)
    
    return extracted_data


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf.py <pdf_path> [output_dir]")
        print("\nExample:")
        print("  python extract_pdf.py 'pdfs/Lec 1 Fintech and Artificial Intelligence.pdf'")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"[ERROR] PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Default output directory based on PDF name
    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_dir = f"extracted/{pdf_name}"
    
    try:
        result = extract_pdf_comprehensive(pdf_path, output_dir)
        print(f"\n[OK] Ready for interactive HTML generation!")
        return 0
    except Exception as e:
        print(f"\n[ERROR] Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
