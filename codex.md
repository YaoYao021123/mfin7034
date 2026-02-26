# CODEX: PDF → Interactive Lecture Standard

This document defines the standard workflow and quality gates for this project.

## 1) Recommended Skills

- Primary skill: `.claude/skill/pdf-to-interactive-learning.md`
- Supporting capability: integrated portal (`html/index.html`) + `serve.py` API endpoints

## 2) Standard Workflow

1. Put PDFs in `pdfs/`
2. Extract content:
   - `python3 extract_pdf.py "<pdf>" "extracted/<name>"`
3. Generate interactive HTML:
   - `python3 generate_html.py "extracted/<name>" "html/<name>_interactive.html"`
4. Launch portal:
   - `python3 serve.py --open html/index.html`

## 3) Hard Quality Gates (Must Pass)

### A. Placeholder ban
Generated HTML must NOT contain any of the following:

- `This concept is like a familiar everyday process.`
- `Understanding this helps in practical applications.`
- `Consider a typical scenario where this applies.`
- `Students often confuse this with related concepts.`

Check:

```bash
rg -n "This concept is like a familiar everyday process|Understanding this helps in practical applications|Consider a typical scenario where this applies|Students often confuse this with related concepts" html/*.html
```

Expected: no matches.

### B. Core rendering checks

- Notes live preview works while typing
- Notes history click-to-read works (Markdown rendered)
- PDF iframe opens correctly
- AI endpoint reachable via `/api/gemini`
- Portal API returns lecture list via `/api/lectures`

### C. Build/syntax checks

```bash
python3 -m py_compile generate_html.py serve.py extract_pdf.py
bash -n run.sh
```

## 4) Mobile App Feature (PWA)

Portal is treated as an installable mini-app:

- `html/manifest.webmanifest`
- `html/sw.js` (service worker cache shell)
- `html/icon.svg`
- Mobile home-screen install supported from `/html/index.html`

## 5) Regeneration Policy

When existing outputs have quality issues:

1. fix generator/skill first
2. regenerate affected lecture HTML
3. rerun all quality gates

Do not ship partial fixes that leave old broken outputs in `html/`.
