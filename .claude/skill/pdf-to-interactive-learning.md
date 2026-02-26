---
name: pdf-to-interactive-learning
description: Extract content from PDF course materials and create interactive, visually rich HTML learning pages using Feynman technique. Includes formula rendering (KaTeX), AI Q&A integration, content expansion, and knowledge testing. Use when converting PDFs to interactive learning experiences.
---

# PDF to Interactive Learning - Feynman Method Skill

Transform static PDF course materials into interactive, self-contained HTML learning experiences that promote deep understanding through the Feynman technique. Each page includes visual explanations, interactive elements, formula rendering, AI-powered Q&A, and knowledge validation.

## Core Philosophy

1. **Feynman Technique** — Learn by explaining simply, identify knowledge gaps, expand with examples
2. **Visual Learning** — Use diagrams, charts, tables, and rich media extracted from PDFs
3. **Interactive Engagement** — Click-to-reveal, hover tooltips, expandable sections, practice questions
4. **Self-Contained** — Single HTML file with inline CSS/JS, works offline, no dependencies
5. **Content Rich** — Never summarize - expand with context, examples, analogies, and real-world applications

---

## Workflow Overview

```
Phase 0: Detect Input → Phase 1: PDF Extraction → Phase 2: Content Analysis → 
Phase 3: Feynman Structure → Phase 4: Generate HTML → Phase 5: Visual Review & Self-Correction → Phase 6: Testing & Delivery
```

---

## Phase 0: Detect Input Mode

Determine what the user has:

**Mode A: PDF File Provided**
- User has uploaded or specified PDF path
- Proceed to Phase 1 (PDF Extraction)

**Mode B: Content Already Extracted**
- User has text/images in a folder
- Skip to Phase 2 (Content Analysis)

**Mode C: Topic Only**
- User wants to create learning page from scratch
- Use AI to generate comprehensive content, then proceed

---

## Phase 1: PDF Extraction

### Step 1.1: Install Required Tools

Check and install PDF processing libraries:

```bash
# Check Python
python3 --version

# Install required packages
pip3 install PyMuPDF pymupdf4llm pdfplumber Pillow
```

### Step 1.2: Extract Content from PDF

Create extraction script that captures:
- **Text content** with structure (headings, paragraphs, lists)
- **Images** (figures, diagrams, charts)
- **Tables** with preserved structure
- **Mathematical formulas** (as text to convert to LaTeX)
- **Metadata** (page numbers, sections)

```python
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import json
import os
import re

def extract_pdf_comprehensive(pdf_path, output_dir):
    """
    Extract all content from PDF with rich structure preservation.
    Returns JSON with text, images, tables, formulas, and metadata.
    """
    
    # Create output directories
    text_dir = os.path.join(output_dir, 'text')
    image_dir = os.path.join(output_dir, 'images')
    table_dir = os.path.join(output_dir, 'tables')
    os.makedirs(text_dir, exist_ok=True)
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(table_dir, exist_ok=True)
    
    extracted_data = {
        'title': '',
        'pages': [],
        'total_images': 0,
        'total_tables': 0
    }
    
    # Open PDF with PyMuPDF for images and text
    doc = fitz.open(pdf_path)
    
    # Extract title from first page or filename
    extracted_data['title'] = os.path.splitext(os.path.basename(pdf_path))[0]
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_data = {
            'page_number': page_num + 1,
            'text_blocks': [],
            'images': [],
            'tables': [],
            'formulas': []
        }
        
        # Extract text blocks with position and style info
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block['type'] == 0:  # Text block
                for line in block.get('lines', []):
                    text = ' '.join([span['text'] for span in line.get('spans', [])])
                    if text.strip():
                        # Detect headings by font size
                        font_size = line['spans'][0]['size'] if line['spans'] else 12
                        is_heading = font_size > 14
                        
                        # Detect potential formulas (contains math symbols)
                        is_formula = bool(re.search(r'[∫∑∏√∂∇∈∉⊂⊃∪∩±≤≥≠≈∞]|[α-ωΑ-Ω]', text))
                        
                        page_data['text_blocks'].append({
                            'text': text,
                            'type': 'heading' if is_heading else ('formula' if is_formula else 'paragraph'),
                            'font_size': font_size,
                            'bbox': line['bbox']
                        })
        
        # Extract images
        image_list = page.get_images()
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            image_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
            image_path = os.path.join(image_dir, image_filename)
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            page_data['images'].append({
                'filename': image_filename,
                'path': f"images/{image_filename}",
                'type': image_ext
            })
            extracted_data['total_images'] += 1
        
        extracted_data['pages'].append(page_data)
    
    doc.close()
    
    # Use pdfplumber for better table extraction
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            
            for table_index, table in enumerate(tables):
                if table and len(table) > 1:  # Valid table with headers
                    table_data = {
                        'headers': table[0],
                        'rows': table[1:],
                        'page': page_num + 1
                    }
                    
                    # Save table as JSON
                    table_filename = f"page{page_num + 1}_table{table_index + 1}.json"
                    table_path = os.path.join(table_dir, table_filename)
                    
                    with open(table_path, 'w', encoding='utf-8') as f:
                        json.dump(table_data, f, ensure_ascii=False, indent=2)
                    
                    extracted_data['pages'][page_num]['tables'].append({
                        'filename': table_filename,
                        'path': f"tables/{table_filename}",
                        'headers': table[0],
                        'row_count': len(table) - 1
                    })
                    extracted_data['total_tables'] += 1
    
    # Save comprehensive extraction data
    output_json = os.path.join(output_dir, 'extracted_content.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)
    
    # Save plain text for easy reading
    plain_text = []
    for page_data in extracted_data['pages']:
        plain_text.append(f"\n{'='*60}\nPAGE {page_data['page_number']}\n{'='*60}\n")
        for block in page_data['text_blocks']:
            plain_text.append(block['text'])
    
    with open(os.path.join(text_dir, 'full_text.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(plain_text))
    
    return extracted_data

# Usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python extract_pdf.py <pdf_path> <output_dir>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    result = extract_pdf_comprehensive(pdf_path, output_dir)
    print(f"\n✓ Extraction complete!")
    print(f"  Title: {result['title']}")
    print(f"  Pages: {len(result['pages'])}")
    print(f"  Images: {result['total_images']}")
    print(f"  Tables: {result['total_tables']}")
    print(f"\n  Output: {output_dir}")
```

### Step 1.3: Verify Extraction

Present extraction summary to user:

```
PDF Extraction Complete ✓

📄 Title: [extracted_title]
📊 Pages: [count]
🖼️  Images: [count] extracted
📋 Tables: [count] extracted
📐 Formulas: [count] detected

Content Preview:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[First 200 words of content...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Files created:
  • extracted_content.json
  • text/full_text.txt
  • images/ (XX files)
  • tables/ (XX files)

Does this look correct? Ready to proceed to content analysis?
```

---

## Phase 2: Content Analysis & Structuring

### Step 2.1: Analyze Content Depth

Use AI to analyze the extracted content:

```
Analyze this course material and identify:

1. **Main Concepts** (5-10 key concepts)
2. **Prerequisites** (what students should know beforehand)
3. **Learning Objectives** (what students will master)
4. **Difficulty Level** (beginner/intermediate/advanced)
5. **Key Formulas** (extract and convert to LaTeX)
6. **Weak Points** (content that seems under-explained)
7. **Example Gaps** (concepts that need more examples)

Content:
[extracted_content]

Format as JSON for processing.
```

### Step 2.2: Identify Content Gaps

For each main concept, determine if expansion is needed:

```json
{
  "concept": "Arbitrage Pricing Theory",
  "current_length": "2 paragraphs",
  "clarity_score": 6,
  "needs_expansion": true,
  "expansion_areas": [
    "Real-world examples",
    "Step-by-step derivation",
    "Comparison with CAPM",
    "Common misconceptions"
  ]
}
```

### Step 2.3: Create Learning Structure

Build Feynman-inspired structure:

1. **Hook** — Why this matters (real-world relevance)
2. **Simple Explanation** — Explain like I'm 12
3. **Deep Dive** — Technical details, formulas, proofs
4. **Visual Analogy** — Metaphors and diagrams
5. **Examples** — Worked examples with step-by-step
6. **Common Mistakes** — What students often get wrong
7. **Practice** — Interactive questions
8. **Connections** — How this relates to other concepts

---

## Phase 3: Content Expansion with AI

For each concept that needs expansion:

### Step 3.1: Generate Analogies

```
Create 2-3 intuitive analogies for:
[concept_name]

Original explanation:
[original_text]

Requirements:
- Use everyday objects/scenarios
- Maintain mathematical accuracy
- Suitable for finance students
- Avoid overused metaphors
```

### Step 3.2: Create Examples

```
Generate 2-3 worked examples for:
[concept_name]

Requirements:
- Start simple, increase complexity
- Show every step with explanation
- Use realistic numbers/scenarios
- Include common edge cases
- Provide visual representation suggestions
```

### Step 3.3: Generate Practice Questions

```
Create 5 practice questions for:
[concept_name]

Types needed:
1. Conceptual understanding (multiple choice)
2. Formula application (numerical)
3. Edge case identification (true/false with explanation)
4. Real-world scenario (case study)
5. Common mistake detection (find the error)

Include detailed solutions with explanations.
```

---

## Phase 4: Generate Interactive HTML

### HTML Architecture

Create self-contained HTML with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Course Title] - Interactive Learning</title>
    
    <!-- KaTeX for formula rendering -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    
    <!-- Chart.js for data visualization -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
    
    <!-- Mermaid for flowcharts, sequence diagrams, concept maps -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <style>
        /* ===========================================
           DESIGN SYSTEM - CSS VARIABLES
           =========================================== */
        :root {
            /* Colors - Professional Academic Theme */
            --bg-primary: #0f1419;
            --bg-secondary: #1a1f29;
            --bg-tertiary: #252d3a;
            --bg-elevated: #2d3748;
            
            --text-primary: #f7fafc;
            --text-secondary: #cbd5e0;
            --text-tertiary: #a0aec0;
            
            --accent-primary: #4299e1;
            --accent-secondary: #48bb78;
            --accent-warning: #ed8936;
            --accent-error: #f56565;
            
            --border-color: rgba(255, 255, 255, 0.1);
            --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
            --shadow-lg: 0 10px 30px rgba(0, 0, 0, 0.5);
            
            /* Typography */
            --font-primary: 'Inter', -apple-system, system-ui, sans-serif;
            --font-mono: 'JetBrains Mono', 'Courier New', monospace;
            
            /* Spacing */
            --space-unit: 8px;
            --page-padding: clamp(1rem, 5vw, 3rem);
            
            /* Animation */
            --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);
            --duration-fast: 200ms;
            --duration-normal: 300ms;
            --duration-slow: 500ms;
        }
        
        /* Light mode support */
        @media (prefers-color-scheme: light) {
            :root {
                --bg-primary: #ffffff;
                --bg-secondary: #f7fafc;
                --bg-tertiary: #edf2f7;
                --bg-elevated: #ffffff;
                
                --text-primary: #1a202c;
                --text-secondary: #4a5568;
                --text-tertiary: #718096;
                
                --border-color: rgba(0, 0, 0, 0.1);
                --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.1);
                --shadow-lg: 0 10px 30px rgba(0, 0, 0, 0.15);
            }
        }
        
        /* ===========================================
           BASE STYLES
           =========================================== */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        html {
            scroll-behavior: smooth;
            font-size: 16px;
        }
        
        body {
            font-family: var(--font-primary);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
        }
        
        /* ===========================================
           LAYOUT STRUCTURE
           =========================================== */
        .page-container {
            display: grid;
            grid-template-columns: 280px 1fr 320px;
            gap: 0;
            min-height: 100vh;
        }
        
        /* Left Sidebar - Table of Contents */
        .sidebar-left {
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            padding: calc(var(--space-unit) * 3);
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
        }
        
        /* Main Content Area */
        .main-content {
            max-width: 900px;
            margin: 0 auto;
            padding: calc(var(--space-unit) * 6) var(--page-padding);
        }
        
        /* Right Sidebar - AI Assistant & Tools */
        .sidebar-right {
            background: var(--bg-secondary);
            border-left: 1px solid var(--border-color);
            padding: calc(var(--space-unit) * 3);
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
        }
        
        /* Responsive */
        @media (max-width: 1400px) {
            .page-container {
                grid-template-columns: 1fr;
            }
            
            .sidebar-left,
            .sidebar-right {
                display: none;
            }
            
            /* Mobile navigation */
            .mobile-nav {
                display: block;
            }
        }
        
        /* ===========================================
           TYPOGRAPHY
           =========================================== */
        h1 {
            font-size: clamp(2rem, 5vw, 3rem);
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: calc(var(--space-unit) * 3);
            color: var(--text-primary);
        }
        
        h2 {
            font-size: clamp(1.5rem, 4vw, 2rem);
            font-weight: 600;
            margin-top: calc(var(--space-unit) * 6);
            margin-bottom: calc(var(--space-unit) * 3);
            color: var(--accent-primary);
        }
        
        h3 {
            font-size: 1.25rem;
            font-weight: 600;
            margin-top: calc(var(--space-unit) * 4);
            margin-bottom: calc(var(--space-unit) * 2);
        }
        
        p {
            margin-bottom: calc(var(--space-unit) * 2);
            color: var(--text-secondary);
            font-size: 1.05rem;
        }
        
        /* ===========================================
           INTERACTIVE COMPONENTS
           =========================================== */
        
        /* Feynman Explanation Block */
        .feynman-block {
            background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-elevated) 100%);
            border-left: 4px solid var(--accent-primary);
            border-radius: 12px;
            padding: calc(var(--space-unit) * 3);
            margin: calc(var(--space-unit) * 4) 0;
            box-shadow: var(--shadow-sm);
        }
        
        .feynman-block .icon {
            font-size: 2rem;
            margin-bottom: calc(var(--space-unit) * 2);
        }
        
        .feynman-block h4 {
            color: var(--accent-primary);
            margin-bottom: calc(var(--space-unit) * 2);
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        /* Expandable Sections */
        .expandable {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin: calc(var(--space-unit) * 3) 0;
            overflow: hidden;
            transition: all var(--duration-normal) var(--ease-smooth);
        }
        
        .expandable-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: calc(var(--space-unit) * 2) calc(var(--space-unit) * 3);
            cursor: pointer;
            user-select: none;
            font-weight: 500;
            transition: background var(--duration-fast);
        }
        
        .expandable-header:hover {
            background: var(--bg-tertiary);
        }
        
        .expandable-icon {
            transition: transform var(--duration-normal) var(--ease-smooth);
        }
        
        .expandable.open .expandable-icon {
            transform: rotate(180deg);
        }
        
        .expandable-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height var(--duration-slow) var(--ease-smooth);
        }
        
        .expandable.open .expandable-content {
            max-height: 5000px;
        }
        
        .expandable-content-inner {
            padding: calc(var(--space-unit) * 3);
            border-top: 1px solid var(--border-color);
        }
        
        /* Formula Display */
        .formula-block {
            background: var(--bg-elevated);
            border-radius: 8px;
            padding: calc(var(--space-unit) * 3);
            margin: calc(var(--space-unit) * 3) 0;
            overflow-x: auto;
            box-shadow: var(--shadow-sm);
        }
        
        .formula-block .katex-display {
            margin: 0;
        }
        
        /* Interactive Quiz */
        .quiz-container {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: calc(var(--space-unit) * 4);
            margin: calc(var(--space-unit) * 4) 0;
            border: 2px solid var(--border-color);
        }
        
        .quiz-question {
            font-size: 1.1rem;
            font-weight: 500;
            margin-bottom: calc(var(--space-unit) * 3);
            color: var(--text-primary);
        }
        
        .quiz-options {
            display: flex;
            flex-direction: column;
            gap: calc(var(--space-unit) * 2);
        }
        
        .quiz-option {
            background: var(--bg-tertiary);
            border: 2px solid var(--border-color);
            border-radius: 8px;
            padding: calc(var(--space-unit) * 2) calc(var(--space-unit) * 3);
            cursor: pointer;
            transition: all var(--duration-fast);
            font-size: 1rem;
        }
        
        .quiz-option:hover {
            border-color: var(--accent-primary);
            transform: translateX(4px);
        }
        
        .quiz-option.selected {
            background: var(--accent-primary);
            border-color: var(--accent-primary);
            color: white;
        }
        
        .quiz-option.correct {
            background: var(--accent-secondary);
            border-color: var(--accent-secondary);
            color: white;
        }
        
        .quiz-option.incorrect {
            background: var(--accent-error);
            border-color: var(--accent-error);
            color: white;
        }
        
        .quiz-feedback {
            margin-top: calc(var(--space-unit) * 3);
            padding: calc(var(--space-unit) * 2);
            border-radius: 8px;
            display: none;
        }
        
        .quiz-feedback.show {
            display: block;
        }
        
        .quiz-feedback.correct {
            background: rgba(72, 187, 120, 0.2);
            border: 1px solid var(--accent-secondary);
        }
        
        .quiz-feedback.incorrect {
            background: rgba(245, 101, 101, 0.2);
            border: 1px solid var(--accent-error);
        }
        
        /* Image Gallery */
        .image-container {
            margin: calc(var(--space-unit) * 4) 0;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: var(--shadow-lg);
        }
        
        .image-container img {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .image-caption {
            background: var(--bg-elevated);
            padding: calc(var(--space-unit) * 2);
            text-align: center;
            font-size: 0.9rem;
            color: var(--text-tertiary);
        }
        
        /* Table Styling */
        .table-container {
            overflow-x: auto;
            margin: calc(var(--space-unit) * 4) 0;
            border-radius: 8px;
            box-shadow: var(--shadow-sm);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-secondary);
        }
        
        thead {
            background: var(--bg-elevated);
        }
        
        th {
            padding: calc(var(--space-unit) * 2);
            text-align: left;
            font-weight: 600;
            color: var(--accent-primary);
            border-bottom: 2px solid var(--border-color);
        }
        
        td {
            padding: calc(var(--space-unit) * 2);
            border-bottom: 1px solid var(--border-color);
        }
        
        tr:hover {
            background: var(--bg-tertiary);
        }
        
        /* ===========================================
           DATA VISUALIZATION & CHARTS
           =========================================== */
        
        /* Chart Container */
        .chart-container {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: calc(var(--space-unit) * 3);
            margin: calc(var(--space-unit) * 4) 0;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
            position: relative;
        }
        
        .chart-container .chart-title {
            font-family: var(--font-primary);
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: calc(var(--space-unit) * 2);
            text-align: center;
        }
        
        .chart-container .chart-subtitle {
            font-size: 0.85rem;
            color: var(--text-tertiary);
            text-align: center;
            margin-bottom: calc(var(--space-unit) * 2);
        }
        
        .chart-container canvas {
            max-height: 400px;
            width: 100% !important;
        }
        
        .chart-caption {
            font-size: 0.85rem;
            color: var(--text-tertiary);
            text-align: center;
            margin-top: calc(var(--space-unit) * 2);
            font-style: italic;
        }
        
        /* Chart Grid - side by side charts */
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: calc(var(--space-unit) * 3);
            margin: calc(var(--space-unit) * 4) 0;
        }
        
        .chart-grid .chart-container {
            margin: 0;
        }
        
        /* Mermaid Diagram Container */
        .diagram-container {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: calc(var(--space-unit) * 3);
            margin: calc(var(--space-unit) * 4) 0;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
            overflow-x: auto;
            text-align: center;
        }
        
        .diagram-container .diagram-title {
            font-family: var(--font-primary);
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: calc(var(--space-unit) * 2);
        }
        
        .diagram-container .mermaid {
            display: flex;
            justify-content: center;
        }
        
        .diagram-container .mermaid svg {
            max-width: 100%;
            height: auto;
        }
        
        .diagram-caption {
            font-size: 0.85rem;
            color: var(--text-tertiary);
            text-align: center;
            margin-top: calc(var(--space-unit) * 2);
            font-style: italic;
        }
        
        /* Comparison Visual Block */
        .comparison-block {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: calc(var(--space-unit) * 2);
            align-items: stretch;
            margin: calc(var(--space-unit) * 4) 0;
        }
        
        .comparison-side {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: calc(var(--space-unit) * 3);
            border: 1px solid var(--border-color);
        }
        
        .comparison-side.left {
            border-top: 3px solid var(--accent-primary);
        }
        
        .comparison-side.right {
            border-top: 3px solid var(--accent-secondary);
        }
        
        .comparison-divider {
            display: flex;
            align-items: center;
            font-size: 1.5rem;
            color: var(--text-tertiary);
        }
        
        /* Timeline / Process Visualization */
        .timeline-block {
            position: relative;
            margin: calc(var(--space-unit) * 4) 0;
            padding-left: calc(var(--space-unit) * 5);
        }
        
        .timeline-block::before {
            content: '';
            position: absolute;
            left: 16px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: linear-gradient(180deg, var(--accent-primary), var(--accent-secondary));
        }
        
        .timeline-item {
            position: relative;
            margin-bottom: calc(var(--space-unit) * 4);
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: calc(var(--space-unit) * 3);
            border: 1px solid var(--border-color);
        }
        
        .timeline-item::before {
            content: '';
            position: absolute;
            left: calc(-1 * var(--space-unit) * 5 + 10px);
            top: 20px;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: var(--accent-primary);
            border: 3px solid var(--bg-primary);
        }
        
        /* Stats / KPI Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: calc(var(--space-unit) * 2);
            margin: calc(var(--space-unit) * 4) 0;
        }
        
        .stat-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: calc(var(--space-unit) * 3);
            text-align: center;
            border: 1px solid var(--border-color);
            transition: transform var(--duration-fast) var(--ease-smooth);
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent-primary);
            display: block;
        }
        
        .stat-label {
            font-size: 0.85rem;
            color: var(--text-tertiary);
            margin-top: calc(var(--space-unit) * 1);
        }
        
        @media (max-width: 768px) {
            .comparison-block { grid-template-columns: 1fr; }
            .comparison-divider { justify-content: center; transform: rotate(90deg); }
            .chart-grid { grid-template-columns: 1fr; }
        }
        
        /* AI Chat Interface */
        .ai-chat {
            background: var(--bg-tertiary);
            border-radius: 12px;
            padding: calc(var(--space-unit) * 3);
            margin-top: calc(var(--space-unit) * 3);
        }
        
        .ai-chat-header {
            display: flex;
            align-items: center;
            gap: calc(var(--space-unit) * 2);
            margin-bottom: calc(var(--space-unit) * 3);
        }
        
        .ai-chat-messages {
            max-height: 400px;
            overflow-y: auto;
            margin-bottom: calc(var(--space-unit) * 2);
            padding: calc(var(--space-unit) * 2);
            background: var(--bg-secondary);
            border-radius: 8px;
        }
        
        .ai-message {
            margin-bottom: calc(var(--space-unit) * 2);
            padding: calc(var(--space-unit) * 2);
            border-radius: 8px;
        }
        
        .ai-message.user {
            background: var(--accent-primary);
            color: white;
            margin-left: calc(var(--space-unit) * 4);
        }
        
        .ai-message.assistant {
            background: var(--bg-elevated);
            margin-right: calc(var(--space-unit) * 4);
        }
        
        .ai-input-group {
            display: flex;
            gap: calc(var(--space-unit) * 2);
        }
        
        .ai-input {
            flex: 1;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: calc(var(--space-unit) * 2);
            color: var(--text-primary);
            font-family: var(--font-primary);
            font-size: 0.95rem;
        }
        
        .ai-send-btn {
            background: var(--accent-primary);
            color: white;
            border: none;
            border-radius: 8px;
            padding: calc(var(--space-unit) * 2) calc(var(--space-unit) * 3);
            cursor: pointer;
            font-weight: 500;
            transition: all var(--duration-fast);
        }
        
        .ai-send-btn:hover {
            background: var(--accent-secondary);
            transform: translateY(-2px);
        }
        
        /* Progress Tracker */
        .progress-tracker {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: var(--bg-secondary);
            z-index: 1000;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
            width: 0%;
            transition: width var(--duration-normal) var(--ease-smooth);
        }
        
        /* ===========================================
           ANIMATIONS
           =========================================== */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .animate-in {
            animation: fadeInUp var(--duration-slow) var(--ease-smooth);
        }
        
        /* Reduced motion support */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
</head>
<body>
    <!-- Progress Tracker -->
    <div class="progress-tracker">
        <div class="progress-bar" id="progressBar"></div>
    </div>

    <div class="page-container">
        <!-- Left Sidebar: Tabbed (Contents / PDF / Notes) -->
        <aside class="sidebar-left">
            <div class="sidebar-tabs">
                <button class="sidebar-tab active" onclick="switchSidebarTab('toc')">Contents</button>
                <button class="sidebar-tab" onclick="switchSidebarTab('pdf')">PDF</button>
                <button class="sidebar-tab" onclick="switchSidebarTab('notes')">Notes</button>
            </div>

            <!-- Tab: Table of Contents -->
            <div id="panel-toc" class="sidebar-panel active">
                <nav id="tocNav">
                    <!-- Generated by JavaScript -->
                </nav>
            </div>

            <!-- Tab: PDF Viewer -->
            <div id="panel-pdf" class="sidebar-panel" style="display:none;">
                <iframe id="pdfViewer" src="pdfs/[source_file.pdf]"
                    style="width:100%;height:calc(100vh - 120px);border:none;border-radius:8px;">
                </iframe>
            </div>

            <!-- Tab: Notes (Markdown) -->
            <div id="panel-notes" class="sidebar-panel" style="display:none;">
                <div id="notesList"></div>
                <textarea id="noteEditor" placeholder="Write a note (Markdown supported)..."
                    style="width:100%;min-height:80px;margin-top:1rem;"></textarea>
                <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
                    <button onclick="addFreeNote()">Add Note</button>
                    <button onclick="exportNotesToObsidian()">Export .md</button>
                </div>
            </div>
        </aside>

        <!-- Main Content -->
        <main class="main-content">
            <header>
                <h1 id="mainTitle">[Course Title]</h1>
                <p style="font-size: 1.1rem; color: var(--text-tertiary);">
                    Interactive Learning Experience • [Date]
                </p>
            </header>

            <!-- Content sections generated here -->
            <section id="content">
                <!-- Dynamically generated from extraction -->
            </section>
        </main>

        <!-- Right Sidebar: AI Assistant & Tools -->
        <aside class="sidebar-right">
            <div class="ai-chat">
                <div class="ai-chat-header">
                    <span style="font-size: 1.5rem;">🤖</span>
                    <h3>AI Study Assistant</h3>
                </div>
                
                <div class="ai-chat-messages" id="aiMessages">
                    <div class="ai-message assistant">
                        Hi! I'm your AI study assistant. Ask me anything about this topic, or request:
                        <ul style="margin-top: 0.5rem; padding-left: 1.5rem;">
                            <li>Explanations in simpler terms</li>
                            <li>More examples</li>
                            <li>Practice questions</li>
                            <li>Connections to other concepts</li>
                        </ul>
                    </div>
                </div>
                
                <div class="ai-input-group">
                    <input 
                        type="text" 
                        class="ai-input" 
                        id="aiInput" 
                        placeholder="Ask a question..."
                        onkeypress="if(event.key==='Enter') sendAIMessage()"
                    />
                    <button class="ai-send-btn" onclick="sendAIMessage()">Send</button>
                </div>
            </div>

            <!-- Quick Actions -->
            <div style="margin-top: 2rem;">
                <h4 style="margin-bottom: 1rem; color: var(--text-tertiary);">⚡ Quick Actions</h4>
                <button onclick="generatePracticeQuiz()" style="width: 100%; margin-bottom: 0.5rem; padding: 0.75rem; background: var(--bg-elevated); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary); cursor: pointer;">
                    🎯 Generate Practice Quiz
                </button>
                <button onclick="createSummary()" style="width: 100%; margin-bottom: 0.5rem; padding: 0.75rem; background: var(--bg-elevated); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary); cursor: pointer;">
                    📝 Create Summary
                </button>
                <button onclick="exportNotes()" style="width: 100%; margin-bottom: 0.5rem; padding: 0.75rem; background: var(--bg-elevated); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary); cursor: pointer;">
                    💾 Export Notes
                </button>
            </div>
        </aside>
    </div>

    <script>
        /* ===========================================
           INTERACTIVE LEARNING CONTROLLER
           Manages all interactive elements and AI integration
           =========================================== */
        
        class LearningPageController {
            constructor() {
                this.initializeKaTeX();
                this.initializeMermaid();
                this.initializeCharts();
                this.setupExpandables();
                this.setupQuizzes();
                this.generateTableOfContents();
                this.setupProgressTracking();
                this.setupKeyboardShortcuts();
                this.initializeAIAssistant();
            }
            
            // Render all math formulas
            initializeKaTeX() {
                document.addEventListener("DOMContentLoaded", () => {
                    renderMathInElement(document.body, {
                        delimiters: [
                            {left: "$$", right: "$$", display: true},
                            {left: "$", right: "$", display: false},
                            {left: "\\[", right: "\\]", display: true},
                            {left: "\\(", right: "\\)", display: false}
                        ],
                        throwOnError: false
                    });
                });
            }
            
            // Initialize Mermaid diagrams
            initializeMermaid() {
                mermaid.initialize({
                    startOnLoad: true,
                    theme: 'dark',
                    themeVariables: {
                        primaryColor: '#4299e1',
                        primaryTextColor: '#f7fafc',
                        primaryBorderColor: '#4299e1',
                        lineColor: '#a0aec0',
                        secondaryColor: '#48bb78',
                        tertiaryColor: '#2d3748',
                        background: '#1a1f29',
                        mainBkg: '#2d3748',
                        nodeBorder: '#4299e1',
                        clusterBkg: '#252d3a',
                        fontSize: '14px'
                    },
                    flowchart: { curve: 'basis', padding: 20 },
                    sequence: { actorMargin: 50 }
                });
            }
            
            // Initialize Chart.js instances with responsive defaults
            initializeCharts() {
                Chart.defaults.color = '#a0aec0';
                Chart.defaults.borderColor = 'rgba(255,255,255,0.1)';
                Chart.defaults.font.family = "'Inter', sans-serif";
                Chart.defaults.responsive = true;
                Chart.defaults.maintainAspectRatio = true;
                Chart.defaults.plugins.legend.labels.usePointStyle = true;
                
                // Auto-initialize any chart canvases with data-chart attribute
                document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
                    try {
                        const config = JSON.parse(canvas.dataset.chart);
                        new Chart(canvas, config);
                    } catch(e) {
                        console.warn('Chart init error:', e);
                    }
                });
            }
            
            // Setup expandable sections
            setupExpandables() {
                const expandables = document.querySelectorAll('.expandable-header');
                expandables.forEach(header => {
                    header.addEventListener('click', () => {
                        const expandable = header.parentElement;
                        expandable.classList.toggle('open');
                    });
                });
            }
            
            // Setup interactive quizzes
            setupQuizzes() {
                const quizOptions = document.querySelectorAll('.quiz-option');
                quizOptions.forEach(option => {
                    option.addEventListener('click', () => this.handleQuizAnswer(option));
                });
            }
            
            handleQuizAnswer(option) {
                const quiz = option.closest('.quiz-container');
                const feedback = quiz.querySelector('.quiz-feedback');
                const isCorrect = option.dataset.correct === 'true';
                
                // Clear previous selections
                quiz.querySelectorAll('.quiz-option').forEach(opt => {
                    opt.classList.remove('selected', 'correct', 'incorrect');
                });
                
                // Mark selection
                option.classList.add('selected');
                option.classList.add(isCorrect ? 'correct' : 'incorrect');
                
                // Show feedback
                feedback.classList.add('show', isCorrect ? 'correct' : 'incorrect');
                feedback.classList.remove(isCorrect ? 'incorrect' : 'correct');
            }
            
            // Generate table of contents
            generateTableOfContents() {
                const content = document.getElementById('content');
                const nav = document.getElementById('tocNav');
                const headings = content.querySelectorAll('h2, h3');
                
                let tocHTML = '<ul style="list-style: none; padding: 0;">';
                headings.forEach((heading, index) => {
                    const id = `section-${index}`;
                    heading.id = id;
                    
                    const indent = heading.tagName === 'H3' ? '1.5rem' : '0';
                    const fontSize = heading.tagName === 'H2' ? '1rem' : '0.9rem';
                    
                    tocHTML += `
                        <li style="margin-bottom: 0.75rem; padding-left: ${indent};">
                            <a href="#${id}" style="
                                color: var(--text-secondary);
                                text-decoration: none;
                                transition: color var(--duration-fast);
                                font-size: ${fontSize};
                                display: block;
                            " onmouseover="this.style.color='var(--accent-primary)'" onmouseout="this.style.color='var(--text-secondary)'">
                                ${heading.textContent}
                            </a>
                        </li>
                    `;
                });
                tocHTML += '</ul>';
                
                nav.innerHTML = tocHTML;
            }
            
            // Track reading progress
            setupProgressTracking() {
                window.addEventListener('scroll', () => {
                    const windowHeight = window.innerHeight;
                    const documentHeight = document.documentElement.scrollHeight - windowHeight;
                    const scrolled = window.scrollY;
                    const progress = (scrolled / documentHeight) * 100;
                    
                    document.getElementById('progressBar').style.width = `${progress}%`;
                });
            }
            
            // Keyboard shortcuts
            setupKeyboardShortcuts() {
                document.addEventListener('keydown', (e) => {
                    // Alt+Q: Generate quiz
                    if (e.altKey && e.key === 'q') {
                        e.preventDefault();
                        generatePracticeQuiz();
                    }
                    
                    // Alt+S: Create summary
                    if (e.altKey && e.key === 's') {
                        e.preventDefault();
                        createSummary();
                    }
                    
                    // Alt+A: Focus AI input
                    if (e.altKey && e.key === 'a') {
                        e.preventDefault();
                        document.getElementById('aiInput').focus();
                    }
                });
            }
            
            // AI Assistant integration
            initializeAIAssistant() {
                // This is a placeholder for AI integration
                // In production, connect to Claude API or similar
                console.log('AI Assistant initialized');
            }
        }
        
        /* ===========================================
           AI ASSISTANT FUNCTIONS
           =========================================== */
        
        function sendAIMessage() {
            const input = document.getElementById('aiInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            const messagesContainer = document.getElementById('aiMessages');
            
            // Add user message
            messagesContainer.innerHTML += `
                <div class="ai-message user">${escapeHtml(message)}</div>
            `;
            
            input.value = '';
            
            // Simulate AI response (replace with actual AI API call)
            setTimeout(() => {
                const response = generateAIResponse(message);
                messagesContainer.innerHTML += `
                    <div class="ai-message assistant">${response}</div>
                `;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }, 1000);
        }
        
        function generateAIResponse(question) {
            // Placeholder AI response logic
            // In production, call Claude API with course content as context
            
            const responses = {
                'default': "I'd be happy to help explain that! Based on the course content, here's what I can tell you...",
                'example': "Let me give you a practical example to illustrate this concept...",
                'simplify': "Let me break this down into simpler terms..."
            };
            
            // Simple keyword matching (replace with actual AI)
            if (question.toLowerCase().includes('example')) {
                return responses.example;
            } else if (question.toLowerCase().includes('explain') || question.toLowerCase().includes('simpl')) {
                return responses.simplify;
            }
            
            return responses.default;
        }
        
        function generatePracticeQuiz() {
            alert('Generating personalized practice quiz based on your reading progress...');
            // Implement quiz generation logic
        }
        
        function createSummary() {
            alert('Creating AI-powered summary of this section...');
            // Implement summary generation
        }
        
        function exportNotes() {
            alert('Exporting your notes and highlights...');
            // Implement export functionality
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Initialize controller when DOM is ready
        document.addEventListener('DOMContentLoaded', () => {
            new LearningPageController();
        });
    </script>
</body>
</html>
```

### Step 4.1: Inject Extracted Content

For each major concept from the PDF:

```html
<section id="concept-X" class="concept-section">
    <h2>[Concept Title]</h2>
    
    <!-- Hook: Why it matters -->
    <div class="feynman-block">
        <div class="icon">🎯</div>
        <h4>Why This Matters</h4>
        <p>[Real-world relevance and application]</p>
    </div>
    
    <!-- Simple Explanation -->
    <div class="feynman-block">
        <div class="icon">💡</div>
        <h4>Explain Like I'm 12</h4>
        <p>[Ultra-simple explanation with analogy]</p>
    </div>
    
    <!-- Original PDF Content -->
    <h3>Deep Dive</h3>
    <p>[Original PDF text]</p>
    
    <!-- Formulas -->
    <div class="formula-block">
        $$[LaTeX formula]$$
    </div>
    
    <!-- Visual from PDF -->
    <div class="image-container">
        <img src="images/page1_img1.png" alt="[Description]">
        <div class="image-caption">[Caption from PDF]</div>
    </div>
    
    <!-- Expanded Examples -->
    <div class="expandable">
        <div class="expandable-header">
            <span>📊 Worked Example 1: [Title]</span>
            <span class="expandable-icon">▼</span>
        </div>
        <div class="expandable-content">
            <div class="expandable-content-inner">
                [Step-by-step example with calculations]
            </div>
        </div>
    </div>
    
    <!-- Common Mistakes -->
    <div class="feynman-block" style="border-left-color: var(--accent-warning);">
        <div class="icon">⚠️</div>
        <h4>Common Mistakes</h4>
        <ul>
            <li>[Mistake 1 and why it happens]</li>
            <li>[Mistake 2 and how to avoid it]</li>
        </ul>
    </div>
    
    <!-- Interactive Quiz -->
    <div class="quiz-container">
        <div class="quiz-question">
            Test your understanding: [Question]
        </div>
        <div class="quiz-options">
            <div class="quiz-option" data-correct="false">A) [Option]</div>
            <div class="quiz-option" data-correct="true">B) [Correct Option]</div>
            <div class="quiz-option" data-correct="false">C) [Option]</div>
            <div class="quiz-option" data-correct="false">D) [Option]</div>
        </div>
        <div class="quiz-feedback correct">
            ✓ Correct! [Explanation of why this is right]
        </div>
        <div class="quiz-feedback incorrect">
            ✗ Not quite. [Explanation and hint]
        </div>
    </div>
</section>
```

### Step 4.2: Add Data Visualizations

For each concept, determine the best visualization type and add appropriate charts/diagrams.

**Decision Matrix — Which Visualization to Use:**

| Content Type | Best Visualization | Library |
|---|---|---|
| Trend / Time Series | Line chart | Chart.js |
| Comparison of quantities | Bar chart (horizontal or vertical) | Chart.js |
| Proportions / Composition | Pie / Doughnut chart | Chart.js |
| Distribution | Histogram or Scatter plot | Chart.js |
| Process / Workflow | Flowchart | Mermaid |
| System relationships | Sequence diagram or Class diagram | Mermaid |
| Concept hierarchy | Mind map or Tree diagram | Mermaid |
| Before vs After / Trade-offs | Comparison block | Custom HTML |
| Timeline / History | Timeline block | Custom HTML |
| Key metrics / Stats | Stats cards grid | Custom HTML |

**Chart.js Example — Line/Bar/Pie:**

```html
<div class="chart-container">
    <div class="chart-title">📈 [Chart Title]</div>
    <div class="chart-subtitle">[Optional subtitle or data source]</div>
    <canvas id="chart-[unique-id]" style="max-height:380px;"></canvas>
    <div class="chart-caption">Figure X: [Description of what the chart shows]</div>
</div>

<script>
new Chart(document.getElementById('chart-[unique-id]'), {
    type: 'line', // or 'bar', 'pie', 'doughnut', 'scatter', 'radar'
    data: {
        labels: ['Label1', 'Label2', 'Label3'],
        datasets: [{
            label: 'Dataset Name',
            data: [10, 20, 30],
            borderColor: '#4299e1',
            backgroundColor: 'rgba(66,153,225,0.15)',
            tension: 0.4,
            fill: true
        }]
    },
    options: {
        plugins: {
            legend: { position: 'bottom' },
            tooltip: { mode: 'index', intersect: false }
        },
        scales: {
            y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
            x: { grid: { color: 'rgba(255,255,255,0.05)' } }
        }
    }
});
</script>
```

**Side-by-side Charts:**

```html
<div class="chart-grid">
    <div class="chart-container">
        <div class="chart-title">📊 [Left Chart Title]</div>
        <canvas id="chart-left-[id]"></canvas>
    </div>
    <div class="chart-container">
        <div class="chart-title">📊 [Right Chart Title]</div>
        <canvas id="chart-right-[id]"></canvas>
    </div>
</div>
```

**Mermaid Diagram Examples:**

```html
<!-- Flowchart -->
<div class="diagram-container">
    <div class="diagram-title">🔀 [Process/Concept Flow]</div>
    <div class="mermaid">
    flowchart TD
        A[Input Data] --> B{Decision}
        B -->|Yes| C[Process A]
        B -->|No| D[Process B]
        C --> E[Output]
        D --> E
    </div>
    <div class="diagram-caption">Figure X: [Description]</div>
</div>

<!-- Concept Relationship Map -->
<div class="diagram-container">
    <div class="diagram-title">🧠 Concept Map</div>
    <div class="mermaid">
    graph LR
        A[Core Concept] --> B[Sub-concept 1]
        A --> C[Sub-concept 2]
        B --> D[Detail 1]
        C --> E[Detail 2]
        B -.->|relates to| C
    </div>
</div>

<!-- Timeline -->
<div class="diagram-container">
    <div class="diagram-title">📅 Timeline</div>
    <div class="mermaid">
    timeline
        title History of [Topic]
        1990 : Event 1
        2000 : Event 2
        2010 : Event 3
        2020 : Event 4
    </div>
</div>
```

**Comparison Block:**

```html
<div class="comparison-block">
    <div class="comparison-side left">
        <h4>🔵 [Option A / Before / Traditional]</h4>
        <ul>
            <li>[Point 1]</li>
            <li>[Point 2]</li>
        </ul>
    </div>
    <div class="comparison-divider">⚡</div>
    <div class="comparison-side right">
        <h4>🟢 [Option B / After / Modern]</h4>
        <ul>
            <li>[Point 1]</li>
            <li>[Point 2]</li>
        </ul>
    </div>
</div>
```

**Stats Cards:**

```html
<div class="stats-grid">
    <div class="stat-card">
        <span class="stat-value">$4.2T</span>
        <div class="stat-label">Global FinTech Market</div>
    </div>
    <div class="stat-card">
        <span class="stat-value">85%</span>
        <div class="stat-label">AI Adoption Rate</div>
    </div>
    <div class="stat-card">
        <span class="stat-value">3.5x</span>
        <div class="stat-label">Efficiency Gain</div>
    </div>
</div>
```

**Timeline Block:**

```html
<div class="timeline-block">
    <div class="timeline-item">
        <h4>Phase 1: [Title]</h4>
        <p>[Description of what happens in this phase]</p>
    </div>
    <div class="timeline-item">
        <h4>Phase 2: [Title]</h4>
        <p>[Description]</p>
    </div>
</div>
```

### Step 4.3: Visualization Guidelines

**Mandatory Visualization Rules:**

1. **Every major concept** (h2 section) MUST have at least ONE visualization (chart, diagram, comparison, or stats block)
2. **Numerical data** mentioned in text → always create a Chart.js chart
3. **Processes/workflows** → always create a Mermaid flowchart
4. **Comparisons** (A vs B, pros/cons, before/after) → always use comparison-block
5. **Key statistics/metrics** → always use stats-grid cards
6. **Historical progression** → use timeline-block or Mermaid timeline
7. **Concept relationships** → use Mermaid graph/mind map
8. **Never use text alone** when a visual can make the point clearer
9. **Chart colors** must use CSS variable colors for theme consistency
10. **Each chart/diagram** must have a descriptive title and caption

### Step 4.4: Notes System, PDF Viewer & Text Highlight

**Left Sidebar Tabs:**

The left sidebar uses a 3-tab interface:
1. **Contents** — auto-generated table of contents + course stats
2. **PDF** — embedded original PDF via iframe (`pdfs/{source_file}`)
3. **Notes** — markdown note-taking panel with Obsidian export

**Tab switching:**
```javascript
function switchSidebarTab(tab) {
    document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.sidebar-panel').forEach(p => p.style.display = 'none');
    document.getElementById('panel-' + tab).style.display = 'block';
    event.target.classList.add('active');
}
```

**Notes System (localStorage):**
- Notes stored in `localStorage` with key `'learning-notes-' + document.title`
- Each note: `{ id, citation, body, section, timestamp }`
- `addNote(citation, body)` — add note with cited text
- `addFreeNote()` — add note from textarea editor
- `deleteNote(id)` — remove note by ID
- `renderNotes()` — display all notes in panel

**Text Highlight & Selection-to-Note:**
- When user selects text in main content, show a floating tooltip
- Tooltip has two buttons: **Highlight** and **+ Note**
- `highlightSelection()` — wraps selected text in `<mark class="text-highlight">`
- `highlightAndNote()` — highlights text + prompts for note body + saves with citation
- Uses `range.surroundContents()` with fallback for cross-element selections

**Obsidian Export:**
```javascript
function exportNotesToObsidian() {
    // Generates .md file with:
    // - YAML frontmatter (tags, source, date)
    // - [[wikilink]] to source PDF
    // - > [!quote] callouts for highlighted text citations
    // - > [!info] callouts for source metadata
    // Downloads as {title}-notes.md
}
```

**Required CSS classes:**
```css
.sidebar-tabs { display: flex; gap: 0.25rem; margin-bottom: 1rem; }
.sidebar-tab { flex: 1; padding: 0.5rem; background: var(--card-bg); border: none; color: var(--text-secondary); cursor: pointer; border-radius: 6px; font-size: 0.85rem; }
.sidebar-tab.active { background: var(--accent-primary); color: white; }
.note-card { background: var(--card-bg); border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem; border-left: 3px solid var(--accent-primary); }
.note-citation { font-style: italic; color: var(--text-tertiary); font-size: 0.85rem; border-left: 2px solid var(--accent-secondary); padding-left: 0.5rem; margin-bottom: 0.5rem; }
.text-highlight { background: rgba(255, 235, 59, 0.3); padding: 0 2px; border-radius: 2px; cursor: pointer; }
.highlight-tooltip { position: fixed; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem; display: flex; gap: 0.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000; }
```

---

## Phase 5: Visual Review & Self-Correction

After generating the HTML, perform an automated visual and content review to identify and fix issues before delivery.

### Step 5.1: Automated Visual QA Checklist

Open the generated HTML in the browser and systematically check:

```
Visual Review Checklist ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 LAYOUT & VISUAL
□ Page loads without blank/white screens
□ No horizontal scroll (overflow-x issues)
□ All sections have adequate spacing (no cramped or overlapping content)
□ Dark mode renders correctly (no unreadable text)
□ Light mode renders correctly (if supported)
□ Mobile viewport (< 768px) is usable

📊 CHARTS & VISUALIZATIONS
□ Every h2 section has at least 1 visualization
□ All Chart.js charts render (no blank canvases)
□ Chart axes have proper labels
□ Chart legends are readable
□ Mermaid diagrams render (no raw text shown)
□ Mermaid diagrams are not clipped/overflowing
□ Comparison blocks display side by side on desktop
□ Stats cards show proper values
□ Timeline items connect properly

📐 FORMULAS
□ All KaTeX formulas render (no raw LaTeX shown)
□ Display-mode formulas ($$) are centered
□ Inline formulas ($) align with text baseline
□ No broken/partial formula rendering

🖼️ IMAGES
□ All images load (no broken image icons)
□ Images are responsive (don't overflow container)
□ Image captions are present and readable

📋 TABLES
□ Tables are readable (not squished)
□ Tables scroll horizontally on small screens
□ Table headers are styled distinctly

🧩 INTERACTIVE ELEMENTS
□ All expandable sections toggle open/close
□ Quiz options are clickable
□ Quiz feedback shows correctly (correct/incorrect)
□ Progress bar updates on scroll
□ Table of contents links work
□ AI chat input accepts text

📝 CONTENT
□ No "Lorem ipsum" or placeholder text
□ No "[TODO]" or "[TBD]" markers
□ No truncated sentences or cut-off content
□ Section numbering is consistent
□ No duplicate content blocks
```

### Step 5.2: Self-Correction Protocol

After visual review, fix any issues found:

**If chart canvas is blank:**
- Check that Chart.js CDN loaded (network tab)
- Verify canvas ID matches the `new Chart()` call
- Ensure chart initialization runs after DOM ready
- Fix: wrap in `document.addEventListener('DOMContentLoaded', ...)`

**If Mermaid diagram shows raw text:**
- Check Mermaid syntax (indentation, arrows, labels)
- Verify Mermaid CDN loaded
- Fix: correct syntax, ensure `mermaid.initialize()` runs

**If KaTeX shows raw LaTeX:**
- Check delimiter matching ($...$, $$...$$)
- Look for unsupported LaTeX commands
- Fix: simplify formula or use supported KaTeX commands

**If layout is broken:**
- Check for unclosed HTML tags
- Look for missing CSS classes
- Verify grid/flex container structure
- Fix: balance tags, add missing classes

**If content feels thin/text-heavy:**
- Add missing chart for numerical data
- Add Mermaid flowchart for processes
- Add comparison-block for contrasts
- Add stats-grid for key metrics
- Goal: **visual-to-text ratio should be ~40:60** (at least 40% visual elements)

### Step 5.3: Iterative Improvement

After fixing issues:

1. **Re-open** the HTML in the browser
2. **Re-check** only the items that were fixed
3. **Repeat** until all checklist items pass
4. **Document** any known limitations

```
Visual Review Complete ✓

Fixed Issues:
- [Issue 1]: [What was wrong] → [How it was fixed]
- [Issue 2]: [What was wrong] → [How it was fixed]

Remaining Known Issues:
- [None / List any acceptable limitations]

Visual Score: [X/Y] checklist items passed
```

---

## Phase 6: Testing & Delivery

### Step 6.1: Quality Checks

Before delivery, verify:

1. **Formula Rendering** — All math formulas display correctly
2. **Images Load** — All extracted images are accessible
3. **Tables Format** — Tables are readable and responsive
4. **Charts Render** — All Chart.js and Mermaid visualizations display
5. **Interactive Elements** — All expandables and quizzes work
6. **AI Assistant** — Input/output functions correctly
7. **Mobile Responsive** — Test on narrow viewport
8. **Accessibility** — Keyboard navigation works
9. **Visual Review Passed** — Phase 5 checklist completed

### Step 6.2: Open in Browser

```bash
open [filename].html
```

### Step 6.3: Provide Summary

```
Interactive Learning Page Complete! ✨

📄 File: [filename].html
📊 Source: [pdf_name].pdf
📖 Sections: [count]
🖼️  Images: [count] embedded
🧮 Formulas: [count] rendered
❓ Practice Questions: [count]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Features Included:
✓ Feynman-style explanations (simple → deep)
✓ Interactive expandable sections
✓ Real-time formula rendering (KaTeX)
✓ Data visualizations (Chart.js charts)
✓ Flowcharts & concept maps (Mermaid)
✓ Comparison blocks & stats cards
✓ Practice quizzes with instant feedback
✓ AI study assistant (right sidebar)
✓ Tabbed left sidebar (Contents / PDF / Notes)
✓ Embedded PDF viewer
✓ Notes system with Markdown support
✓ Obsidian-compatible .md export with Zotero-style citations
✓ Text highlight & selection-to-note
✓ Auto-generated table of contents
✓ Progress tracking
✓ Dark/light mode support
✓ Mac/Windows keyboard shortcut adaptation
✓ Visual review passed ✓
✓ Fully offline-capable
✓ Mobile responsive

📊 Visualizations: [count] charts, [count] diagrams, [count] comparison blocks
🔍 Visual Review: [X/Y] checks passed

Keyboard Shortcuts:
  ⌥A / Alt+A — Focus AI assistant (Mac / Windows)
  ⌥S / Alt+S — Create summary

To customize:
  • Colors: Edit :root CSS variables
  • Add more questions: Add .quiz-container blocks
  • Expand concepts: Add .feynman-block sections
  • Connect AI: Replace generateAIResponse() with API call

Would you like me to:
  1. Add more practice questions?
  2. Expand any specific concept?
  3. Create a companion study guide?
  4. Generate flashcards from this content?
```

---

## Advanced Features

### AI Q&A Integration (Production)

To connect real AI (Claude API):

```javascript
async function sendAIMessage() {
    const input = document.getElementById('aiInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    const messagesContainer = document.getElementById('aiMessages');
    
    // Add user message
    addMessage('user', message);
    input.value = '';
    
    // Show typing indicator
    const typingId = addMessage('assistant', '💭 Thinking...');
    
    try {
        // Call Claude API (requires API key)
        const response = await fetch('YOUR_API_ENDPOINT', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer YOUR_API_KEY'
            },
            body: JSON.stringify({
                model: 'claude-3-5-sonnet-20241022',
                messages: [{
                    role: 'user',
                    content: `Context: ${getCourseContext()}\n\nQuestion: ${message}`
                }],
                max_tokens: 1000
            })
        });
        
        const data = await response.json();
        const answer = data.content[0].text;
        
        // Remove typing indicator
        document.getElementById(typingId).remove();
        
        // Add AI response
        addMessage('assistant', answer);
    } catch (error) {
        console.error('AI Error:', error);
        document.getElementById(typingId).innerHTML = '⚠️ Sorry, I encountered an error.';
    }
}

function getCourseContext() {
    // Extract main content as context for AI
    const content = document.getElementById('content');
    return content.innerText.substring(0, 3000); // First 3000 chars
}

function addMessage(role, content) {
    const messagesContainer = document.getElementById('aiMessages');
    const id = `msg-${Date.now()}`;
    
    messagesContainer.innerHTML += `
        <div class="ai-message ${role}" id="${id}">${escapeHtml(content)}</div>
    `;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return id;
}
```

---

## Content Expansion Guidelines

### When to Expand

Expand content if:
- **Too Abstract** — Original text uses jargon without examples
- **Missing Steps** — Jumps from A to C without explaining B
- **No Context** — Doesn't explain why this matters
- **Complex Formula** — Math without intuitive explanation
- **Short Coverage** — Less than 1 paragraph for major concept

### How Much to Expand

For each concept:
- **Minimum**: 1 simple analogy + 1 worked example
- **Standard**: 2 analogies + 2 examples + common mistakes
- **Complex topics**: 3+ examples with increasing difficulty + visual diagram

### Expansion Template

```markdown
Original (PDF): "[original 2-sentence explanation]"

Expanded Version:

**Simple Analogy**: [Everyday comparison]

**Intuitive Explanation**: [Paragraph without jargon]

**Why It Matters**: [Real-world application]

**Step-by-Step Breakdown**:
1. [First principle]
2. [Build on it]
3. [Connect to formula]

**Example 1 (Basic)**: [Simple scenario with numbers]

**Example 2 (Real-world)**: [Realistic case study]

**Common Mistake**: [What students often get wrong]

**Connection to Other Concepts**: [Links to related topics]
```

---

## Troubleshooting

### Formula Not Rendering

- Check LaTeX syntax validity
- Ensure KaTeX library loads before content
- Use double $$ for display mode

### Images Not Loading

- Verify image paths are relative to HTML file
- Check image files exist in images/ directory
- Use forward slashes in paths (not backslashes)

### AI Assistant Not Responding

- Check API key configuration
- Verify CORS settings if calling external API
- Implement fallback responses for offline mode

### Expandable Sections Not Working

- Ensure JavaScript controller initialized
- Check for duplicate IDs
- Verify CSS classes match JS selectors

---

## Related Skills

- **frontend-slides** — For creating presentation versions
- **planning-with-files** — For organizing multi-chapter projects
- **ui-ux-pro-max** — For enhancing visual design

---

## Example Session Flow

1. **User**: "Convert my Financial Derivatives lecture PDF to an interactive learning page"
2. **Skill**: Extracts PDF → finds 23 pages, 8 images, 15 formulas, 3 tables
3. **Skill**: Analyzes content → identifies 7 major concepts, notes thin coverage on Black-Scholes
4. **Skill**: Asks user: "I noticed Black-Scholes is explained in only 3 paragraphs. Should I expand with more examples and visual derivation?"
5. **User**: "Yes, expand everything that seems rushed"
6. **Skill**: Generates comprehensive content with AI
7. **Skill**: Creates HTML with all features integrated
8. **Skill**: Opens in browser for review
9. **User**: "Can you add more practice questions on option pricing?"
10. **Skill**: Adds 5 new interactive quiz questions
11. **Final**: Fully interactive learning page delivered

---

## Quality Checklist

Before marking complete, ensure:

- [ ] All PDF content extracted successfully
- [ ] Every major concept has Feynman-style explanation
- [ ] Minimum 2 examples per concept
- [ ] All formulas render correctly with KaTeX
- [ ] Images embedded with captions
- [ ] Tables formatted and responsive
- [ ] **Every h2 section has at least 1 visualization** (chart, diagram, comparison, or stats)
- [ ] **All Chart.js canvases render** (no blank areas)
- [ ] **All Mermaid diagrams render** (no raw syntax shown)
- [ ] **Comparison blocks and stats cards display correctly**
- [ ] 3+ practice questions per major topic
- [ ] AI assistant functional (no placeholder stubs)
- [ ] Table of contents auto-generated
- [ ] Progress bar works
- [ ] Mobile responsive (tested)
- [ ] Keyboard navigation works
- [ ] Dark/light mode both functional
- [ ] No content gaps (everything explained thoroughly)
- [ ] **Visual review (Phase 5) completed and all fixes applied**
- [ ] **Visual-to-text ratio ≥ 40:60**
- [ ] **Left sidebar tabs** (Contents / PDF / Notes) switch correctly
- [ ] **PDF viewer** loads source PDF in iframe
- [ ] **Notes system** — add, delete, render notes via localStorage
- [ ] **No generic fallback sentences** in final HTML:
  - "This concept is like a familiar everyday process."
  - "Understanding this helps in practical applications."
  - "Consider a typical scenario where this applies."
  - "Students often confuse this with related concepts."
- [ ] **Text highlight** — selection tooltip appears with Highlight & + Note buttons
- [ ] **Obsidian export** — downloads valid .md with YAML frontmatter and `> [!quote]` callouts
- [ ] **Keyboard shortcuts** adapt to Mac (⌘) vs Windows (Alt)
- [ ] File size reasonable (<5MB ideally)
- [ ] Opens correctly in all major browsers

---

## 2026 Hardening Addendum (Required)

### A) Anti-Placeholder Generation Rules

When generating `SIMPLE_ANALOGY / WHY_IT_MATTERS / EXAMPLE / COMMON_MISTAKE`:

1. Never output template filler text.
2. If model JSON parsing fails, retry once with stricter prompt.
3. If second attempt still fails, use **contextual fallback** built from lecture source text (not generic sentence templates).
4. Run placeholder scan before delivery and fail generation if generic fallback text is detected.

### B) Review Gate for Existing HTML

Before accepting existing outputs in `html/`, run a folder-level scan for the 4 banned generic sentences.
If found:
- regenerate affected lecture HTML from extracted content, or
- patch with context-grounded content and re-run checks.

### C) Mobile App Capability (PWA Baseline)

The integrated portal should support mobile "mini-app" usage:

- Add `manifest.webmanifest`
- Register service worker (`sw.js`) for shell/offline caching
- Ensure touch-friendly card/list actions and responsive layout
- Verify installability on mobile browsers

### D) Mandatory Verification Commands

```bash
rg -n "This concept is like a familiar everyday process|Understanding this helps in practical applications|Consider a typical scenario where this applies|Students often confuse this with related concepts" html/*.html
python3 -m py_compile generate_html.py serve.py
```

Expected: first command returns no matches.

---

## Output File Structure

```
[project-name]/
├── [topic-name].html              # Main interactive learning page
├── extract_pdf.py                 # Extraction script (keep for reference)
├── extracted_content.json         # Structured JSON data
├── images/                        # All images from PDF
│   ├── page1_img1.png
│   ├── page2_img1.png
│   └── ...
├── tables/                        # Table data as JSON
│   ├── page1_table1.json
│   └── ...
└── text/                          # Plain text backup
    └── full_text.txt
```

---

## Tips for Best Results

1. **Read Full PDF First** — Understand complete context before generating
2. **Preserve Voice** — Match original lecture style (formal vs. conversational)
3. **Visual Hierarchy** — Use headings, color coding, icons consistently
4. **Progressive Disclosure** — Complex content in expandable sections
5. **Redundancy is Good** — Repeat key concepts in different ways (Feynman principle)
6. **Test Understanding** — Every major concept needs a quiz question
7. **Connect Everything** — Show relationships between concepts explicitly
8. **Real Examples** — Use actual data, companies, scenarios
9. **No Dead Ends** — Every term/concept either explained or linked
10. **Make it Fun** — Use humor and interesting examples (while maintaining accuracy)
11. **Visualize Everything** — If data exists, chart it; if process exists, diagram it; if comparison exists, show it side by side
12. **Self-Review** — Always run the Phase 5 visual review before delivering; fix issues iteratively

---

## Future Enhancements

Potential features to add:

- **Spaced Repetition** — Schedule practice questions over time
- **Progress Persistence** — Save progress to localStorage
- ~~**Collaborative Notes** — Share annotations with classmates~~ ✅ Notes system implemented (localStorage + Obsidian export)
- **Video Embeds** — Link to relevant YouTube/Khan Academy
- **Flashcard Export** — Generate Anki cards from content
- **Print Stylesheet** — Beautiful printable version
- **Dictation Mode** — Audio narration of content
- ~~**Graph Visualization** — Concept map showing relationships~~ ✅ Implemented via Mermaid
- **Interactive Chart Drill-down** — Click chart data points to see details
- **Auto-Screenshot Review** — Use headless browser to capture and validate renders
- ~~**PDF Viewer** — View original PDF alongside interactive content~~ ✅ Implemented via sidebar tab
