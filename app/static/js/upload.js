// app/static/js/upload.js
// Role: Upload page client-side behavior — manages CSV file selection (click + drag/drop), keeps the <input type="file"> in sync,
//       renders the selected file list with per-file bank selection, provides a preview modal, validates submit, and applies top-bar scroll styling.

const uploadArea = document.getElementById("upload-area");
const fileInput = document.getElementById("file-input");
const fileRowsContainer = document.getElementById("file-rows");
const fileListContainer = document.getElementById("file-list-container");
const topBar = document.getElementById("top-bar");

const previewModal = document.getElementById("preview-modal");
const previewContent = document.getElementById("preview-content");
const previewTitle = document.getElementById("preview-title");
const previewClose = document.getElementById("preview-close");

let files = [];
let fileIdCounter = 0;

// Sync `files` array with the native <input type="file"> element so form submission includes the current selection.
function syncInputFiles() {
    const dt = new DataTransfer();
    files.forEach(f => dt.items.add(f));
    fileInput.files = dt.files;
}

// Format bytes for display in the file list (e.g., "12 KB", "3.4 MB").
function formatBytes(bytes) {
    if (!bytes && bytes !== 0) return "";
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    let value = bytes;
    while (value >= 1024 && i < units.length - 1) {
        value /= 1024;
        i++;
    }
    return `${value.toFixed(value < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
}

// Render file list UI based on current `files`.
function renderFileList() {
    fileRowsContainer.innerHTML = "";

    if (!files.length) {
        fileListContainer.classList.remove("has-files");
        return;
    }

    fileListContainer.classList.add("has-files");

    files.forEach(file => {
        const row = document.createElement("div");
        row.className = "file-row";

        const name = document.createElement("div");
        name.className = "file-name";
        name.textContent = file.name;

        const meta = document.createElement("div");
        meta.className = "file-meta";
        meta.textContent = `${formatBytes(file.size)} • CSV`;

        // Bank select name matches backend expectation ("banks") and is repeated per file row.
        const bankSelect = document.createElement("select");
        bankSelect.className = "file-bank-select";
        bankSelect.name = "banks";

        ["Select bank", "Revolut", "Monobank", "Erste"].forEach(label => {
            const opt = document.createElement("option");
            opt.textContent = label;
            opt.value = label === "Select bank" ? "" : label.toLowerCase();
            bankSelect.appendChild(opt);
        });

        const previewBtn = document.createElement("button");
        previewBtn.type = "button";
        previewBtn.className = "preview-link";
        previewBtn.textContent = "Preview";
        previewBtn.addEventListener("click", () => handlePreview(file));

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "remove-file-btn";
        removeBtn.textContent = "Remove";
        removeBtn.addEventListener("click", () => {
            files = files.filter(f => f._id !== file._id);
            syncInputFiles();
            renderFileList();
        });

        row.append(name, meta, bankSelect, previewBtn, removeBtn);
        fileRowsContainer.appendChild(row);
    });
}

// Handle file selection from either input picker or drag/drop.
function handleFiles(selectedFiles) {
    if (!selectedFiles || !selectedFiles.length) return;

    // Only accept CSV files.
    const newFiles = Array.from(selectedFiles)
        .filter(f => f.name.toLowerCase().endsWith(".csv"))
        .map(f => {
            f._id = `f_${Date.now()}_${fileIdCounter++}`;
            return f;
        });

    files = files.concat(newFiles);

    // Enforce max file count for the upload flow.
    if (files.length > 3) {
        files = files.slice(0, 3);
        alert("You can upload up to 3 CSV files.");
    }

    syncInputFiles();
    renderFileList();
}

// ===== Preview modal =====
function openModal() {
    previewModal.setAttribute("aria-hidden", "false");
}

function closeModal() {
    previewModal.setAttribute("aria-hidden", "true");
    previewContent.textContent = "";
    previewTitle.textContent = "";
}

// Reads the file client-side and shows a small snippet (first ~40 lines).
function handlePreview(file) {
    const reader = new FileReader();
    reader.onload = e => {
        const text = e.target.result || "";
        const lines = text.split(/\r?\n/).slice(0, 40);
        previewContent.textContent = lines.join("\n") || "File is empty or could not be previewed.";
        previewTitle.textContent = file.name;
        openModal();
    };
    reader.onerror = () => {
        previewContent.textContent = "Unable to read this file.";
        previewTitle.textContent = file.name;
        openModal();
    };
    reader.readAsText(file);
}

// ===== Events =====

// Click on the dropzone opens native file picker.
uploadArea.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    fileInput.click();
});

// Native file picker selection.
fileInput.addEventListener("change", e => {
    handleFiles(e.target.files);
});

// Drag/drop UI state (adds/removes .dragover class).
["dragenter", "dragover"].forEach(eventName => {
    uploadArea.addEventListener(eventName, e => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add("dragover");
    });
});

["dragleave", "drop"].forEach(eventName => {
    uploadArea.addEventListener(eventName, e => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove("dragover");
    });
});

// Handle dropped files.
uploadArea.addEventListener("drop", e => {
    e.preventDefault();
    e.stopPropagation();
    const dt = e.dataTransfer;
    const droppedFiles = dt && dt.files;
    uploadArea.classList.remove("dragover");
    handleFiles(droppedFiles);
});

// Modal close controls.
previewClose.addEventListener("click", closeModal);

previewModal.addEventListener("click", e => {
    if (e.target === previewModal || e.target.classList.contains("modal-backdrop")) {
        closeModal();
    }
});

document.addEventListener("keydown", e => {
    if (e.key === "Escape" && previewModal.getAttribute("aria-hidden") === "false") {
        closeModal();
    }
});

const uploadForm = document.getElementById("upload-form");

// Prevent submit when no files are selected.
uploadForm.addEventListener("submit", e => {
    if (!files.length) {
        e.preventDefault();
        alert("Please add at least one CSV file before continuing.");
        return;
    }
    syncInputFiles();
});

function initDraftDeletes() {
    const buttons = document.querySelectorAll(".draft-delete-btn");
    if (!buttons.length) return;

    buttons.forEach(btn => {
        btn.addEventListener("click", async () => {
            const importId = btn.dataset.importId;
            if (!importId) return;
            const ok = window.confirm("Delete this draft import? This cannot be undone.");
            if (!ok) return;

            try {
                const resp = await fetch(`/import/${encodeURIComponent(importId)}`, {
                    method: "DELETE",
                });
                if (!resp.ok) throw new Error("Delete failed");
                const row = btn.closest(".draft-row");
                if (row) row.remove();
            } catch {
                window.alert("Failed to delete draft import.");
            }
        });
    });
}

initDraftDeletes();


// Sticky header shadow on scroll (visual only).
let lastScrollTop = 0;
window.addEventListener("scroll", () => {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    if (scrollTop > 10) {
        topBar.classList.add("scrolled");
    } else {
        topBar.classList.remove("scrolled");
    }
    lastScrollTop = scrollTop;
}, { passive: true });
