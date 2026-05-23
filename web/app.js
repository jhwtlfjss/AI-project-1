const messages = document.querySelector("#messages");
const form = document.querySelector("#composer");
const input = document.querySelector("#input");
const statusText = document.querySelector("#status");
const clearButton = document.querySelector("#clear");
const params = new URLSearchParams(window.location.search);
if (params.get("token")) {
  localStorage.setItem("companionToken", params.get("token"));
}

function authHeaders() {
  const token = localStorage.getItem("companionToken") || "";
  return token ? { "X-Companion-Token": token } : {};
}

function askForToken() {
  const token = window.prompt("Access token");
  if (token) {
    localStorage.setItem("companionToken", token.trim());
    refreshStatus();
  }
}

function addBubble(role, text) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.textContent = text;
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}

async function refreshStatus() {
  try {
    const response = await fetch("/api/status", { headers: authHeaders() });
    if (response.status === 401) {
      statusText.textContent = "token required";
      askForToken();
      return;
    }
    const data = await response.json();
    const learned = data.knowledge_cache ? `${data.knowledge_entries || 0} notes` : "no cache";
    const memory = `${data.memory_facts || 0} facts`;
    const live = data.live_web ? "live web on" : "live web off";
    const realtime = data.realtime_data ? "tools on" : "tools off";
    const hub = data.hub?.hub_name ? `${data.hub.hub_name}` : "hub";
    statusText.textContent = data.ready
      ? `${hub} · ready on ${data.device} · ${memory} · ${learned} · ${live} · ${realtime}`
      : `${hub} · waiting for checkpoint · ${memory} · ${learned} · ${live} · ${realtime}`;
  } catch {
    statusText.textContent = "server unavailable";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addBubble("user", text);
  addBubble("assistant", "...");
  const pending = messages.lastElementChild;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ message: text }),
    });
    if (response.status === 401) {
      pending.textContent = "需要访问令牌。";
      askForToken();
      return;
    }
    const data = await response.json();
    pending.textContent = data.reply || "我在这里。";
  } catch {
    pending.textContent = "连接断开了。检查本地服务是否还在运行。";
  }
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    form.requestSubmit();
  }
});

clearButton.addEventListener("click", () => {
  messages.innerHTML = "";
});

addBubble("assistant", "我在这里。训练好模型后，我们就可以只在你的设备里说话。");
refreshStatus();
