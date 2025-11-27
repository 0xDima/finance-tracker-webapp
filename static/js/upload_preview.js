// upload_preview.js
document.addEventListener("DOMContentLoaded", () => {
    setupDeleteCheckboxes();
    setupCategorySelects();
    setupInlineEditing();
});

/**
 * Toggle visual strike-through on rows marked for delete.
 */
function setupDeleteCheckboxes() {
    document.querySelectorAll(".delete-checkbox").forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
            const row = checkbox.closest("tr.main-row");
            if (!row) return;
            row.classList.toggle("row-marked-for-delete", checkbox.checked);
        });
    });
}

/**
 * Keep hidden category input in sync with category <select>.
 */
function setupCategorySelects() {
    document.querySelectorAll(".category-select").forEach((selectEl) => {
        const tempId = selectEl.dataset.tempId;
        if (!tempId) return;

        selectEl.addEventListener("change", () => {
            const hidden = document.querySelector(
                `input[name="transactions[${tempId}][category]"]`
            );
            if (hidden) {
                hidden.value = selectEl.value;
            }
        });
    });
}

/**
 * Setup inline editing for cells with data-field (except category which uses select).
 * Double-click on a cell to edit.
 */
function setupInlineEditing() {
    document.querySelectorAll("tr.main-row").forEach((row) => {
        const tempId = row.dataset.tempId;
        if (!tempId) return;

        row.querySelectorAll("td[data-field]").forEach((cell) => {
            const field = cell.dataset.field;
            if (!field) return;
            if (field === "category") return; // handled by <select>

            cell.addEventListener("dblclick", () => {
                startEditingCell(cell, tempId, field);
            });
        });
    });
}

/**
 * Helper to get hidden input for a transaction field.
 */
function getHiddenInput(tempId, field) {
    return document.querySelector(
        `input[name="transactions[${tempId}][${field}]"]`
    );
}

/**
 * Start inline editing for a specific cell/field.
 */
function startEditingCell(cell, tempId, field) {
    if (cell.classList.contains("editing")) return;

    // Determine initial value for input from hidden inputs (source of truth)
    let initialValue = "";

    if (field === "amount_original") {
        const amtInput = getHiddenInput(tempId, "amount_original");
        if (amtInput) {
            initialValue = amtInput.value || "";
        }
    } else if (field === "amount_eur") {
        const amtEurInput = getHiddenInput(tempId, "amount_eur");
        if (amtEurInput) {
            initialValue = amtEurInput.value || "";
        }
    } else if (field === "notes") {
        const notesInput = getHiddenInput(tempId, "notes");
        if (notesInput) {
            initialValue = notesInput.value || "";
        }
    } else {
        const hidden = getHiddenInput(tempId, field);
        if (hidden) {
            initialValue = hidden.value || "";
        } else {
            initialValue = cell.textContent.trim();
        }
    }

    // Create input
    const input = document.createElement("input");
    input.type = "text";
    input.className = "inline-input";
    input.value = initialValue;

    // Replace cell content with input
    cell.innerHTML = "";
    cell.classList.add("editing");
    cell.appendChild(input);
    input.focus();
    input.select();

    const commitEdit = () => {
        const newVal = input.value.trim();
        cell.classList.remove("editing");

        // Update hidden inputs based on field
        if (field === "amount_original") {
            const amtInput = getHiddenInput(tempId, "amount_original");
            if (amtInput) {
                amtInput.value = newVal;
            }
            // currency_original is not edited inline; we keep it as-is
            updateAmountOriginalCell(cell, tempId);
        } else if (field === "amount_eur") {
            const amtEurInput = getHiddenInput(tempId, "amount_eur");
            if (amtEurInput) {
                amtEurInput.value = newVal;
            }
            updateAmountEurCell(cell, tempId);
        } else if (field === "notes") {
            const notesInput = getHiddenInput(tempId, "notes");
            if (notesInput) {
                notesInput.value = newVal;
            }
            updateNotesCell(cell, newVal);
        } else {
            const hidden = getHiddenInput(tempId, field);
            if (hidden) {
                hidden.value = newVal;
            }
            cell.textContent = newVal;
        }
    };

    const cancelEdit = () => {
        cell.classList.remove("editing");
        // Restore from hidden inputs
        if (field === "amount_original") {
            updateAmountOriginalCell(cell, tempId);
        } else if (field === "amount_eur") {
            updateAmountEurCell(cell, tempId);
        } else if (field === "notes") {
            const notesInput = getHiddenInput(tempId, "notes");
            const fullVal = notesInput ? notesInput.value || "" : "";
            updateNotesCell(cell, fullVal);
        } else {
            const hidden = getHiddenInput(tempId, field);
            const val = hidden ? hidden.value || "" : "";
            cell.textContent = val;
        }
    };

    input.addEventListener("blur", () => {
        commitEdit();
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            input.blur(); // triggers commitEdit via blur
        } else if (e.key === "Escape") {
            e.preventDefault();
            cancelEdit();
        }
    });
}

/**
 * Re-render the Original amount cell from hidden amount_original + currency_original.
 */
function updateAmountOriginalCell(cell, tempId) {
    const amtInput = getHiddenInput(tempId, "amount_original");
    const currInput = getHiddenInput(tempId, "currency_original");

    const amount = amtInput ? (amtInput.value || "") : "";
    const currency = currInput ? (currInput.value || "") : "";

    if (!amount && !currency) {
        cell.textContent = "";
        return;
    }

    cell.textContent = currency ? `${amount} ${currency}` : amount;
}

/**
 * Re-render the EUR amount cell with pill styling (+/-) from hidden amount_eur.
 */
function updateAmountEurCell(cell, tempId) {
    const amtInput = getHiddenInput(tempId, "amount_eur");
    const raw = amtInput ? amtInput.value : null;

    cell.innerHTML = "";

    const span = document.createElement("span");
    span.classList.add("amount");

    if (raw === null || raw === "" || raw === "None") {
        span.textContent = "--";
        cell.appendChild(span);
        return;
    }

    const amt = parseFloat(raw);
    if (isNaN(amt)) {
        span.textContent = "--";
        cell.appendChild(span);
        return;
    }

    if (amt < 0) {
        span.classList.add("amount-negative");
        span.textContent = `${amt} €`;
    } else {
        span.classList.add("amount-positive");
        span.textContent = `+${amt} €`;
    }

    cell.appendChild(span);
}

/**
 * Re-render notes cell with truncated value (but keep full in hidden input).
 */
function updateNotesCell(cell, fullValue) {
    const full = fullValue || "";
    const truncated =
        full.length > 40 ? full.slice(0, 40) + "…" : full;
    cell.textContent = truncated;
}