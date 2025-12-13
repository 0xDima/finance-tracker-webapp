// app/static/js/transactions.js
// Progressive enhancement only:
// - Flatpickr date range -> fills #start_date and #end_date
// - Preset buttons
// - Multi-select search filtering + chip removal
// - Close dropdown on outside click / ESC
// - Close other dropdown when one opens
// - Prevent dropdown overflow (viewport-aware positioning)
// - Clear buttons in dropdown footer (category/account)

(function () {
  function qs(sel, root = document) { return root.querySelector(sel); }
  function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

  // ===== Date range (Flatpickr) =====
  const form = qs('form.filters');
  const dateRangeInput = qs('#date_range');
  const startInput = qs('#start_date');
  const endInput = qs('#end_date');
  const fallbackWrap = qs('[data-date-fallback]');

  function pad2(n) { return String(n).padStart(2, '0'); }
  function toYMD(d) {
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  }

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

  // Always keep pretty text in sync with native inputs too
  if (startInput) startInput.addEventListener('change', updateDateRangeText);
  if (endInput) endInput.addEventListener('change', updateDateRangeText);

  updateDateRangeText();

  // Mark JS state
  if (fallbackWrap) fallbackWrap.classList.add('js-on');

  // Helper: apply preset dates
  function applyPreset(preset) {
    const now = new Date();
    let s, e;

    if (preset === 'this-month') {
      s = new Date(now.getFullYear(), now.getMonth(), 1);
      e = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    } else if (preset === 'last-30') {
      e = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      s = new Date(e);
      s.setDate(s.getDate() - 29);
    } else if (preset === 'this-year') {
      s = new Date(now.getFullYear(), 0, 1);
      e = new Date(now.getFullYear(), 11, 31);
    }

    if (s && e) setDates(toYMD(s), toYMD(e));
    return { s, e };
  }

  // Flatpickr enhancement if available
  let fp = null;
  if (window.flatpickr && dateRangeInput && startInput && endInput) {
    // Make the pretty input display-only
    dateRangeInput.setAttribute('readonly', 'readonly');

    const existingStart = startInput.value ? new Date(startInput.value) : null;
    const existingEnd = endInput.value ? new Date(endInput.value) : null;

    fp = window.flatpickr(dateRangeInput, {
      mode: 'range',
      dateFormat: 'Y-m-d',
      allowInput: false,

      // Nice UX: show readable value but keep submitted format in hidden inputs
      // (We still submit start_date/end_date only, backend untouched)
      onReady: function () {
        // If native inputs already set, reflect them
        updateDateRangeText();
      },

      // ✅ Some users click around; onChange catches most, onClose catches the rest
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

    // Restore existing values into flatpickr calendar selection (if both present)
    if (existingStart && existingEnd) {
      fp.setDate([existingStart, existingEnd], false);
      setDates(startInput.value, endInput.value);
    }
  }

  // Presets (work with or without flatpickr)
  qsa('[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => {
      const preset = btn.getAttribute('data-preset');
      const { s, e } = applyPreset(preset);

      // If flatpickr exists, keep calendar UI in sync too
      if (fp && s && e) fp.setDate([s, e], true);
    });
  });

  if (form) {
    form.addEventListener('submit', () => {
      updateDateRangeText();

      const s = startInput?.value?.trim() || "";
      const e = endInput?.value?.trim() || "";

      // 🚫 Do NOT submit empty dates (FastAPI date parser will crash)
      if (!s) startInput.removeAttribute("name");
      else startInput.setAttribute("name", "start_date");

      if (!e) endInput.removeAttribute("name");
      else endInput.setAttribute("name", "end_date");
    });
  }

  // ===== Multi-select helpers =====
  const multiSelects = qsa('details.multi-select');

  function closeAllMultiSelects(except) {
    multiSelects.forEach(d => {
      if (d !== except) d.removeAttribute('open');
    });
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
      panel.style.top = 'calc(100% + 8px)';
      panel.style.bottom = 'auto';
      panel.style.maxHeight = `${Math.max(180, spaceBelow)}px`;
    } else {
      panel.style.top = 'auto';
      panel.style.bottom = 'calc(100% + 8px)';
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

      const checkbox = qsa(`input[type="checkbox"][name="${group}"]`, root)
        .find(cb => cb.value === value);

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
})();