const API_BASE = "https://hendri.pythonanywhere.com";

const dropZone = document.getElementById("dropZone");
const browseBtn = document.getElementById("browseBtn");
const fileInput = document.getElementById("fileInput");
const fileName = document.getElementById("fileName");
const sheetArea = document.getElementById("sheetArea");
const pageSelect = document.getElementById("pageSelect");
const convertBtn = document.getElementById("convertBtn");
const statusArea = document.getElementById("statusArea");
const statusText = document.getElementById("statusText");
const progressText = document.getElementById("progressText");
const progressBar = document.getElementById("progressBar");
const downloadBtn = document.getElementById("downloadBtn");
const message = document.getElementById("message");

let selectedFile = null;
let pageCount = 1;

browseBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) handleFile(file);
});

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    dropZone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    dropZone.classList.remove("dragover");
  });
});

dropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (file) handleFile(file);
});

async function handleFile(file) {
  resetResult();
  message.textContent = "";

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    message.textContent = "Please select a PDF file.";
    return;
  }

  selectedFile = file;
  fileName.textContent = `${file.name} • ${formatBytes(file.size)}`;
  convertBtn.disabled = true;

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    message.textContent = "Reading PDF...";
    const response = await fetch(`${API_BASE}/pdf-info`, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }

    const info = await response.json();
    pageCount = Number(info.page_count || 1);

    pageSelect.innerHTML = "";

    if (pageCount > 1) {
      for (let i = 1; i <= pageCount; i++) {
        const option = document.createElement("option");
        option.value = i;
        option.textContent = `Sheet ${i}`;
        pageSelect.appendChild(option);
      }
      sheetArea.classList.remove("hidden");
    } else {
      sheetArea.classList.add("hidden");
    }

    convertBtn.disabled = false;
    message.textContent = `${pageCount} page${pageCount > 1 ? "s" : ""} detected.`;
  } catch (error) {
    selectedFile = null;
    message.textContent = `Unable to read PDF: ${error.message}`;
  }
}

convertBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  resetResult();
  statusArea.classList.remove("hidden");
  convertBtn.disabled = true;
  statusText.textContent = "Uploading and converting...";
  setProgress(10);

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("page", pageSelect.value || "1");

  try {
    setProgress(25);

    const response = await fetch(`${API_BASE}/convert`, {
      method: "POST",
      body: formData
    });

    setProgress(75);

    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    let filename = selectedFile.name.replace(/\.pdf$/i, "");
    filename += `_page_${pageSelect.value || "1"}.dxf`;

    downloadBtn.href = url;
    downloadBtn.download = filename;
    downloadBtn.classList.remove("hidden");

    setProgress(100);
    statusText.textContent = "Conversion complete";
    message.textContent = `${filename} is ready.`;
  } catch (error) {
    setProgress(0);
    statusText.textContent = "Conversion failed";
    message.textContent = error.message;
  } finally {
    convertBtn.disabled = false;
  }
});

function setProgress(value) {
  progressBar.style.width = `${value}%`;
  progressText.textContent = `${value}%`;
}

function resetResult() {
  statusArea.classList.add("hidden");
  downloadBtn.classList.add("hidden");
  if (downloadBtn.href.startsWith("blob:")) {
    URL.revokeObjectURL(downloadBtn.href);
  }
  setProgress(0);
}

async function getErrorMessage(response) {
  try {
    const data = await response.json();
    return data.detail || `Server error (${response.status})`;
  } catch {
    return `Server error (${response.status})`;
  }
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
