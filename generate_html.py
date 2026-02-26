#!/usr/bin/env python3
"""
Interactive Learning HTML Generator
Uses Gemini AI to expand content with Feynman technique
"""

import json
import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv('.env.local')

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview')

if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in .env.local")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

REQUIRED_EXPANSION_KEYS = [
    "SIMPLE_ANALOGY",
    "WHY_IT_MATTERS",
    "DEEP_EXPLANATION",
    "EXAMPLE",
    "COMMON_MISTAKE",
]

GENERIC_EXPANSION_PHRASES = [
    "this concept is like a familiar everyday process",
    "understanding this helps in practical applications",
    "consider a typical scenario where this applies",
    "students often confuse this with related concepts",
]


def _normalize_text(value):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _is_generic_or_empty(text):
    clean = _normalize_text(text).lower()
    if not clean:
        return True
    return any(phrase in clean for phrase in GENERIC_EXPANSION_PHRASES)


def build_contextual_fallback_expansion(concept_name, original_text):
    source = _normalize_text(original_text)
    if not source:
        source = f"{concept_name} is a core topic in this lecture and should be interpreted together with the surrounding context."
    if len(source) > 520:
        source = source[:520].rsplit(" ", 1)[0] + "..."

    return {
        "SIMPLE_ANALOGY": f"Think of {concept_name} like a workflow where each step depends on the quality of the previous step; if one part is weak, the final outcome is unreliable.",
        "WHY_IT_MATTERS": f"In this lecture, {concept_name} influences how evidence is interpreted and how decisions are made, so getting it right improves both analysis quality and practical decisions.",
        "DEEP_EXPLANATION": source,
        "EXAMPLE": f"A practical way to apply {concept_name} is to start from the lecture's core definition, test it on a concrete case, and compare results under different assumptions.",
        "COMMON_MISTAKE": f"A common mistake is to memorize {concept_name} as a slogan without checking assumptions, data quality, and the specific decision context.",
    }


def sanitize_expansion(concept_name, original_text, expansion):
    fallback = build_contextual_fallback_expansion(concept_name, original_text)
    if not isinstance(expansion, dict):
        expansion = {}

    cleaned = {}
    for key in REQUIRED_EXPANSION_KEYS:
        text = _normalize_text(expansion.get(key, ""))
        if len(text) < 24 or _is_generic_or_empty(text):
            text = fallback[key]
        cleaned[key] = text

    viz = expansion.get("VISUALIZATION")
    if isinstance(viz, dict) and viz.get("viz_type"):
        cleaned["VISUALIZATION"] = viz
    return cleaned


def analyze_content(text_content, title):
    """Use AI to analyze content and identify main concepts"""
    
    print("\n🤖 Analyzing content with AI...")
    
    prompt = f"""Analyze this course lecture content and identify the main concepts for learning.

Title: {title}

Content (first 8000 chars):
{text_content[:8000]}

Please provide a JSON response with:
1. main_concepts: List of 5-10 key concepts (each with name and brief description)
2. difficulty_level: "beginner", "intermediate", or "advanced"
3. prerequisites: List of 3-5 prerequisite topics
4. learning_objectives: List of 3-5 main learning objectives

Format as valid JSON only, no markdown or explanation."""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Clean markdown code blocks if present
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        analysis = json.loads(result_text)
        print(f"  ✓ Identified {len(analysis.get('main_concepts', []))} main concepts")
        return analysis
    except Exception as e:
        print(f"  ⚠️  Warning: AI analysis failed: {e}")
        # Return default structure
        return {
            "main_concepts": [{"name": "Overview", "description": "Introduction to the topic"}],
            "difficulty_level": "intermediate",
            "prerequisites": ["Basic understanding of the subject"],
            "learning_objectives": ["Understand the main concepts"]
        }


def expand_concept(concept_name, original_text, context=""):
    """Use AI to expand a concept with Feynman technique"""
    
    prompt = f"""You are an expert educator using the Feynman technique. Expand this concept for deep learning.

Concept: {concept_name}

Original explanation from lecture:
{original_text[:2000]}

Context: {context[:1000]}

Provide a comprehensive explanation with:

1. SIMPLE_ANALOGY: One intuitive, everyday analogy (2-3 sentences)

2. WHY_IT_MATTERS: Real-world application and importance (2-3 sentences)

3. DEEP_EXPLANATION: Clear, detailed explanation without jargon (1 paragraph)

4. EXAMPLE: One practical, worked example with numbers or concrete scenario (3-4 sentences)

5. COMMON_MISTAKE: One common misconception or error students make (2 sentences)

6. VISUALIZATION: A data visualization specification. Choose ONE type that best fits the concept:
   - If the concept involves numerical data, trends, or comparisons, provide a Chart.js config:
     {{"viz_type": "chartjs", "chart_type": "line|bar|pie|doughnut|radar|scatter", "title": "...", "caption": "...", "labels": [...], "datasets": [{{"label": "...", "data": [...], "borderColor": "#4299e1", "backgroundColor": "rgba(66,153,225,0.15)"}}]}}
   - If the concept involves a process, flow, or relationship, provide a Mermaid diagram:
     {{"viz_type": "mermaid", "title": "...", "caption": "...", "code": "flowchart TD\\n    A[Step1] --> B[Step2]\\n    B --> C[Step3]"}}
   - If the concept involves comparing two approaches/methods, provide a comparison:
     {{"viz_type": "comparison", "left_title": "...", "left_points": ["..."], "right_title": "...", "right_points": ["..."]}}
   - If the concept has key metrics or stats, provide stats cards:
     {{"viz_type": "stats", "stats": [{{"value": "...", "label": "..."}}]}}

Format as JSON with these exact keys. Keep it concise and clear.
Never use generic filler text such as "This concept is like a familiar everyday process." or similarly vague placeholders."""

    last_error = None
    for attempt in range(2):
        try:
            attempt_prompt = prompt
            if attempt == 1:
                attempt_prompt += "\nPrevious output was too generic. Use concrete, lecture-grounded details."
            response = model.generate_content(attempt_prompt)
            result_text = response.text.strip()
            
            # Clean markdown if present
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            expansion = json.loads(result_text)
            return sanitize_expansion(concept_name, original_text, expansion)
        except Exception as e:
            last_error = e
            print(f"    ⚠️  Expand attempt {attempt + 1} failed for {concept_name}: {e}")

    print(f"    ⚠️  Using contextual fallback for {concept_name}: {last_error}")
    return build_contextual_fallback_expansion(concept_name, original_text)


def generate_quiz_questions(concept_name, content):
    """Generate interactive quiz questions"""
    
    prompt = f"""Create 3 multiple choice quiz questions for this concept.

Concept: {concept_name}
Content: {content[:1500]}

For each question provide:
- question: The question text
- options: Array of 4 options (A, B, C, D)
- correct: Index of correct answer (0-3)
- explanation: Why this answer is correct (1 sentence)

Return as JSON array of 3 questions."""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        questions = json.loads(result_text)
        return questions[:3]  # Ensure only 3 questions
    except Exception as e:
        print(f"    ⚠️  Could not generate quiz: {e}")
        return []


def generate_html(extracted_dir, output_file):
    """Generate interactive HTML from extracted content"""
    
    print(f"\n🎨 Generating interactive HTML...")
    print("="*60)
    
    extracted_path = Path(extracted_dir)
    
    # Load extracted data
    with open(extracted_path / 'extracted_content.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Load full text
    with open(extracted_path / 'text/full_text.txt', 'r', encoding='utf-8') as f:
        full_text = f.read()
    
    title = data['title']
    print(f"📄 Title: {title}")
    
    # Analyze content with AI
    analysis = analyze_content(full_text, title)
    
    # Prepare main concepts for expansion
    main_concepts = analysis.get('main_concepts', [])[:8]  # Limit to 8 concepts
    
    print(f"\n📝 Expanding concepts with Feynman technique...")
    expanded_concepts = []
    
    for i, concept in enumerate(main_concepts, 1):
        concept_name = concept.get('name', f'Concept {i}')
        print(f"  {i}. {concept_name}...", end=' ')
        
        # Find relevant content from full text
        concept_lower = concept_name.lower()
        # Extract paragraph containing concept
        lines = full_text.split('\n')
        relevant_text = ""
        for j, line in enumerate(lines):
            if concept_lower in line.lower():
                # Get surrounding context
                start = max(0, j - 3)
                end = min(len(lines), j + 10)
                relevant_text = '\n'.join(lines[start:end])
                break
        
        if not relevant_text:
            relevant_text = concept.get('description', '')
        
        # Expand with AI
        expansion = expand_concept(concept_name, relevant_text, full_text[:3000])
        
        # Generate quiz questions
        quiz_questions = generate_quiz_questions(concept_name, relevant_text)
        
        expanded_concepts.append({
            'name': concept_name,
            'description': concept.get('description', ''),
            'original_text': relevant_text[:1000],
            'expansion': expansion,
            'quiz': quiz_questions
        })
        
        print("✓")
    
    # Generate HTML
    print(f"\n🔨 Building HTML...")
    output_path = Path(output_file)
    output_dir = output_path.parent if str(output_path.parent) else Path('.')
    pdf_src = os.path.relpath(Path('pdfs') / data['source_file'], start=output_dir).replace('\\', '/')

    html = generate_html_template(
        title=title,
        source_file=data['source_file'],
        pdf_src=pdf_src,
        analysis=analysis,
        concepts=expanded_concepts,
        images=data.get('total_images', 0),
        tables=data.get('total_tables', 0),
        extracted_dir=extracted_dir
    )
    
    # Write HTML file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML generated: {output_file}")
    print(f"   Size: {len(html)} bytes")
    print(f"   Concepts: {len(expanded_concepts)}")
    
    return output_path


def build_visualization_html(viz, concept_index):
    """Build HTML for a visualization specification from AI"""
    if not viz or not isinstance(viz, dict):
        return ""
    
    viz_type = viz.get('viz_type', '')
    
    if viz_type == 'chartjs':
        chart_type = viz.get('chart_type', 'bar')
        title = viz.get('title', 'Chart')
        caption = viz.get('caption', '')
        labels = json.dumps(viz.get('labels', []))
        
        # Build datasets JS
        datasets = viz.get('datasets', [])
        colors = ['#f6c177', '#a3d9a5', '#c4b5fd', '#7dd3fc', '#fb7185', '#fbbf24']
        datasets_js = []
        for idx, ds in enumerate(datasets):
            color = ds.get('borderColor', colors[idx % len(colors)])
            bg = ds.get('backgroundColor', color.replace(')', ',0.15)').replace('rgb', 'rgba') if 'rgb' in color else f'{color}26')
            ds_obj = {
                'label': ds.get('label', f'Series {idx+1}'),
                'data': ds.get('data', []),
                'borderColor': color,
                'backgroundColor': bg,
            }
            if chart_type == 'line':
                ds_obj['tension'] = 0.4
                ds_obj['fill'] = True
            datasets_js.append(ds_obj)
        
        canvas_id = f'chart-{concept_index}'
        datasets_json = json.dumps(datasets_js)
        
        # Determine scales config based on chart type
        scales_config = ""
        if chart_type in ('line', 'bar', 'scatter'):
            scales_config = """scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { color: 'rgba(255,255,255,0.05)' } }
            }"""
        
        return f'''
        <div class="chart-container">
            <div class="chart-title">{title}</div>
            <canvas id="{canvas_id}" style="max-height:380px;"></canvas>
            {f'<div class="chart-caption">{caption}</div>' if caption else ''}
        </div>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('{canvas_id}');
            if (ctx && typeof Chart !== 'undefined') {{
                new Chart(ctx, {{
                    type: '{chart_type}',
                    data: {{
                        labels: {labels},
                        datasets: {datasets_json}
                    }},
                    options: {{
                        plugins: {{
                            legend: {{ position: 'bottom' }},
                            tooltip: {{ mode: 'index', intersect: false }}
                        }},
                        {scales_config}
                    }}
                }});
            }}
        }});
        </script>
        '''
    
    elif viz_type == 'mermaid':
        title = viz.get('title', 'Diagram')
        caption = viz.get('caption', '')
        code = viz.get('code', '')
        if not code:
            return ""
        return f'''
        <div class="diagram-container">
            <div class="diagram-title">{title}</div>
            <div class="mermaid">
{code}
            </div>
            {f'<div class="diagram-caption">{caption}</div>' if caption else ''}
        </div>
        '''
    
    elif viz_type == 'comparison':
        left_title = viz.get('left_title', 'Option A')
        right_title = viz.get('right_title', 'Option B')
        left_points = viz.get('left_points', [])
        right_points = viz.get('right_points', [])
        left_items = ''.join(f'<li>{p}</li>' for p in left_points)
        right_items = ''.join(f'<li>{p}</li>' for p in right_points)
        return f'''
        <div class="comparison-block">
            <div class="comparison-side left">
                <h4>🔵 {left_title}</h4>
                <ul>{left_items}</ul>
            </div>
            <div class="comparison-divider">vs</div>
            <div class="comparison-side right">
                <h4>🟢 {right_title}</h4>
                <ul>{right_items}</ul>
            </div>
        </div>
        '''
    
    elif viz_type == 'stats':
        stats = viz.get('stats', [])
        if not stats:
            return ""
        cards = ''.join(
            f'<div class="stat-card"><span class="stat-value">{s.get("value","")}</span><div class="stat-label">{s.get("label","")}</div></div>'
            for s in stats
        )
        return f'<div class="stats-grid">{cards}</div>'
    
    return ""


def generate_html_template(title, source_file, pdf_src, analysis, concepts, images, tables, extracted_dir):
    """Generate the complete HTML template"""
    
    # Generate concept sections
    concepts_html = ""
    toc_items = ""
    
    for i, concept in enumerate(concepts, 1):
        concept_id = f"concept-{i}"
        concept_name = concept['name']
        expansion = concept['expansion']
        
        # Add to TOC
        toc_items += f'''
            <li style="margin-bottom: 0.75rem;">
                <a href="#{concept_id}" class="toc-link">{concept_name}</a>
            </li>
        '''
        
        # Generate quiz HTML
        quiz_html = ""
        if concept.get('quiz'):
            for q_idx, q in enumerate(concept['quiz']):
                options_html = ""
                for opt_idx, option in enumerate(q.get('options', [])):
                    is_correct = opt_idx == q.get('correct', 0)
                    options_html += f'''
                    <div class="quiz-option" data-correct="{str(is_correct).lower()}">
                        {option}
                    </div>
                    '''
                
                quiz_html += f'''
                <div class="quiz-container">
                    <div class="quiz-question">
                        <strong>Question {q_idx + 1}:</strong> {q.get('question', '')}
                    </div>
                    <div class="quiz-options">
                        {options_html}
                    </div>
                    <div class="quiz-feedback correct">
                        ✓ Correct! {q.get('explanation', '')}
                    </div>
                    <div class="quiz-feedback incorrect">
                        ✗ Not quite. {q.get('explanation', '')}
                    </div>
                </div>
                '''
        
        # Build visualization HTML
        viz_data = expansion.get('VISUALIZATION', None)
        viz_html = build_visualization_html(viz_data, i)
        
        # Generate concept section
        concepts_html += f'''
        <section id="{concept_id}" class="concept-section">
            <h2>{concept_name}</h2>
            
            <!-- Simple Analogy -->
            <div class="feynman-block" style="border-left-color: var(--accent-primary);">
                <h4>Simple Analogy</h4>
                <p>{expansion.get('SIMPLE_ANALOGY', '')}</p>
            </div>
            
            <!-- Why It Matters -->
            <div class="feynman-block" style="border-left-color: var(--accent-secondary);">
                <h4>Why This Matters</h4>
                <p>{expansion.get('WHY_IT_MATTERS', '')}</p>
            </div>
            
            <!-- Visualization -->
            {viz_html}
            
            <!-- Deep Explanation -->
            <div class="expandable">
                <div class="expandable-header">
                    <span>Deep Dive: Detailed Explanation</span>
                    <span class="expandable-icon">▼</span>
                </div>
                <div class="expandable-content">
                    <div class="expandable-content-inner">
                        <p>{expansion.get('DEEP_EXPLANATION', '')}</p>
                        {f'<div style="margin-top: 1rem; padding: 1rem; background: var(--bg-elevated); border-radius: 8px; font-size: 0.95rem; color: var(--text-tertiary);"><strong>From lecture:</strong><br>{concept.get("original_text", "")[:500]}</div>' if concept.get('original_text') else ''}
                    </div>
                </div>
            </div>
            
            <!-- Practical Example -->
            <div class="expandable open">
                <div class="expandable-header">
                    <span>Practical Example</span>
                    <span class="expandable-icon">▼</span>
                </div>
                <div class="expandable-content">
                    <div class="expandable-content-inner">
                        <p>{expansion.get('EXAMPLE', '')}</p>
                    </div>
                </div>
            </div>
            
            <!-- Common Mistakes -->
            <div class="feynman-block" style="border-left-color: var(--accent-warning);">
                <h4>Common Mistakes</h4>
                <p>{expansion.get('COMMON_MISTAKE', '')}</p>
            </div>
            
            <!-- Quiz Questions -->
            {quiz_html}
        </section>
        '''
    
    # Prerequisites HTML
    prereqs_html = "".join([f"<li>{p}</li>" for p in analysis.get('prerequisites', [])])
    
    # Learning objectives HTML
    objectives_html = "".join([f"<li>{obj}</li>" for obj in analysis.get('learning_objectives', [])])
    
    # Full HTML template
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Interactive Learning</title>
    
    <!-- KaTeX for formula rendering -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    
    <!-- Chart.js for data visualization -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
    
    <!-- Mermaid for flowcharts and diagrams -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
    
    <!-- Fonts: Noto Serif for body, Inter for headings -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="./app-shell.css?v=10">
    
    <style>
        {get_css_styles()}
    </style>
</head>
<body data-shell-page="lecture" data-lecture-title="{title}">
    <!-- Progress Tracker -->
    <div class="progress-tracker">
        <div class="progress-bar" id="progressBar"></div>
    </div>

    <div class="page-container">
        <!-- Left Sidebar -->
        <aside class="sidebar-left">
            <!-- Sidebar Tabs -->
            <div class="sidebar-tabs">
                <button class="sidebar-tab active" data-tab="toc" onclick="switchSidebarTab('toc')">Contents</button>
                <button class="sidebar-tab" data-tab="pdf" onclick="switchSidebarTab('pdf')">PDF</button>
                <button class="sidebar-tab" data-tab="notes" onclick="switchSidebarTab('notes')">Notes</button>
            </div>
            
            <!-- Tab: Table of Contents -->
            <div class="sidebar-panel" id="panel-toc">
                <ul style="list-style: none; padding: 0;">
                    <li style="margin-bottom: 0.75rem;">
                        <a href="#overview" class="toc-link">Overview</a>
                    </li>
                    {toc_items}
                </ul>
                
                <div style="margin-top: 3rem; padding: 1rem; background: var(--bg-elevated); border-radius: 8px; font-size: 0.85rem;">
                    <div style="color: var(--text-tertiary); margin-bottom: 0.5rem;">Course Stats</div>
                    <div style="color: var(--text-secondary);">
                        <div>{len(concepts)} Concepts</div>
                        <div>{images} Images</div>
                        <div>{tables} Tables</div>
                    </div>
                </div>
            </div>
            
            <!-- Tab: PDF Viewer -->
            <div class="sidebar-panel" id="panel-pdf" style="display:none;">
                <div id="pdfViewerContainer" style="height: calc(100vh - 80px); display: flex; flex-direction: column;">
                    <p style="font-size: 0.85rem; color: var(--text-tertiary); margin-bottom: 0.75rem;">Source: {source_file}</p>
                    <iframe id="pdfFrame" src="{pdf_src}" style="flex:1; width:100%; border:none; border-radius: var(--radius-sm); background: var(--bg-tertiary);"></iframe>
                </div>
            </div>
            
            <!-- Tab: Notes -->
            <div class="sidebar-panel" id="panel-notes" style="display:none;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <span style="font-size: 0.85rem; color: var(--text-tertiary);" id="notesCount">0 notes</span>
                    <button onclick="exportNotesToObsidian()" class="action-btn" style="width:auto; padding: 0.4rem 0.75rem; font-size: 0.8rem;">Export .md</button>
                </div>
                <div id="notesList" style="display: flex; flex-direction: column; gap: 0.5rem; max-height: 32vh; overflow-y: auto;"></div>
                <div id="noteReader" class="note-reader">
                    <div class="reader-title">Reading</div>
                    <div class="reader-content">Click a note in history to read it here.</div>
                </div>
                <div style="margin-top: 0.75rem; border-top: 1px solid var(--border-color); padding-top: 0.75rem;">
                    <textarea id="noteInput" oninput="handleNoteInputChange(this.value)" placeholder="Write a note (Markdown supported)..." style="width:100%; min-height: 80px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 0.5rem; color: var(--text-primary); font-family: var(--font-mono); font-size: 0.85rem; resize: vertical;"></textarea>
                    <div id="noteDraftPreview" class="note-reader note-draft-preview">
                        <div class="reader-title">Live Preview</div>
                        <div class="reader-content" id="noteDraftPreviewContent">Type in the note box to preview Markdown rendering in real time.</div>
                    </div>
                    <button onclick="addFreeNote()" class="action-btn" style="margin-top: 0.375rem;">Add Note</button>
                </div>
            </div>
        </aside>

        <div class="column-resizer" id="resizerLeft" role="separator" aria-orientation="vertical" aria-label="Resize left sidebar"></div>

        <!-- Main Content -->
        <main class="main-content">
            <header id="overview">
                <h1>{title}</h1>
                <p style="font-size: 1.1rem; color: var(--text-tertiary); margin-bottom: 2rem;">
                    Interactive Learning Experience • Source: {source_file}
                </p>
                
                <!-- Course Overview -->
                <div class="feynman-block" style="border-left-color: #9f7aea;">
                    <h4>Course Overview</h4>
                    <p><strong>Difficulty:</strong> {analysis.get('difficulty_level', 'Intermediate').title()}</p>
                    
                    <h5 style="margin-top: 1.5rem; margin-bottom: 0.5rem; color: var(--accent-primary);">Prerequisites:</h5>
                    <ul style="margin-left: 1.5rem;">
                        {prereqs_html}
                    </ul>
                    
                    <h5 style="margin-top: 1.5rem; margin-bottom: 0.5rem; color: var(--accent-secondary);">Learning Objectives:</h5>
                    <ul style="margin-left: 1.5rem;">
                        {objectives_html}
                    </ul>
                </div>
            </header>

            <!-- Concept Sections -->
            {concepts_html}
            
            <!-- Completion -->
            <div style="margin-top: 4rem; padding: 2rem; background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)); border-radius: 12px; text-align: center; color: white;">
                <h3 style="margin-bottom: 1rem;">Course Complete!</h3>
                <p>You've reviewed all {len(concepts)} main concepts. Keep practicing with the quizzes above.</p>
            </div>
        </main>

        <div class="column-resizer" id="resizerRight" role="separator" aria-orientation="vertical" aria-label="Resize right sidebar"></div>

        <!-- Right Sidebar: AI Assistant & Tools -->
        <aside class="sidebar-right">
            <div class="ai-chat">
                <div class="ai-chat-header">
                    <div>
                        <h3 style="margin: 0;">AI Study Assistant</h3>
                        <p style="font-size: 0.8rem; color: var(--text-tertiary); margin: 0;">Powered by Gemini</p>
                    </div>
                </div>
                
                <div class="ai-chat-messages" id="aiMessages">
                    <div class="ai-message assistant">
                        Hi! I'm your AI study assistant. Ask me anything about this topic, or request:
                        <ul style="margin-top: 0.5rem; padding-left: 1.5rem; font-size: 0.9rem;">
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
                <h4 style="margin-bottom: 1rem; color: var(--text-tertiary);">Quick Actions</h4>
                <button onclick="reviewAllQuizzes()" class="action-btn">
                    Review All Quizzes
                </button>
                <button onclick="createSummary()" class="action-btn">
                    Generate Summary
                </button>
                <button onclick="window.print()" class="action-btn">
                    Print Notes
                </button>
            </div>
            
            <!-- Keyboard Shortcuts -->
            <div style="margin-top: 2rem; padding: 1rem; background: var(--bg-elevated); border-radius: 8px; font-size: 0.85rem;">
                <h5 style="margin-bottom: 0.75rem; color: var(--text-tertiary);">Shortcuts</h5>
                <div id="shortcutsDisplay" style="color: var(--text-secondary); line-height: 1.8;">
                    <div><kbd id="shortcutFocusAI">Alt+A</kbd> Focus AI</div>
                    <div><kbd id="shortcutSummary">Alt+S</kbd> Summary</div>
                </div>
            </div>
        </aside>
    </div>

    <script>
        {get_javascript()}
    </script>
    <script src="./app-shell.js?v=10"></script>
    <script src="./lecture-enhancements.js?v=4"></script>
    
    <!-- KaTeX auto-render -->
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            if (typeof renderMathInElement !== 'undefined') {{
                renderMathInElement(document.body, {{
                    delimiters: [
                        {{left: "$$", right: "$$", display: true}},
                        {{left: "$", right: "$", display: false}},
                        {{left: "\\\\(", right: "\\\\)", display: false}},
                        {{left: "\\\\[", right: "\\\\]", display: true}}
                    ],
                    throwOnError: false
                }});
            }}
        }});
    </script>
</body>
</html>'''
    
    return html


def get_css_styles():
    """Return CSS styles as string"""
    return '''
        :root {
            /* Warm Academic Theme - Clean & Readable */
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-tertiary: #1f2b47;
            --bg-elevated: #263352;
            --bg-card: #1c2a45;
            
            --text-primary: #edf2f7;
            --text-secondary: #a0aec0;
            --text-tertiary: #718096;
            
            /* Warm Gold + Sage Green palette */
            --accent-primary: #f6c177;
            --accent-secondary: #a3d9a5;
            --accent-tertiary: #c4b5fd;
            --accent-warning: #fbbf24;
            --accent-error: #fb7185;
            --accent-info: #7dd3fc;
            
            --gradient-primary: linear-gradient(135deg, #f6c177 0%, #e8a87c 100%);
            --gradient-heading: linear-gradient(135deg, #f6c177 0%, #c4b5fd 100%);
            
            --border-color: rgba(255, 255, 255, 0.06);
            --border-hover: rgba(246, 193, 119, 0.25);
            --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.25);
            --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.3);
            --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.4);
            
            --font-body: 'Georgia', 'Times New Roman', 'Noto Serif SC', serif;
            --font-heading: -apple-system, 'Helvetica Neue', 'PingFang SC', sans-serif;
            --font-mono: 'SF Mono', 'Menlo', 'Monaco', monospace;
            
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            
            --ease: cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        @media (prefers-color-scheme: light) {
            :root {
                --bg-primary: #faf8f5;
                --bg-secondary: #f0ece4;
                --bg-tertiary: #e8e2d8;
                --bg-elevated: #ffffff;
                --bg-card: #ffffff;
                
                --text-primary: #1c1917;
                --text-secondary: #57534e;
                --text-tertiary: #a8a29e;
                
                --accent-primary: #c2742f;
                --accent-secondary: #3d8b40;
                --accent-tertiary: #7c3aed;
                --accent-warning: #b45309;
                --accent-error: #dc2626;
                
                --gradient-heading: linear-gradient(135deg, #c2742f 0%, #7c3aed 100%);
                
                --border-color: rgba(0, 0, 0, 0.06);
                --border-hover: rgba(194, 116, 47, 0.3);
                --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.06);
                --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
                --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);
            }
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        html {
            scroll-behavior: smooth;
            font-size: 16px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        body {
            font-family: var(--font-body);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.8;
            overflow-x: hidden;
        }
        
        .page-container {
            --left-width: 260px;
            --right-width: 300px;
            display: grid;
            grid-template-columns: minmax(200px, var(--left-width)) 8px minmax(0, 1fr) 8px minmax(220px, var(--right-width));
            min-height: 100vh;
            position: relative;
            z-index: 1;
        }

        .column-resizer {
            cursor: col-resize;
            background: transparent;
            transition: background-color 0.15s var(--ease);
            position: sticky;
            top: 0;
            height: 100vh;
            z-index: 5;
        }
        .column-resizer:hover,
        .column-resizer.dragging {
            background: rgba(246, 193, 119, 0.2);
        }
        
        .sidebar-left, .sidebar-right {
            background: var(--bg-secondary);
            padding: 2rem 1.25rem;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
        }
        
        .sidebar-left {
            border-right: 1px solid var(--border-color);
        }
        
        .sidebar-right {
            border-left: 1px solid var(--border-color);
        }
        
        .main-content {
            max-width: none;
            min-width: 0;
            width: 100%;
            margin: 0 auto;
            padding: 3rem 2.5rem;
        }
        
        @media (max-width: 1200px) {
            .page-container { grid-template-columns: 1fr; }
            .sidebar-left, .sidebar-right, .column-resizer { display: none; }
            .main-content { padding: 2rem 1.25rem; }
        }
        
        h1 {
            font-family: var(--font-heading);
            font-size: clamp(1.875rem, 4vw, 2.5rem);
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 0.75rem;
            letter-spacing: -0.01em;
            color: var(--text-primary);
        }
        
        h2 {
            font-family: var(--font-heading);
            font-size: 1.5rem;
            font-weight: 600;
            margin-top: 3.5rem;
            margin-bottom: 1.25rem;
            color: var(--accent-primary);
            letter-spacing: -0.01em;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        h3 {
            font-family: var(--font-heading);
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            color: var(--text-primary);
        }
        
        h4 {
            font-family: var(--font-heading);
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--accent-primary);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        
        h5 {
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        p {
            margin-bottom: 1rem;
            color: var(--text-secondary);
            font-size: 1rem;
            line-height: 1.8;
        }
        
        .feynman-block {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-left: 3px solid var(--accent-primary);
            border-radius: var(--radius-md);
            padding: 1.5rem;
            margin: 1.5rem 0;
            transition: border-color 0.2s var(--ease);
        }
        
        .feynman-block:hover {
            border-color: var(--border-hover);
        }
        
        .feynman-block .icon {
            font-size: 1.75rem;
            margin-bottom: 0.75rem;
            display: inline-block;
        }
        
        .expandable {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            margin: 1.5rem 0;
            overflow: hidden;
        }
        
        .expandable-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.25rem;
            cursor: pointer;
            user-select: none;
            font-weight: 500;
            font-family: var(--font-heading);
            transition: background 0.15s var(--ease);
        }
        
        .expandable-header:hover {
            background: var(--bg-tertiary);
        }
        
        .expandable-icon {
            transition: transform 0.25s var(--ease);
            display: inline-block;
            font-size: 0.8rem;
        }
        
        .expandable.open .expandable-icon {
            transform: rotate(180deg);
        }
        
        .expandable-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.4s var(--ease);
        }
        
        .expandable.open .expandable-content {
            max-height: 5000px;
        }
        
        .expandable-content-inner {
            padding: 1.25rem;
            border-top: 1px solid var(--border-color);
        }
        
        .quiz-container {
            background: var(--bg-card);
            border-radius: var(--radius-md);
            padding: 1.5rem;
            margin: 2rem 0;
            border: 1px solid var(--border-color);
        }
        
        .quiz-question {
            font-size: 1.05rem;
            font-family: var(--font-heading);
            margin-bottom: 1.25rem;
            color: var(--text-primary);
        }
        
        .quiz-options {
            display: flex;
            flex-direction: column;
            gap: 0.625rem;
        }
        
        .quiz-option {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 0.75rem 1rem;
            cursor: pointer;
            transition: all 0.15s var(--ease);
            font-size: 0.95rem;
        }
        
        .quiz-option:hover {
            border-color: var(--accent-primary);
            padding-left: 1.25rem;
        }
        
        .quiz-option.correct {
            background: rgba(163, 217, 165, 0.2);
            border-color: var(--accent-secondary);
            color: var(--accent-secondary);
        }
        
        .quiz-option.incorrect {
            background: rgba(251, 113, 133, 0.15);
            border-color: var(--accent-error);
            color: var(--accent-error);
        }
        
        .quiz-feedback {
            margin-top: 1rem;
            padding: 0.75rem 1rem;
            border-radius: var(--radius-sm);
            display: none;
            font-size: 0.9rem;
        }
        
        .quiz-feedback.show { display: block; }
        .quiz-feedback.correct { background: rgba(163, 217, 165, 0.15); border: 1px solid var(--accent-secondary); }
        .quiz-feedback.incorrect { background: rgba(251, 113, 133, 0.1); border: 1px solid var(--accent-error); }
        
        .progress-tracker {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: var(--bg-secondary);
            z-index: 1000;
        }
        
        .progress-bar {
            height: 100%;
            background: var(--gradient-primary);
            width: 0%;
            transition: width 0.2s var(--ease);
        }
        
        .ai-chat {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 1.25rem;
        }
        
        .ai-chat-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .ai-chat-messages {
            max-height: 320px;
            overflow-y: auto;
            margin-bottom: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-primary);
            border-radius: var(--radius-sm);
        }
        
        .ai-message {
            margin-bottom: 0.75rem;
            padding: 0.625rem 0.875rem;
            border-radius: var(--radius-sm);
            font-size: 0.875rem;
            line-height: 1.6;
        }
        
        .ai-message.user {
            background: var(--accent-primary);
            color: var(--bg-primary);
            margin-left: 1.5rem;
            font-weight: 500;
        }
        
        .ai-message.assistant {
            background: var(--bg-tertiary);
            margin-right: 1.5rem;
        }
        
        .ai-input-group { display: flex; gap: 0.5rem; }
        
        .ai-input {
            flex: 1;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 0.625rem 0.75rem;
            color: var(--text-primary);
            font-family: var(--font-body);
            font-size: 0.875rem;
        }
        
        .ai-input:focus {
            outline: none;
            border-color: var(--accent-primary);
        }
        
        .ai-send-btn, .action-btn {
            background: var(--accent-primary);
            color: var(--bg-primary);
            border: none;
            border-radius: var(--radius-sm);
            padding: 0.625rem 1rem;
            cursor: pointer;
            font-weight: 600;
            font-family: var(--font-heading);
            font-size: 0.85rem;
            transition: opacity 0.15s;
        }
        
        .action-btn {
            width: 100%;
            margin-bottom: 0.5rem;
            text-align: left;
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
        }
        
        .ai-send-btn:hover { opacity: 0.85; }
        .action-btn:hover { border-color: var(--accent-primary); color: var(--accent-primary); }
        
        kbd {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 0.15rem 0.5rem;
            font-family: var(--font-mono);
            font-size: 0.8em;
        }
        
        .toc-link {
            color: var(--text-secondary);
            text-decoration: none;
            display: block;
            padding: 0.375rem 0.5rem;
            border-radius: var(--radius-sm);
            font-size: 0.875rem;
            font-family: var(--font-heading);
            transition: color 0.15s, background 0.15s;
        }
        
        .toc-link:hover {
            color: var(--accent-primary);
            background: var(--bg-tertiary);
        }
        
        /* Scroll reveal - simple fade */
        .reveal-on-scroll {
            opacity: 0;
            transform: translateY(16px);
            transition: opacity 0.5s var(--ease), transform 0.5s var(--ease);
        }
        .reveal-on-scroll.revealed {
            opacity: 1;
            transform: translateY(0);
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--bg-elevated); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-tertiary); }
        
        ::selection { background: var(--accent-primary); color: var(--bg-primary); }
        
        /* Print */
        @media print {
            .sidebar-left, .sidebar-right, .progress-tracker { display: none; }
            .page-container { grid-template-columns: 1fr; }
            body { background: white; color: black; }
        }
        
        /* ===========================================
           DATA VISUALIZATION & CHARTS
           =========================================== */
        .chart-container {
            background: var(--bg-card);
            border-radius: var(--radius-md);
            padding: 1.5rem;
            margin: 2rem 0;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
        }
        .chart-container .chart-title {
            font-family: var(--font-heading);
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.75rem;
            text-align: center;
        }
        .chart-container canvas { max-height: 380px; width: 100% !important; }
        .chart-caption {
            font-size: 0.85rem;
            color: var(--text-tertiary);
            text-align: center;
            margin-top: 0.75rem;
            font-style: italic;
        }
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }
        .chart-grid .chart-container { margin: 0; }
        
        .diagram-container {
            background: var(--bg-card);
            border-radius: var(--radius-md);
            padding: 1.5rem;
            margin: 2rem 0;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
            overflow-x: auto;
            text-align: center;
        }
        .diagram-container .diagram-title {
            font-family: var(--font-heading);
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.75rem;
        }
        .diagram-container .mermaid { display: flex; justify-content: center; }
        .diagram-container .mermaid svg { max-width: 100%; height: auto; }
        .diagram-caption {
            font-size: 0.85rem;
            color: var(--text-tertiary);
            text-align: center;
            margin-top: 0.75rem;
            font-style: italic;
        }
        
        .comparison-block {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: 1rem;
            align-items: stretch;
            margin: 2rem 0;
        }
        .comparison-side {
            background: var(--bg-card);
            border-radius: var(--radius-md);
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }
        .comparison-side.left { border-top: 3px solid var(--accent-primary); }
        .comparison-side.right { border-top: 3px solid var(--accent-secondary); }
        .comparison-side h4 { margin-bottom: 0.75rem; }
        .comparison-side ul { padding-left: 1.25rem; }
        .comparison-side li { margin-bottom: 0.5rem; color: var(--text-secondary); font-size: 0.95rem; }
        .comparison-divider {
            display: flex;
            align-items: center;
            font-size: 1.5rem;
            color: var(--text-tertiary);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        .stat-card {
            background: var(--bg-card);
            border-radius: var(--radius-md);
            padding: 1.25rem;
            text-align: center;
            border: 1px solid var(--border-color);
            transition: transform 0.15s var(--ease);
        }
        .stat-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
        .stat-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--accent-primary);
            display: block;
            font-family: var(--font-heading);
        }
        .stat-label {
            font-size: 0.8rem;
            color: var(--text-tertiary);
            margin-top: 0.25rem;
        }
        
        @media (max-width: 768px) {
            .comparison-block { grid-template-columns: 1fr; }
            .comparison-divider { justify-content: center; padding: 0.5rem 0; }
            .chart-grid { grid-template-columns: 1fr; }
        }
        
        /* ===========================================
           SIDEBAR TABS & PANELS
           =========================================== */
        .sidebar-tabs {
            display: flex;
            gap: 2px;
            margin-bottom: 1rem;
            background: var(--bg-primary);
            border-radius: var(--radius-sm);
            padding: 2px;
        }
        .sidebar-tab {
            flex: 1;
            padding: 0.5rem 0.25rem;
            background: transparent;
            border: none;
            color: var(--text-tertiary);
            font-family: var(--font-heading);
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.15s var(--ease);
        }
        .sidebar-tab:hover { color: var(--text-secondary); }
        .sidebar-tab.active {
            background: var(--bg-elevated);
            color: var(--accent-primary);
        }
        
        /* ===========================================
           NOTES SYSTEM
           =========================================== */
        .note-card {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 0.625rem;
            font-size: 0.85rem;
            position: relative;
            cursor: pointer;
            transition: border-color 0.15s var(--ease), transform 0.15s var(--ease);
        }
        .note-card:hover { border-color: var(--border-hover); }
        .note-card.active {
            border-color: var(--accent-primary);
            transform: translateY(-1px);
        }
        .note-card.focused {
            border-left: 3px solid var(--accent-secondary);
            padding-left: calc(0.625rem - 2px);
        }
        .note-card .note-citation {
            font-size: 0.75rem;
            color: var(--text-tertiary);
            border-left: 2px solid var(--accent-primary);
            padding-left: 0.5rem;
            margin-bottom: 0.375rem;
            font-style: italic;
            line-height: 1.4;
        }
        .note-card .note-body {
            color: var(--text-secondary);
            line-height: 1.5;
        }
        .note-card .note-meta {
            font-size: 0.7rem;
            color: var(--text-tertiary);
            margin-top: 0.375rem;
            display: flex;
            justify-content: space-between;
        }
        .note-card .note-delete {
            background: none;
            border: none;
            color: var(--text-tertiary);
            cursor: pointer;
            font-size: 0.75rem;
            padding: 0;
        }
        .note-card .note-delete:hover { color: var(--accent-error); }
        .note-card .note-focus {
            background: none;
            border: none;
            color: var(--accent-secondary);
            cursor: pointer;
            font-size: 0.75rem;
            padding: 0;
            margin-right: 0.5rem;
        }
        .note-card .note-focus:hover { color: var(--accent-primary); }
        .note-reader {
            margin-top: 0.75rem;
            padding: 0.75rem;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            background: var(--bg-primary);
            overflow-y: auto;
            max-height: 34vh;
        }
        .note-reader .reader-title {
            font-size: 0.8rem;
            color: var(--text-tertiary);
            margin-bottom: 0.5rem;
        }
        .note-reader .reader-content {
            color: var(--text-secondary);
            line-height: 1.65;
            font-size: 0.9rem;
        }
        .note-reader .reader-content code {
            background: var(--bg-tertiary);
            padding: 0.1em 0.35em;
            border-radius: 4px;
            font-size: 0.85em;
        }
        .note-draft-preview {
            margin-top: 0.5rem;
            max-height: 20vh;
        }
        
        /* ===========================================
           TEXT HIGHLIGHT
           =========================================== */
        .text-highlight {
            background: rgba(246, 193, 119, 0.25);
            border-bottom: 2px solid var(--accent-primary);
            cursor: pointer;
            transition: background 0.15s;
        }
        .text-highlight:hover {
            background: rgba(246, 193, 119, 0.4);
        }
        
        /* Highlight context menu */
        .highlight-tooltip {
            position: fixed;
            background: var(--bg-elevated);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow-lg);
            padding: 0.25rem;
            display: none;
            z-index: 1001;
            gap: 2px;
        }
        .highlight-tooltip.show { display: flex; }
        .highlight-tooltip button {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 0.375rem 0.625rem;
            cursor: pointer;
            font-size: 0.8rem;
            font-family: var(--font-heading);
            border-radius: 4px;
            white-space: nowrap;
        }
        .highlight-tooltip button:hover {
            background: var(--bg-tertiary);
            color: var(--accent-primary);
        }
    '''


def get_javascript():
    """Return JavaScript code as string"""
    return '''
        // ── Gemini Proxy Configuration ──
        const GEMINI_PROXY_URL = '../api/gemini';
        const LAYOUT_STORAGE_KEY = 'learning-layout-widths-v1';
        
        let courseContext = '';
        let conversationHistory = [];

        function escapeHtml(value) {
            return String(value ?? '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }
        
        // ── Main Controller ──
        class LearningPageController {
            constructor() {
                this.isMac = /Mac|iPhone|iPod|iPad/i.test(navigator.platform);
                this.setupExpandables();
                this.setupQuizzes();
                this.setupProgressTracking();
                this.setupScrollReveal();
                this.setupCourseContext();
                this.setupKeyboardShortcuts();
                this.initializeMermaid();
                this.initializeCharts();
                this.updateShortcutsDisplay();
                this.setupColumnResizers();
            }
            
            initializeMermaid() {
                if (typeof mermaid !== 'undefined') {
                    mermaid.initialize({
                        startOnLoad: true,
                        theme: 'dark',
                        themeVariables: {
                            primaryColor: '#263352',
                            primaryTextColor: '#edf2f7',
                            primaryBorderColor: '#f6c177',
                            lineColor: '#a0aec0',
                            secondaryColor: '#1f2b47',
                            tertiaryColor: '#1c2a45',
                            background: '#16213e',
                            mainBkg: '#263352',
                            nodeBorder: '#f6c177',
                            clusterBkg: '#1f2b47',
                            fontSize: '14px'
                        },
                        flowchart: { curve: 'basis', padding: 20 },
                        sequence: { actorMargin: 50 }
                    });
                }
            }
            
            initializeCharts() {
                if (typeof Chart !== 'undefined') {
                    Chart.defaults.color = '#a0aec0';
                    Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
                    Chart.defaults.font.family = "-apple-system, 'Helvetica Neue', sans-serif";
                    Chart.defaults.responsive = true;
                    Chart.defaults.maintainAspectRatio = true;
                    Chart.defaults.plugins.legend.labels.usePointStyle = true;
                }
            }
            
            setupCourseContext() {
                const mc = document.querySelector('.main-content');
                if (mc) courseContext = mc.innerText.substring(0, 6000);
            }
            
            setupExpandables() {
                document.querySelectorAll('.expandable-header').forEach(header => {
                    header.addEventListener('click', () => {
                        header.parentElement.classList.toggle('open');
                    });
                });
            }
            
            setupQuizzes() {
                document.querySelectorAll('.quiz-option').forEach(opt => {
                    opt.addEventListener('click', () => this.handleQuiz(opt));
                });
            }
            
            handleQuiz(option) {
                const quiz = option.closest('.quiz-container');
                const isCorrect = option.dataset.correct === 'true';
                
                quiz.querySelectorAll('.quiz-option').forEach(o => {
                    o.classList.remove('selected','correct','incorrect');
                });
                
                option.classList.add('selected');
                option.classList.add(isCorrect ? 'correct' : 'incorrect');
                
                // Show correct answer if wrong
                if (!isCorrect) {
                    quiz.querySelectorAll('.quiz-option').forEach(o => {
                        if (o.dataset.correct === 'true') o.classList.add('correct');
                    });
                }
                
                const cf = quiz.querySelector('.quiz-feedback.correct');
                const ic = quiz.querySelector('.quiz-feedback.incorrect');
                if (isCorrect) { cf.classList.add('show'); ic.classList.remove('show'); }
                else { ic.classList.add('show'); cf.classList.remove('show'); }
            }
            
            setupProgressTracking() {
                window.addEventListener('scroll', () => {
                    const h = document.documentElement.scrollHeight - window.innerHeight;
                    const p = h > 0 ? Math.min((window.scrollY / h) * 100, 100) : 0;
                    document.getElementById('progressBar').style.width = p + '%';
                });
            }
            
            setupScrollReveal() {
                const obs = new IntersectionObserver((entries) => {
                    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('revealed'); });
                }, { threshold: 0.08 });
                document.querySelectorAll('.reveal-on-scroll').forEach(el => obs.observe(el));
            }
            
            setupKeyboardShortcuts() {
                document.addEventListener('keydown', (e) => {
                    if (e.altKey && e.key === 'a') {
                        e.preventDefault();
                        document.getElementById('aiInput')?.focus();
                    }
                    if (e.altKey && e.key === 's') {
                        e.preventDefault();
                        askSummary();
                    }
                });
            }
            
            updateShortcutsDisplay() {
                const prefix = this.isMac ? '⌥' : 'Alt+';
                const focusEl = document.getElementById('shortcutFocusAI');
                const summaryEl = document.getElementById('shortcutSummary');
                if (focusEl) focusEl.textContent = prefix + 'A';
                if (summaryEl) summaryEl.textContent = prefix + 'S';
            }

            setupColumnResizers() {
                if (window.matchMedia('(max-width: 1200px)').matches) return;
                const container = document.querySelector('.page-container');
                const leftResizer = document.getElementById('resizerLeft');
                const rightResizer = document.getElementById('resizerRight');
                if (!container || !leftResizer || !rightResizer) return;

                const minLeft = 200, maxLeft = 560;
                const minRight = 220, maxRight = 560;
                const minMain = 520;
                let leftWidth = 260;
                let rightWidth = 300;

                const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
                const applyWidths = () => {
                    container.style.setProperty('--left-width', leftWidth + 'px');
                    container.style.setProperty('--right-width', rightWidth + 'px');
                };
                const getTotalWidth = () => container.getBoundingClientRect().width - 16;
                const clampAll = () => {
                    const total = getTotalWidth();
                    leftWidth = clamp(leftWidth, minLeft, maxLeft);
                    rightWidth = clamp(rightWidth, minRight, maxRight);
                    if (total - leftWidth - rightWidth < minMain) {
                        const overflow = minMain - (total - leftWidth - rightWidth);
                        leftWidth = clamp(leftWidth - overflow / 2, minLeft, maxLeft);
                        rightWidth = clamp(rightWidth - overflow / 2, minRight, maxRight);
                        if (total - leftWidth - rightWidth < minMain) {
                            const rightCap = clamp(total - leftWidth - minMain, minRight, maxRight);
                            rightWidth = rightCap;
                            leftWidth = clamp(total - rightWidth - minMain, minLeft, maxLeft);
                        }
                    }
                };

                try {
                    const cached = JSON.parse(localStorage.getItem(LAYOUT_STORAGE_KEY) || '{}');
                    if (Number.isFinite(cached.left)) leftWidth = cached.left;
                    if (Number.isFinite(cached.right)) rightWidth = cached.right;
                } catch {}
                clampAll();
                applyWidths();

                const startDrag = (side) => (evt) => {
                    evt.preventDefault();
                    const rect = container.getBoundingClientRect();
                    const total = getTotalWidth();
                    const onMove = (moveEvt) => {
                        if (side === 'left') {
                            const rawLeft = moveEvt.clientX - rect.left;
                            const maxAllowed = Math.min(maxLeft, total - rightWidth - minMain);
                            leftWidth = clamp(rawLeft, minLeft, Math.max(minLeft, maxAllowed));
                        } else {
                            const rawRight = rect.right - moveEvt.clientX;
                            const maxAllowed = Math.min(maxRight, total - leftWidth - minMain);
                            rightWidth = clamp(rawRight, minRight, Math.max(minRight, maxAllowed));
                        }
                        applyWidths();
                    };
                    const stopMove = () => {
                        document.body.style.userSelect = '';
                        document.body.style.cursor = '';
                        leftResizer.classList.remove('dragging');
                        rightResizer.classList.remove('dragging');
                        localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify({ left: leftWidth, right: rightWidth }));
                        document.removeEventListener('pointermove', onMove);
                        document.removeEventListener('pointerup', stopMove);
                    };
                    document.body.style.userSelect = 'none';
                    document.body.style.cursor = 'col-resize';
                    (side === 'left' ? leftResizer : rightResizer).classList.add('dragging');
                    document.addEventListener('pointermove', onMove);
                    document.addEventListener('pointerup', stopMove);
                };

                leftResizer.addEventListener('pointerdown', startDrag('left'));
                rightResizer.addEventListener('pointerdown', startDrag('right'));
                window.addEventListener('resize', () => {
                    if (window.matchMedia('(max-width: 1200px)').matches) return;
                    clampAll();
                    applyWidths();
                });
            }
        }
        
        // ── AI Chat (Real Gemini API) ──
        async function sendAIMessage() {
            const input = document.getElementById('aiInput');
            const msg = input.value.trim();
            if (!msg) return;
            
            appendMsg('user', msg);
            input.value = '';
            input.disabled = true;
            
            const typingEl = appendMsg('assistant', '<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>');
            
            try {
                const answer = await callGemini(msg);
                typingEl.innerHTML = formatMd(answer);
            } catch (err) {
                const errMsg = err?.message || String(err);
                let hint = 'Check console for details.';
                if (window.location.protocol === 'file:' || errMsg.includes('Failed to fetch')) {
                    const current = window.location.pathname.split('/').pop();
                    hint = `Start local server: python3 serve.py --open html/${current} and ensure GEMINI_API_KEY exists in .env.local`;
                }
                typingEl.innerHTML = '⚠️ Error: ' + escapeHtml(errMsg) + '<br><small>' + escapeHtml(hint) + '</small>';
                console.error('Gemini API error:', err);
            } finally {
                input.disabled = false;
                input.focus();
            }
        }
        
        async function callGemini(userMessage) {
            if (window.location.protocol === 'file:') {
                throw new Error('This page is opened as file:// and cannot reach ../api/gemini');
            }

            const prompt = `You are a concise study assistant for this course.

Course content (excerpt):
${courseContext.substring(0, 3500)}

Previous conversation:
${conversationHistory.slice(-4).map(m => m.role + ': ' + m.content).join('\\n')}

Student question: ${userMessage}

Instructions:
- Answer in 3-6 sentences, be direct and complete
- Always finish your sentences, never leave a thought incomplete
- Use the course content as reference
- If the question is in Chinese, answer in Chinese`;

            const res = await fetch(GEMINI_PROXY_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: prompt,
                    generationConfig: { temperature: 0.7, maxOutputTokens: 1024 }
                })
            });
            
            if (!res.ok) {
                const errText = await res.text();
                throw new Error(`API ${res.status}: ${errText.substring(0, 200)}`);
            }
            
            const data = await res.json();
            const candidate = data.candidates?.[0];
            const answer = candidate?.content?.parts?.[0]?.text;
            if (!answer) throw new Error('Empty response from API');
            
            // Check if response was truncated
            if (candidate?.finishReason === 'MAX_TOKENS') {
                conversationHistory.push({ role: 'user', content: userMessage }, { role: 'assistant', content: answer });
                return answer + '...\\n\\n_(Response was trimmed. Ask a follow-up for more detail.)_';
            }
            
            conversationHistory.push({ role: 'user', content: userMessage }, { role: 'assistant', content: answer });
            return answer;
        }
        
        function appendMsg(role, html) {
            const container = document.getElementById('aiMessages');
            const div = document.createElement('div');
            div.className = 'ai-message ' + role;
            div.innerHTML = html;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
            return div;
        }
        
        function formatMd(text) {
            return text
                .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/\\*(.+?)\\*/g, '<em>$1</em>')
                .replace(/`(.+?)`/g, '<code style="background:var(--bg-tertiary);padding:0.1em 0.4em;border-radius:3px;font-size:0.9em;">$1</code>')
                .replace(/\\n/g, '<br>');
        }
        
        function askSummary() {
            const input = document.getElementById('aiInput');
            input.value = 'Please summarize the key concepts of this lesson in bullet points.';
            sendAIMessage();
        }
        
        function reviewAllQuizzes() {
            const q = document.querySelector('.quiz-container');
            if (q) q.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        function createSummary() { askSummary(); }
        
        // ── Sidebar Tabs ──
        function switchSidebarTab(tabName) {
            document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.sidebar-panel').forEach(p => p.style.display = 'none');
            document.querySelector(`.sidebar-tab[data-tab="${tabName}"]`)?.classList.add('active');
            const panel = document.getElementById('panel-' + tabName);
            if (panel) panel.style.display = 'block';
        }
        
        // ── Notes System ──
        const NOTES_STORAGE_KEY = 'learning-notes-' + document.title;
        const NOTES_FOCUS_KEY = NOTES_STORAGE_KEY + '-focus';
        const NOTES_ACTIVE_KEY = NOTES_STORAGE_KEY + '-active';
        const NOTES_DRAFT_KEY = NOTES_STORAGE_KEY + '-draft';
        
        function loadNotes() {
            try {
                const raw = JSON.parse(localStorage.getItem(NOTES_STORAGE_KEY) || '[]');
                if (!Array.isArray(raw)) return [];
                return raw.map((n, idx) => {
                    const idNum = Number(n?.id);
                    return {
                        id: Number.isFinite(idNum) ? idNum : -(idx + 1),
                        citation: typeof n?.citation === 'string' ? n.citation : (typeof n?.quote === 'string' ? n.quote : ''),
                        body: typeof n?.body === 'string' ? n.body : (typeof n?.text === 'string' ? n.text : (typeof n?.content === 'string' ? n.content : '')),
                        section: typeof n?.section === 'string' ? n.section : (typeof n?.title === 'string' ? n.title : ''),
                        timestamp: typeof n?.timestamp === 'string' && n.timestamp
                            ? n.timestamp
                            : (typeof n?.created_at === 'string' && n.created_at ? n.created_at : new Date().toISOString())
                    };
                });
            }
            catch { return []; }
        }
        
        function saveNotes(notes) {
            localStorage.setItem(NOTES_STORAGE_KEY, JSON.stringify(notes));
            renderNotes();
        }

        function saveDraft(text) {
            localStorage.setItem(NOTES_DRAFT_KEY, text || '');
        }

        function loadDraft() {
            return localStorage.getItem(NOTES_DRAFT_KEY) || '';
        }

        function renderDraftPreview(text) {
            const preview = document.getElementById('noteDraftPreviewContent');
            if (!preview) return;
            const clean = text || '';
            if (!clean.trim()) {
                preview.innerHTML = '<span style="color: var(--text-tertiary);">Type in the note box to preview Markdown rendering in real time.</span>';
                return;
            }
            preview.innerHTML = renderNoteMarkdown(clean);
        }

        function handleNoteInputChange(value) {
            saveDraft(value);
            renderDraftPreview(value);
        }

        function initNoteComposer() {
            const input = document.getElementById('noteInput');
            if (!input) return;
            const draft = loadDraft();
            input.value = draft;
            renderDraftPreview(draft);
            input.addEventListener('input', () => {
                handleNoteInputChange(input.value);
            });
            input.addEventListener('keydown', (e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                    e.preventDefault();
                    addFreeNote();
                }
            });
        }

        function getFocusedNoteId() {
            const value = localStorage.getItem(NOTES_FOCUS_KEY);
            return value ? Number(value) : null;
        }

        function getActiveNoteId() {
            const value = localStorage.getItem(NOTES_ACTIVE_KEY);
            return value ? Number(value) : null;
        }

        function setFocusedNoteId(id) {
            if (!id) localStorage.removeItem(NOTES_FOCUS_KEY);
            else localStorage.setItem(NOTES_FOCUS_KEY, String(id));
        }

        function setActiveNoteId(id) {
            if (!id) localStorage.removeItem(NOTES_ACTIVE_KEY);
            else localStorage.setItem(NOTES_ACTIVE_KEY, String(id));
        }

        function toggleFocusNote(id, e) {
            e?.stopPropagation();
            const focusedId = getFocusedNoteId();
            setFocusedNoteId(focusedId === id ? null : id);
            renderNotes();
        }

        function openNote(id) {
            setActiveNoteId(id);
            renderNotes();
            switchSidebarTab('notes');
        }

        function ensureNoteReader() {
            const panel = document.getElementById('panel-notes');
            const notesList = document.getElementById('notesList');
            if (!panel || !notesList) return null;
            notesList.style.maxHeight = '32vh';

            let reader = document.getElementById('noteReader');
            if (!reader) {
                reader = document.createElement('div');
                reader.id = 'noteReader';
                reader.className = 'note-reader';
                notesList.insertAdjacentElement('afterend', reader);
            }
            return reader;
        }

        function renderNoteMarkdown(text) {
            return escapeHtml(text || '')
                .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/\\*(.+?)\\*/g, '<em>$1</em>')
                .replace(/`(.+?)`/g, '<code>$1</code>')
                .replace(/\\n/g, '<br>');
        }

        function renderNoteReader(notes) {
            const reader = ensureNoteReader();
            if (!reader) return;
            if (notes.length === 0) {
                reader.innerHTML = '<div class="reader-title">Reader</div><div class="reader-content">No notes yet.</div>';
                return;
            }

            let activeId = getActiveNoteId();
            let active = notes.find(n => n.id === activeId);
            if (!active) {
                active = notes[0];
                setActiveNoteId(active.id);
            }
            const time = new Date(active.timestamp).toLocaleString();
            const citationHtml = active.citation ? `<div class="note-citation">${escapeHtml(active.citation)}</div>` : '';
            const activeBody = typeof active.body === 'string' ? active.body : '';
            reader.innerHTML = `
                <div class="reader-title">Reading • ${escapeHtml(active.section || 'General')} • ${time}</div>
                ${citationHtml}
                <div class="reader-content">${renderNoteMarkdown(activeBody)}</div>
            `;
        }
        
        function addNote(citation, body, section) {
            const notes = loadNotes();
            const note = {
                id: Date.now(),
                citation: citation || '',
                body: body || '',
                section: section || '',
                timestamp: new Date().toISOString()
            };
            notes.push(note);
            setActiveNoteId(note.id);
            saveNotes(notes);
            // Switch to notes tab
            switchSidebarTab('notes');
        }
        
        function addFreeNote() {
            const input = document.getElementById('noteInput');
            const text = input.value.trim();
            if (!text) return;
            addNote('', text, '');
            input.value = '';
            saveDraft('');
            renderDraftPreview('');
        }
        
        function deleteNote(id, e) {
            e?.stopPropagation();
            const notes = loadNotes().filter(n => n.id !== id);
            if (getFocusedNoteId() === id) setFocusedNoteId(null);
            if (getActiveNoteId() === id) setActiveNoteId(notes.length ? notes[0].id : null);
            saveNotes(notes);
        }
        
        function renderNotes() {
            const notes = loadNotes();
            const container = document.getElementById('notesList');
            const counter = document.getElementById('notesCount');
            if (!container) return;
            
            counter.textContent = notes.length + ' note' + (notes.length !== 1 ? 's' : '');
            
            if (notes.length === 0) {
                container.innerHTML = '<p style="font-size:0.85rem; color:var(--text-tertiary); text-align:center; padding:2rem 0;">Select text and click "Add Note" to begin, or write freely below.</p>';
                renderNoteReader(notes);
                return;
            }

            const focusedId = getFocusedNoteId();
            const activeId = getActiveNoteId();
            const sortedNotes = [...notes].sort((a, b) => {
                const aFocused = a.id === focusedId ? 1 : 0;
                const bFocused = b.id === focusedId ? 1 : 0;
                if (aFocused !== bFocused) return bFocused - aFocused;
                return new Date(b.timestamp) - new Date(a.timestamp);
            });

            container.innerHTML = sortedNotes.map(n => {
                const time = new Date(n.timestamp).toLocaleString();
                const citationHtml = n.citation 
                    ? `<div class="note-citation">${escapeHtml(n.citation)}</div>` 
                    : '';
                const noteBody = typeof n.body === 'string' ? n.body : '';
                const preview = noteBody.length > 140 ? (noteBody.slice(0, 140) + '...') : noteBody;
                const focusLabel = n.id === focusedId ? 'Unfocus' : 'Focus';
                return `<div class="note-card ${n.id === activeId ? 'active' : ''} ${n.id === focusedId ? 'focused' : ''}" onclick="openNote(${n.id})">
                    ${citationHtml}
                    <div class="note-body">${escapeHtml(preview)}</div>
                    <div class="note-meta">
                        <span>${n.section ? escapeHtml(n.section) : ''} ${time}</span>
                        <span>
                            <button class="note-focus" onclick="toggleFocusNote(${n.id}, event)">${focusLabel}</button>
                            <button class="note-delete" onclick="deleteNote(${n.id}, event)">Delete</button>
                        </span>
                    </div>
                </div>`;
            }).join('');
            renderNoteReader(sortedNotes);
        }
        
        function exportNotesToObsidian() {
            const notes = loadNotes();
            if (notes.length === 0) { alert('No notes to export.'); return; }
            
            const title = document.title.replace(' - Interactive Learning', '');
            const sourceFile = document.querySelector('.main-content header p')?.textContent?.match(/Source: (.+)/)?.[1] || '';
            
            let md = `---\ntags: [lecture-notes, mfin7034]\nsource: "${sourceFile}"\ndate: ${new Date().toISOString().split('T')[0]}\n---\n\n`;
            md += `# ${title}\n\n`;
            md += `> [!info] Source\n> PDF: [[${sourceFile.replace('.pdf','')}]]\n\n`;
            
            notes.forEach((n, idx) => {
                if (n.citation) {
                    md += `> [!quote] Highlight\n> ${n.citation}\n\n`;
                }
                const noteBody = typeof n.body === 'string' ? n.body : '';
                md += noteBody + `\n\n`;
                if (idx < notes.length - 1) md += `---\n\n`;
            });
            
            md += `\n## References\n\n- Source: ${sourceFile}\n- Generated: ${new Date().toLocaleString()}\n`;
            
            const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = title.replace(/[^a-zA-Z0-9\u4e00-\u9fff ]/g, '_') + '.md';
            a.click();
            URL.revokeObjectURL(a.href);
        }
        
        // ── Text Highlight & Selection ──
        const highlightTooltip = document.createElement('div');
        highlightTooltip.className = 'highlight-tooltip';
        highlightTooltip.innerHTML = `
            <button onclick="highlightSelection()">Highlight</button>
            <button onclick="highlightAndNote()">+ Note</button>
        `;
        document.body.appendChild(highlightTooltip);
        
        document.addEventListener('mouseup', (e) => {
            const sel = window.getSelection();
            const text = sel.toString().trim();
            
            // Only show for selections within main content
            const main = document.querySelector('.main-content');
            if (!text || text.length < 3 || !main?.contains(sel.anchorNode)) {
                highlightTooltip.classList.remove('show');
                return;
            }
            
            const range = sel.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            highlightTooltip.style.left = rect.left + (rect.width / 2) - 60 + 'px';
            highlightTooltip.style.top = rect.top - 40 + window.scrollY + 'px';
            highlightTooltip.classList.add('show');
        });
        
        document.addEventListener('mousedown', (e) => {
            if (!highlightTooltip.contains(e.target)) {
                highlightTooltip.classList.remove('show');
            }
        });
        
        function highlightSelection() {
            const sel = window.getSelection();
            if (!sel.rangeCount) return;
            const range = sel.getRangeAt(0);
            const mark = document.createElement('mark');
            mark.className = 'text-highlight';
            try {
                range.surroundContents(mark);
            } catch(e) {
                // Cross-element selection: fall back
                const text = sel.toString();
                mark.textContent = text;
                range.deleteContents();
                range.insertNode(mark);
            }
            sel.removeAllRanges();
            highlightTooltip.classList.remove('show');
        }
        
        function highlightAndNote() {
            const sel = window.getSelection();
            const text = sel.toString().trim();
            if (!text) return;
            
            // Find section context
            let section = '';
            let node = sel.anchorNode;
            while (node && node !== document.body) {
                if (node.classList?.contains('concept-section')) {
                    const h2 = node.querySelector('h2');
                    if (h2) section = h2.textContent;
                    break;
                }
                node = node.parentNode;
            }
            
            highlightSelection();
            openInlineSelectionNoteEditor(text, section, sel.getRangeAt(0).getBoundingClientRect());
        }

        function closeInlineSelectionNoteEditor() {
            document.getElementById('inlineSelectionNoteEditor')?.remove();
        }

        function openInlineSelectionNoteEditor(selectionText, section, rect) {
            closeInlineSelectionNoteEditor();
            const editor = document.createElement('div');
            editor.id = 'inlineSelectionNoteEditor';
            editor.style.position = 'absolute';
            editor.style.zIndex = '10030';
            editor.style.width = 'min(420px, 90vw)';
            editor.style.background = 'var(--bg-card)';
            editor.style.border = '1px solid var(--border-color)';
            editor.style.borderRadius = '12px';
            editor.style.boxShadow = '0 16px 36px rgba(0,0,0,0.32)';
            editor.style.padding = '0.65rem';
            editor.style.top = (window.scrollY + rect.bottom + 10) + 'px';
            editor.style.left = Math.max(12, Math.min(window.scrollX + rect.left, window.scrollX + window.innerWidth - 440)) + 'px';
            editor.innerHTML = `
                <div style="font-size:0.78rem;color:var(--text-tertiary);margin-bottom:0.4rem;">Add note for selection</div>
                <textarea id="inlineSelectionNoteInput" placeholder="Write note... (Markdown supported)" style="width:100%;min-height:88px;background:var(--bg-primary);color:var(--text-primary);border:1px solid var(--border-color);border-radius:8px;padding:0.5rem;font-size:0.86rem;resize:vertical;"></textarea>
                <div style="display:flex;justify-content:flex-end;gap:0.45rem;margin-top:0.45rem;">
                    <button type="button" id="inlineSelectionNoteCancel" style="border:1px solid var(--border-color);background:var(--bg-elevated);color:var(--text-primary);border-radius:8px;padding:0.3rem 0.6rem;cursor:pointer;font-size:0.8rem;">Cancel</button>
                    <button type="button" id="inlineSelectionNoteSave" style="border:1px solid rgba(163,217,165,.55);background:var(--bg-elevated);color:var(--accent-secondary);border-radius:8px;padding:0.3rem 0.6rem;cursor:pointer;font-size:0.8rem;">Save</button>
                </div>
            `;
            document.body.appendChild(editor);
            const input = editor.querySelector('#inlineSelectionNoteInput');
            input?.focus();
            editor.querySelector('#inlineSelectionNoteCancel')?.addEventListener('click', closeInlineSelectionNoteEditor);
            editor.querySelector('#inlineSelectionNoteSave')?.addEventListener('click', () => {
                const body = (input?.value || '').trim() || '(highlighted)';
                addNote(selectionText, body, section);
                closeInlineSelectionNoteEditor();
            });
        }
        
        // ── Init ──
        document.addEventListener('DOMContentLoaded', () => {
            new LearningPageController();
            
            // Add reveal animation to concept sections
            document.querySelectorAll('.feynman-block, .quiz-container, .expandable, .chart-container, .diagram-container, .comparison-block, .stats-grid').forEach(el => {
                el.classList.add('reveal-on-scroll');
            });
            
            // Re-init observer for dynamically added elements
            const obs = new IntersectionObserver((entries) => {
                entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('revealed'); });
            }, { threshold: 0.08 });
            document.querySelectorAll('.reveal-on-scroll').forEach(el => obs.observe(el));
            
            // Initialize note draft autosave + live markdown preview
            initNoteComposer();
            // Load saved notes
            renderNotes();
        });
        
        // Typing dots animation
        const typingStyle = document.createElement('style');
        typingStyle.textContent = `
            .typing-dots span {
                animation: blink 1.4s infinite;
                font-size: 1.5em;
                line-height: 1;
            }
            .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
            .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
            @keyframes blink {
                0%, 60%, 100% { opacity: 0.2; }
                30% { opacity: 1; }
            }
        `;
        document.head.appendChild(typingStyle);
    '''


def visual_review(html_content, output_file):
    """Perform automated visual review and self-correction on generated HTML"""
    
    print(f"\n🔍 Visual Review & Self-Correction...")
    print("="*60)
    
    issues = []
    fixes_applied = 0
    
    # Check 1: Chart.js CDN present
    if 'chart.js' not in html_content and 'Chart' not in html_content:
        issues.append("⚠️  Chart.js CDN missing")
    else:
        print("  ✓ Chart.js CDN present")
    
    # Check 2: Mermaid CDN present
    if 'mermaid' not in html_content.lower():
        issues.append("⚠️  Mermaid CDN missing")
    else:
        print("  ✓ Mermaid CDN present")
    
    # Check 3: Every concept section has at least one visualization
    sections = re.findall(r'<section id="concept-(\d+)".*?</section>', html_content, re.DOTALL)
    for section in sections:
        section_num = section if isinstance(section, str) else section[0] if section else '?'
        # Actually search within the section content
    
    concept_sections = re.split(r'<section id="concept-\d+"', html_content)
    viz_count = 0
    for idx, sec in enumerate(concept_sections[1:], 1):  # Skip before first concept
        has_viz = any(marker in sec for marker in [
            'chart-container', 'diagram-container', 'comparison-block', 'stats-grid',
            '<canvas id="chart-', '<div class="mermaid">'
        ])
        if has_viz:
            viz_count += 1
            print(f"  ✓ Concept {idx}: has visualization")
        else:
            issues.append(f"⚠️  Concept {idx}: missing visualization")
    
    total_concepts = len(concept_sections) - 1
    
    # Check 4: Canvas IDs match Chart.js initialization
    canvas_ids = re.findall(r'<canvas id="(chart-\d+)"', html_content)
    chart_inits = re.findall(r"getElementById\('(chart-\d+)'\)", html_content)
    for cid in canvas_ids:
        if cid in chart_inits:
            print(f"  ✓ Chart '{cid}': canvas & init matched")
        else:
            issues.append(f"⚠️  Chart '{cid}': canvas exists but no Chart.js init found")
    
    # Check 5: Mermaid syntax basic validation
    mermaid_blocks = re.findall(r'<div class="mermaid">(.*?)</div>', html_content, re.DOTALL)
    for midx, block in enumerate(mermaid_blocks):
        block = block.strip()
        if block and any(kw in block for kw in ['flowchart', 'graph', 'sequenceDiagram', 'classDiagram', 'timeline', 'mindmap', 'pie', 'gantt']):
            print(f"  ✓ Mermaid block {midx+1}: valid diagram type")
        elif block:
            issues.append(f"⚠️  Mermaid block {midx+1}: may have invalid syntax")
    
    # Check 6: No unclosed HTML tags (basic)
    open_divs = html_content.count('<div')
    close_divs = html_content.count('</div>')
    if abs(open_divs - close_divs) > 2:
        issues.append(f"⚠️  Unbalanced div tags: {open_divs} open vs {close_divs} close")
    else:
        print(f"  ✓ Div tags balanced: {open_divs}/{close_divs}")
    
    # Check 7: No placeholder text (including generic fallback sentences)
    placeholder_patterns = [
        r'\[TODO\]',
        r'\[TBD\]',
        r'\[PLACEHOLDER\]',
        r'Lorem ipsum',
        r'This concept is like a familiar everyday process\.',
        r'Understanding this helps in practical applications\.',
        r'Consider a typical scenario where this applies\.',
        r'Students often confuse this with related concepts\.',
    ]
    placeholder_hits = []
    for pattern in placeholder_patterns:
        found = re.findall(pattern, html_content, re.IGNORECASE)
        if found:
            placeholder_hits.extend(found)

    if placeholder_hits:
        issues.append(f"⚠️  Found {len(placeholder_hits)} placeholder(s): {placeholder_hits[:3]}")
    else:
        print("  ✓ No placeholder text found")
    
    # Check 8: KaTeX delimiters balanced
    dollar_singles = len(re.findall(r'(?<!\$)\$(?!\$)', html_content))
    if dollar_singles % 2 != 0:
        issues.append(f"⚠️  Unbalanced $ delimiters ({dollar_singles} found)")
    
    # Check 9: Quiz options have data-correct attributes
    quiz_options = re.findall(r'class="quiz-option"', html_content)
    data_correct = re.findall(r'data-correct="(true|false)"', html_content)
    if quiz_options and len(data_correct) < len(quiz_options):
        issues.append(f"⚠️  Some quiz options missing data-correct attribute")
    elif quiz_options:
        print(f"  ✓ All {len(quiz_options)} quiz options have data-correct")
    
    # Summary
    print(f"\n{'='*60}")
    viz_ratio = (viz_count / max(total_concepts, 1)) * 100
    print(f"📊 Visualization coverage: {viz_count}/{total_concepts} concepts ({viz_ratio:.0f}%)")
    print(f"📊 Charts: {len(canvas_ids)} | Mermaid diagrams: {len(mermaid_blocks)}")
    
    if issues:
        print(f"\n⚠️  {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"\n✅ All visual checks passed!")
    
    print(f"\n🔍 Visual Review Score: {max(0, 9 - len(issues))}/9 checks passed")
    
    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_html.py <extracted_dir> [output_file]")
        print("\nExample:")
        print("  python generate_html.py 'extracted/Lec 1 Fintech and Artificial Intelligence'")
        sys.exit(1)
    
    extracted_dir = sys.argv[1]
    
    if not os.path.exists(extracted_dir):
        print(f"❌ Error: Extracted directory not found: {extracted_dir}")
        sys.exit(1)
    
    # Default output file
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        dir_name = os.path.basename(extracted_dir.rstrip('/'))
        output_file = f"html/{dir_name}_interactive.html"
    
    try:
        output_path = generate_html(extracted_dir, output_file)
        
        # Run visual review
        with open(output_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        issues = visual_review(html_content, output_file)
        
        print(f"\n✨ Success! Open the file to view:")
        print(f"   {output_path}")
        if issues:
            print(f"   ⚠️  {len(issues)} visual issue(s) to check manually")
        return 0
    except Exception as e:
        print(f"\n❌ Error during HTML generation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
