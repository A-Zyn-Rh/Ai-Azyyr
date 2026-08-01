/* =========================================================
   AI CHATBOT — FRONTEND LOGIC (AzyyrAI Multi-Session Chat)
   ========================================================= */

(() => {
  "use strict";

  /* ---------- DOM refs ---------- */
  const appShell = document.querySelector(".app-shell");
  const sidebarOverlay = document.getElementById("sidebarOverlay");
  const sidebarOpenBtn = document.getElementById("sidebarOpen");
  const sidebarCloseBtn = document.getElementById("sidebarClose");
  const deviceIdLabel = document.getElementById("deviceIdLabel");

  const newChatBtn = document.getElementById("newChatBtn");
  const clearTopBtn = document.getElementById("clearTopBtn");
  const conversationList = document.getElementById("conversationList");

  const chatScrollArea = document.getElementById("chatScrollArea");
  const messagesList = document.getElementById("messagesList");
  const emptyState = document.getElementById("emptyState");

  const messageInput = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");
  const attachBtn = document.getElementById("attachBtn");
  const fileInput = document.getElementById("fileInput");
  const attachmentPreviewRow = document.getElementById("attachmentPreviewRow");
  const dropZone = document.getElementById("dropZone");

  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightboxImg");
  const lightboxClose = document.getElementById("lightboxClose");

  const toastContainer = document.getElementById("toastContainer");

  /* ---------- State ---------- */
  let deviceId = null;
  let currentChatId = null;
  let pendingFile = null;
  let pendingPreviewUrl = null;
  let isSending = false;

  const MAX_FILE_MB = 25;
  const ALLOWED_EXT = {
    image: ["jpg", "jpeg", "png", "gif", "webp"],
    video: ["mp4", "webm", "mov"],
    document: ["pdf", "txt", "doc", "docx", "csv", "md"],
  };

  const DOC_ICONS = {
    pdf: "fa-file-pdf",
    txt: "fa-file-lines",
    md: "fa-file-lines",
    doc: "fa-file-word",
    docx: "fa-file-word",
    csv: "fa-file-csv",
  };

  function getOrCreateDeviceId() {
    let id = localStorage.getItem("device_id");
    if (!id) {
      id =
        (crypto.randomUUID && crypto.randomUUID()) ||
        `dev-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      localStorage.setItem("device_id", id);
    }
    return id;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
  }

  function getExt(filename) {
    if (!filename || !filename.includes(".")) return "";
    return filename.split(".").pop().toLowerCase();
  }

  function detectCategory(filename) {
    const ext = getExt(filename);
    for (const [cat, exts] of Object.entries(ALLOWED_EXT)) {
      if (exts.includes(ext)) return cat;
    }
    return null;
  }

  function formatTime(isoLike) {
    try {
      const d = new Date(
        isoLike.includes("T") ? isoLike : isoLike.replace(" ", "T") + "Z",
      );
      if (isNaN(d.getTime())) return "";
      return d.toLocaleTimeString("id-ID", {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  }

  function scrollToBottom(smooth = true) {
    chatScrollArea.scrollTo({
      top: chatScrollArea.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
  }

  function showToast(message, type = "info") {
    const icon =
      type === "error"
        ? "fa-circle-exclamation"
        : type === "success"
          ? "fa-circle-check"
          : "fa-circle-info";
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `<i class="fa-solid ${icon}"></i><span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.25s ease";
      setTimeout(() => el.remove(), 260);
    }, 3800);
  }

  function toggleEmptyState() {
    const hasMessages = messagesList.children.length > 0;
    emptyState.style.display = hasMessages ? "none" : "flex";
  }

  function renderMarkdown(rawText) {
    if (!rawText) return "";
    const blocks = [];
    let text = rawText.replace(
      /```([a-zA-Z0-9]*)\n?([\s\S]*?)```/g,
      (_m, lang, code) => {
        const idx = blocks.length;
        blocks.push(
          `<pre><code class="lang-${escapeHtml(lang || "plain")}">${escapeHtml(code.trim())}</code></pre>`,
        );
        return `%%BLOCK_${idx}%%`;
      },
    );

    text = escapeHtml(text);
    text = text.replace(/`([^`\n]+)`/g, "<code>$1</code>");
    text = text.replace(/\*\*([^\*\n]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");

    const paragraphs = text
      .split(/\n{2,}/)
      .map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`);
    text = paragraphs.join("");

    return text.replace(/%%BLOCK_(\d+)%%/g, (_m, idx) => blocks[Number(idx)]);
  }

  function buildMediaHtml(filePath, fileType) {
    if (!filePath) return "";
    const filename = filePath.split("/").pop();

    if (fileType === "image") {
      return `<img src="${escapeHtml(filePath)}" alt="Gambar" class="msg-image" data-lightbox="${escapeHtml(filePath)}">`;
    }
    if (fileType === "video") {
      return `<video src="${escapeHtml(filePath)}" class="msg-video" controls preload="metadata"></video>`;
    }

    const ext = getExt(filename);
    return `
      <a class="doc-card" href="${escapeHtml(filePath)}" download target="_blank" rel="noopener">
        <span class="doc-card-icon"><i class="fa-solid ${DOC_ICONS[ext] || "fa-file"}"></i></span>
        <span class="doc-card-info">
          <span class="doc-card-name">${escapeHtml(filename)}</span>
          <span class="doc-card-sub">Klik untuk mengunduh</span>
        </span>
      </a>`;
  }

  function renderMessage(msg, { animateTyping = false } = {}) {
    const row = document.createElement("div");
    row.className = `message-row ${msg.sender}`;

    let avatarHtml =
      msg.sender === "assistant"
        ? `<div class="avatar assistant-avatar"><i class="fa-solid fa-sparkles"></i></div>`
        : "";
    const mediaHtml = buildMediaHtml(msg.file_path, msg.file_type);

    const col = document.createElement("div");
    col.className = "message-col";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    if (mediaHtml) {
      const mediaWrap = document.createElement("div");
      mediaWrap.innerHTML = mediaHtml;
      bubble.appendChild(mediaWrap.firstElementChild);
    }

    const textWrap = document.createElement("div");
    bubble.appendChild(textWrap);
    col.appendChild(bubble);

    const timeEl = document.createElement("div");
    timeEl.className = "msg-timestamp";
    timeEl.textContent = formatTime(msg.timestamp || new Date().toISOString());
    col.appendChild(timeEl);

    row.innerHTML = avatarHtml;
    row.appendChild(col);
    messagesList.appendChild(row);

    const imgEl = bubble.querySelector(".msg-image");
    if (imgEl) {
      imgEl.addEventListener("click", () =>
        openLightbox(imgEl.getAttribute("data-lightbox")),
      );
    }

    if (animateTyping && msg.sender === "assistant" && msg.content) {
      typeOutText(textWrap, msg.content);
    } else if (msg.content) {
      textWrap.innerHTML = renderMarkdown(msg.content);
    }

    toggleEmptyState();
    return row;
  }

  function typeOutText(container, fullText) {
    container.classList.add("typing-cursor");
    let i = 0;
    const interval = setInterval(() => {
      i += 3;
      container.textContent = fullText.slice(0, i);
      scrollToBottom(false);
      if (i >= fullText.length) {
        clearInterval(interval);
        container.classList.remove("typing-cursor");
        container.innerHTML = renderMarkdown(fullText);
        scrollToBottom(false);
      }
    }, 16);
  }

  function renderTypingIndicator() {
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.id = "typingIndicatorRow";
    row.innerHTML = `
      <div class="avatar assistant-avatar"><i class="fa-solid fa-sparkles"></i></div>
      <div class="message-col">
        <div class="bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>
      </div>`;
    messagesList.appendChild(row);
    scrollToBottom();
    return row;
  }

  function removeTypingIndicator() {
    const el = document.getElementById("typingIndicatorRow");
    if (el) el.remove();
  }

  /* --- MANAJEMEN SESI CHAT SIDEBAR --- */

  async function loadSidebarSessions() {
    if (!conversationList) return;
    try {
      const res = await fetch(
        `/api/sessions?device_id=${encodeURIComponent(deviceId)}`,
      );
      const data = await res.json();

      if (data.success && Array.isArray(data.sessions)) {
        conversationList.innerHTML = "";

        if (data.sessions.length === 0) {
          conversationList.innerHTML = `<div style="padding:10px 12px; font-size:12px; color:var(--text-muted);">Belum ada percakapan</div>`;
          return;
        }

        data.sessions.forEach((sess) => {
          const item = document.createElement("div");
          item.className = `conversation-item ${sess.chat_id === currentChatId ? "active" : ""}`;
          item.dataset.chatId = sess.chat_id;

          item.innerHTML = `
            <i class="fa-regular fa-message"></i>
            <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1;">${escapeHtml(sess.title)}</span>
          `;

          item.addEventListener("click", () => switchChatSession(sess.chat_id));
          conversationList.appendChild(item);
        });
      }
    } catch (err) {
      console.error("Gagal memuat sesi sidebar:", err);
    }
  }

  async function switchChatSession(chatId) {
    if (currentChatId === chatId) return;
    currentChatId = chatId;

    document.querySelectorAll(".conversation-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.chatId === chatId);
    });

    await loadHistory(chatId);
    closeSidebarOnMobile();
  }

  async function loadHistory(chatId = null) {
    try {
      messagesList.innerHTML = "";
      if (!chatId) {
        toggleEmptyState();
        return;
      }

      const res = await fetch(
        `/api/history?device_id=${encodeURIComponent(deviceId)}&chat_id=${chatId}`,
      );
      const data = await res.json();

      if (data.success && Array.isArray(data.history)) {
        data.history.forEach((msg) =>
          renderMessage(msg, { animateTyping: false }),
        );
        scrollToBottom(false);
      }
    } catch (err) {
      console.error("Gagal memuat riwayat:", err);
    } finally {
      toggleEmptyState();
    }
  }

  function startNewChat() {
    currentChatId = null;
    messagesList.innerHTML = "";
    document
      .querySelectorAll(".conversation-item")
      .forEach((el) => el.classList.remove("active"));
    toggleEmptyState();
    closeSidebarOnMobile();
  }

  async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text && !pendingFile) return;
    if (isSending) return;

    isSending = true;
    sendBtn.disabled = true;

    const filePreviewSnapshot = pendingFile;
    const previewUrlSnapshot = pendingPreviewUrl;

    const optimisticMsg = {
      sender: "user",
      content: text,
      file_path: previewUrlSnapshot || null,
      file_type: filePreviewSnapshot
        ? detectCategory(filePreviewSnapshot.name)
        : null,
      timestamp: new Date().toISOString(),
    };
    const optimisticRow = renderMessage(optimisticMsg, {
      animateTyping: false,
    });
    scrollToBottom();

    messageInput.value = "";
    autoResizeTextarea();
    clearAttachment({ keepFocus: true });
    updateSendButtonState();

    renderTypingIndicator();

    try {
      const formData = new FormData();
      formData.append("device_id", deviceId);
      if (currentChatId) formData.append("chat_id", currentChatId);
      formData.append("message", text);
      if (filePreviewSnapshot) formData.append("file", filePreviewSnapshot);

      const res = await fetch("/api/chat", { method: "POST", body: formData });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      removeTypingIndicator();

      if (!data.success) throw new Error(data.error || "Gagal mengirim pesan.");

      if (data.chat_id) {
        currentChatId = data.chat_id;
      }

      if (data.user_message && data.user_message.file_path) {
        optimisticRow.remove();
        renderMessage(data.user_message, { animateTyping: false });
      }

      if (data.assistant_message) {
        renderMessage(data.assistant_message, { animateTyping: true });
      }

      // Refresh daftar sidebar agar chat baru muncul
      await loadSidebarSessions();
      scrollToBottom();
    } catch (err) {
      console.error("Error kirim pesan:", err);
      removeTypingIndicator();
      showToast(err.message || "Gagal mengirim pesan.", "error");
    } finally {
      isSending = false;
      updateSendButtonState();
      if (previewUrlSnapshot) URL.revokeObjectURL(previewUrlSnapshot);
    }
  }

  function autoResizeTextarea() {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + "px";
  }

  function updateSendButtonState() {
    sendBtn.disabled =
      (!messageInput.value.trim() && !pendingFile) || isSending;
  }

  /* --- SUGGESTION CHIPS EVENT DELEGATION --- */
  document.addEventListener("click", (e) => {
    const chip = e.target.closest(".suggestion-chip");
    if (!chip) return;

    const text = chip.getAttribute("data-text") || chip.innerText.trim();
    if (text && messageInput) {
      messageInput.value = text;
      autoResizeTextarea();
      updateSendButtonState();
      messageInput.focus();
    }
  });

  messageInput.addEventListener("input", () => {
    autoResizeTextarea();
    updateSendButtonState();
  });

  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener("click", sendMessage);

  function clearAttachment({ keepFocus = false } = {}) {
    pendingFile = null;
    if (pendingPreviewUrl) {
      URL.revokeObjectURL(pendingPreviewUrl);
      pendingPreviewUrl = null;
    }
    attachmentPreviewRow.innerHTML = "";
    fileInput.value = "";
    updateSendButtonState();
    if (keepFocus) messageInput.focus();
  }

  attachBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    if (file) {
      pendingFile = file;
      const category = detectCategory(file.name);
      pendingPreviewUrl =
        category !== "document" ? URL.createObjectURL(file) : null;

      attachmentPreviewRow.innerHTML = `<div class="attachment-thumb"><span style="font-size:11px; padding:4px;">${escapeHtml(file.name)}</span></div>`;
      updateSendButtonState();
    }
  });

  newChatBtn.addEventListener("click", startNewChat);

  clearTopBtn.addEventListener("click", async () => {
    if (!currentChatId) return;
    if (!confirm("Hapus percakapan aktif ini?")) return;

    try {
      const res = await fetch("/api/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: deviceId, chat_id: currentChatId }),
      });
      const data = await res.json();
      if (data.success) {
        startNewChat();
        await loadSidebarSessions();
        showToast("Percakapan berhasil dihapus.", "success");
      }
    } catch (err) {
      showToast("Gagal menghapus percakapan.", "error");
    }
  });

  function isMobileViewport() {
    return window.matchMedia("(max-width: 768px)").matches;
  }
  function closeSidebarOnMobile() {
    if (isMobileViewport()) appShell.classList.add("sidebar-collapsed");
  }

  sidebarOpenBtn.addEventListener("click", () =>
    appShell.classList.remove("sidebar-collapsed"),
  );
  sidebarCloseBtn.addEventListener("click", () =>
    appShell.classList.add("sidebar-collapsed"),
  );
  sidebarOverlay.addEventListener("click", () =>
    appShell.classList.add("sidebar-collapsed"),
  );

  function openLightbox(src) {
    lightboxImg.src = src;
    lightbox.classList.add("active");
  }
  lightboxClose.addEventListener("click", () =>
    lightbox.classList.remove("active"),
  );

  function init() {
    deviceId = getOrCreateDeviceId();
    if (deviceIdLabel) {
      deviceIdLabel.textContent = deviceId.slice(0, 18) + "...";
    }

    loadSidebarSessions();
    autoResizeTextarea();
    updateSendButtonState();
  }

  init();
})();
