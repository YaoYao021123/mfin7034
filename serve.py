#!/usr/bin/env python3
import argparse
import cgi
import html
import json
import os
import re
import shutil
import ssl
import subprocess
import tempfile
import threading
import webbrowser
from datetime import datetime
from http.client import RemoteDisconnected
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:
    certifi = None


# Global for tracking processing tasks
_processing_tasks: dict[str, dict] = {}


def update_processing_task(task_id: str, status: str, message: str, **extra) -> None:
    task = _processing_tasks.get(task_id)
    if task is None:
        return
    task["status"] = status
    task["message"] = message
    task.update(extra)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def normalize_open_path(raw_path: str) -> str:
    target = raw_path.strip().strip('"').strip("'").lstrip("/")
    target = re.sub(r"[^0-9A-Za-z._/\-]+$", "", target)
    return target


def normalize_asset_name(raw_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", raw_name.lower())


def build_course_badge(code: str, icon: str = "") -> str:
    normalized_code = (code or "").strip().upper()
    digit_groups = re.findall(r"\d{2,}", normalized_code)
    if digit_groups:
        return digit_groups[-1][-4:]

    letters = re.sub(r"[^A-Z]", "", normalized_code)
    if letters:
        return letters[:4]
    return "COUR"


def extract_html_title(html_file: Path, fallback: str) -> str:
    try:
        head = html_file.read_text(encoding="utf-8", errors="ignore")[:12000]
    except OSError:
        return fallback

    match = re.search(r"<title>\s*(.*?)\s*-\s*Interactive Learning\s*</title>", head, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return fallback

    title = re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()
    return title or fallback


def extract_pdf_title_from_file(pdf_file: Path, fallback: str) -> str:
    if not pdf_file or not pdf_file.exists():
        return fallback
    try:
        import extract_pdf as pdf_extractor
        import fitz

        with fitz.open(pdf_file) as doc:
            return pdf_extractor.derive_pdf_title(doc, str(pdf_file)) or fallback
    except Exception:
        return fallback


def write_course_lectures_json(base_dir: Path, course_id: str) -> list[dict]:
    lectures = build_lecture_list(base_dir, course_id)
    output_file = base_dir / "data" / course_id / "html" / "lectures.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps({"lectures": lectures, "count": len(lectures)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return lectures


def build_course_portal_html(course: dict) -> str:
    course_id = html.escape(course.get("id", ""))
    course_code = html.escape(course.get("code", "COURSE"))
    course_name = html.escape(course.get("name", course_code))
    school = html.escape(course.get("school", "").strip())
    description = html.escape(course.get("description", "").strip())
    badge_color = html.escape(course.get("color", "#f6c177"))
    subtitle = description or school or "Open lectures fast, continue notes, and add new PDFs from this course portal."
    subtitle = html.escape(subtitle)
    school_line = f"{course_code} • {school}" if school else course_code

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{course_code} - Lecture Portal</title>
    <link rel="stylesheet" href="../../../html/app-shell.css?v=16" />
    <style>
        :root {{
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-tertiary: #1f2b47;
            --bg-elevated: #263352;
            --bg-card: #1c2a45;
            --text-primary: #edf2f7;
            --text-secondary: #a0aec0;
            --text-tertiary: #718096;
            --accent-primary: {badge_color};
            --accent-secondary: #a3d9a5;
            --border-color: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(246, 193, 119, 0.35);
            --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.32);
            --shadow-lg: 0 14px 30px rgba(0, 0, 0, 0.4);
            --font-body: 'Georgia', 'Times New Roman', 'Noto Serif SC', serif;
            --font-heading: -apple-system, 'Helvetica Neue', 'PingFang SC', sans-serif;
            --glow-warm: rgba(246, 193, 119, 0.14);
        }}
        @media (prefers-color-scheme: light) {{
            :root {{
                --bg-primary: #faf8f5;
                --bg-secondary: #f0ece4;
                --bg-tertiary: #e8e2d8;
                --bg-elevated: #ffffff;
                --bg-card: #ffffff;
                --text-primary: #1c1917;
                --text-secondary: #57534e;
                --text-tertiary: #a8a29e;
                --border-color: rgba(0, 0, 0, 0.08);
                --border-hover: rgba(194, 116, 47, 0.3);
                --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
                --shadow-lg: 0 10px 24px rgba(0, 0, 0, 0.14);
                --glow-warm: rgba(194, 116, 47, 0.08);
            }}
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: var(--font-body);
            background: radial-gradient(50vw 50vw at 10% 10%, var(--glow-warm), transparent 70%), var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }}
        .container {{ max-width: 1180px; margin: 0 auto; padding: 32px 18px 124px; }}
        .breadcrumb {{ display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: var(--text-tertiary); font-family: var(--font-heading); margin-bottom: 20px; }}
        .breadcrumb a {{ color: var(--accent-primary); text-decoration: none; }}
        .breadcrumb a:hover {{ opacity: 0.8; }}
        .breadcrumb-sep {{ opacity: 0.5; }}
        .header {{ display: flex; gap: 14px; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; margin-bottom: 14px; }}
        .header-left {{ flex: 1; min-width: 280px; }}
        .course-code {{
            display: inline-block;
            font-family: var(--font-heading);
            font-size: 0.78rem;
            color: var(--accent-primary);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 4px 10px;
            background: rgba(246, 193, 119, 0.12);
            border: 1px solid rgba(246, 193, 119, 0.25);
            border-radius: 6px;
            margin-bottom: 12px;
        }}
        h1 {{
            font-family: var(--font-heading);
            font-size: clamp(2.5rem, 5.7vw, 4.45rem);
            line-height: 1.06;
            margin-bottom: 14px;
            letter-spacing: -0.03em;
            max-width: 980px;
        }}
        .sub {{ color: var(--text-secondary); max-width: 980px; line-height: 1.55; font-size: 1rem; margin-bottom: 28px; }}
        .toolbar {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
        .toolbar input {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 10px 12px;
            border-radius: 12px;
            min-width: min(320px, 78vw);
            box-shadow: var(--shadow-md), inset 0 1px 0 rgba(255,255,255,0.18);
            -webkit-backdrop-filter: blur(16px) saturate(145%);
            backdrop-filter: blur(16px) saturate(145%);
        }}
        .btn {{
            border: 1px solid var(--border-color);
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            padding: 9px 14px;
            border-radius: 12px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            font-family: var(--font-heading);
            font-size: 0.9rem;
            transition: border-color 0.18s ease, transform 0.18s ease;
            -webkit-backdrop-filter: blur(14px) saturate(135%);
            backdrop-filter: blur(14px) saturate(135%);
        }}
        .btn:hover {{ border-color: var(--border-hover); transform: translateY(-1px); }}
        .btn.primary {{
            border-color: rgba(246, 193, 119, 0.45);
            background: rgba(246, 193, 119, 0.12);
            color: var(--accent-primary);
        }}
        .stats {{ margin-top: 16px; color: var(--text-secondary); font-size: 0.9rem; }}
        .empty {{ margin-top: 20px; color: var(--text-tertiary); }}
        .grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
            margin-top: 16px;
            align-items: stretch;
        }}
        .card {{
            border: 1px solid var(--border-color);
            background:
                linear-gradient(145deg, rgba(255,255,255,0.11), rgba(255,255,255,0.02) 42%, rgba(255,255,255,0.01)),
                rgba(29, 42, 69, 0.58);
            border-radius: 16px;
            padding: 18px;
            box-shadow: var(--shadow-md);
            transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
            position: relative;
            overflow: hidden;
            -webkit-backdrop-filter: blur(22px) saturate(165%);
            backdrop-filter: blur(22px) saturate(165%);
            flex: 1 1 360px;
            max-width: 760px;
        }}
        .card:hover {{ border-color: var(--border-hover); transform: translateY(-2px); box-shadow: var(--shadow-lg); }}
        .card[data-context-target] {{ cursor: context-menu; }}
        .title {{ font-family: var(--font-heading); font-size: 1.04rem; font-weight: 650; line-height: 1.35; margin-bottom: 10px; }}
        .meta {{ color: var(--text-tertiary); font-size: 0.82rem; margin-bottom: 18px; }}
        .actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .actions .btn {{
            padding: 14px 28px;
            border-radius: 20px;
            font-size: 0.95rem;
            font-weight: 600;
        }}
        .actions .btn.open {{
            border-color: rgba(246, 193, 119, 0.45);
            background: rgba(246, 193, 119, 0.12);
            color: var(--accent-primary);
        }}
        .actions .btn.pdf {{
            border-color: rgba(163, 217, 165, 0.45);
            background: rgba(163, 217, 165, 0.12);
            color: var(--accent-secondary);
        }}
        .context-menu {{
            position: fixed;
            background: var(--bg-elevated);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 6px 0;
            min-width: 180px;
            box-shadow: var(--shadow-lg);
            z-index: 3000;
            display: none;
        }}
        .context-menu.is-open {{ display: block; }}
        .context-menu-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 16px;
            font-family: var(--font-heading);
            font-size: 0.85rem;
            color: var(--text-primary);
            cursor: pointer;
            transition: background 0.15s;
        }}
        .context-menu-item:hover {{ background: var(--bg-tertiary); }}
        .context-menu-item.danger {{ color: #ef4444; }}
        .context-menu-item.danger:hover {{ background: rgba(239, 68, 68, 0.1); }}
        .context-menu-divider {{ height: 1px; background: var(--border-color); margin: 6px 0; }}
        .toast-container {{
            position: fixed;
            bottom: 100px;
            right: 24px;
            z-index: 2500;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .toast {{
            background: var(--bg-elevated);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px 18px;
            box-shadow: var(--shadow-lg);
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 280px;
            max-width: 400px;
        }}
        .toast.success {{ border-left: 3px solid var(--accent-secondary); }}
        .toast.error {{ border-left: 3px solid #ef4444; }}
        .toast.loading {{ border-left: 3px solid var(--accent-primary); }}
        .toast-icon {{ width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; }}
        .toast-content {{ flex: 1; }}
        .toast-title {{ font-family: var(--font-heading); font-size: 0.9rem; font-weight: 600; margin-bottom: 2px; }}
        .toast-message {{ font-size: 0.8rem; color: var(--text-secondary); }}
        .toast-close {{ background: none; border: none; color: var(--text-tertiary); cursor: pointer; padding: 4px; font-size: 1.1rem; }}
        .toast-spinner {{
            width: 20px;
            height: 20px;
            border: 2px solid var(--border-color);
            border-top-color: var(--accent-primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        @media (prefers-color-scheme: light) {{
            .toolbar input, .btn {{
                background: rgba(255, 255, 255, 0.82);
                box-shadow: var(--shadow-md), inset 0 1px 0 rgba(255,255,255,0.8);
            }}
            .card {{
                background:
                    linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,255,255,0.68) 35%, rgba(255,255,255,0.62)),
                    rgba(255,255,255,0.78);
            }}
        }}
        @media (max-width: 720px) {{
            .toolbar {{ width: 100%; }}
            .toolbar input {{ min-width: 100%; width: 100%; }}
            .toolbar .btn {{ width: 100%; justify-content: center; }}
            .toast-container {{ right: 12px; left: 12px; }}
            .toast {{ min-width: 0; max-width: none; }}
            h1 {{ font-size: clamp(2rem, 12vw, 3rem); }}
            .actions .btn {{ width: auto; padding: 12px 22px; }}
        }}
    </style>
</head>
<body data-shell-page="portal" data-course-id="{course_id}">
    <div class="container">
        <nav class="breadcrumb">
            <a href="../../../">Platform Home</a>
            <span class="breadcrumb-sep">›</span>
            <span>{course_code}</span>
        </nav>

        <div class="header">
            <div class="header-left">
                <div class="course-code">{html.escape(school_line)}</div>
                <h1>{course_name}</h1>
                <div class="sub">{subtitle}</div>
            </div>
            <div class="toolbar">
                <input id="searchInput" type="text" placeholder="Search by lecture number or keyword..." />
                <button class="btn primary" id="addLectureBtn" type="button">+ Add Lecture</button>
                <input id="uploadInput" type="file" accept=".pdf" hidden />
            </div>
        </div>

        <div class="stats" id="stats">Syncing lecture index...</div>
        <div id="lectureGrid" class="grid"></div>
        <div id="empty" class="empty" style="display:none;">No lecture matched your search.</div>
    </div>

    <div class="context-menu" id="contextMenu">
        <div class="context-menu-item" data-action="open">Open Lecture</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item" data-action="copy">Copy Link</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item danger" data-action="delete">Delete Lecture</div>
    </div>

    <div class="toast-container" id="toastContainer"></div>

    <script>
        const COURSE_ID = document.body.dataset.courseId || '{course_id}';
        const uploadInput = document.getElementById('uploadInput');
        const contextMenu = document.getElementById('contextMenu');
        const toastContainer = document.getElementById('toastContainer');
        const statusLabel = {{
            queued: 'Queued in the background',
            extracting: 'Preparing files',
            extracting_content: 'Extracting PDF content',
            generating_html: 'Generating interactive HTML',
            complete: 'Lecture ready'
        }};
        let lectures = [];
        let contextTarget = null;

        const normalizePath = (href) => {{
            if (!href) return href;
            if (/^(https?:)?\\/\\//i.test(href)) return href;
            if (href.startsWith('./') || href.startsWith('../')) return href;
            return './' + href;
        }};

        function showToast(type, title, message, duration = 5000) {{
            const toast = document.createElement('div');
            toast.className = `toast ${{type}}`;
            const iconMap = {{ success: '[OK]', error: '[!]', loading: '' }};
            toast.innerHTML = `
                <div class="toast-icon">${{type === 'loading' ? '<div class="toast-spinner"></div>' : iconMap[type]}}</div>
                <div class="toast-content">
                    <div class="toast-title">${{title}}</div>
                    <div class="toast-message">${{message}}</div>
                </div>
                <button class="toast-close" type="button">&times;</button>
            `;
            toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());
            toastContainer.appendChild(toast);
            if (type !== 'loading' && duration > 0) {{
                setTimeout(() => toast.remove(), duration);
            }}
            return toast;
        }}

        function shouldUseNativeContextMenu(target) {{
            if (!target) return true;
            if (target.closest('input, textarea, [contenteditable="true"]')) {{
                return true;
            }}
            const selectedText = window.getSelection && window.getSelection().toString().trim();
            return Boolean(selectedText);
        }}

        function showContextMenu(event, lectureSlug) {{
            event.preventDefault();
            contextTarget = lectureSlug;
            contextMenu.style.left = event.pageX + 'px';
            contextMenu.style.top = event.pageY + 'px';
            contextMenu.classList.add('is-open');
        }}

        function hideContextMenu() {{
            contextMenu.classList.remove('is-open');
            contextTarget = null;
        }}

        function render(items) {{
            const grid = document.getElementById('lectureGrid');
            const empty = document.getElementById('empty');
            grid.innerHTML = items.map((lecture) => {{
                const pdfBtn = lecture.pdf_path
                    ? `<a class="btn pdf" target="_blank" href="${{normalizePath(lecture.pdf_path)}}">Open PDF</a>`
                    : '';
                const lectureHref = normalizePath(lecture.html_path);
                return `
                    <div class="card" data-context-target data-lecture-slug="${{lecture.slug}}">
                        <div class="title">${{lecture.title}}</div>
                        <div class="meta">Updated: ${{lecture.updated_at.replace('T', ' ')}}</div>
                        <div class="actions">
                            <a class="btn open" href="${{lectureHref}}" data-open-lecture="${{lectureHref}}">Open Interactive Page</a>
                            ${{pdfBtn}}
                        </div>
                    </div>
                `;
            }}).join('');
            empty.style.display = items.length ? 'none' : 'block';
            document.getElementById('stats').textContent = `${{items.length}} lecture(s) shown`;
        }}

        async function loadLectures() {{
            const stats = document.getElementById('stats');
            try {{
                const res = await fetch(`../../../api/lectures?course=${{encodeURIComponent(COURSE_ID)}}`);
                if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
                const data = await res.json();
                lectures = data.lectures || [];
                stats.textContent = `${{data.count || lectures.length}} lecture(s) loaded`;
                render(lectures);
            }} catch (error) {{
                try {{
                    const fallback = await fetch('./lectures.json');
                    if (!fallback.ok) throw new Error(`HTTP ${{fallback.status}}`);
                    const data = await fallback.json();
                    lectures = data.lectures || [];
                    stats.textContent = `${{data.count || lectures.length}} lecture(s) loaded (static mode)`;
                    render(lectures);
                }} catch (fallbackError) {{
                    stats.textContent = `Load failed: ${{fallbackError.message}}`;
                    lectures = [];
                    render([]);
                }}
            }}
        }}

        async function uploadPdf(file) {{
            if (!file || file.type !== 'application/pdf') {{
                showToast('error', 'Invalid File', 'Please select a PDF file.');
                return;
            }}

            const formData = new FormData();
            formData.append('file', file);
            formData.append('action', 'add_lecture');
            formData.append('course_id', COURSE_ID);

            const loadingToast = showToast('loading', 'Processing PDF...', 'Queued in the background', 0);

            try {{
                const uploadRes = await fetch('../../../api/upload', {{
                    method: 'POST',
                    body: formData
                }});
                const uploadData = await uploadRes.json();
                if (!uploadRes.ok) {{
                    throw new Error(uploadData.error || 'Upload failed');
                }}

                const taskId = uploadData.task_id;
                let completed = false;
                while (!completed) {{
                    await new Promise((resolve) => setTimeout(resolve, 2000));
                    const statusRes = await fetch(`../../../api/upload/status?task_id=${{encodeURIComponent(taskId)}}`);
                    const statusData = await statusRes.json();
                    if (!statusRes.ok) {{
                        throw new Error(statusData.error || `Status check failed (${{statusRes.status}})`);
                    }}

                    if (statusData.status === 'complete') {{
                        completed = true;
                        loadingToast.remove();
                        await loadLectures();
                        showToast('success', 'Lecture Ready', 'The new lecture has been added to this portal.', 7000);
                    }} else if (statusData.status === 'error') {{
                        throw new Error(statusData.error || 'Processing failed');
                    }} else {{
                        const message = statusData.message || statusLabel[statusData.status] || 'Still processing...';
                        const messageNode = loadingToast.querySelector('.toast-message');
                        if (messageNode) messageNode.textContent = message;
                    }}
                }}
            }} catch (error) {{
                loadingToast.remove();
                showToast('error', 'Upload Failed', error.message);
            }} finally {{
                uploadInput.value = '';
            }}
        }}

        document.getElementById('searchInput').addEventListener('input', (event) => {{
            const query = event.target.value.trim().toLowerCase();
            render(!query ? lectures : lectures.filter((lecture) => lecture.title.toLowerCase().includes(query)));
        }});

        document.getElementById('addLectureBtn').addEventListener('click', () => uploadInput.click());
        uploadInput.addEventListener('change', (event) => uploadPdf(event.target.files[0]));

        document.addEventListener('click', (event) => {{
            const link = event.target.closest('[data-open-lecture]');
            if (!link) return;
            localStorage.setItem('lecture-last-opened', link.getAttribute('data-open-lecture'));
        }});

        contextMenu.querySelectorAll('.context-menu-item').forEach((item) => {{
            item.addEventListener('click', async () => {{
                const lecture = lectures.find((entry) => entry.slug === contextTarget);
                const action = item.dataset.action;

                if (!lecture) {{
                    hideContextMenu();
                    return;
                }}

                if (action === 'open') {{
                    window.location.href = normalizePath(lecture.html_path);
                }} else if (action === 'copy') {{
                    const absoluteUrl = new URL(normalizePath(lecture.html_path), window.location.href);
                    navigator.clipboard.writeText(absoluteUrl.href);
                    showToast('success', 'Copied', 'Lecture link copied to clipboard');
                }} else if (action === 'delete') {{
                    if (confirm(`Delete "${{lecture.title}}"? This will move it to the recycle bin.`)) {{
                        const loadingToast = showToast('loading', 'Deleting...', 'Moving lecture to recycle bin', 0);
                        try {{
                            const response = await fetch('../../../api/recycle', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{
                                    target_type: 'lecture',
                                    course_id: COURSE_ID,
                                    lecture_slug: lecture.slug
                                }})
                            }});
                            const result = await response.json();
                            if (!response.ok) {{
                                throw new Error(result.error || 'Delete failed');
                            }}
                            loadingToast.remove();
                            await loadLectures();
                            showToast('success', 'Moved to Recycle Bin', result.message || 'Lecture deleted');
                        }} catch (error) {{
                            loadingToast.remove();
                            showToast('error', 'Delete Failed', error.message);
                        }}
                    }}
                }}
                hideContextMenu();
            }});
        }});

        document.addEventListener('click', hideContextMenu);
        document.addEventListener('contextmenu', (event) => {{
            if (shouldUseNativeContextMenu(event.target)) {{
                hideContextMenu();
                return;
            }}
            const card = event.target.closest('[data-context-target]');
            if (card) {{
                showContextMenu(event, card.dataset.lectureSlug);
            }} else {{
                hideContextMenu();
            }}
        }});

        loadLectures();
    </script>
    <script src="../../../html/app-shell.js?v=16"></script>
</body>
</html>
"""


def sync_course_portal_assets(base_dir: Path, course_id: str) -> None:
    courses = load_courses(base_dir)
    course = next((item for item in courses if item.get("id") == course_id), None)
    if course is None:
        return

    html_dir = base_dir / "data" / course_id / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    write_course_lectures_json(base_dir, course_id)
    (html_dir / "index.html").write_text(build_course_portal_html(course), encoding="utf-8")


def build_ssl_context() -> ssl.SSLContext:
    allow_insecure = os.getenv("GEMINI_INSECURE_SSL", "").lower() in {"1", "true", "yes"}
    if allow_insecure:
        return ssl._create_unverified_context()
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_courses(base_dir: Path) -> list[dict]:
    """Load courses from courses.json."""
    courses_file = base_dir / "courses" / "courses.json"
    if not courses_file.exists():
        return []
    try:
        data = json.loads(courses_file.read_text(encoding="utf-8"))
        return data.get("courses", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_courses(base_dir: Path, courses: list[dict]) -> None:
    """Save courses to courses.json."""
    courses_file = base_dir / "courses" / "courses.json"
    courses_file.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "courses": courses,
        "version": "1.0.0",
        "lastUpdated": datetime.now().isoformat(timespec="seconds"),
    }
    courses_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_recycle_root(base_dir: Path) -> Path:
    root = base_dir / ".recycle_bin"
    root.mkdir(parents=True, exist_ok=True)
    return root


def append_recycle_entry(base_dir: Path, entry: dict) -> None:
    recycle_root = get_recycle_root(base_dir)
    index_file = recycle_root / "index.json"
    payload = {"entries": [], "lastUpdated": ""}
    if index_file.exists():
        try:
            payload = json.loads(index_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            payload = {"entries": [], "lastUpdated": ""}

    payload.setdefault("entries", []).append(entry)
    payload["lastUpdated"] = datetime.now().isoformat(timespec="seconds")
    index_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def move_course_to_recycle_bin(base_dir: Path, course_id: str) -> dict:
    courses = load_courses(base_dir)
    course = next((item for item in courses if item.get("id") == course_id), None)
    if course is None:
        raise FileNotFoundError(f"Course not found: {course_id}")

    deleted_at = datetime.now().isoformat(timespec="seconds")
    course_dir = base_dir / "data" / course_id
    recycle_dir = get_recycle_root(base_dir) / "courses" / f"{deleted_at.replace(':', '-')}_{course_id}"
    recycle_dir.parent.mkdir(parents=True, exist_ok=True)

    if course_dir.exists():
        shutil.move(str(course_dir), str(recycle_dir))

    remaining_courses = [item for item in courses if item.get("id") != course_id]
    save_courses(base_dir, remaining_courses)

    append_recycle_entry(
        base_dir,
        {
            "type": "course",
            "course_id": course_id,
            "title": course.get("name") or course.get("code") or course_id,
            "deleted_at": deleted_at,
            "recycled_path": str(recycle_dir.relative_to(base_dir)) if recycle_dir.exists() else "",
        },
    )
    return course


def move_lecture_to_recycle_bin(base_dir: Path, course_id: str, lecture_slug: str) -> dict:
    lectures = build_lecture_list(base_dir, course_id)
    lecture = next((item for item in lectures if item.get("slug") == lecture_slug), None)
    if lecture is None:
        raise FileNotFoundError(f"Lecture not found: {lecture_slug}")

    deleted_at = datetime.now().isoformat(timespec="seconds")
    course_dir = base_dir / "data" / course_id
    html_file = course_dir / "html" / f"{lecture_slug}_interactive.html"
    pdf_file = course_dir / "pdfs" / Path(lecture.get("pdf_path") or "").name if lecture.get("pdf_path") else None
    recycle_dir = get_recycle_root(base_dir) / "lectures" / course_id / f"{deleted_at.replace(':', '-')}_{lecture_slug}"
    recycle_dir.mkdir(parents=True, exist_ok=True)

    if html_file.exists():
        shutil.move(str(html_file), str(recycle_dir / html_file.name))
    if pdf_file and pdf_file.exists():
        shutil.move(str(pdf_file), str(recycle_dir / pdf_file.name))

    courses = load_courses(base_dir)
    for course in courses:
        if course.get("id") == course_id:
            course["lectureCount"] = len(build_lecture_list(base_dir, course_id))
            course["updatedAt"] = deleted_at
            break
    save_courses(base_dir, courses)
    sync_course_portal_assets(base_dir, course_id)

    append_recycle_entry(
        base_dir,
        {
            "type": "lecture",
            "course_id": course_id,
            "lecture_slug": lecture_slug,
            "title": lecture.get("title") or lecture_slug,
            "deleted_at": deleted_at,
            "recycled_path": str(recycle_dir.relative_to(base_dir)),
        },
    )
    return lecture


def build_lecture_list(base_dir: Path, course_id: str | None = None) -> list[dict]:
    """Build lecture list for a specific course or legacy structure."""
    if course_id:
        # New multi-course structure
        course_dir = base_dir / "data" / course_id
        html_dir = course_dir / "html"
        pdf_dir = course_dir / "pdfs"
    else:
        # Legacy single-course structure
        html_dir = base_dir / "html"
        pdf_dir = base_dir / "pdfs"
    
    if not html_dir.exists():
        return []

    def sort_key(path: Path):
        match = re.search(r"^Lec[_ ]?(\d+)", path.stem, flags=re.IGNORECASE)
        lecture_no = int(match.group(1)) if match else 9999
        return (lecture_no, path.stem.lower())

    pdf_index: dict[str, Path] = {}
    if pdf_dir.exists():
        for pdf_file in pdf_dir.glob("*.pdf"):
            pdf_index.setdefault(normalize_asset_name(pdf_file.stem), pdf_file)

    lectures = []
    for html_file in sorted(html_dir.glob("*_interactive.html"), key=sort_key):
        stem = html_file.stem.removesuffix("_interactive")
        normalized = normalize_asset_name(stem)
        pdf_file = pdf_index.get(normalized)
        if pdf_file is None:
            guessed_pdf = pdf_dir / f"{stem.replace('_', ' ')}.pdf"
            if guessed_pdf.exists():
                pdf_file = guessed_pdf
        fallback_title = stem.replace("_", " ")
        display_title = extract_html_title(html_file, fallback_title)
        if re.fullmatch(r"upload[_ ]\d{8,}[_ ]\d+", display_title, flags=re.IGNORECASE) and pdf_file is not None:
            display_title = extract_pdf_title_from_file(pdf_file, display_title)
        lectures.append(
            {
                "title": display_title,
                "slug": stem,
                "html_path": f"./{html_file.name}",
                "pdf_path": f"../pdfs/{pdf_file.name}" if pdf_file else None,
                "updated_at": datetime.fromtimestamp(html_file.stat().st_mtime).isoformat(timespec="seconds"),
            }
        )
    return lectures


def process_pdf_upload(base_dir: Path, pdf_path: Path, course_id: str, task_id: str) -> None:
    """Process uploaded PDF in background thread."""
    global _processing_tasks
    
    try:
        update_processing_task(task_id, "extracting", "Preparing uploaded PDF")
        
        # Determine output directories
        course_dir = base_dir / "data" / course_id
        html_dir = course_dir / "html"
        pdf_dir = course_dir / "pdfs"
        
        html_dir.mkdir(parents=True, exist_ok=True)
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy PDF to course pdfs directory
        pdf_dest = pdf_dir / pdf_path.name
        shutil.copy2(pdf_path, pdf_dest)
        
        # Create extracted content directory
        pdf_stem = pdf_path.stem
        extracted_dir = base_dir / "extracted" / pdf_stem
        extracted_dir.mkdir(parents=True, exist_ok=True)
        
        # Run extract_pdf.py
        update_processing_task(task_id, "extracting_content", "Extracting PDF structure and title")
        extract_result = subprocess.run(
            ["python3", str(base_dir / "extract_pdf.py"), str(pdf_dest), str(extracted_dir)],
            cwd=str(base_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        if extract_result.returncode != 0:
            update_processing_task(
                task_id,
                "error",
                "PDF extraction failed",
                error=f"Extraction failed: {extract_result.stderr or extract_result.stdout}",
            )
            return
        
        # Run generate_html.py
        update_processing_task(task_id, "generating_html", "Generating interactive HTML")
        generate_result = subprocess.run(
            ["python3", str(base_dir / "generate_html.py"), str(extracted_dir), "--output", str(html_dir)],
            cwd=str(base_dir),
            capture_output=True,
            text=True,
            timeout=600,
        )
        
        if generate_result.returncode != 0:
            update_processing_task(
                task_id,
                "error",
                "Interactive HTML generation failed",
                error=f"HTML generation failed: {generate_result.stderr or generate_result.stdout}",
            )
            return
        
        # Update course lecture count
        courses = load_courses(base_dir)
        for course in courses:
            if course["id"] == course_id:
                lectures = build_lecture_list(base_dir, course_id)
                course["lectureCount"] = len(lectures)
                course["updatedAt"] = datetime.now().isoformat(timespec="seconds")
                course["icon"] = build_course_badge(course.get("code", ""), course.get("icon", ""))
                break
        save_courses(base_dir, courses)
        sync_course_portal_assets(base_dir, course_id)

        newest_html = None
        html_candidates = list(html_dir.glob("*_interactive.html"))
        if html_candidates:
            newest_html = max(html_candidates, key=lambda path: path.stat().st_mtime)
        
        update_processing_task(
            task_id,
            "complete",
            "Lecture is ready",
            redirect=f"./data/{course_id}/html/index.html",
            latest_lecture=f"./data/{course_id}/html/{newest_html.name}" if newest_html else None,
        )
        
    except subprocess.TimeoutExpired:
        update_processing_task(task_id, "error", "Processing timed out", error="Processing timed out")
    except Exception as e:
        update_processing_task(task_id, "error", "Processing failed", error=str(e))
    finally:
        # Clean up temp file if exists
        if pdf_path.exists() and str(pdf_path).startswith(tempfile.gettempdir()):
            try:
                pdf_path.unlink()
            except Exception:
                pass


class ProxyHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/") or path.endswith((".html", ".js", ".css", ".webmanifest")):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def parse_query_params(self) -> dict[str, str]:
        """Parse query string parameters."""
        query = self.path.split("?", 1)[1] if "?" in self.path else ""
        params = {}
        for pair in query.split("&"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                params[key] = value
        return params

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        params = self.parse_query_params()
        
        # GET /api/courses - List all courses
        if path == "/api/courses":
            courses = load_courses(Path.cwd())
            self.send_json({"courses": courses, "count": len(courses)}, 200)
            return
        
        # GET /api/lectures - List lectures (optionally filtered by course)
        if path == "/api/lectures":
            course_id = params.get("course")
            lectures = build_lecture_list(Path.cwd(), course_id)
            self.send_json({"lectures": lectures, "count": len(lectures)}, 200)
            return
        
        # GET /api/upload/status - Check upload processing status
        if path == "/api/upload/status":
            task_id = params.get("task_id", "")
            if task_id in _processing_tasks:
                self.send_json(_processing_tasks[task_id], 200)
            else:
                self.send_json({"error": "Task not found"}, 404)
            return
        
        super().do_GET()

    def do_OPTIONS(self):
        api_paths = ["/api/gemini", "/api/upload", "/api/courses", "/api/recycle"]
        if not any(self.path.startswith(p) for p in api_paths):
            self.send_error(404, "Not Found")
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        
        # POST /api/upload - Upload PDF file
        if path == "/api/upload":
            self.handle_upload()
            return
        
        # POST /api/courses - Create new course
        if path == "/api/courses":
            self.handle_create_course()
            return

        # POST /api/recycle - Move a course or lecture to recycle bin
        if path == "/api/recycle":
            self.handle_recycle_request()
            return
        
        # POST /api/gemini - Proxy to Gemini API
        if path != "/api/gemini":
            self.send_error(404, "Not Found")
            return
        
        self.handle_gemini_proxy()

    def handle_upload(self):
        """Handle PDF file upload."""
        global _processing_tasks
        
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_json({"error": "Expected multipart/form-data"}, 400)
            return
        
        # Parse multipart form data
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": content_type,
                },
            )
        except Exception as e:
            self.send_json({"error": f"Failed to parse form data: {e}"}, 400)
            return
        
        # Get uploaded file
        if "file" not in form:
            self.send_json({"error": "No file uploaded"}, 400)
            return
        
        file_item = form["file"]
        if not file_item.filename:
            self.send_json({"error": "No file selected"}, 400)
            return
        
        if not file_item.filename.lower().endswith(".pdf"):
            self.send_json({"error": "Only PDF files are accepted"}, 400)
            return
        
        # Get action and course info
        action = form.getvalue("action", "add_to_course")
        course_id = form.getvalue("course_id", "")
        
        base_dir = Path.cwd()
        
        # Handle new course creation
        if action == "new_course":
            course_code = form.getvalue("course_code", "").strip()
            course_name = form.getvalue("course_name", "").strip()
            course_desc = form.getvalue("course_desc", "").strip()
            
            if not course_code or not course_name:
                self.send_json({"error": "Course code and name are required"}, 400)
                return
            
            course_id = slugify(course_code)
            
            # Create course
            courses = load_courses(base_dir)
            if any(c["id"] == course_id for c in courses):
                self.send_json({"error": f"Course {course_code} already exists"}, 400)
                return
            
            new_course = {
                "id": course_id,
                "code": course_code.upper(),
                "name": course_name,
                "description": course_desc,
                "school": "",
                "color": "#f6c177",
                "icon": build_course_badge(course_code),
                "lectureCount": 0,
                "createdAt": datetime.now().isoformat(timespec="seconds"),
                "updatedAt": datetime.now().isoformat(timespec="seconds"),
            }
            courses.append(new_course)
            save_courses(base_dir, courses)
            
            # Create course directories
            course_dir = base_dir / "data" / course_id
            (course_dir / "html").mkdir(parents=True, exist_ok=True)
            (course_dir / "pdfs").mkdir(parents=True, exist_ok=True)
            sync_course_portal_assets(base_dir, course_id)
        
        elif not course_id:
            self.send_json({"error": "Course ID is required"}, 400)
            return
        
        # Save uploaded file to temp location with clean name derived from original filename
        original_name = Path(file_item.filename).stem
        # Clean up the filename to use as base name (remove common prefixes/suffixes)
        clean_name = re.sub(r'^(upload_\d+_|Lecture_?\d*_?|Slides?[-_]?\d*[-_]?)', '', original_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'[-_]+', '_', clean_name).strip('_')
        if not clean_name:
            clean_name = original_name
        # Use cleaned name for the temp file
        temp_dir = Path(tempfile.gettempdir())
        temp_pdf = temp_dir / f"{clean_name}.pdf"
        
        try:
            with open(temp_pdf, "wb") as f:
                f.write(file_item.file.read())
        except Exception as e:
            self.send_json({"error": f"Failed to save file: {e}"}, 500)
            return
        
        # Create processing task
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        _processing_tasks[task_id] = {
            "status": "queued",
            "message": "Queued in the background",
            "course_id": course_id,
            "filename": file_item.filename,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        
        # Start background processing
        thread = threading.Thread(
            target=process_pdf_upload,
            args=(base_dir, temp_pdf, course_id, task_id),
            daemon=True,
        )
        thread.start()
        
        # Return task ID for polling
        self.send_json({
            "task_id": task_id,
            "status": "processing",
            "message": "Upload received, processing started",
            "redirect": f"./data/{course_id}/html/index.html",
        }, 202)

    def handle_create_course(self):
        """Handle course creation."""
        content_length = int(self.headers.get("Content-Length", "0"))
        body_bytes = self.rfile.read(content_length)
        
        try:
            payload = json.loads(body_bytes or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON payload"}, 400)
            return
        
        code = payload.get("code", "").strip()
        name = payload.get("name", "").strip()
        description = payload.get("description", "").strip()
        
        if not code or not name:
            self.send_json({"error": "Course code and name are required"}, 400)
            return
        
        base_dir = Path.cwd()
        course_id = slugify(code)
        
        courses = load_courses(base_dir)
        if any(c["id"] == course_id for c in courses):
            self.send_json({"error": f"Course {code} already exists"}, 400)
            return
        
        new_course = {
            "id": course_id,
            "code": code.upper(),
            "name": name,
            "description": description,
            "school": payload.get("school", ""),
            "color": payload.get("color", "#f6c177"),
            "icon": build_course_badge(code, payload.get("icon", "")),
            "lectureCount": 0,
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "updatedAt": datetime.now().isoformat(timespec="seconds"),
        }
        courses.append(new_course)
        save_courses(base_dir, courses)
        
        # Create directories
        course_dir = base_dir / "data" / course_id
        (course_dir / "html").mkdir(parents=True, exist_ok=True)
        (course_dir / "pdfs").mkdir(parents=True, exist_ok=True)
        sync_course_portal_assets(base_dir, course_id)
        
        self.send_json({"course": new_course, "message": "Course created successfully"}, 201)

    def handle_recycle_request(self):
        """Handle recycle-bin deletion requests."""
        content_length = int(self.headers.get("Content-Length", "0"))
        body_bytes = self.rfile.read(content_length)

        try:
            payload = json.loads(body_bytes or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON payload"}, 400)
            return

        target_type = payload.get("target_type", "").strip()
        course_id = payload.get("course_id", "").strip()
        base_dir = Path.cwd()

        if not course_id:
            self.send_json({"error": "course_id is required"}, 400)
            return

        try:
            if target_type == "course":
                course = move_course_to_recycle_bin(base_dir, course_id)
                self.send_json(
                    {
                        "message": f'Moved course "{course.get("name") or course_id}" to recycle bin.',
                        "target_type": "course",
                        "course_id": course_id,
                    },
                    200,
                )
                return

            if target_type == "lecture":
                lecture_slug = payload.get("lecture_slug", "").strip()
                if not lecture_slug:
                    self.send_json({"error": "lecture_slug is required for lecture deletion"}, 400)
                    return
                lecture = move_lecture_to_recycle_bin(base_dir, course_id, lecture_slug)
                self.send_json(
                    {
                        "message": f'Moved lecture "{lecture.get("title") or lecture_slug}" to recycle bin.',
                        "target_type": "lecture",
                        "course_id": course_id,
                        "lecture_slug": lecture_slug,
                    },
                    200,
                )
                return

            self.send_json({"error": "Unsupported target_type"}, 400)
        except FileNotFoundError as error:
            self.send_json({"error": str(error)}, 404)
        except Exception as error:
            self.send_json({"error": str(error)}, 500)

    def handle_gemini_proxy(self):
        """Proxy requests to Gemini API."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.send_json(
                {"error": "GEMINI_API_KEY missing. Put it in .env.local before starting server."},
                500,
            )
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body_bytes = self.rfile.read(content_length)
        try:
            payload = json.loads(body_bytes or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON payload."}, 400)
            return

        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            self.send_json({"error": "Request must include non-empty 'prompt'."}, 400)
            return

        generation_config = payload.get("generationConfig")
        if not isinstance(generation_config, dict):
            generation_config = {"temperature": 0.7, "maxOutputTokens": 1024}

        model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        request_body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        gemini_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        )
        req = Request(
            gemini_url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(req, timeout=90, context=build_ssl_context()) as resp:
                response_bytes = resp.read()
                status_code = resp.status
        except ssl.SSLCertVerificationError as err:
            self.send_json(
                {
                    "error": (
                        "Gemini SSL verification failed. Install local Python certificates "
                        "or set GEMINI_INSECURE_SSL=1 for local testing only. "
                        f"Details: {err}"
                    )
                },
                502,
            )
            return
        except RemoteDisconnected as err:
            self.send_json({"error": f"Gemini request failed: remote server disconnected ({err})."}, 502)
            return
        except HTTPError as err:
            response_bytes = err.read()
            if not response_bytes:
                response_bytes = json.dumps({"error": f"Gemini API error {err.code}"}).encode("utf-8")
            status_code = err.code
        except URLError as err:
            if isinstance(err.reason, ssl.SSLCertVerificationError):
                self.send_json(
                    {
                        "error": (
                            "Gemini SSL verification failed. Install local Python certificates "
                            "or set GEMINI_INSECURE_SSL=1 for local testing only. "
                            f"Details: {err.reason}"
                        )
                    },
                    502,
                )
                return
            self.send_json({"error": f"Gemini request failed: {err.reason}"}, 502)
            return

        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def send_json(self, payload: dict, status_code: int) -> None:
        response_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve static files and proxy Gemini requests.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument(
        "--open",
        dest="open_path",
        default="",
        help="Open this relative path in browser after startup, e.g. html/index.html",
    )
    args = parser.parse_args()

    load_env_file(Path(".env.local"))

    server = ThreadingHTTPServer(("0.0.0.0", args.port), ProxyHandler)
    print(f"[OK] Serving at http://localhost:{args.port}")
    print("   Gemini proxy endpoint: POST /api/gemini")
    if args.open_path:
        target = normalize_open_path(args.open_path) or "html/index.html"
        if not Path(target).exists():
            print(f"[WARN] Open path not found: {args.open_path} -> {target}; opening root instead.")
            target = ""
        open_url = f"http://localhost:{args.port}/" + target
        print(f"   Opening: {open_url}")
        webbrowser.open_new_tab(open_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
