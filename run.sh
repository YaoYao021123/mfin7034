#!/bin/bash
# PDF to Interactive Learning - Complete Workflow

set -e  # Exit on error

echo "======================================"
echo "PDF to Interactive Learning Generator"
echo "======================================"
echo ""

# Check if PDF path provided
if [ -z "$1" ]; then
    echo "Usage: ./run.sh <pdf_file> [output_name]"
    echo ""
    echo "Examples:"
    echo "  ./run.sh 'pdfs/Lec 1 Fintech and Artificial Intelligence.pdf'"
    echo "  ./run.sh 'pdfs/Lec 2 Regression and Prediction ML.pdf' Lec2_ML"
    echo ""
    echo "Available PDFs:"
    ls -1 pdfs/*.pdf 2>/dev/null || echo "  (No PDFs found in pdfs/ directory)"
    exit 1
fi

PDF_PATH="$1"
PDF_NAME=$(basename "$PDF_PATH" .pdf)

# Determine output name
if [ -z "$2" ]; then
    OUTPUT_NAME="${PDF_NAME// /_}"
else
    OUTPUT_NAME="$2"
fi

EXTRACTED_DIR="extracted/$PDF_NAME"
OUTPUT_HTML="html/${OUTPUT_NAME}_interactive.html"

echo "📄 Input: $PDF_PATH"
echo "📁 Extraction dir: $EXTRACTED_DIR"
echo "🌐 Output HTML: $OUTPUT_HTML"
echo ""

# Step 1: Extract PDF content
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1/3: Extracting PDF content..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 extract_pdf.py "$PDF_PATH" "$EXTRACTED_DIR"

if [ $? -ne 0 ]; then
    echo "❌ Extraction failed!"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2/3: Analyzing with AI..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏳ This may take 1-2 minutes (calling Gemini API)..."
echo ""

# Step 2: Generate interactive HTML
python3 generate_html.py "$EXTRACTED_DIR" "$OUTPUT_HTML"

if [ $? -ne 0 ]; then
    echo "❌ HTML generation failed!"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3/4: Syncing lecture index..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 scripts/sync_lectures_json.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4/4: Starting local server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 3: Start local server with API proxy
echo "🌐 Opened via local server so API key stays in .env.local"
echo "📚 Portal: http://localhost:8000/html/index.html"
echo "🎯 Latest page: http://localhost:8000/$OUTPUT_HTML"
echo "🛑 Press Ctrl+C to stop the server"
python3 serve.py --open "html/index.html"

echo ""
echo "======================================"
echo "✅ Complete!"
echo "======================================"
echo ""
echo "📂 Files created:"
echo "   • $OUTPUT_HTML (interactive learning page)"
echo "   • $EXTRACTED_DIR/ (extracted content)"
echo ""
echo "🎯 Features included:"
echo "   ✓ Feynman-style explanations"
echo "   ✓ Interactive quizzes"
echo "   ✓ AI-expanded content"
echo "   ✓ Progress tracking"
echo "   ✓ AI study assistant"
echo ""
echo "💡 Tip: Keep using serve.py to enable AI chat securely."
echo ""
