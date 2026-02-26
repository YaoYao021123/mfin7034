(() => {
  const SHELL_VERSION = '11';
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
          { id: 'landing', label: 'Home',   icon: '⌂', onClick: () => (window.location.href = withBase('/')) },
          { id: 'search',  label: 'Search', icon: '⌕', onClick: () => document.getElementById('searchInput')?.focus() },
          { id: 'latest',  label: 'Latest', icon: '⟲', onClick: () => { const href = localStorage.getItem('lecture-last-opened'); if (!href) return; window.location.href = href.startsWith('/') ? `${withBase(href)}` : href; } },
        ]
      : [
          { id: 'landing', label: 'Home',   icon: '⌂', onClick: () => (window.location.href = withBase('/')) },
          { id: 'home',    label: 'Portal', icon: '⊞', onClick: () => (window.location.href = withBase('/html/index.html')) },
          { id: 'pdf',     label: 'PDF',    icon: '▣', onClick: () => window.switchSidebarTab?.('pdf') },
          { id: 'notes',   label: 'Notes',  icon: '✎', onClick: () => window.switchSidebarTab?.('notes') },
          { id: 'ai',      label: 'AI',     icon: '✦', onClick: () => focusAIInput() },
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

  // ── AI Config System ──────────────────────────────────────────────────────

  const AI_CONFIG_KEY = 'mfin_ai_config';

  // format: 'gemini' | 'anthropic' | 'openai-compat' | 'proxy'
  // needsEndpoint: show editable endpoint URL field
  const AI_PROVIDERS = [
    { id: 'proxy',     label: 'Local Server',    needsKey: false,  format: 'proxy',        models: [],
      hint: 'Routes through <code>serve.py</code>. Requires <code>python3 serve.py</code> running locally.' },
    { id: 'openai',    label: 'OpenAI',           needsKey: true,   format: 'openai-compat',
      endpoint: 'https://api.openai.com/v1/chat/completions',
      models: ['gpt-4o', 'o3', 'gpt-4o-mini', 'o1', 'o1-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
      keyPlaceholder: 'sk-...', keyLink: 'https://platform.openai.com/api-keys' },
    { id: 'gemini',    label: 'Google Gemini',    needsKey: true,   format: 'gemini',
      models: ['gemini-3.1-pro-preview', 'gemini-3-flash-preview', 'gemini-3-pro-preview', 'gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'],
      keyPlaceholder: 'AIza...', keyLink: 'https://aistudio.google.com/app/apikey' },
    { id: 'anthropic', label: 'Anthropic Claude', needsKey: true,   format: 'anthropic',
      models: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229', 'claude-3-sonnet-20240229'],
      keyPlaceholder: 'sk-ant-...', keyLink: 'https://console.anthropic.com/settings/keys' },
    { id: 'grok',      label: 'Grok (xAI)',       needsKey: true,   format: 'openai-compat',
      endpoint: 'https://api.x.ai/v1/chat/completions',
      models: ['grok-4', 'grok-3', 'grok-3-mini'],
      keyPlaceholder: 'xai-...', keyLink: 'https://console.x.ai' },
    { id: 'glm',       label: 'GLM (Zhipu AI)',   needsKey: true,   format: 'openai-compat',
      endpoint: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
      models: ['glm-4-plus', 'glm-4', 'glm-4-air', 'glm-4-flash'],
      keyPlaceholder: 'your-glm-key', keyLink: 'https://open.bigmodel.cn/usercenter/apikeys' },
    { id: 'kimi',      label: 'Kimi (Moonshot)',  needsKey: true,   format: 'openai-compat',
      endpoint: 'https://api.moonshot.cn/v1/chat/completions',
      models: ['moonshot-v1-128k', 'moonshot-v1-32k', 'moonshot-v1-8k'],
      keyPlaceholder: 'sk-...', keyLink: 'https://platform.moonshot.cn/console/api-keys' },
    { id: 'qwen',      label: 'Qwen (Alibaba)',   needsKey: true,   format: 'openai-compat',
      endpoint: 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
      models: ['qwen-max', 'qwen-plus', 'qwen-turbo', 'qwen-long'],
      keyPlaceholder: 'sk-...', keyLink: 'https://bailian.console.aliyun.com/' },
    { id: 'minimax',   label: 'MiniMax',          needsKey: true,   format: 'openai-compat',
      endpoint: 'https://api.minimaxi.chat/v1/text/chatcompletion_v2',
      models: ['MiniMax-Text-01', 'abab6.5s-chat', 'abab5.5-chat'],
      keyPlaceholder: 'your-minimax-key', keyLink: 'https://platform.minimaxi.com/user-center/basic-information/interface-key' },
    { id: 'custom',    label: 'Custom',            needsKey: true,   format: 'openai-compat', needsEndpoint: true,
      endpoint: '', models: [],
      keyPlaceholder: 'API key', keyLink: '' },
  ];

  function getAIConfig() {
    try { return JSON.parse(localStorage.getItem(AI_CONFIG_KEY) || '{}'); } catch { return {}; }
  }
  function setAIConfig(cfg) { localStorage.setItem(AI_CONFIG_KEY, JSON.stringify(cfg || {})); }

  function providerLabel(cfg) {
    if (!cfg || !cfg.provider) return 'AI';
    const p = AI_PROVIDERS.find((x) => x.id === cfg.provider);
    return p ? p.label : cfg.provider;
  }

  function ensureAIConfigStyle() {
    if (document.getElementById('aiConfigStyle')) return;
    const style = document.createElement('style');
    style.id = 'aiConfigStyle';
    style.textContent = `
      .ai-cfg-overlay{position:fixed;inset:0;background:rgba(8,12,24,.65);backdrop-filter:blur(8px);z-index:10050;display:none;align-items:center;justify-content:center;padding:1rem}
      .ai-cfg-overlay.show{display:flex}
      .ai-cfg-modal{width:min(460px,96vw);background:var(--bg-card,#1c2a45);border:1px solid var(--border-color,rgba(255,255,255,.13));border-radius:18px;box-shadow:0 30px 70px rgba(0,0,0,.45);padding:1.6rem;color:var(--text-primary,#edf2f7)}
      .ai-cfg-title{font-size:1.05rem;font-weight:600;margin-bottom:1.15rem;display:flex;align-items:center;gap:.45rem}
      .ai-cfg-lbl{font-size:.78rem;color:var(--text-secondary,#a0aec0);margin-bottom:.3rem}
      .ai-cfg-sel,.ai-cfg-inp{width:100%;background:var(--bg-primary,#111827);color:var(--text-primary,#edf2f7);border:1px solid var(--border-color,rgba(255,255,255,.14));border-radius:9px;padding:.45rem .65rem;font-size:.88rem;margin-bottom:.9rem;box-sizing:border-box}
      .ai-cfg-sel:focus,.ai-cfg-inp:focus{outline:2px solid var(--accent-primary,#f6c177);outline-offset:1px}
      .ai-cfg-hint{font-size:.74rem;color:var(--text-tertiary,#718096);margin-bottom:.9rem;line-height:1.55}
      .ai-cfg-hint a{color:var(--accent-primary,#f6c177)}
      .ai-cfg-hint code{background:var(--bg-tertiary,#1f2b47);padding:.1em .35em;border-radius:4px;font-size:.88em}
      .ai-cfg-row{display:flex;gap:.55rem;justify-content:flex-end;margin-top:.2rem}
      .ai-cfg-btn{border:1px solid var(--border-color,rgba(255,255,255,.14));background:var(--bg-elevated,#263352);color:var(--text-primary,#edf2f7);border-radius:9px;padding:.4rem 1rem;cursor:pointer;font-size:.84rem;transition:opacity .15s}
      .ai-cfg-btn.primary{border-color:rgba(246,193,119,.5);color:var(--accent-primary,#f6c177)}
      .ai-cfg-btn:hover{opacity:.8}
      .ai-cfg-gear{background:none;border:none;cursor:pointer;padding:.18rem .38rem;color:var(--text-tertiary,#718096);font-size:.95rem;border-radius:6px;line-height:1;transition:color .15s}
      .ai-cfg-gear:hover{color:var(--accent-primary,#f6c177)}
      .ai-provider-badge{font-size:.72rem;color:var(--text-tertiary,#718096);margin-top:.12rem;cursor:pointer}
      .ai-provider-badge:hover{color:var(--accent-primary,#f6c177)}
    `;
    document.head.appendChild(style);
  }

  function buildAIConfigModal() {
    ensureAIConfigStyle();
    let overlay = document.getElementById('aiCfgOverlay');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'aiCfgOverlay';
    overlay.className = 'ai-cfg-overlay';
    overlay.innerHTML = `
      <div class="ai-cfg-modal">
        <div class="ai-cfg-title">⚙️ AI Study Assistant — Provider</div>
        <div class="ai-cfg-lbl">Provider</div>
        <select class="ai-cfg-sel" id="aiCfgProvider">
          ${AI_PROVIDERS.map((p) => `<option value="${p.id}">${p.label}</option>`).join('')}
        </select>
        <div id="aiCfgKeyGroup">
          <div class="ai-cfg-lbl">API Key</div>
          <input type="password" class="ai-cfg-inp" id="aiCfgKey" placeholder="Paste your API key" autocomplete="off"/>
          <div class="ai-cfg-hint" id="aiCfgKeyHint"></div>
        </div>
        <div id="aiCfgEndpointGroup" style="display:none">
          <div class="ai-cfg-lbl">Endpoint URL</div>
          <input type="text" class="ai-cfg-inp" id="aiCfgEndpoint" placeholder="https://api.example.com/v1/chat/completions" autocomplete="off"/>
        </div>
        <div id="aiCfgModelGroup">
          <div class="ai-cfg-lbl">Model</div>
          <select class="ai-cfg-sel" id="aiCfgModel"></select>
        </div>
        <div id="aiCfgCustomModelGroup" style="display:none">
          <div class="ai-cfg-lbl">Model name</div>
          <input type="text" class="ai-cfg-inp" id="aiCfgCustomModel" placeholder="Enter model name"/>
        </div>
        <div class="ai-cfg-hint" id="aiCfgProxyHint" style="display:none"></div>
        <div class="ai-cfg-row">
          <button class="ai-cfg-btn" id="aiCfgCancel">Cancel</button>
          <button class="ai-cfg-btn primary" id="aiCfgSave">Save &amp; Connect</button>
        </div>
      </div>`;
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.classList.remove('show'); });
    document.body.appendChild(overlay);

    const provSel = overlay.querySelector('#aiCfgProvider');
    const keyGroup = overlay.querySelector('#aiCfgKeyGroup');
    const endpointGroup = overlay.querySelector('#aiCfgEndpointGroup');
    const modelGroup = overlay.querySelector('#aiCfgModelGroup');
    const customModelGroup = overlay.querySelector('#aiCfgCustomModelGroup');
    const modelSel = overlay.querySelector('#aiCfgModel');
    const keyHint = overlay.querySelector('#aiCfgKeyHint');
    const proxyHint = overlay.querySelector('#aiCfgProxyHint');
    const keyInp = overlay.querySelector('#aiCfgKey');
    const endpointInp = overlay.querySelector('#aiCfgEndpoint');
    const customModelInp = overlay.querySelector('#aiCfgCustomModel');

    function refreshModelSel() {
      const p = AI_PROVIDERS.find((x) => x.id === provSel.value);
      if (!p) return;
      const isCustomProvider = p.id === 'custom';
      if (isCustomProvider) {
        modelGroup.style.display = 'none';
        customModelGroup.style.display = '';
      } else if (p.models.length) {
        modelGroup.style.display = '';
        customModelGroup.style.display = 'none';
        modelSel.innerHTML = p.models.map((m) => `<option value="${m}">${m}</option>`).join('')
          + '<option value="__custom__">— enter model name —</option>';
        modelSel.onchange = () => {
          customModelGroup.style.display = modelSel.value === '__custom__' ? '' : 'none';
        };
        modelSel.onchange();
      } else {
        modelGroup.style.display = 'none';
        customModelGroup.style.display = 'none';
      }
    }

    function refresh() {
      const p = AI_PROVIDERS.find((x) => x.id === provSel.value);
      if (!p) return;
      keyGroup.style.display = p.needsKey ? '' : 'none';
      endpointGroup.style.display = p.needsEndpoint ? '' : 'none';
      proxyHint.style.display = p.needsKey ? 'none' : '';
      if (p.needsKey) {
        keyInp.placeholder = p.keyPlaceholder || 'Paste API key';
        keyHint.innerHTML = p.keyLink
          ? `Key stored locally in your browser only. <a href="${p.keyLink}" target="_blank" rel="noopener">Get a key →</a>`
          : '';
      } else {
        proxyHint.innerHTML = p.hint || '';
      }
      refreshModelSel();
    }
    provSel.addEventListener('change', refresh);
    refresh();

    overlay.querySelector('#aiCfgCancel').addEventListener('click', () => overlay.classList.remove('show'));
    overlay.querySelector('#aiCfgSave').addEventListener('click', () => {
      const p = AI_PROVIDERS.find((x) => x.id === provSel.value);
      const key = keyInp.value.trim();
      if (p.needsKey && !key) {
        keyInp.style.outline = '2px solid #f87171';
        keyInp.placeholder = 'API key is required';
        return;
      }
      keyInp.style.outline = '';
      const rawModel = modelSel.value === '__custom__' || p.id === 'custom'
        ? (customModelInp.value.trim() || modelSel.value)
        : modelSel.value;
      const endpoint = endpointInp.value.trim() || p.endpoint || '';
      setAIConfig({ provider: provSel.value, apiKey: key, model: rawModel, endpoint });
      patchAIProviderBadge();
      overlay.classList.remove('show');
      if (typeof overlay._onSave === 'function') { const cb = overlay._onSave; overlay._onSave = null; cb(); }
    });
    return overlay;
  }

  function openAIConfigModal(onSave) {
    const overlay = buildAIConfigModal();
    const cfg = getAIConfig();
    const provSel = overlay.querySelector('#aiCfgProvider');
    const keyInp = overlay.querySelector('#aiCfgKey');
    const modelSel = overlay.querySelector('#aiCfgModel');
    const endpointInp = overlay.querySelector('#aiCfgEndpoint');
    const customModelInp = overlay.querySelector('#aiCfgCustomModel');
    if (cfg.provider && provSel) {
      provSel.value = cfg.provider;
      provSel.dispatchEvent(new Event('change'));
    }
    if (cfg.apiKey && keyInp) keyInp.value = cfg.apiKey;
    if (cfg.endpoint && endpointInp) endpointInp.value = cfg.endpoint;
    if (cfg.model) {
      if (modelSel.querySelector(`option[value="${CSS.escape(cfg.model)}"]`)) {
        modelSel.value = cfg.model;
        modelSel.dispatchEvent(new Event('change'));
      } else if (cfg.model && customModelInp) {
        modelSel.value = '__custom__';
        modelSel.dispatchEvent(new Event('change'));
        customModelInp.value = cfg.model;
      }
    }
    overlay._onSave = onSave || null;
    overlay.classList.add('show');
  }

  function patchAIProviderBadge() {
    const badge = document.getElementById('aiProviderBadge');
    if (!badge) return;
    const cfg = getAIConfig();
    badge.textContent = cfg.provider ? providerLabel(cfg) : 'Click ⚙ to configure';
  }

  function patchAIChatHeader() {
    const header = document.querySelector('.ai-chat-header');
    if (!header || header.dataset.aiCfgPatched) return;
    header.dataset.aiCfgPatched = '1';
    // Remove "Powered by Gemini" / any "Powered by" subtitle
    header.querySelectorAll('p').forEach((p) => {
      if (/powered\s+by|gemini/i.test(p.textContent)) p.remove();
    });
    // Add provider badge below title
    const titleDiv = header.querySelector('div');
    if (titleDiv) {
      const badge = document.createElement('p');
      badge.id = 'aiProviderBadge';
      badge.className = 'ai-provider-badge';
      const cfg = getAIConfig();
      badge.textContent = cfg.provider ? providerLabel(cfg) : 'Click ⚙ to configure';
      badge.addEventListener('click', () => openAIConfigModal());
      titleDiv.appendChild(badge);
    }
    // Add gear button
    const gear = document.createElement('button');
    gear.className = 'ai-cfg-gear';
    gear.type = 'button';
    gear.title = 'Configure AI provider';
    gear.textContent = '⚙';
    gear.addEventListener('click', () => openAIConfigModal());
    header.style.display = 'flex';
    header.style.alignItems = 'center';
    header.style.justifyContent = 'space-between';
    header.appendChild(gear);
  }

  // ── Multi-provider callAI ─────────────────────────────────────────────────

  async function callAI(prompt) {
    const cfg = getAIConfig();
    const provider = cfg.provider || 'proxy';
    const p = AI_PROVIDERS.find((x) => x.id === provider);

    // Local proxy (serve.py)
    if (provider === 'proxy') {
      const base = getBasePrefix();
      const url = base ? `${base}/api/gemini` : '../api/gemini';
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, generationConfig: { temperature: 0.7, maxOutputTokens: 1024 } }),
      });
      if (!res.ok) { const t = await res.text(); throw new Error(`API ${res.status}: ${t.substring(0, 200)}`); }
      const data = await res.json();
      const answer = data.candidates?.[0]?.content?.parts?.[0]?.text;
      if (!answer) throw new Error('Empty response from proxy');
      return answer;
    }

    // Gemini REST API
    if (provider === 'gemini') {
      const model = cfg.model || 'gemini-2.5-flash';
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${cfg.apiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ role: 'user', parts: [{ text: prompt }] }],
            generationConfig: { temperature: 0.7, maxOutputTokens: 1024 },
          }),
        }
      );
      if (!res.ok) { const t = await res.text(); throw new Error(`Gemini ${res.status}: ${t.substring(0, 200)}`); }
      const data = await res.json();
      const answer = data.candidates?.[0]?.content?.parts?.[0]?.text;
      if (!answer) throw new Error('Empty response from Gemini');
      return answer;
    }

    // Anthropic Claude
    if (provider === 'anthropic') {
      const model = cfg.model || 'claude-3-5-sonnet-20241022';
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': cfg.apiKey, 'anthropic-version': '2023-06-01' },
        body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }], max_tokens: 1024 }),
      });
      if (!res.ok) { const t = await res.text(); throw new Error(`Claude ${res.status}: ${t.substring(0, 200)}`); }
      const data = await res.json();
      const answer = data.content?.[0]?.text;
      if (!answer) throw new Error('Empty response from Claude');
      return answer;
    }

    // OpenAI-compatible (OpenAI, Grok, GLM, Kimi, Qwen, MiniMax, Custom)
    if (p && (p.format === 'openai-compat' || p.endpoint)) {
      const endpoint = cfg.endpoint || p.endpoint;
      if (!endpoint) throw new Error(`No endpoint configured for provider: ${provider}`);
      const model = cfg.model || (p.models[0] || '');
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${cfg.apiKey}` },
        body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }], max_tokens: 1024, temperature: 0.7 }),
      });
      if (!res.ok) { const t = await res.text(); throw new Error(`${p.label} ${res.status}: ${t.substring(0, 200)}`); }
      const data = await res.json();
      const answer = data.choices?.[0]?.message?.content;
      if (!answer) throw new Error(`Empty response from ${p.label}`);
      return answer;
    }

    throw new Error(`Unknown provider: ${provider}`);
  }

  // ── Override global sendAIMessage / callGemini ────────────────────────────

  function installAIOverrides() {
    function buildPrompt(userMessage) {
      const ctx = typeof window.courseContext === 'string' ? window.courseContext : '';
      const hist = Array.isArray(window.conversationHistory) ? window.conversationHistory : [];
      return `You are a concise study assistant for this course.\n\nCourse content (excerpt):\n${ctx.substring(0, 3500)}\n\nPrevious conversation:\n${hist.slice(-4).map((m) => m.role + ': ' + m.content).join('\n')}\n\nStudent question: ${userMessage}\n\nInstructions:\n- Answer in 3-6 sentences, be direct and complete\n- Always finish your sentences\n- Use the course content as reference\n- If the question is in Chinese, answer in Chinese`;
    }

    window.callGemini = async function callGemini(userMessage) {
      const cfg = getAIConfig();
      if (!cfg.provider) {
        openAIConfigModal(() => setTimeout(() => window.callGemini(userMessage), 100));
        throw new Error('Please configure an AI provider first.');
      }
      const answer = await callAI(buildPrompt(userMessage));
      if (Array.isArray(window.conversationHistory)) {
        window.conversationHistory.push({ role: 'user', content: userMessage }, { role: 'assistant', content: answer });
      }
      return answer;
    };

    window.sendAIMessage = async function sendAIMessage() {
      const cfg = getAIConfig();
      if (!cfg.provider) {
        openAIConfigModal(() => setTimeout(() => window.sendAIMessage(), 100));
        return;
      }
      const input = document.getElementById('aiInput');
      const msg = input?.value.trim();
      if (!msg) return;

      const _appendMsg = typeof window.appendMsg === 'function' ? window.appendMsg : (role, html) => {
        const c = document.getElementById('aiMessages');
        if (!c) return null;
        const d = document.createElement('div');
        d.className = 'ai-message ' + role;
        d.innerHTML = html;
        c.appendChild(d);
        c.scrollTop = c.scrollHeight;
        return d;
      };
      const _fmt = typeof window.formatMd === 'function' ? window.formatMd : (t) =>
        t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>')
         .replace(/`(.+?)`/g, '<code>$1</code>').replace(/\n/g, '<br>');

      _appendMsg('user', escapeHtml(msg));
      if (input) { input.value = ''; input.disabled = true; }
      const typingEl = _appendMsg('assistant', '<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>');

      try {
        const answer = await callAI(buildPrompt(msg));
        if (Array.isArray(window.conversationHistory)) {
          window.conversationHistory.push({ role: 'user', content: msg }, { role: 'assistant', content: answer });
        }
        if (typingEl) typingEl.innerHTML = _fmt(answer);
      } catch (err) {
        const errMsg = escapeHtml(err?.message || String(err));
        if (typingEl) {
          typingEl.innerHTML = `⚠️ ${errMsg}<br><small style="cursor:pointer;color:var(--accent-primary,#f6c177)" onclick="openAIConfigModal()">Configure AI provider →</small>`;
        }
      } finally {
        if (input) { input.disabled = false; input.focus(); }
      }
    };

    window.openAIConfigModal = openAIConfigModal;
  }

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
    try { patchAIChatHeader(); } catch {}
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

  // Install AI overrides immediately (before DOM events fire)
  try { installAIOverrides(); } catch {}

  window.addEventListener('DOMContentLoaded', initEnhancements);
  window.addEventListener('load', initEnhancements);
})();
