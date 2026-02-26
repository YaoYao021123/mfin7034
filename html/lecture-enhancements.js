(() => {
  const SHELL_VERSION = '10';
  const getBasePrefix = () => {
    const lower = window.location.pathname.toLowerCase();
    const idx = lower.indexOf('/html/');
    return idx >= 0 ? window.location.pathname.slice(0, idx) : '';
  };
  const withBase = (path) => `${getBasePrefix()}${path}`;

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderMd(text) {
    const lines = String(text || '').split('\n');
    const html = [];
    let inList = false;
    for (const lineRaw of lines) {
      const line = lineRaw.trimEnd();
      if (/^\s*[-*]\s+/.test(line)) {
        if (!inList) {
          html.push('<ul>');
          inList = true;
        }
        const item = line.replace(/^\s*[-*]\s+/, '');
        html.push(`<li>${escapeHtml(item)
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.+?)\*/g, '<em>$1</em>')
          .replace(/`(.+?)`/g, '<code>$1</code>')}</li>`);
        continue;
      }
      if (inList) {
        html.push('</ul>');
        inList = false;
      }
      if (/^###\s+/.test(line)) {
        html.push(`<h4>${escapeHtml(line.replace(/^###\s+/, ''))}</h4>`);
      } else if (/^##\s+/.test(line)) {
        html.push(`<h3>${escapeHtml(line.replace(/^##\s+/, ''))}</h3>`);
      } else if (/^#\s+/.test(line)) {
        html.push(`<h2>${escapeHtml(line.replace(/^#\s+/, ''))}</h2>`);
      } else if (!line.trim()) {
        html.push('<br>');
      } else {
        html.push(`<p>${escapeHtml(line)
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.+?)\*/g, '<em>$1</em>')
          .replace(/`(.+?)`/g, '<code>$1</code>')}</p>`);
      }
    }
    if (inList) html.push('</ul>');
    return html.join('');
  }

  function notesStorageKey() {
    return 'learning-notes-' + document.title;
  }

  function loadNotes() {
    try {
      const value = JSON.parse(localStorage.getItem(notesStorageKey()) || '[]');
      return Array.isArray(value) ? value : [];
    } catch {
      return [];
    }
  }

  function saveNotes(notes) {
    localStorage.setItem(notesStorageKey(), JSON.stringify(notes || []));
  }

  function activeNoteId() {
    const raw = localStorage.getItem(notesStorageKey() + '-active');
    const id = Number(raw);
    return Number.isFinite(id) ? id : null;
  }

  function setActiveNoteId(id) {
    if (!id) localStorage.removeItem(notesStorageKey() + '-active');
    else localStorage.setItem(notesStorageKey() + '-active', String(id));
  }

  function focusAIInput() {
    document.getElementById('aiInput')?.focus();
    document.querySelector('.sidebar-right')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function triggerSummary() {
    if (typeof window.createSummary === 'function') return window.createSummary();
    if (typeof window.askSummary === 'function') return window.askSummary();
  }

  function ensureOverlayStyle() {
    if (document.getElementById('notesFocusOverlayStyle')) return;
    const style = document.createElement('style');
    style.id = 'notesFocusOverlayStyle';
    style.textContent = `
      .notes-focus-overlay { position: fixed; inset: 0; background: rgba(8,12,24,0.55); backdrop-filter: blur(4px); z-index: 10020; display: none; align-items: center; justify-content: center; padding: 1rem; }
      .notes-focus-overlay.show { display: flex; }
      .notes-focus-modal { width: min(760px, 96vw); max-height: 82vh; overflow: auto; background: var(--bg-card, #1c2a45); border: 1px solid var(--border-color, rgba(255,255,255,0.12)); border-radius: 14px; box-shadow: 0 24px 50px rgba(0,0,0,0.35); padding: 1rem; }
      .notes-focus-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:.75rem; font-family: var(--font-heading, sans-serif); }
      .notes-focus-close { border:1px solid var(--border-color, rgba(255,255,255,0.2)); background:transparent; color:var(--text-secondary,#a0aec0); border-radius:8px; padding:.3rem .6rem; cursor:pointer; }
      .notes-focus-body { color: var(--text-secondary,#a0aec0); line-height:1.65; }
      .notes-focus-body code { background: var(--bg-tertiary,#1f2b47); padding: 0.1em 0.35em; border-radius: 4px; }
      .shortcut-clickable { cursor:pointer; user-select:none; }
      .shortcut-clickable:hover { color: var(--accent-primary,#f6c177); }
      .inline-note-editor { position: absolute; z-index: 10030; width: min(420px, 90vw); background: var(--bg-card,#1c2a45); border:1px solid var(--border-color, rgba(255,255,255,0.16)); border-radius: 12px; box-shadow: 0 16px 36px rgba(0,0,0,0.32); padding: .65rem; }
      .inline-note-editor textarea { width:100%; min-height: 88px; background: var(--bg-primary,#1a1a2e); color: var(--text-primary,#edf2f7); border:1px solid var(--border-color, rgba(255,255,255,0.14)); border-radius:8px; padding:.5rem; font-size:.86rem; resize: vertical; }
      .inline-note-actions { display:flex; justify-content:flex-end; gap:.45rem; margin-top:.45rem; }
      .inline-note-actions button { border:1px solid var(--border-color, rgba(255,255,255,0.16)); background: var(--bg-elevated,#263352); color: var(--text-primary,#edf2f7); border-radius:8px; padding:.3rem .6rem; cursor:pointer; font-size:.8rem; }
      .inline-note-actions .save { border-color: rgba(163,217,165,.55); color: var(--accent-secondary,#a3d9a5); }
    `;
    document.head.appendChild(style);
  }

  function ensureOverlay() {
    ensureOverlayStyle();
    let overlay = document.getElementById('notesFocusOverlay');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'notesFocusOverlay';
    overlay.className = 'notes-focus-overlay';
    overlay.innerHTML = `
      <div class="notes-focus-modal">
        <div class="notes-focus-head">
          <strong>Notes Focus</strong>
          <button class="notes-focus-close" type="button" id="notesFocusCloseBtn">Close</button>
        </div>
        <div class="notes-focus-body" id="notesFocusBody">No notes yet.</div>
      </div>
    `;
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.remove('show');
    });
    overlay.querySelector('#notesFocusCloseBtn')?.addEventListener('click', () => {
      overlay.classList.remove('show');
    });
    document.body.appendChild(overlay);
    return overlay;
  }

  function renderOverlayBody() {
    const overlay = ensureOverlay();
    const body = overlay.querySelector('#notesFocusBody');
    const notes = loadNotes();
    const activeId = activeNoteId();
    const active = notes.find((n) => Number(n?.id) === activeId) || notes[notes.length - 1] || null;
    const activeBody = active?.body || active?.text || '';
    const citation = active?.citation ? `<div style="margin-bottom:.5rem; color:var(--text-tertiary,#718096); font-style:italic;">${escapeHtml(active.citation)}</div>` : '';
    const noteOptions = notes.map((n) => {
      const id = Number(n?.id);
      const label = (n?.section || 'General') + ' • ' + new Date(n?.timestamp || Date.now()).toLocaleString();
      const selected = active && Number(active.id) === id ? 'selected' : '';
      return `<option value="${id}" ${selected}>${escapeHtml(label)}</option>`;
    }).join('');
    body.innerHTML = `
      <div style="display:flex; gap:.45rem; align-items:center; margin-bottom:.55rem;">
        <select id="notesFocusSelect" style="flex:1; min-width:0; background:var(--bg-primary,#1a1a2e); color:var(--text-primary,#edf2f7); border:1px solid var(--border-color, rgba(255,255,255,0.14)); border-radius:8px; padding:.35rem .45rem;">
          ${noteOptions || '<option value="">No note selected</option>'}
        </select>
        <button id="notesFocusNewBtn" type="button" class="notes-focus-close">New</button>
      </div>
      ${citation}
      <textarea id="notesFocusEditor" style="width:100%; min-height:120px; background:var(--bg-primary,#1a1a2e); color:var(--text-primary,#edf2f7); border:1px solid var(--border-color, rgba(255,255,255,0.14)); border-radius:8px; padding:.55rem; font-size:.92rem; resize:vertical;">${escapeHtml(activeBody)}</textarea>
      <div style="display:flex; justify-content:flex-end; margin-top:.5rem;">
        <button id="notesFocusSaveBtn" type="button" class="notes-focus-close" style="border-color:rgba(163,217,165,.55); color:var(--accent-secondary,#a3d9a5);">Save Note</button>
      </div>
      <div style="font-size:.78rem; color:var(--text-tertiary,#718096); margin:.6rem 0 .35rem;">Preview</div>
      <div id="notesFocusPreview">${renderMd(activeBody)}</div>
    `;
    const editor = body.querySelector('#notesFocusEditor');
    const preview = body.querySelector('#notesFocusPreview');
    const select = body.querySelector('#notesFocusSelect');
    editor?.addEventListener('input', () => {
      if (preview) preview.innerHTML = renderMd(editor.value);
    });
    select?.addEventListener('change', () => {
      const id = Number(select.value);
      setActiveNoteId(id || null);
      renderOverlayBody();
    });
    body.querySelector('#notesFocusNewBtn')?.addEventListener('click', () => {
      const all = loadNotes();
      const note = {
        id: Date.now(),
        citation: '',
        body: '',
        section: 'General',
        timestamp: new Date().toISOString()
      };
      all.push(note);
      saveNotes(all);
      setActiveNoteId(note.id);
      if (typeof window.renderNotes === 'function') window.renderNotes();
      renderOverlayBody();
    });
    body.querySelector('#notesFocusSaveBtn')?.addEventListener('click', () => {
      let currentId = Number(select?.value || active?.id);
      if (!Number.isFinite(currentId) || !currentId) {
        const created = {
          id: Date.now(),
          citation: '',
          body: editor?.value || '',
          section: 'General',
          timestamp: new Date().toISOString()
        };
        const withNew = loadNotes();
        withNew.push(created);
        saveNotes(withNew);
        setActiveNoteId(created.id);
        if (typeof window.renderNotes === 'function') window.renderNotes();
        overlay.classList.remove('show');
        return;
      }
      const updated = loadNotes().map((n) => {
        if (Number(n?.id) === currentId) {
          return { ...n, body: editor?.value || '' };
        }
        return n;
      });
      saveNotes(updated);
      setActiveNoteId(currentId);
      if (typeof window.renderNotes === 'function') window.renderNotes();
      overlay.classList.remove('show');
    });
  }

  function openNotesFocusModal() {
    if (typeof window.switchSidebarTab === 'function') window.switchSidebarTab('notes');
    renderOverlayBody();
    ensureOverlay().classList.add('show');
  }

  function addFocusNotesButton() {
    if (document.getElementById('focusNotesActionBtn')) return;
    const headerRow = document.getElementById('notesCount')?.parentElement;
    if (!headerRow) return;
    const exportBtn = headerRow.querySelector('button');
    if (!exportBtn) return;
    let rightGroup = headerRow.querySelector('.notes-header-actions');
    if (!rightGroup) {
      rightGroup = document.createElement('div');
      rightGroup.className = 'notes-header-actions';
      rightGroup.style.display = 'flex';
      rightGroup.style.gap = '0.4rem';
      exportBtn.replaceWith(rightGroup);
      rightGroup.appendChild(exportBtn);
    }
    const btn = document.createElement('button');
    btn.id = 'focusNotesActionBtn';
    btn.type = 'button';
    btn.className = 'action-btn';
    btn.style.width = 'auto';
    btn.style.padding = '0.4rem 0.75rem';
    btn.style.fontSize = '0.8rem';
    btn.textContent = 'Focus+Edit';
    btn.addEventListener('click', openNotesFocusModal);
    rightGroup.appendChild(btn);
  }

  function bindShortcutClicks() {
    const focusShortcut = document.getElementById('shortcutFocusAI')?.parentElement;
    if (focusShortcut) {
      focusShortcut.classList.add('shortcut-clickable');
      focusShortcut.onclick = focusAIInput;
    }
    const summaryShortcut = document.getElementById('shortcutSummary')?.parentElement;
    if (summaryShortcut) {
      summaryShortcut.classList.add('shortcut-clickable');
      summaryShortcut.onclick = triggerSummary;
    }
  }

  function inferShellPage() {
    const lower = window.location.pathname.toLowerCase();
    if (document.body?.dataset?.shellPage) return document.body.dataset.shellPage;
    if (lower.endsWith('/html/index.html') || lower === '/') return 'portal';
    if (lower.includes('interactive')) return 'lecture';
    return '';
  }

  function buildFallbackNav(page) {
    if (document.querySelector('.ios26-shell')) return;
    const items = page === 'portal'
      ? [
          { id: 'home', label: 'Home', icon: '⌂', onClick: () => (window.location.href = withBase('/html/index.html')) },
          { id: 'search', label: 'Search', icon: '⌕', onClick: () => document.getElementById('searchInput')?.focus() },
          { id: 'latest', label: 'Latest', icon: '⟲', onClick: () => { const href = localStorage.getItem('lecture-last-opened'); if (!href) return; window.location.href = href.startsWith('/') ? `${withBase(href)}` : href; } },
          { id: 'demo', label: 'Demo', icon: '◈', onClick: () => (window.location.href = withBase('/demo.html')) },
        ]
      : [
          { id: 'home', label: 'Portal', icon: '⌂', onClick: () => (window.location.href = withBase('/html/index.html')) },
          { id: 'pdf', label: 'PDF', icon: '▣', onClick: () => window.switchSidebarTab?.('pdf') },
          { id: 'notes', label: 'Notes', icon: '✎', onClick: () => window.switchSidebarTab?.('notes') },
          { id: 'ai', label: 'AI', icon: '✦', onClick: () => focusAIInput() },
        ];
    const nav = document.createElement('nav');
    nav.className = 'ios26-shell';
    nav.setAttribute('aria-label', 'Bottom navigation');
    const inner = document.createElement('div');
    inner.className = 'ios26-shell__inner';
    items.forEach((item, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ios26-shell__btn';
      if (idx === 0) btn.classList.add('is-active');
      btn.innerHTML = `<span class="ios26-shell__icon">${item.icon}</span><span class="ios26-shell__label">${item.label}</span>`;
      btn.addEventListener('click', () => {
        inner.querySelectorAll('.ios26-shell__btn').forEach((x) => x.classList.remove('is-active'));
        btn.classList.add('is-active');
        item.onClick();
      });
      inner.appendChild(btn);
    });
    nav.appendChild(inner);
    document.body.appendChild(nav);
  }

  function ensureShellAssets() {
    const page = inferShellPage();
    if (!page) return;
    const cssHref = `${withBase('/html/app-shell.css')}?v=${SHELL_VERSION}`;
    const hasCss = [...document.querySelectorAll('link[rel="stylesheet"]')]
      .some((l) => (l.getAttribute('href') || '').includes('/html/app-shell.css'));
    if (!hasCss) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = cssHref;
      document.head.appendChild(link);
    }

    const ensureNavScript = () => {
      if (document.querySelector('.ios26-shell')) return;
      const script = document.createElement('script');
      script.src = `${withBase('/html/app-shell.js')}?v=${SHELL_VERSION}`;
      script.async = true;
      script.onload = () => {
        setTimeout(() => {
          if (!document.querySelector('.ios26-shell')) buildFallbackNav(page);
        }, 60);
      };
      document.body.appendChild(script);
    };

    ensureNavScript();
    setTimeout(ensureNavScript, 300);
    setTimeout(() => {
      if (!document.querySelector('.ios26-shell')) buildFallbackNav(page);
    }, 1200);
  }

  function patchNoteFunctions() {
    ['renderNotes', 'addFreeNote', 'deleteNote', 'openNote'].forEach((name) => {
      const original = window[name];
      if (typeof original !== 'function' || original.__notesWrapped) return;
      const wrapped = function (...args) {
        const res = original.apply(this, args);
        const overlay = document.getElementById('notesFocusOverlay');
        if (overlay?.classList.contains('show')) renderOverlayBody();
        ensureNoteCardEditButtons();
        return res;
      };
      wrapped.__notesWrapped = true;
      window[name] = wrapped;
    });
  }

  function parseNoteIdFromCard(card) {
    const onclick = card?.getAttribute('onclick') || '';
    const match = onclick.match(/openNote\(([-\d]+)\)/);
    return match ? Number(match[1]) : null;
  }

  function ensureNoteCardEditButtons() {
    document.querySelectorAll('.note-card').forEach((card) => {
      const actions = card.querySelector('.note-meta span:last-child');
      if (!actions || actions.querySelector('.note-edit')) return;
      const id = parseNoteIdFromCard(card);
      if (!id) return;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'note-edit';
      btn.textContent = 'Edit';
      btn.style.background = 'none';
      btn.style.border = 'none';
      btn.style.color = 'var(--accent-primary,#f6c177)';
      btn.style.cursor = 'pointer';
      btn.style.fontSize = '0.75rem';
      btn.style.padding = '0';
      btn.style.marginRight = '0.5rem';
      btn.addEventListener('click', (e) => startInlineCardEdit(id, card, e));
      const deleteBtn = actions.querySelector('.note-delete');
      actions.insertBefore(btn, deleteBtn || null);
    });
  }

  function startInlineCardEdit(id, card, event) {
    event?.stopPropagation();
    if (!card || card.querySelector('.inline-card-editor')) return;
    const notes = loadNotes();
    const note = notes.find((n) => Number(n?.id) === Number(id));
    if (!note) return;
    const host = card.querySelector('.note-body');
    if (!host) return;
    const editor = document.createElement('div');
    editor.className = 'inline-card-editor';
    editor.style.marginTop = '0.4rem';
    editor.innerHTML = `
      <textarea style="width:100%; min-height:86px; background:var(--bg-primary,#1a1a2e); color:var(--text-primary,#edf2f7); border:1px solid var(--border-color, rgba(255,255,255,0.14)); border-radius:8px; padding:.45rem; font-size:.82rem;">${escapeHtml(note.body || note.text || '')}</textarea>
      <div style="display:flex; justify-content:flex-end; gap:.4rem; margin-top:.35rem;">
        <button type="button" class="inline-card-cancel" style="border:1px solid var(--border-color, rgba(255,255,255,0.14)); background:var(--bg-elevated,#263352); color:var(--text-secondary,#a0aec0); border-radius:8px; padding:.2rem .55rem; font-size:.75rem;">Cancel</button>
        <button type="button" class="inline-card-save" style="border:1px solid rgba(163,217,165,.55); background:var(--bg-elevated,#263352); color:var(--accent-secondary,#a3d9a5); border-radius:8px; padding:.2rem .55rem; font-size:.75rem;">Save</button>
      </div>
    `;
    host.appendChild(editor);
    const textarea = editor.querySelector('textarea');
    textarea?.focus();
    editor.querySelector('.inline-card-cancel')?.addEventListener('click', () => editor.remove());
    editor.querySelector('.inline-card-save')?.addEventListener('click', () => {
      const updated = loadNotes().map((n) => Number(n?.id) === Number(id) ? { ...n, body: textarea?.value || '' } : n);
      saveNotes(updated);
      if (typeof window.renderNotes === 'function') window.renderNotes();
    });
  }

  function closeInlineNoteEditor() {
    document.getElementById('inlineNoteEditor')?.remove();
  }

  function openInlineNoteEditor(selectionText, section, rect) {
    ensureOverlayStyle();
    closeInlineNoteEditor();
    const editor = document.createElement('div');
    editor.id = 'inlineNoteEditor';
    editor.className = 'inline-note-editor';
    const top = window.scrollY + rect.bottom + 10;
    const left = Math.max(12, Math.min(window.scrollX + rect.left, window.scrollX + window.innerWidth - 440));
    editor.style.top = `${top}px`;
    editor.style.left = `${left}px`;
    editor.innerHTML = `
      <div style="font-size:.78rem; color:var(--text-tertiary,#718096); margin-bottom:.4rem;">Add note for selection</div>
      <textarea id="inlineNoteInput" placeholder="Write note... (Markdown supported)"></textarea>
      <div class="inline-note-actions">
        <button type="button" id="inlineNoteCancel">Cancel</button>
        <button type="button" class="save" id="inlineNoteSave">Save</button>
      </div>
    `;
    document.body.appendChild(editor);
    const input = editor.querySelector('#inlineNoteInput');
    input?.focus();
    editor.querySelector('#inlineNoteCancel')?.addEventListener('click', closeInlineNoteEditor);
    editor.querySelector('#inlineNoteSave')?.addEventListener('click', () => {
      const body = (input?.value || '').trim() || '(highlighted)';
      if (typeof window.addNote === 'function') {
        window.addNote(selectionText, body, section || '');
      }
      closeInlineNoteEditor();
    });
  }

  function patchHighlightAndNote() {
    window.highlightAndNote = function highlightAndNoteInline() {
      const sel = window.getSelection();
      const text = sel?.toString().trim();
      if (!text || !sel.rangeCount) return;
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
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
      if (typeof window.highlightSelection === 'function') {
        window.highlightSelection();
      }
      openInlineNoteEditor(text, section, rect);
    };
  }

  window.openNotesFocusModal = openNotesFocusModal;

  function initEnhancements() {
    window.renderNoteMarkdown = renderMd;
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations()
        .then((regs) => regs.forEach((r) => r.unregister()))
        .catch(() => {});
    }
    try { ensureShellAssets(); } catch {}
    try { addFocusNotesButton(); } catch {}
    try { bindShortcutClicks(); } catch {}
    try { patchNoteFunctions(); } catch {}
    try { patchHighlightAndNote(); } catch {}
    try {
      const noteInput = document.getElementById('noteInput');
      if (noteInput && typeof window.renderDraftPreview === 'function') {
        window.renderDraftPreview(noteInput.value || '');
      }
      if (typeof window.renderNotes === 'function') {
        window.renderNotes();
      }
    } catch {}
  }

  window.addEventListener('DOMContentLoaded', initEnhancements);
  window.addEventListener('load', initEnhancements);
})();
