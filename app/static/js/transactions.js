// app/static/js/transactions.js
(function () {
  function qs(sel, root = document) { return root.querySelector(sel); }
  function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

  const page = qs('[data-page]');
  if (page) requestAnimationFrame(() => page.classList.add('is-ready'));

  const topbar = qs('[data-topbar]');
  function updateTopbar() {
    if (!topbar) return;
    const y = window.scrollY || document.documentElement.scrollTop || 0;
    topbar.classList.toggle('is-scrolled', y > 6);
  }
  updateTopbar();
  window.addEventListener('scroll', updateTopbar, { passive: true });

  const filtersToggle = qs('[data-filters-toggle]');
  const filtersBody = qs('[data-filters-body]');
  function setFiltersCollapsed(collapsed) {
    if (!filtersToggle || !filtersBody) return;
    filtersBody.classList.toggle('is-collapsed', collapsed);
    filtersToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  }
  if (filtersToggle && filtersBody) {
    filtersToggle.addEventListener('click', () => {
      const collapsed = filtersBody.classList.contains('is-collapsed');
      setFiltersCollapsed(!collapsed);
    });
    const mq = window.matchMedia('(max-width: 860px)');
    if (mq.matches) setFiltersCollapsed(false);
  }

  const form = qs('form.filters');
  const dateRangeInput = qs('#date_range');
  const startInput = qs('#start_date');
  const endInput = qs('#end_date');
  const fallbackWrap = qs('[data-date-fallback]');

  function pad2(n) { return String(n).padStart(2, '0'); }
  function toYMD(d) { return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`; }

  function updateDateRangeText() {
    if (!dateRangeInput || !startInput || !endInput) return;
    const s = (startInput.value || '').trim();
    const e = (endInput.value || '').trim();
    dateRangeInput.value = (s && e) ? `${s} → ${e}` : (s ? `${s} →` : (e ? `→ ${e}` : ''));
  }

  function setDates(start, end) {
    if (startInput) startInput.value = start || '';
    if (endInput) endInput.value = end || '';
    updateDateRangeText();
  }

  if (startInput) startInput.addEventListener('change', updateDateRangeText);
  if (endInput) endInput.addEventListener('change', updateDateRangeText);
  updateDateRangeText();

  if (fallbackWrap) fallbackWrap.classList.add('js-on');

  function applyPreset(preset) {
    const now = new Date();
    let s = null, e = null;

    if (preset === 'last-month') {
      const firstThis = new Date(now.getFullYear(), now.getMonth(), 1);
      const lastPrev = new Date(firstThis.getFullYear(), firstThis.getMonth(), 0);
      s = new Date(lastPrev.getFullYear(), lastPrev.getMonth(), 1);
      e = lastPrev;
    } else if (preset === 'ytd') {
      s = new Date(now.getFullYear(), 0, 1);
      e = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    } else if (preset === 'all') {
      setDates('', '');
      return { s: null, e: null };
    }

    if (s && e) setDates(toYMD(s), toYMD(e));
    return { s, e };
  }

  let fp = null;
  if (window.flatpickr && dateRangeInput && startInput && endInput) {
    dateRangeInput.setAttribute('readonly', 'readonly');

    const existingStart = startInput.value ? new Date(startInput.value) : null;
    const existingEnd = endInput.value ? new Date(endInput.value) : null;

    fp = window.flatpickr(dateRangeInput, {
      mode: 'range',
      dateFormat: 'Y-m-d',
      allowInput: false,
      onReady: function () { updateDateRangeText(); },
      onChange: function (selectedDates) {
        const s = selectedDates[0] ? toYMD(selectedDates[0]) : '';
        const e = selectedDates[1] ? toYMD(selectedDates[1]) : '';
        setDates(s, e);
      },
      onClose: function (selectedDates) {
        const s = selectedDates[0] ? toYMD(selectedDates[0]) : '';
        const e = selectedDates[1] ? toYMD(selectedDates[1]) : '';
        setDates(s, e);
      }
    });

    if (existingStart && existingEnd) {
      fp.setDate([existingStart, existingEnd], false);
      setDates(startInput.value, endInput.value);
    }
  }

  qsa('[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => {
      const preset = btn.getAttribute('data-preset');
      const { s, e } = applyPreset(preset);
      if (fp && s && e) fp.setDate([s, e], true);
      if (fp && preset === 'all') fp.clear();
    });
  });

  if (form) {
    form.addEventListener('submit', () => {
      updateDateRangeText();

      const s = startInput?.value?.trim() || "";
      const e = endInput?.value?.trim() || "";

      if (!s) startInput.removeAttribute("name");
      else startInput.setAttribute("name", "start_date");

      if (!e) endInput.removeAttribute("name");
      else endInput.setAttribute("name", "end_date");
    });
  }

  // ===== Multi-select helpers =====
  const multiSelects = qsa('details.multi-select');

  function closeAllMultiSelects(except) {
    multiSelects.forEach(d => { if (d !== except) d.removeAttribute('open'); });
  }

  function updateMeta(details) {
    const group = details.getAttribute('data-multiselect');
    const meta = qs(`[data-multi-meta="${group}"]`);
    if (!meta) return;
    const checked = qsa(`input[type="checkbox"][name="${group}"]`, details).filter(cb => cb.checked).length;
    meta.textContent = checked ? `${checked} selected` : 'Any';
  }

  function positionPanel(details) {
    const panel = qs('.multi-panel', details);
    const summary = qs('summary', details);
    if (!panel || !summary) return;

    panel.style.left = '';
    panel.style.right = '';
    panel.style.top = '';
    panel.style.bottom = '';
    panel.style.maxHeight = '';

    const sRect = summary.getBoundingClientRect();
    const pRect = panel.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const margin = 12;

    const desiredLeft = sRect.left;
    if (desiredLeft + pRect.width > vw - margin) {
      panel.style.left = 'auto';
      panel.style.right = '0';
    } else {
      panel.style.right = 'auto';
      panel.style.left = '0';
    }

    const spaceBelow = vh - sRect.bottom - margin;
    const spaceAbove = sRect.top - margin;
    const openDown = spaceBelow >= 220 || spaceBelow >= spaceAbove;

    if (openDown) {
      panel.style.top = 'calc(100% + 10px)';
      panel.style.bottom = 'auto';
      panel.style.maxHeight = `${Math.max(180, spaceBelow)}px`;
    } else {
      panel.style.top = 'auto';
      panel.style.bottom = 'calc(100% + 10px)';
      panel.style.maxHeight = `${Math.max(180, spaceAbove)}px`;
    }
  }

  multiSelects.forEach(details => {
    const search = qs('[data-multi-search]', details);
    const items = qsa('[data-multi-item]', details);

    if (search) {
      search.addEventListener('input', () => {
        const q = search.value.trim().toLowerCase();
        items.forEach(row => {
          const label = row.textContent.trim().toLowerCase();
          row.style.display = label.includes(q) ? '' : 'none';
        });
      });
    }

    details.addEventListener('toggle', () => {
      if (details.open) {
        closeAllMultiSelects(details);
        positionPanel(details);
      }
      updateMeta(details);
    });

    details.addEventListener('change', (e) => {
      if (e.target && e.target.matches('input[type="checkbox"]')) updateMeta(details);
    });
  });

  qsa('[data-clear-group]').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.getAttribute('data-clear-group');
      const root = qs(`details.multi-select[data-multiselect="${group}"]`);
      if (!root) return;
      qsa(`input[type="checkbox"][name="${group}"]`, root).forEach(cb => cb.checked = false);
      updateMeta(root);
    });
  });

  qsa('.chip[data-chip-for]').forEach(chip => {
    chip.addEventListener('click', () => {
      const group = chip.getAttribute('data-chip-for');
      const value = chip.getAttribute('data-chip-value');
      const root = qs(`details[data-multiselect="${group}"]`);
      if (!root) return;

      const checkbox = qsa(`input[type="checkbox"][name="${group}"]`, root).find(cb => cb.value === value);
      if (checkbox) checkbox.checked = false;
      chip.style.display = 'none';
      updateMeta(root);
    });
  });

  document.addEventListener('click', (e) => {
    qsa('details.multi-select[open]').forEach(openDetails => {
      if (!openDetails.contains(e.target)) openDetails.removeAttribute('open');
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      qsa('details.multi-select[open]').forEach(openDetails => openDetails.removeAttribute('open'));
    }
  });

  const reposition = () => {
    const openOne = qs('details.multi-select[open]');
    if (openOne) positionPanel(openOne);
  };
  window.addEventListener('resize', reposition, { passive: true });
  window.addEventListener('scroll', reposition, { passive: true });

  multiSelects.forEach(updateMeta);

  // ===== Date formatting (collapsed rows: "November 5") =====
  function formatMonthDay(ymd) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((ymd || '').trim());
    if (!m) return ymd;
    const year = Number(m[1]);
    const month = Number(m[2]) - 1;
    const day = Number(m[3]);
    const d = new Date(Date.UTC(year, month, day));
    try { return new Intl.DateTimeFormat(undefined, { month: 'long', day: 'numeric' }).format(d); }
    catch (_) {
      const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
      return `${monthNames[month]} ${day}`;
    }
  }

  // ===== Row expand/collapse =====
  const rows = qsa('[data-tx-row]');
  function getDetails(row) { return qs('[data-row-details]', row); }
  function getDateCell(row) { return qs('[data-date-cell]', row); }

  function syncDateDisplay(row, expanded) {
    const cell = getDateCell(row);
    if (!cell) return;
    if (!cell.dataset.rawDate) cell.dataset.rawDate = (cell.textContent || '').trim();
    const raw = cell.dataset.rawDate;
    cell.textContent = expanded ? raw : formatMonthDay(raw);
  }

  function setRowExpanded(row, expanded) {
    const det = getDetails(row);
    if (!det) return;
    det.open = !!expanded;
    row.classList.toggle('is-open', !!expanded);
    syncDateDisplay(row, !!expanded);
  }

  rows.forEach(row => {
    const det = getDetails(row);
    const expanded = !!(det && det.open);
    row.classList.toggle('is-open', expanded);
    syncDateDisplay(row, expanded);

    row.addEventListener('click', (e) => {
      const t = e.target;
      if (!t) return;
      if (t.closest('a, button, input, select, textarea, label, summary, details, .multi-panel, .chip')) return;

      const details = getDetails(row);
      if (!details) return;
      details.open = !details.open;
      row.classList.toggle('is-open', details.open);
      syncDateDisplay(row, details.open);
    });

    if (det) {
      det.addEventListener('toggle', () => {
        row.classList.toggle('is-open', det.open);
        syncDateDisplay(row, det.open);
      });
    }
  });

  const expandAllBtn = qs('[data-expand-all]');
  const collapseAllBtn = qs('[data-collapse-all]');
  if (expandAllBtn) expandAllBtn.addEventListener('click', () => rows.forEach(r => setRowExpanded(r, true)));
  if (collapseAllBtn) collapseAllBtn.addEventListener('click', () => rows.forEach(r => setRowExpanded(r, false)));

  const tableScroll = qs('[data-table-scroll]');
  function updateTableShadow() {
    if (!tableScroll) return;
    tableScroll.classList.toggle('has-shadow', tableScroll.scrollTop > 2);
  }
  if (tableScroll) {
    updateTableShadow();
    tableScroll.addEventListener('scroll', updateTableShadow, { passive: true });
  }
})();
