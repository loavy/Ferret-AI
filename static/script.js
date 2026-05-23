let isLoading = false;
let currentTheme = localStorage.getItem("theme") || "light";
let isSidebarCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
let activeConversationId = null;
let conversations = [];

const textarea = document.getElementById("messageInput");
const messagesContainer = document.getElementById("messages");
const themeButton = document.getElementById("theme-button");
const sidebarToggle = document.getElementById("sidebar-toggle");
const clearButton = document.getElementById("clear-button");
const newConversationButton = document.getElementById("new-conversation-button");
const importButton = document.getElementById("import-button");
const importInput = document.getElementById("log-import-input");
const dropZone = document.getElementById("drop-zone");
const conversationList = document.getElementById("conversation-list");
const composer = document.getElementById("composer");
const statusPill = document.getElementById("status");
const moon = document.getElementById("moon");
const sun = document.getElementById("sun");
const sendButton = document.getElementById("send-button");

init();

function init() {
  applyTheme();
  applySidebarState();
  bindEvents();
  refreshStatus();
  loadConversations();
}

function bindEvents() {
  themeButton.addEventListener("click", () => {
    currentTheme = currentTheme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", currentTheme);
    applyTheme();
  });

  sidebarToggle.addEventListener("click", () => {
    isSidebarCollapsed = !isSidebarCollapsed;
    localStorage.setItem("sidebarCollapsed", String(isSidebarCollapsed));
    applySidebarState();
  });

  clearButton.addEventListener("click", createConversation);
  newConversationButton.addEventListener("click", createConversation);
  importButton.addEventListener("click", () => importInput.click());
  importInput.addEventListener("change", () => {
    const file = importInput.files[0];
    if (file) importLog(file);
    importInput.value = "";
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("dragging");
    });
  });

  dropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (file) importLog(file);
  });

  composer.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage();
  });

  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  textarea.addEventListener("input", resizeTextarea);
  bindPromptButtons(document);
}

function applySidebarState() {
  document.body.classList.toggle("sidebar-collapsed", isSidebarCollapsed);
  sidebarToggle.setAttribute("aria-expanded", String(!isSidebarCollapsed));
}

function applyTheme() {
  document.documentElement.setAttribute("data-theme", currentTheme);
  const isDark = currentTheme === "dark";
  sun.hidden = !isDark;
  moon.hidden = isDark;
  sun.style.display = isDark ? "block" : "none";
  moon.style.display = isDark ? "none" : "block";
}

async function refreshStatus() {
  try {
    const response = await fetch("/status");
    const data = await response.json();
    statusPill.textContent = data.online
      ? data.model_available ? "Local model ready" : "Ollama online, model missing"
      : "Ollama offline";
    statusPill.dataset.state = data.online && data.model_available ? "ok" : "warn";
  } catch {
    statusPill.textContent = "Status unavailable";
    statusPill.dataset.state = "warn";
  }
}

async function loadConversations() {
  const response = await fetch("/conversations");
  const data = await response.json();
  conversations = data.conversations;
  activeConversationId = data.active_id;
  renderConversationList();
  renderMessages(data.messages);
}

async function createConversation() {
  if (isLoading) return;
  const response = await fetch("/conversations", { method: "POST" });
  const data = await response.json();
  activeConversationId = data.conversation.id;
  await loadConversations();
  textarea.focus();
}

async function switchConversation(id) {
  if (isLoading || id === activeConversationId) return;
  const response = await fetch(`/conversations/${id}/activate`, { method: "POST" });
  const data = await response.json();
  activeConversationId = data.conversation.id;
  await loadConversations();
  textarea.focus();
}

async function importLog(file) {
  if (isLoading) return;
  const formData = new FormData();
  formData.append("log", file);

  dropZone.classList.add("working");
  try {
    const response = await fetch("/conversations/import", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not import log.");

    activeConversationId = data.conversation.id;
    await loadConversations();
    textarea.focus();
  } catch (error) {
    renderSystemMessage(error.message);
  } finally {
    dropZone.classList.remove("working");
  }
}

function renderConversationList() {
  conversationList.innerHTML = "";
  conversations.forEach((conversation) => {
    const item = document.createElement("div");
    item.className = "conversation-item";
    if (conversation.id === activeConversationId) item.classList.add("active");

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "conversation-open";

    const title = document.createElement("span");
    title.className = "conversation-title";
    title.textContent = conversation.title || "New chat";

    const meta = document.createElement("span");
    meta.className = "conversation-meta";
    meta.textContent = conversation.source === "import" ? "Imported log" : "Web chat";

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "conversation-delete";
    deleteButton.title = "Delete conversation";
    deleteButton.setAttribute("aria-label", `Delete ${conversation.title || "conversation"}`);
    deleteButton.innerHTML = `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 6h18"></path>
        <path d="M8 6V4h8v2"></path>
        <path d="M19 6l-1 14H6L5 6"></path>
        <path d="M10 11v5M14 11v5"></path>
      </svg>`;

    openButton.append(title, meta);
    openButton.addEventListener("click", () => switchConversation(conversation.id));
    deleteButton.addEventListener("click", () => deleteConversation(conversation.id));

    item.append(openButton, deleteButton);
    conversationList.appendChild(item);
  });
}

async function deleteConversation(id) {
  if (isLoading) return;
  const response = await fetch(`/conversations/${id}`, { method: "DELETE" });
  const data = await response.json();
  if (!response.ok) {
    renderSystemMessage(data.error || "Could not delete conversation.");
    return;
  }

  conversations = data.conversations;
  activeConversationId = data.active_id;
  renderConversationList();
  renderMessages(data.messages);
  textarea.focus();
}

async function sendMessage() {
  if (isLoading) return;
  const text = textarea.value.trim();
  if (!text) return;

  removeWelcome();
  addMessage(text, "user");
  textarea.value = "";
  resizeTextarea();
  setLoading(true);

  const aiMessage = createMessageDiv("ai");
  const typing = createTypingIndicator();
  aiMessage.appendChild(typing);
  messagesContainer.appendChild(aiMessage);
  scrollToBottom();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data = await response.json();
      typing.remove();
      renderFormattedMessage(aiMessage, data.content || data.error || "No response.");
      await loadConversations();
      return;
    }

    if (!response.body) throw new Error("Streaming is not available in this browser.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = "";
    let streamBuffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      streamBuffer += decoder.decode(value, { stream: true });
      const lines = streamBuffer.split("\n");
      streamBuffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = JSON.parse(line.slice(6));

        if (data.error) throw new Error(data.error);

        if (data.content) {
          fullText += data.content;
          aiMessage.textContent = fullText;
          scrollToBottom();
        }
      }
    }

    aiMessage.textContent = "";
    renderFormattedMessage(aiMessage, fullText || "I did not get any text back from the model.");
    await loadConversations();
  } catch (error) {
    aiMessage.classList.add("error");
    aiMessage.textContent = error.message || "Error connecting to Ferret.";
  } finally {
    setLoading(false);
    textarea.focus();
    scrollToBottom();
  }
}

function setLoading(value) {
  isLoading = value;
  textarea.disabled = value;
  sendButton.disabled = value;
}

function resizeTextarea() {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 220)}px`;
}

function renderMessages(messages) {
  messagesContainer.innerHTML = "";
  if (!messages.length) {
    addWelcome();
    return;
  }
  messages.forEach((message) => {
    const div = createMessageDiv(message.role === "assistant" ? "ai" : "user");
    renderFormattedMessage(div, message.content);
    messagesContainer.appendChild(div);
  });
  scrollToBottom();
}

function renderSystemMessage(text) {
  removeWelcome();
  const div = createMessageDiv("ai");
  div.classList.add("error");
  div.textContent = text;
  messagesContainer.appendChild(div);
  scrollToBottom();
}

function createMessageDiv(sender) {
  const div = document.createElement("article");
  div.className = `message ${sender}`;
  return div;
}

function addMessage(text, sender) {
  const div = createMessageDiv(sender);
  div.textContent = text;
  messagesContainer.appendChild(div);
  scrollToBottom();
}

function addWelcome() {
  const welcome = document.createElement("div");
  welcome.className = "welcome";
  welcome.innerHTML = `
    <div class="welcome-mark">Ferret</div>
    <h1>Fresh chat.</h1>
    <p>What are we thinking through?</p>
    <div class="quick-actions" aria-label="Prompt shortcuts">
      <button type="button" data-prompt="Help me think through this:\\n\\n">Think</button>
      <button type="button" data-prompt="Make this clearer and better written:\\n\\n">Write</button>
      <button type="button" data-prompt="Help me debug this:\\n\\n">Debug</button>
      <button type="button" data-prompt="Give me a small practical plan for:\\n\\n">Plan</button>
    </div>`;
  messagesContainer.appendChild(welcome);
  bindPromptButtons(welcome);
}

function bindPromptButtons(root) {
  root.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      textarea.value = button.dataset.prompt;
      resizeTextarea();
      textarea.focus();
    });
  });
}

function removeWelcome() {
  const welcome = messagesContainer.querySelector(".welcome");
  if (welcome) welcome.remove();
}

function scrollToBottom() {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function createTypingIndicator() {
  const container = document.createElement("span");
  container.className = "typing-dots";
  for (let i = 0; i < 3; i += 1) {
    container.appendChild(document.createElement("span"));
  }
  return container;
}

function renderFormattedMessage(div, text) {
  const codeBlockRegex = /```([a-zA-Z0-9_+-]*)?\n?([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    appendText(div, text.slice(lastIndex, match.index));
    div.appendChild(createCodeBlock(match[2], match[1]));
    lastIndex = codeBlockRegex.lastIndex;
  }

  appendText(div, text.slice(lastIndex));
}

function appendText(parent, text) {
  if (!text) return;
  const parts = text.split(/(\n{2,})/);
  parts.forEach((part) => {
    if (!part) return;
    if (/^\n{2,}$/.test(part)) {
      parent.appendChild(document.createElement("br"));
      return;
    }
    const span = document.createElement("span");
    span.textContent = part;
    parent.appendChild(span);
  });
}

function createCodeBlock(codeText, language = "") {
  const wrapper = document.createElement("div");
  wrapper.className = "code-block";

  const header = document.createElement("div");
  header.className = "code-header";
  header.textContent = language || "code";

  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.textContent = "Copy";
  copyBtn.addEventListener("click", async () => {
    await navigator.clipboard.writeText(codeText);
    copyBtn.textContent = "Copied";
    setTimeout(() => (copyBtn.textContent = "Copy"), 1400);
  });

  const pre = document.createElement("pre");
  const code = document.createElement("code");
  code.textContent = codeText.trimEnd();
  pre.appendChild(code);
  header.appendChild(copyBtn);
  wrapper.append(header, pre);
  return wrapper;
}
