(() => {
  const bodyTag = document.body;
  const fromDataset = bodyTag?.dataset?.shellPage;
  const lowerPath = window.location.pathname.toLowerCase();
  
  // Detect if we're in a course-specific context
  const courseMatch = window.location.pathname.match(/\/data\/([^/]+)\/html\//);
  const courseId = courseMatch ? courseMatch[1] : bodyTag?.dataset?.courseId || null;
  
  // Calculate base prefix for multi-level navigation
  const htmlRootIdx = lowerPath.indexOf('/html/');
  const dataIdx = lowerPath.indexOf('/data/');
  let basePrefix = '';
  
  if (dataIdx >= 0 && courseId) {
    // New multi-course structure: /data/{course}/html/
    basePrefix = window.location.pathname.slice(0, dataIdx);
  } else if (htmlRootIdx >= 0) {
    // Legacy structure: /html/
    basePrefix = window.location.pathname.slice(0, htmlRootIdx);
  }
  
  const withBase = (path) => `${basePrefix}${path}`;
  
  // Get course portal path
  const getCoursePortalPath = () => {
    if (courseId) {
      return withBase(`/data/${courseId}/html/index.html`);
    }
    return withBase('/html/index.html');
  };
  
  const resolveHref = (href) => {
    if (!href) return href;
    if (/^(https?:)?\/\//i.test(href)) return href;
    if (href.startsWith('/')) return withBase(href);
    return href;
  };
  
  const fromPath = lowerPath.endsWith('/html/index.html') || lowerPath === '/'
    ? 'portal'
    : (lowerPath.includes('interactive') ? 'lecture' : '');
  const fromDom = document.getElementById('aiInput') ? 'lecture' : '';
  const page = fromDataset || fromPath || fromDom;
  
  // Skip nav bar for platform home page and when embedded in iframe
  if (!page || !['portal', 'lecture', 'platform'].includes(page)) return;
  if (window !== window.top) return; // Don't render nav bar when embedded in iframe
  if (page === 'platform') return; // Platform home has its own nav

  const iconMarkup = {
    landing: `<svg class="ios26-shell__glyph" viewBox="0 0 24 24"><path d="M4.5 10.5L12 4l7.5 6.5" /><path d="M6.5 9.5V19h11V9.5" /></svg>`,
    home: `<svg class="ios26-shell__glyph" viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" rx="3" /><path d="M12 5v14M5 12h14" /></svg>`,
    lectures: `<svg class="ios26-shell__glyph" viewBox="0 0 24 24"><path d="M7 6.5h11" /><path d="M7 12h11" /><path d="M7 17.5h11" /><circle cx="4.5" cy="6.5" r="1" class="ios26-shell__glyph-fill" /><circle cx="4.5" cy="12" r="1" class="ios26-shell__glyph-fill" /><circle cx="4.5" cy="17.5" r="1" class="ios26-shell__glyph-fill" /></svg>`,
    search: `<svg class="ios26-shell__glyph" viewBox="0 0 24 24"><circle cx="11" cy="11" r="5.5" /><path d="M15 15l4.5 4.5" /></svg>`,
    latest: `<svg class="ios26-shell__glyph" viewBox="0 0 24 24"><path d="M12 6v6l3.5 2" /><path d="M20 12a8 8 0 1 1-2.4-5.7" /></svg>`,
    pdf: `<svg class="ios26-shell__glyph" viewBox="0 0 24 24"><path d="M8 3.5h5l4 4v13H8c-1.1 0-2-.9-2-2v-13c0-1.1.9-2 2-2z" /><path d="M13 3.5v4h4" /><path d="M9.5 13h5M9.5 16h5" /></svg>`,
    notes: `<svg class="ios26-shell__glyph" viewBox="0 0 24 24"><path d="M6 5.5h12v13H6z" /><path d="M9 9h6M9 12h6M9 15h4" /></svg>`,
    ai: `<svg class="ios26-shell__glyph" viewBox="0 0 24 24"><path d="M12 4.5l1.6 3.9 3.9 1.6-3.9 1.6L12 15.5l-1.6-3.9-3.9-1.6 3.9-1.6z" /><path d="M18.5 5.5v3M20 7h-3" /></svg>`,
    upload: `<svg class="ios26-shell__glyph" viewBox="0 0 24 24"><path d="M12 15V6.5" /><path d="M8.5 10L12 6.5 15.5 10" /><path d="M5.5 17.5h13" /><path d="M7.5 20h9" /></svg>`,
  };

  const openLatestLecture = () => {
    const saved = localStorage.getItem('lecture-last-opened');
    if (saved) {
      window.location.href = resolveHref(saved);
      return;
    }
    const first = document.querySelector('[data-open-lecture]');
    if (first) {
      window.location.href = resolveHref(first.getAttribute('href'));
    }
  };

  const switchTab = (tab) => {
    if (typeof window.switchSidebarTab === 'function') {
      window.switchSidebarTab(tab);
      return true;
    }
    return false;
  };

  const items = page === 'portal'
    ? [
        { id: 'landing', label: 'Home',   onClick: () => (window.location.href = withBase('/')) },
        { id: 'search',  label: 'Search', onClick: () => document.getElementById('searchInput')?.focus() },
        {
          id: 'lectures',
          label: 'Lectures',
          onClick: () => document.getElementById('lectureGrid')?.scrollIntoView({ block: 'start', behavior: 'smooth' }),
        },
        { id: 'latest',  label: 'Latest', onClick: openLatestLecture },
      ]
    : [
        { id: 'landing', label: 'Home',   onClick: () => (window.location.href = withBase('/')) },
        { id: 'home',    label: 'Portal', onClick: () => (window.location.href = getCoursePortalPath()) },
        {
          id: 'pdf',
          label: 'PDF',
          onClick: () => {
            if (!switchTab('pdf')) {
              const pdf = document.getElementById('pdfFrame')?.getAttribute('src');
              if (pdf) window.open(pdf, '_blank', 'noopener');
            }
          },
        },
        {
          id: 'notes',
          label: 'Notes',
          onClick: () => {
            switchTab('notes');
            document.getElementById('noteInput')?.focus();
          },
        },
        {
          id: 'ai',
          label: 'AI',
          onClick: () => {
            document.getElementById('aiInput')?.focus();
            document.querySelector('.sidebar-right')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
          },
        },
      ];

  const nav = document.createElement('nav');
  nav.className = 'ios26-shell';
  nav.setAttribute('aria-label', 'Bottom navigation');
  nav.innerHTML = '<div class="ios26-shell__inner"></div>';
  const inner = nav.firstElementChild;

  const setActive = (id) => {
    inner.querySelectorAll('.ios26-shell__btn').forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.id === id);
    });
  };

  const initialActiveId = page === 'portal' ? 'landing' : null;

  items.forEach((item) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ios26-shell__btn';
    btn.dataset.id = item.id;
    btn.innerHTML = `<span class="ios26-shell__icon" aria-hidden="true">${iconMarkup[item.id] || ''}</span><span class="ios26-shell__label">${item.label}</span>`;
    btn.addEventListener('click', () => {
      setActive(item.id);
      item.onClick();
    });
    if (item.id === initialActiveId) {
      btn.classList.add('is-active');
    }
    inner.appendChild(btn);
  });

  bodyTag.appendChild(nav);

  if (page === 'lecture') {
    localStorage.setItem('lecture-last-opened', window.location.pathname);
  }
})();
