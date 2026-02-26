# PDF to Interactive Learning - Feynman Method

> Transform static PDF course materials into interactive, AI-enhanced HTML learning experiences

## 🎯 Overview

This system converts PDF lecture notes into rich, interactive learning pages using:
- **Feynman Learning Technique** - Simple analogies → Deep explanations → Examples
- **AI Content Expansion** - Gemini API adds context, examples, and practice questions
- **Interactive Elements** - Quizzes, expandable sections, progress tracking
- **Self-Contained HTML** - One file with everything embedded, works offline

## ✨ Features

### 📚 Content Features
- ✅ **PDF Extraction** - Text, images, tables, formulas
- ✅ **AI Analysis** - Identifies main concepts and learning objectives
- ✅ **Feynman Expansion** - Each concept gets:
  - Simple analogy (ELI12 explanation)
  - Why it matters (real-world application)
  - Deep dive (detailed explanation)
  - Practical examples
  - Common mistakes to avoid
- ✅ **Interactive Quizzes** - Auto-generated multiple choice questions
- ✅ **Formula Rendering** - Beautiful math with KaTeX

### 🎨 UX Features
- ✅ **Three-Column Layout** - TOC | Content | AI Assistant
- ✅ **Progress Tracking** - Visual progress bar at top
- ✅ **Dark/Light Mode** - Auto-adapts to system preference
- ✅ **Mobile Responsive** - Works on all screen sizes
- ✅ **Keyboard Shortcuts** - Alt+A (AI), Alt+S (Summary)
- ✅ **Expandable Sections** - Click to reveal detailed content

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.7+
python3 --version

# Install dependencies
pip3 install PyMuPDF pdfplumber Pillow python-dotenv google-generativeai
```

### Setup

1. **Add your Gemini API key** to `.env.local`:
```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3-flash-preview
```
You can start from:
```bash
cp .env.example .env.local
```

2. **Place PDFs** in the `pdfs/` folder

### Usage

**Option 1: One-command workflow**
```bash
./run.sh "pdfs/Lec 1 Fintech and Artificial Intelligence.pdf"
```

**Option 2: Step by step**
```bash
# Step 1: Extract PDF
python3 extract_pdf.py "pdfs/Lec 1 Fintech and Artificial Intelligence.pdf"

# Step 2: Generate HTML with AI
python3 generate_html.py "extracted/Lec 1 Fintech and Artificial Intelligence"

# Step 3: Start local server (required for secure AI chat)
python3 serve.py --open html/index.html
```

Use the portal page to open any generated lecture HTML directly.

## 🌐 Deploy frontend to GitHub Pages

1. Push this repository to GitHub (branch `main`).
2. In GitHub repository settings, enable **Pages** and set **Source = GitHub Actions**.
3. The included workflow `.github/workflows/deploy-pages.yml` will publish the static site.
4. Open:
   - `https://<your-username>.github.io/<repo>/` (auto-redirects)
   - or `https://<your-username>.github.io/<repo>/html/index.html`

Notes:
- API key remains server-side only in `.env.local` (ignored by git).
- GitHub Pages is static, so AI chat (`/api/gemini`) needs a separate backend to work online.
- Portal lecture listing falls back to `html/lectures.json` automatically in static mode.

## 📂 Project Structure

```
.
├── pdfs/                          # Place your PDF files here
│   ├── Lec 1 Fintech and AI.pdf
│   ├── Lec 2 Regression ML.pdf
│   └── Lec 3 Gradient Method.pdf
│
├── extracted/                     # Extracted content (auto-generated)
│   └── [Lecture Name]/
│       ├── extracted_content.json
│       ├── text/full_text.txt
│       ├── images/
│       └── tables/
│
├── html/                           # Generated interactive pages + portal (index.html)
│
├── extract_pdf.py                 # PDF extraction script
├── generate_html.py               # HTML generator with AI
├── serve.py                       # Local server + Gemini proxy
├── run.sh                         # One-click workflow
│
├── .env.local                     # API keys (not in git)
└── README.md                      # This file
```

## 🧠 How It Works

### 1. PDF Extraction (`extract_pdf.py`)

Extracts from PDF:
- **Text blocks** with formatting (headings, paragraphs, lists)
- **Images** (saves to images/ folder)
- **Tables** (converts to JSON)
- **Formulas** (detects math symbols)
- **Metadata** (page numbers, structure)

Output: `extracted/[name]/extracted_content.json`

### 2. AI Analysis & Expansion (`generate_html.py`)

Uses Gemini AI to:
1. **Analyze content** - Identify 5-10 main concepts
2. **Determine prerequisites** - What students need to know
3. **Set learning objectives** - What students will master
4. **Expand each concept** with Feynman technique:
   - Simple analogy
   - Real-world importance
   - Deep explanation
   - Practical example
   - Common mistakes
5. **Generate quizzes** - 3 questions per concept

### 3. HTML Generation

Creates single-file HTML with:
- **Embedded CSS** - Professional dark theme
- **Inline JavaScript** - Full interactivity
- **Base64 images** - Optional (for true single-file)
- **KaTeX CDN** - Math rendering
- **Google Fonts** - Beautiful typography

## 🎨 Customization

### Change Color Theme

Edit CSS variables in generated HTML:

```css
:root {
    --accent-primary: #4299e1;    /* Blue */
    --accent-secondary: #48bb78;  /* Green */
    --accent-warning: #ed8936;    /* Orange */
    --accent-error: #f56565;      /* Red */
}
```

### Adjust AI Model

In `.env.local`:
```env
# Fast and cheap
GEMINI_MODEL=gemini-3-flash-preview

# More powerful (slower, costs more)
GEMINI_MODEL=gemini-3-pro
```

### Add More Concepts

AI automatically limits to 8 concepts. To change:

Edit `generate_html.py` line ~125:
```python
main_concepts = analysis.get('main_concepts', [])[:8]  # Change 8 to desired number
```

## 🔧 Troubleshooting

### Images Not Displaying
- Check that `images/` folder is in same directory as HTML
- Or use absolute paths in HTML

### AI Not Expanding Content
- Verify API key in `.env.local`
- Check Gemini API quota/limits
- Review console for error messages

### Formulas Not Rendering
- Ensure internet connection (KaTeX loads from CDN)
- Check browser console for errors

### Extraction Taking Too Long
- Large PDFs (100+ pages) may take 1-2 minutes
- Progress is shown in terminal

## 📊 Example Output

For a 58-page lecture PDF:
- **Extraction time**: ~15 seconds
- **AI expansion**: ~2 minutes (6 concepts)
- **HTML size**: ~80KB (without embedded images)
- **Features**: 6 concepts, 18 quiz questions, interactive TOC

## 🎓 Educational Benefits

### Feynman Technique Applied
1. **Simple Explanation** - Forces clarity
2. **Identify Gaps** - AI spots missing examples
3. **Review & Simplify** - Multiple analogies provided
4. **Organize** - Structured progression

### Active Learning
- ✅ Self-testing with quizzes
- ✅ Spaced repetition ready
- ✅ Progress visualization
- ✅ AI tutor available

### Accessibility
- ✅ Keyboard navigation
- ✅ Screen reader friendly
- ✅ Adjustable font sizes
- ✅ High contrast mode

## 🚧 Future Enhancements

Planned features:
- [ ] Spaced repetition scheduler
- [ ] Anki flashcard export
- [ ] Progress persistence (localStorage)
- [ ] Collaborative notes
- [ ] Video embeds
- [ ] Audio narration
- [ ] Concept map visualization
- [ ] Live AI chat (real API integration)

## 📝 License

MIT License - Feel free to use for your studies!

## 🙏 Credits

- **PDF Processing**: PyMuPDF, pdfplumber
- **AI**: Google Gemini
- **Math Rendering**: KaTeX
- **Fonts**: Google Fonts (Inter, JetBrains Mono)
- **Inspiration**: Feynman Technique, Andy Matuschak's notes

## 📧 Support

Questions or issues? Check the troubleshooting section above or review the inline code comments.

---

**Happy Learning! 🎓✨**
