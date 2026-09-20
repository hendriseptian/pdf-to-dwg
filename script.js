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

/* =========================
   TEMP MANAGER ELEMENTS
========================= */

const tempRefreshBtn = document.getElementById("tempRefreshBtn");
const tempDeleteAllBtn = document.getElementById("tempDeleteAllBtn");
const tempList = document.getElementById("tempList");
const tempTotalFiles = document.getElementById("tempTotalFiles");
const tempTotalSize = document.getElementById("tempTotalSize");
const tempMessage = document.getElementById("tempMessage");

let selectedFile = null;
let pageCount = 1;

/* =========================
   FILE SELECT
========================= */

browseBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", (event) => {
  const file = event.target.files[0];

  if (file) {
    handleFile(file);
  }
});

/* =========================
   DRAG & DROP
========================= */

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

  if (file) {
    handleFile(file);
  }
});

/* =========================
   READ PDF
========================= */

async function handleFile(file) {
  resetResult();
  message.textContent = "";

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    message.textContent = "Please select a PDF file.";
    return;
  }

  selectedFile = file;

  fileName.textContent =
    `${file.name} • ${formatBytes(file.size)}`;

  convertBtn.disabled = true;

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    message.textContent = "Reading PDF...";

    const response = await fetch(
      `${API_BASE}/pdf-info`,
      {
        method: "POST",
        body: formData
      }
    );

    if (!response.ok) {
      throw new Error(
        await getErrorMessage(response)
      );
    }

    const info = await response.json();

    pageCount = Number(
      info.page_count || 1
    );

    pageSelect.innerHTML = "";

    if (pageCount > 1) {

      for (let i = 1; i <= pageCount; i++) {

        const option =
          document.createElement("option");

        option.value = i;
        option.textContent = `Sheet ${i}`;

        pageSelect.appendChild(option);
      }

      sheetArea.classList.remove("hidden");

    } else {

      sheetArea.classList.add("hidden");
    }

    convertBtn.disabled = false;

    message.textContent =
      `${pageCount} page${pageCount > 1 ? "s" : ""} detected.`;

  } catch (error) {

    selectedFile = null;

    message.textContent =
      `Unable to read PDF: ${error.message}`;
  }
}

/* =========================
   CONVERT
========================= */

convertBtn.addEventListener("click", async () => {

  if (!selectedFile) {
    return;
  }

  resetResult();

  statusArea.classList.remove("hidden");

  convertBtn.disabled = true;

  statusText.textContent =
    "Uploading and converting...";

  setProgress(10);

  const formData = new FormData();

  formData.append(
    "file",
    selectedFile
  );

  formData.append(
    "page",
    pageSelect.value || "1"
  );

  try {

    setProgress(25);

    const response =
      await fetch(
        `${API_BASE}/convert`,
        {
          method: "POST",
          body: formData
        }
      );

    setProgress(75);

    if (!response.ok) {

      throw new Error(
        await getErrorMessage(response)
      );
    }

    const blob =
      await response.blob();

    const url =
      URL.createObjectURL(blob);

    let filename =
      selectedFile.name.replace(
        /\.pdf$/i,
        ""
      );

    filename +=
      `_page_${pageSelect.value || "1"}.dxf`;

    downloadBtn.href = url;

    downloadBtn.download =
      filename;

    downloadBtn.classList.remove(
      "hidden"
    );

    setProgress(100);

    statusText.textContent =
      "Conversion complete";

    message.textContent =
      `${filename} is ready.`;

  } catch (error) {

    setProgress(0);

    statusText.textContent =
      "Conversion failed";

    message.textContent =
      error.message;

  } finally {

    convertBtn.disabled = false;

  }
});

/* =========================
   PROGRESS
========================= */

function setProgress(value) {

  progressBar.style.width =
    `${value}%`;

  progressText.textContent =
    `${value}%`;
}

/* =========================
   RESET RESULT
========================= */

function resetResult() {

  statusArea.classList.add(
    "hidden"
  );

  downloadBtn.classList.add(
    "hidden"
  );

  if (
    downloadBtn.href.startsWith(
      "blob:"
    )
  ) {

    URL.revokeObjectURL(
      downloadBtn.href
    );
  }

  setProgress(0);
}

/* =========================
   ERROR MESSAGE
========================= */

async function getErrorMessage(response) {

  try {

    const data =
      await response.json();

    return (
      data.detail ||
      `Server error (${response.status})`
    );

  } catch {

    return `Server error (${response.status})`;
  }
}

/* =========================
   FORMAT BYTES
========================= */

function formatBytes(bytes) {

  if (!Number.isFinite(bytes)) {
    return "0 B";
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {

    return `${(
      bytes / 1024
    ).toFixed(1)} KB`;
  }

  return `${(
    bytes /
    1024 /
    1024
  ).toFixed(1)} MB`;
}

/* =========================================================
   TEMP FILE MANAGER
========================================================= */

/* =========================
   LOAD TEMP FILES
========================= */

async function loadTempFiles() {

  if (!tempList) {
    return;
  }

  tempMessage.textContent =
    "Loading temporary files...";

  tempList.innerHTML = "";

  try {

    const response =
      await fetch(
        `${API_BASE}/temp-files`
      );

    if (!response.ok) {

      throw new Error(
        await getErrorMessage(response)
      );
    }

    const data =
      await response.json();

    updateTempSummary(data);

    if (
      !data.files ||
      data.files.length === 0
    ) {

      tempList.innerHTML = `
        <div class="temp-empty">
          No temporary files.
        </div>
      `;

      tempMessage.textContent =
        "Temp folder is empty.";

      return;
    }

    data.files.forEach(
      (file) => {

        const item =
          document.createElement(
            "div"
          );

        item.className =
          "temp-file-item";

        item.innerHTML = `
          <div class="temp-file-info">
            <div class="temp-file-name">
              ${escapeHtml(file.name)}
            </div>

            <div class="temp-file-size">
              ${formatBytes(file.size)}
            </div>
          </div>

          <button
            class="temp-delete-btn"
            type="button"
            data-filename="${escapeHtml(file.name)}"
          >
            DELETE
          </button>
        `;

        const deleteBtn =
          item.querySelector(
            ".temp-delete-btn"
          );

        deleteBtn.addEventListener(
          "click",
          () => {
            deleteTempFile(
              file.name
            );
          }
        );

        tempList.appendChild(item);
      }
    );

    tempMessage.textContent =
      `${data.total_files} temporary file${data.total_files !== 1 ? "s" : ""}.`;

  } catch (error) {

    tempMessage.textContent =
      `Unable to load temp files: ${error.message}`;

    tempList.innerHTML = `
      <div class="temp-error">
        ${escapeHtml(error.message)}
      </div>
    `;
  }
}

/* =========================
   UPDATE SUMMARY
========================= */

function updateTempSummary(data) {

  if (tempTotalFiles) {

    tempTotalFiles.textContent =
      data.total_files || 0;
  }

  if (tempTotalSize) {

    tempTotalSize.textContent =
      formatBytes(
        data.total_size || 0
      );
  }
}

/* =========================
   DELETE ONE FILE
========================= */

async function deleteTempFile(
  filename
) {

  const confirmed =
    confirm(
      `Delete this temporary file?\n\n${filename}`
    );

  if (!confirmed) {
    return;
  }

  tempMessage.textContent =
    "Deleting file...";

  try {

    const response =
      await fetch(
        `${API_BASE}/temp-files/${encodeURIComponent(filename)}`,
        {
          method: "DELETE"
        }
      );

    if (!response.ok) {

      throw new Error(
        await getErrorMessage(response)
      );
    }

    await loadTempFiles();

  } catch (error) {

    tempMessage.textContent =
      `Delete failed: ${error.message}`;
  }
}

/* =========================
   DELETE ALL
========================= */

async function deleteAllTempFiles() {

  const confirmed =
    confirm(
      "Delete ALL temporary files?\n\nThis action cannot be undone."
    );

  if (!confirmed) {
    return;
  }

  tempMessage.textContent =
    "Deleting all temporary files...";

  try {

    const response =
      await fetch(
        `${API_BASE}/temp-files`,
        {
          method: "DELETE"
        }
      );

    if (!response.ok) {

      throw new Error(
        await getErrorMessage(response)
      );
    }

    await loadTempFiles();

  } catch (error) {

    tempMessage.textContent =
      `Delete all failed: ${error.message}`;
  }
}

/* =========================
   BUTTON EVENTS
========================= */

if (tempRefreshBtn) {

  tempRefreshBtn.addEventListener(
    "click",
    loadTempFiles
  );
}

if (tempDeleteAllBtn) {

  tempDeleteAllBtn.addEventListener(
    "click",
    deleteAllTempFiles
  );
}

/* =========================
   HTML ESCAPE
========================= */

function escapeHtml(value) {

  return String(value)
    .replace(
      /&/g,
      "&amp;"
    )
    .replace(
      /</g,
      "&lt;"
    )
    .replace(
      />/g,
      "&gt;"
    )
    .replace(
      /"/g,
      "&quot;"
    )
    .replace(
      /'/g,
      "&#039;"
    );
}

/* =========================
   INITIAL TEMP LOAD
========================= */

document.addEventListener(
  "DOMContentLoaded",
  () => {

    loadTempFiles();

  }
);
