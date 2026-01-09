// filename: app/static/js/upload_preview.js
// Role: Upload Preview client-side behavior — supports reviewing parsed transactions before import:
//       header/table scroll styling, delete/select-all, category selection syncing, inline cell editing,
//       adding new manual transactions, and optional AI auto-categorization.

const AUTO_APPLY_CONFIDENCE_THRESHOLD = 0.85;
const SAVE_DEBOUNCE_MS = 600;

const ALLOWED_CATEGORIES = new Set([
  "Groceries",
  "Transportation",
  "Coffee",
  "Dining & Restaurants",
  "Shopping",
  "Home",
  "Cash Withdrawals",
  "Entertainment & Subscriptions",
  "Travelling",
  "Education & Studying",
  "Other",
  "Investments",
  "Income",
]);

let IMPORT_ID = "";
const pendingSaves = new Map();
let activeSaveCount = 0;

document.addEventListener("DOMContentLoaded", () => {
  IMPORT_ID = getImportId();
  setSaveIndicator("saved");

  // Bootstraps all interactive behaviors on the preview/review table.
  initHeaderScroll();
  initTableScroll();
  initDeleteCheckboxes();
  initSelectAll();
  initCategorySelects();
  initInlineEditing();
  initAddManualTransaction();
  initDeleteImport();
  updateImportCount();

  // AI auto-categorization (silent failure by design)
  initAutoCategorizeOnLoad();
});

function initHeaderScroll() {
  // Adds a shadow to the sticky header once the page has been scrolled.
  const header = document.querySelector(".page-header");
  if (!header) return;

  window.addEventListener("scroll", () => {
    if (window.scrollY > 10) header.classList.add("scrolled");
    else header.classList.remove("scrolled");
  });
}

function initTableScroll() {
  // Adds a subtle separator effect when the table body is scrolled vertically.
  const scroll = document.querySelector(".table-scroll");
  if (!scroll) return;

  scroll.addEventListener("scroll", () => {
    if (scroll.scrollTop > 10) scroll.classList.add("scrolled-y");
    else scroll.classList.remove("scrolled-y");
  });
}

function initDeleteCheckboxes(root = document) {
  // Binds per-row "delete" checkboxes (soft delete / exclude from import).
  // Uses a data flag to avoid double-binding when rows are dynamically added.
  root.querySelectorAll(".delete-checkbox").forEach((cb) => {
    if (cb.dataset.bound === "1") return;
    cb.dataset.bound = "1";

    cb.addEventListener("change", () => {
      const row = cb.closest("tr.tx-row");
      if (!row) return;
      row.classList.toggle("deleted", cb.checked);
      updateImportCount();
    });
  });
}

function initSelectAll() {
  // Toggles all delete checkboxes at once.
  const selectAll = document.getElementById("select-all");
  if (!selectAll) return;

  selectAll.addEventListener("change", () => {
    const checkboxes = document.querySelectorAll(".delete-checkbox");
    checkboxes.forEach((cb) => {
      cb.checked = selectAll.checked;
      const row = cb.closest("tr.tx-row");
      if (row) row.classList.toggle("deleted", cb.checked);
    });
    updateImportCount();
  });
}

function updateImportCount() {
  // Updates the “X transactions to import” counter.
  const total = document.querySelectorAll(".tx-row").length;
  const deleted = document.querySelectorAll(".delete-checkbox:checked").length;
  const count = total - deleted;
  const el = document.getElementById("import-count");
  if (el) el.textContent = count;
}

function getImportId() {
  const input = document.querySelector('input[name="import_id"]');
  return input ? (input.value || "").trim() : "";
}

function setSaveIndicator(state, message) {
  const indicator = document.getElementById("save-indicator");
  if (!indicator) return;

  indicator.classList.remove("is-saving", "is-saved", "is-error");

  if (state === "saving") {
    indicator.classList.add("is-saving");
    indicator.textContent = message || "Saving...";
  } else if (state === "saved") {
    indicator.classList.add("is-saved");
    indicator.textContent = message || "Saved ✓";
  } else if (state === "error") {
    indicator.classList.add("is-error");
    indicator.textContent = message || "Error";
  } else {
    indicator.textContent = message || "";
  }
}

function initDeleteImport() {
  const btn = document.getElementById("delete-import-btn");
  if (!btn || !IMPORT_ID) return;

  btn.addEventListener("click", async () => {
    const ok = window.confirm(
      "Discard this import? All staged rows will be deleted and cannot be recovered."
    );
    if (!ok) return;

    try {
      const resp = await fetch(`/import/${encodeURIComponent(IMPORT_ID)}`, {
        method: "DELETE",
      });
      if (!resp.ok) throw new Error("Delete failed");
      window.location.href = "/upload";
    } catch {
      window.alert("Failed to discard import. Please try again.");
    }
  });
}

function queueRowSave(rowId, payload, immediate = false) {
  if (!rowId || !IMPORT_ID) return;

  const existing = pendingSaves.get(rowId) || { payload: {}, timerId: null };
  existing.payload = { ...existing.payload, ...payload };

  if (existing.timerId) {
    clearTimeout(existing.timerId);
    existing.timerId = null;
  }

  if (immediate) {
    pendingSaves.delete(rowId);
    sendRowPatch(rowId, existing.payload);
    return;
  }

  existing.timerId = setTimeout(() => {
    pendingSaves.delete(rowId);
    sendRowPatch(rowId, existing.payload);
  }, SAVE_DEBOUNCE_MS);

  pendingSaves.set(rowId, existing);
}

async function sendRowPatch(rowId, payload) {
  if (!rowId || !IMPORT_ID) return;

  activeSaveCount += 1;
  setSaveIndicator("saving");

  try {
    const resp = await fetch(`/import/${encodeURIComponent(IMPORT_ID)}/staging/${rowId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      throw new Error("Save failed");
    }

    if (activeSaveCount > 0) activeSaveCount -= 1;
    if (activeSaveCount === 0) {
      setSaveIndicator("saved");
    }
  } catch (err) {
    activeSaveCount = Math.max(0, activeSaveCount - 1);
    setSaveIndicator("error");
  }
}

function initCategorySelects(root = document) {
  // Keeps the visible <select> in sync with the hidden form input used by the backend.
  // Also marks the row as "touched" when the user changes the category manually.
  root.querySelectorAll(".category-select").forEach((sel) => {
    if (sel.dataset.bound === "1") return;
    sel.dataset.bound = "1";

    const rowId = sel.dataset.rowId;
    if (!rowId) return;

    sel.addEventListener("change", () => {
      const hidden = document.querySelector(
        `input[name="transactions[${cssEscape(rowId)}][category]"]`
      );
      if (hidden) hidden.value = sel.value;

      const row = sel.closest("tr.tx-row");
      if (row) row.dataset.categoryTouched = "1";

      queueRowSave(rowId, { category: sel.value }, true);
    });
  });
}

function initInlineEditing() {
  // Enables double-click inline editing for cells that declare a data-field attribute.
  const tbody = document.getElementById("tx-tbody");
  if (!tbody) return;

  if (tbody.dataset.dblBound === "1") return;
  tbody.dataset.dblBound = "1";

  tbody.addEventListener("dblclick", (e) => {
    const cell = e.target.closest("td[data-field]");
    if (!cell) return;

    const row = cell.closest("tr.tx-row");
    if (!row) return;

    const rowId = row.dataset.rowId;
    const field = cell.dataset.field;
    if (!rowId || !field) return;

    startEditingCell(cell, rowId, field);
  });
}

function getHiddenInput(rowId, field) {
  // Finds the hidden form input backing a given transaction field.
  return document.querySelector(
    `input[name="transactions[${cssEscape(rowId)}][${cssEscape(field)}]"]`
  );
}

function startEditingCell(cell, rowId, field) {
  // Converts a table cell into an <input>, then commits back into hidden inputs on blur/Enter.
  if (cell.classList.contains("editing")) return;

  let initialValue = "";
  const originalValue = {};

  if (field === "amount_original") {
    // show combined: "<amount> <currency>"
    const amtInp = getHiddenInput(rowId, "amount_original");
    const curInp = getHiddenInput(rowId, "currency_original");
    const a = amtInp ? amtInp.value || "" : "";
    const c = curInp ? curInp.value || "" : "";
    initialValue = a && c ? `${a} ${c}` : a || c || "";
    originalValue.amount_original = a;
    originalValue.currency_original = c;
  } else if (field === "amount_eur") {
    const inp = getHiddenInput(rowId, "amount_eur");
    if (inp) initialValue = inp.value || "";
    originalValue.amount_eur = initialValue;
  } else if (field === "notes") {
    const inp = getHiddenInput(rowId, "notes");
    if (inp) initialValue = inp.value || "";
    originalValue.notes = initialValue;
  } else {
    const inp = getHiddenInput(rowId, field);
    initialValue = inp ? inp.value || "" : cell.textContent.trim();
    originalValue[field] = initialValue;
  }

  const input = document.createElement("input");
  input.type = "text";
  input.className = "inline-input";
  input.value = initialValue;

  cell.innerHTML = "";
  cell.classList.add("editing");
  cell.appendChild(input);
  input.focus();
  input.select();

  const commitEdit = () => {
    const newVal = input.value.trim();
    cell.classList.remove("editing");

    if (field === "amount_original") {
      // accepts "123.45 USD" or just "123.45" (keeps currency) or just "USD" (keeps amount)
      const amtInp = getHiddenInput(rowId, "amount_original");
      const curInp = getHiddenInput(rowId, "currency_original");
      const prevAmt = amtInp ? amtInp.value || "" : "";
      const prevCur = curInp ? curInp.value || "" : "";

      const parsed = parseAmountCurrency(newVal);
      const nextAmt = parsed.amount !== null ? String(parsed.amount) : prevAmt;
      const nextCur = parsed.currency !== null ? parsed.currency : prevCur;

      if (amtInp) amtInp.value = nextAmt;
      if (curInp) curInp.value = nextCur;

      updateAmountOriginalCell(cell, rowId);
      queueRowSave(rowId, { amount_original: nextAmt, currency_original: nextCur }, true);
    } else if (field === "amount_eur") {
      const inp = getHiddenInput(rowId, "amount_eur");
      if (inp) inp.value = newVal;
      updateAmountEurCell(cell, rowId);
      queueRowSave(rowId, { amount_eur: newVal }, true);
    } else if (field === "notes") {
      const inp = getHiddenInput(rowId, "notes");
      if (inp) inp.value = newVal;
      updateNotesCell(cell, newVal);
      queueRowSave(rowId, { notes: newVal }, true);
    } else {
      const inp = getHiddenInput(rowId, field);
      if (inp) inp.value = newVal;
      cell.textContent = newVal;
      queueRowSave(rowId, { [field]: newVal }, true);
    }
  };

  const cancelEdit = () => {
    // Restores current hidden input value into the cell without modifying data.
    cell.classList.remove("editing");
    if (field === "amount_original") {
      const amtInp = getHiddenInput(rowId, "amount_original");
      const curInp = getHiddenInput(rowId, "currency_original");
      if (amtInp && Object.hasOwn(originalValue, "amount_original")) {
        amtInp.value = originalValue.amount_original;
      }
      if (curInp && Object.hasOwn(originalValue, "currency_original")) {
        curInp.value = originalValue.currency_original;
      }
      updateAmountOriginalCell(cell, rowId);
      queueRowSave(
        rowId,
        {
          amount_original: originalValue.amount_original,
          currency_original: originalValue.currency_original,
        },
        true
      );
    } else if (field === "amount_eur") {
      const inp = getHiddenInput(rowId, "amount_eur");
      if (inp && Object.hasOwn(originalValue, "amount_eur")) {
        inp.value = originalValue.amount_eur;
      }
      updateAmountEurCell(cell, rowId);
      queueRowSave(rowId, { amount_eur: originalValue.amount_eur }, true);
    } else if (field === "notes") {
      const inp = getHiddenInput(rowId, "notes");
      const val = Object.hasOwn(originalValue, "notes") ? originalValue.notes : "";
      if (inp) inp.value = val;
      updateNotesCell(cell, val);
      queueRowSave(rowId, { notes: val }, true);
    } else {
      const inp = getHiddenInput(rowId, field);
      const val = Object.hasOwn(originalValue, field) ? originalValue[field] : "";
      if (inp) inp.value = val;
      cell.textContent = val;
      queueRowSave(rowId, { [field]: val }, true);
    }
  };

  input.addEventListener("input", () => {
    const liveVal = input.value.trim();
    if (field === "amount_original") {
      const amtInp = getHiddenInput(rowId, "amount_original");
      const curInp = getHiddenInput(rowId, "currency_original");
      const prevAmt = amtInp ? amtInp.value || "" : "";
      const prevCur = curInp ? curInp.value || "" : "";
      const parsed = parseAmountCurrency(liveVal);
      const nextAmt = parsed.amount !== null ? String(parsed.amount) : prevAmt;
      const nextCur = parsed.currency !== null ? parsed.currency : prevCur;
      if (amtInp) amtInp.value = nextAmt;
      if (curInp) curInp.value = nextCur;
      queueRowSave(rowId, { amount_original: nextAmt, currency_original: nextCur });
    } else if (field === "amount_eur") {
      const inp = getHiddenInput(rowId, "amount_eur");
      if (inp) inp.value = liveVal;
      queueRowSave(rowId, { amount_eur: liveVal });
    } else if (field === "notes") {
      const inp = getHiddenInput(rowId, "notes");
      if (inp) inp.value = liveVal;
      queueRowSave(rowId, { notes: liveVal });
    } else {
      const inp = getHiddenInput(rowId, field);
      if (inp) inp.value = liveVal;
      queueRowSave(rowId, { [field]: liveVal });
    }
  });

  // Blur commits edits so users can click away naturally.
  input.addEventListener("blur", () => commitEdit());

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      input.blur();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelEdit();
    }
  });
}

function updateAmountOriginalCell(cell, rowId) {
  // Renders combined "<amount> <currency>" view from the underlying hidden inputs.
  const amtInp = getHiddenInput(rowId, "amount_original");
  const currInp = getHiddenInput(rowId, "currency_original");

  const amt = amtInp ? amtInp.value || "" : "";
  const curr = currInp ? currInp.value || "" : "";

  if (!amt && !curr) {
    cell.textContent = "";
    return;
  }

  cell.textContent = curr ? `${amt} ${curr}` : amt;
}

function updateAmountEurCell(cell, rowId) {
  // Renders the EUR amount as a styled pill (positive/negative/empty).
  const inp = getHiddenInput(rowId, "amount_eur");
  const raw = inp ? inp.value : null;

  cell.innerHTML = "";

  const span = document.createElement("span");
  span.classList.add("amount");

  if (raw === null || raw === "" || raw === "None") {
    span.textContent = "—";
    cell.appendChild(span);
    return;
  }

  const amt = parseFloat(raw);
  if (isNaN(amt)) {
    span.textContent = "—";
    cell.appendChild(span);
    return;
  }

  if (amt < 0) {
    span.classList.add("negative");
    span.textContent = `${amt} €`;
  } else {
    span.classList.add("positive");
    span.textContent = `+${amt} €`;
  }

  cell.appendChild(span);
}

function updateNotesCell(cell, fullValue) {
  // Notes are truncated in the table for layout; full value remains in hidden input.
  const full = fullValue || "";
  const truncated = full.length > 40 ? full.slice(0, 40) + "…" : full;
  cell.textContent = truncated;
}

/* -------------------- AI Auto-categorize -------------------- */

function initAutoCategorizeOnLoad() {
  const form = document.getElementById("preview-form");
  if (!form) return;

  if (!IMPORT_ID) return;

  // Fire and forget (silent failure)
  (async () => {
    try {
      const deleteIds = Array.from(document.querySelectorAll(".delete-checkbox:checked"))
        .map((cb) => cb.value)
        .filter(Boolean);

      const resp = await fetch(`/import/${encodeURIComponent(IMPORT_ID)}/suggest-categories`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ delete_ids: deleteIds }),
      });

      if (!resp.ok) return;

      const data = await resp.json();
      if (!data || typeof data !== "object") return;

      const suggestions = data.suggestions;
      if (!suggestions || typeof suggestions !== "object") return;

      applyCategorySuggestions(suggestions);
    } catch {
      // silent failure by design
    }
  })();
}

function applyCategorySuggestions(suggestions) {
  for (const [rowId, sug] of Object.entries(suggestions)) {
    if (!rowId) continue;
    if (!sug || typeof sug !== "object") continue;

    const row = document.querySelector(`tr.tx-row[data-row-id="${escapeAttr(rowId)}"]`);
    if (!row) continue;

    // Skip deleted rows
    if (row.classList.contains("deleted")) continue;
    const delCb = row.querySelector(".delete-checkbox");
    if (delCb && delCb.checked) continue;

    // Skip touched rows
    if (row.dataset.categoryTouched === "1") continue;

    const hidden = document.querySelector(
      `input[name="transactions[${cssEscape(rowId)}][category]"]`
    );
    if (!hidden) continue;

    // Only apply if empty (safe v0 rule)
    const current = (hidden.value || "").trim();
    if (current) continue;

    const category = typeof sug.category === "string" ? sug.category.trim() : "";
    const confidence = Number(sug.confidence);
    const reason = typeof sug.reason === "string" ? sug.reason.trim() : "";

    if (!category) continue;
    if (!ALLOWED_CATEGORIES.has(category)) continue;
    if (!Number.isFinite(confidence) || confidence < AUTO_APPLY_CONFIDENCE_THRESHOLD) continue;

    const sel = row.querySelector(".category-select");
    if (!sel) continue;

    sel.value = category;
    hidden.value = category;
    queueRowSave(rowId, { category }, true);

    const pct = Math.round(confidence * 100);
    sel.title = reason ? `${reason} (${pct}%)` : `AI suggested (${pct}%)`;

    // Mark as auto-applied (optional, for future revert)
    row.dataset.categoryAutoApplied = "1";
  }
}

/* -------------------- Manual add row -------------------- */

function initAddManualTransaction() {
  // Adds a new editable row into the preview table and ensures it participates in form submission.
  const btn = document.getElementById("add-manual-tx");
  const tbody = document.getElementById("tx-tbody");
  if (!btn || !tbody) return;

  btn.addEventListener("click", async () => {
    const created = await createManualRow();
    if (!created) return;

    const row = buildManualRow(created.id);
    tbody.appendChild(row);

    // Bind behaviors for the new row (delete toggle, category select sync, inline edits).
    initDeleteCheckboxes(row);
    initCategorySelects(row);
    initInlineEditing(row);
    updateImportCount();

    // Scroll to bottom + focus date cell for quick entry.
    row.scrollIntoView({ behavior: "smooth", block: "end" });
    const dateCell = row.querySelector('td[data-field="date"]');
    if (dateCell) startEditingCell(dateCell, String(created.id), "date");
  });
}

async function createManualRow() {
  if (!IMPORT_ID) return null;
  try {
    const resp = await fetch(`/import/${encodeURIComponent(IMPORT_ID)}/staging`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

function buildManualRow(rowId) {
  // Constructs a new transaction <tr> matching the same hidden input schema as imported rows.
  const tr = document.createElement("tr");
  tr.className = "tx-row manual-row";
  tr.dataset.rowId = rowId;

  tr.innerHTML = `
        <td class="cell-delete">
            <input type="checkbox" class="delete-checkbox checkbox" name="delete_ids" value="${escapeHtml(
              rowId
            )}">
        </td>
        <td class="cell-temp-id"><span class="temp-id">${escapeHtml(rowId)}</span></td>
        <td class="cell-date" data-field="date"></td>
        <td class="cell-account" data-field="account_name"></td>
        <td class="cell-description" data-field="description"></td>
        <td class="cell-amount-orig" data-field="amount_original"></td>
        <td class="cell-amount-eur" data-field="amount_eur"><span class="amount">—</span></td>
        <td class="cell-category">
            ${buildCategorySelectHtml(rowId)}
        </td>
        <td class="cell-notes" data-field="notes"></td>
        <td class="hidden-inputs">
            <input type="hidden" name="transactions[${escapeHtml(rowId)}][date]" value="">
            <input type="hidden" name="transactions[${escapeHtml(rowId)}][account_name]" value="">
            <input type="hidden" name="transactions[${escapeHtml(rowId)}][description]" value="">
            <input type="hidden" name="transactions[${escapeHtml(rowId)}][amount_original]" value="">
            <input type="hidden" name="transactions[${escapeHtml(rowId)}][currency_original]" value="">
            <input type="number" step="0.01" name="transactions[${escapeHtml(rowId)}][amount_eur]" value="" class="amount-eur-input">
            <input type="hidden" name="transactions[${escapeHtml(rowId)}][category]" value="">
            <input type="hidden" name="transactions[${escapeHtml(rowId)}][notes]" value="">
        </td>
    `;

  // Show subtle placeholders for manual rows (CSS uses .manual-empty for muted styling).
  tr.querySelectorAll("td[data-field]").forEach((td) => {
    td.classList.add("manual-empty");
    td.textContent = "";
  });

  // amount_original shows placeholder too
  const ao = tr.querySelector(".cell-amount-orig");
  if (ao) {
    ao.classList.add("manual-empty");
    ao.textContent = "";
  }

  return tr;
}

function buildCategorySelectHtml(rowId) {
  // Keep exact same options as template
  return `
      <select class="category-select" data-row-id="${escapeHtml(rowId)}">
        <option value="" selected>Uncategorized</option>
        <option value="Groceries">Groceries</option>
        <option value="Transportation">Transportation</option>
        <option value="Coffee">Coffee</option>
        <option value="Dining & Restaurants">Dining & Restaurants</option>
        <option value="Shopping">Shopping</option>
        <option value="Home">Home</option>
        <option value="Cash Withdrawals">Cash Withdrawals</option>
        <option value="Entertainment & Subscriptions">Entertainment & Subscriptions</option>
        <option value="Travelling">Travelling</option>
        <option value="Education & Studying">Education & Studying</option>
        <option value="Other">Other</option>
        <option value="Investments">Investments</option>
        <option value="Income">Income</option>
      </select>
    `;
}

function parseAmountCurrency(raw) {
  // Parses "amount currency" (e.g., "123.45 USD") with permissive fallbacks.
  const s = String(raw || "").trim();
  if (!s) return { amount: null, currency: null };

  // try "amount currency"
  const parts = s.split(/\s+/).filter(Boolean);

  if (parts.length === 1) {
    // either amount or currency
    const maybeAmt = normalizeNumber(parts[0]);
    if (maybeAmt !== null) return { amount: maybeAmt, currency: null };
    return { amount: null, currency: parts[0].toUpperCase() };
  }

  // prefer first token as amount, last as currency
  const maybeAmt = normalizeNumber(parts[0]);
  const cur = parts[parts.length - 1].toUpperCase();
  return { amount: maybeAmt, currency: cur || null };
}

function normalizeNumber(s) {
  // Normalizes decimal commas and converts to Number (returns null on invalid).
  const v = String(s || "").trim().replace(",", ".");
  if (!v) return null;
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  return n;
}

function cssEscape(v) {
  // Minimal safe escape for use inside attribute selectors.
  return String(v).replace(/(["\\\]\[])/g, "\\$1");
}

function escapeHtml(str) {
  // Basic HTML escaping for values injected into innerHTML templates.
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttr(str) {
  // Escapes minimal characters for attribute selectors in querySelector.
  return String(str).replace(/"/g, '\\"');
}
