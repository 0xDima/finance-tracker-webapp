//upload.js

const uploadArea = document.getElementById("upload-area");
const fileInput = document.getElementById("file-input");
const fileRowsContainer = document.getElementById("file-rows");
const fileListHeader = document.getElementById("file-list-header");

const previewModal = document.getElementById("preview-modal");
const previewContent = document.getElementById("preview-content");
const previewTitle = document.getElementById("preview-title");
const previewClose = document.getElementById("preview-close");

let files = [];

function syncInputFiles() {
    const dt = new DataTransfer();
    files.forEach(f => dt.items.add(f));
    fileInput.files = dt.files;
}



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

function renderFileList() {
    fileRowsContainer.innerHTML = "";

    if (!files.length) {
        fileListHeader.style.display = "none";
        return;
    }

    fileListHeader.style.display = "block";

    files.forEach(file => {
        const row = document.createElement("div");
        row.className = "file-row";

        const name = document.createElement("div");
        name.className = "file-name";
        name.textContent = file.name;

        const meta = document.createElement("div");
        meta.className = "file-meta";
        meta.textContent = `${formatBytes(file.size)} • CSV`;

        const bankSelect = document.createElement("select");
        bankSelect.className = "file-bank-select";
        bankSelect.name = "banks"; // <-- this makes multiple values arrive as a list

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

        row.append(name, meta, bankSelect, previewBtn);
        fileRowsContainer.appendChild(row);
    });
}

function handleFiles(selectedFiles) {
    if (!selectedFiles || !selectedFiles.length) return;

    const newFiles = Array.from(selectedFiles).filter(f =>
        f.name.toLowerCase().endsWith(".csv")
    );

    files = files.concat(newFiles);

    if (files.length > 3) {
        files = files.slice(0, 3);
        alert("You can upload up to 3 CSV files.");
    }

    syncInputFiles();
    renderFileList();
}

/* --------- Preview modal ---------- */

function openModal() {
    previewModal.classList.add("is-open");
    previewModal.setAttribute("aria-hidden", "false");
}

function closeModal() {
    previewModal.classList.remove("is-open");
    previewModal.setAttribute("aria-hidden", "true");
    previewContent.textContent = "";
    previewTitle.textContent = "";
}

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

/* --------- Events ---------- */

// Click -> open file picker
uploadArea.addEventListener("click", () => fileInput.click());

// Input change
fileInput.addEventListener("change", e => {
    handleFiles(e.target.files);
    fileInput.value = "";
});

// Drag & drop on upload area
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
        if (eventName === "dragleave") {
            uploadArea.classList.remove("dragover");
        }
    });
});

uploadArea.addEventListener("drop", e => {
    const dt = e.dataTransfer;
    const droppedFiles = dt && dt.files;
    uploadArea.classList.remove("dragover");
    handleFiles(droppedFiles);
});

// Modal close
previewClose.addEventListener("click", closeModal);

previewModal.addEventListener("click", e => {
    if (e.target === previewModal) {
        closeModal();
    }
});

document.addEventListener("keydown", e => {
    if (e.key === "Escape" && previewModal.classList.contains("is-open")) {
        closeModal();
    }
});


const uploadForm = document.getElementById("upload-form");

uploadForm.addEventListener("submit", e => {
    if (!files.length) {
        e.preventDefault();
        alert("Please add at least one CSV file before continuing.");
        return;
    }

    // make sure input has the current files
    syncInputFiles();
});