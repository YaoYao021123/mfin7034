(() => {
  const bodyTag = document.body;
  const fromDataset = bodyTag?.dataset?.shellPage;
  const lowerPath = window.location.pathname.toLowerCase();
  const htmlRootIdx = lowerPath.indexOf('/html/');
  const basePrefix = htmlRootIdx >= 0 ? window.location.pathname.slice(0, htmlRootIdx) : '';
  const withBase = (path) => `${basePrefix}${path}`;
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
  if (!page || !['portal', 'lecture'].includes(page)) return;
  if (window !== window.top) return; // Don't render nav bar when embedded in iframe

  const icon = {
    landing: '⌂',
    home: '⊞',
    search: '⌕',
    latest: '⟲',
    pdf: '▣',
    notes: '✎',
    ai: '✦',
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
        { id: 'latest',  label: 'Latest', onClick: openLatestLecture },
      ]
    : [
        { id: 'landing', label: 'Home',   onClick: () => (window.location.href = withBase('/')) },
        { id: 'home',    label: 'Portal', onClick: () => (window.location.href = withBase('/html/index.html')) },
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
    btn.innerHTML = `<span class="ios26-shell__icon">${icon[item.id] || '•'}</span><span class="ios26-shell__label">${item.label}</span>`;
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
