import * as vscode from "vscode";
import { randomBytes } from "crypto";

const API_BASE_URL = "http://127.0.0.1:8000/api";

type BackendData = Record<string, unknown>;

export function activate(context: vscode.ExtensionContext): void {
  const provider = new CodeMindChatProvider(context.extensionUri);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "codemind-ai.chatView",
      provider,
      {
        webviewOptions: {
          retainContextWhenHidden: true,
        },
      },
    ),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("codemind-ai.openChat", async () => {
      await vscode.commands.executeCommand(
        "workbench.view.extension.codemind-ai",
      );
    }),
  );
}

export function deactivate(): void {}

class CodeMindChatProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;

  constructor(private readonly extensionUri: vscode.Uri) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
    };

    webviewView.webview.html = this.getHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage(
      async (message: {
        type?: string;
        text?: string;
        approvalId?: string;
      }) => {
        await this.handleMessage(webviewView, message);
      },
    );
  }

  private async handleMessage(
    view: vscode.WebviewView,
    message: {
      type?: string;
      text?: string;
      approvalId?: string;
    },
  ): Promise<void> {
    try {
      if (message.type === "ready") {
        return;
      }

      const workspaceFolder = vscode.workspace.workspaceFolders?.[0];

      if (!workspaceFolder) {
        throw new Error("Please open a project folder in VS Code first.");
      }

      const workspace = workspaceFolder.uri.fsPath;
      let endpoint: string;
      let body: Record<string, unknown>;
      let loadingText = "CodeMind is thinking...";

      if (message.type === "sendMessage") {
        const text = message.text?.trim();

        if (!text) {
          return;
        }

        endpoint = "chat";
        body = { message: text, workspace };
      } else if (message.type === "approve" || message.type === "deny") {
        if (!message.approvalId) {
          throw new Error("Approval ID is missing.");
        }

        endpoint = message.type === "approve" ? "chat/approve" : "chat/deny";

        body = {
          approval_id: message.approvalId,
          workspace,
        };

        loadingText =
          message.type === "approve"
            ? "Executing approved actions..."
            : "Cancelling actions...";
      } else {
        return;
      }

      view.webview.postMessage({
        type: "loading",
        text: loadingText,
      });

      let response: Response;

      try {
        response = await fetch(API_BASE_URL + "/" + endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(180000),
        });
      } catch (error) {
        if (error instanceof Error && error.name === "TimeoutError") {
          throw new Error(
            "Backend request timed out. Check that FastAPI and Ollama are running.",
          );
        }

        throw new Error(
          "Cannot connect to CodeMind backend at " +
            API_BASE_URL +
            ". Start FastAPI and try again.",
        );
      }

      let rawData: unknown;

      try {
        rawData = await response.json();
      } catch {
        throw new Error(
          "Backend returned an invalid response. Check the FastAPI terminal.",
        );
      }

      if (
        typeof rawData !== "object" ||
        rawData === null ||
        Array.isArray(rawData)
      ) {
        throw new Error("Invalid response received from backend.");
      }

      const data = rawData as BackendData;

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "API error: " + response.status,
        );
      }

      view.webview.postMessage({
        type: "apiResponse",
        action: message.type,
        data,
      });
    } catch (error) {
      view.webview.postMessage({
        type: "assistantMessage",
        text:
          "CodeMind error: " +
          (error instanceof Error ? error.message : "Unknown error"),
      });
    } finally {
      view.webview.postMessage({ type: "requestFinished" });
    }
  }

  private getHtml(webview: vscode.Webview): string {
    const logoUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "media", "codemind.svg"),
    );

    const nonce = randomBytes(16).toString("hex");

    return /* html */ `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; img-src ${webview.cspSource}; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';"
  >

  <title>CodeMind AI</title>

  <style>
    * { box-sizing: border-box; }

    html, body {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
    }

    body {
      color: var(--vscode-foreground);
      background: var(--vscode-sideBar-background);
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
    }

    button, textarea { font: inherit; }
    button { color: inherit; }

    .app {
      display: flex;
      flex-direction: column;
      width: 100%;
      height: 100%;
      min-height: 0;
      overflow: hidden;
    }

    .header {
      display: flex;
      flex: 0 0 auto;
      align-items: center;
      gap: 10px;
      padding: 12px;
      border-bottom: 1px solid var(--vscode-panel-border);
    }

    .logo {
      width: 38px;
      height: 38px;
      flex: 0 0 38px;
      display: grid;
      place-items: center;
      border: 1px solid var(--vscode-panel-border);
      border-radius: 10px;
      overflow: hidden;
    }

    .logo img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }

    .brand { flex: 1; min-width: 0; }

    .title {
      font-size: 14px;
      font-weight: 600;
    }

    .subtitle {
      margin-top: 3px;
      color: var(--vscode-descriptionForeground);
      font-size: 11px;
    }

    .icon-button {
      width: 32px;
      height: 32px;
      display: grid;
      place-items: center;
      border: 1px solid var(--vscode-button-border, var(--vscode-panel-border));
      border-radius: 7px;
      background: transparent;
      cursor: pointer;
      font-size: 20px;
    }

    .icon-button:hover {
      background: var(--vscode-toolbar-hoverBackground);
    }

    .conversation {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
    }

    .welcome {
      min-height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 20px 12px;
    }

    .welcome-center { text-align: center; }

    .hero-logo {
      width: 72px;
      height: 72px;
      margin: 0 auto 18px;
    }

    .hero-logo img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }

    .welcome h2 {
      margin: 0 0 10px;
      font-size: 19px;
      line-height: 1.35;
    }

    .muted {
      color: var(--vscode-descriptionForeground);
      line-height: 1.55;
    }

    .suggestions {
      display: grid;
      gap: 8px;
      margin-top: 24px;
    }

    .suggestion {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      padding: 10px;
      text-align: left;
      border: 1px solid var(--vscode-panel-border);
      border-radius: 9px;
      background: var(--vscode-sideBar-background);
      cursor: pointer;
    }

    .suggestion:hover {
      background: var(--vscode-list-hoverBackground);
      border-color: var(--vscode-focusBorder);
    }

    .suggestion-icon {
      width: 30px;
      height: 30px;
      flex: 0 0 30px;
      display: grid;
      place-items: center;
      border-radius: 7px;
      background: var(--vscode-textBlockQuote-background);
    }

    .suggestion-title {
      font-size: 12px;
      font-weight: 600;
    }

    .suggestion-desc {
      margin-top: 3px;
      color: var(--vscode-descriptionForeground);
      font-size: 11px;
    }

    #messages {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 16px 12px;
    }

    .message {
      display: flex;
      align-items: flex-start;
      gap: 9px;
      line-height: 1.6;
      overflow-wrap: anywhere;
    }

    .avatar {
      width: 28px;
      height: 28px;
      flex: 0 0 28px;
      display: grid;
      place-items: center;
      border-radius: 8px;
      background: var(--vscode-textBlockQuote-background);
      overflow: hidden;
      font-size: 10px;
      font-weight: 700;
    }

    .message.user .avatar {
      background: #2878e8;
      color: white;
    }

    .avatar img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }

    .message-content {
      flex: 1;
      min-width: 0;
      padding-top: 3px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .message-name {
      margin-bottom: 4px;
      color: var(--vscode-descriptionForeground);
      font-size: 11px;
      font-weight: 600;
    }

    .loading-row {
      display: flex;
      align-items: center;
      gap: 9px;
      padding: 0 12px 16px;
      color: var(--vscode-descriptionForeground);
      font-size: 12px;
    }

    .dots { display: inline-flex; gap: 4px; }

    .dots span {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: var(--vscode-progressBar-background, #2878e8);
      animation: pulse 1s infinite ease-in-out;
    }

    .dots span:nth-child(2) { animation-delay: .15s; }
    .dots span:nth-child(3) { animation-delay: .3s; }

    @keyframes pulse {
      0%, 80%, 100% { opacity: .25; transform: translateY(0); }
      40% { opacity: 1; transform: translateY(-3px); }
    }

    .approval-card {
      margin-top: 12px;
      padding: 12px;
      border: 1px solid var(--vscode-inputValidation-warningBorder, #c99b35);
      border-radius: 9px;
      background: var(--vscode-inputValidation-warningBackground);
    }

    .approval-title {
      margin-bottom: 6px;
      font-weight: 600;
    }

    .approval-description {
      margin-bottom: 12px;
      color: var(--vscode-descriptionForeground);
      font-size: 12px;
      line-height: 1.5;
    }

    .approval-list {
      margin: 0 0 12px;
      padding-left: 20px;
      font-size: 12px;
      overflow-wrap: anywhere;
    }

    .approval-actions { display: flex; gap: 8px; }

    .approval-button {
      flex: 1;
      min-height: 32px;
      padding: 6px 10px;
      border: 1px solid transparent;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
    }

    .approve-button {
      color: var(--vscode-button-foreground);
      background: var(--vscode-button-background);
    }

    .approve-button:hover {
      background: var(--vscode-button-hoverBackground);
    }

    .deny-button {
      color: var(--vscode-button-secondaryForeground);
      background: var(--vscode-button-secondaryBackground);
      border-color: var(--vscode-panel-border);
    }

    .approval-button:disabled { opacity: .5; cursor: wait; }

    .approval-status {
      margin-top: 10px;
      color: var(--vscode-descriptionForeground);
      font-size: 11px;
    }

    .composer-wrap {
      flex: 0 0 auto;
      padding: 10px 12px 12px;
      border-top: 1px solid var(--vscode-panel-border);
      background: var(--vscode-sideBar-background);
    }

    .composer {
      padding: 8px;
      border: 1px solid var(--vscode-input-border, var(--vscode-panel-border));
      border-radius: 10px;
      background: var(--vscode-input-background);
    }

    .composer:focus-within {
      border-color: var(--vscode-focusBorder);
    }

    textarea {
      display: block;
      width: 100%;
      min-height: 56px;
      max-height: 160px;
      resize: vertical;
      padding: 4px;
      border: 0;
      outline: 0;
      background: transparent;
      color: var(--vscode-input-foreground);
      line-height: 1.5;
    }

    textarea::placeholder {
      color: var(--vscode-input-placeholderForeground);
    }

    .actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding-top: 5px;
    }

    .hint {
      color: var(--vscode-descriptionForeground);
      font-size: 10px;
    }

    #send {
      width: 32px;
      height: 32px;
      border: 0;
      border-radius: 7px;
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      cursor: pointer;
      font-size: 18px;
    }

    #send:hover { background: var(--vscode-button-hoverBackground); }
    #send:disabled { opacity: .5; cursor: wait; }
    [hidden] { display: none !important; }
  </style>
</head>

<body>
  <div class="app">
    <header class="header">
      <div class="logo">
        <img src="${logoUri}" alt="CodeMind">
      </div>

      <div class="brand">
        <div class="title">CodeMind AI</div>
        <div class="subtitle">Local AI coding assistant</div>
      </div>

      <button
        id="newChat"
        class="icon-button"
        type="button"
        title="New chat"
        aria-label="New chat"
      >＋</button>
    </header>

    <main id="conversation" class="conversation">
      <section id="welcome" class="welcome">
        <div class="welcome-center">
          <div class="hero-logo">
            <img src="${logoUri}" alt="CodeMind logo">
          </div>
          <h2>What can I help you build?</h2>
          <div class="muted">
            Ask questions about your code, debug errors, or explore your project.
          </div>
        </div>

        <div class="suggestions">
          <button class="suggestion" type="button"
            data-prompt="Explain my current project">
            <span class="suggestion-icon">⌕</span>
            <span>
              <div class="suggestion-title">Explain my project</div>
              <div class="suggestion-desc">Understand the files and folders</div>
            </span>
          </button>

          <button class="suggestion" type="button"
            data-prompt="Help me find and fix a bug in my project">
            <span class="suggestion-icon">⚒</span>
            <span>
              <div class="suggestion-title">Find and fix a bug</div>
              <div class="suggestion-desc">Investigate a coding issue</div>
            </span>
          </button>

          <button class="suggestion" type="button"
            data-prompt="Help me create a REST API">
            <span class="suggestion-icon">⌘</span>
            <span>
              <div class="suggestion-title">Create a REST API</div>
              <div class="suggestion-desc">Plan an endpoint and its code</div>
            </span>
          </button>
        </div>
      </section>

      <section id="messages" aria-live="polite"></section>

      <div id="loading" class="loading-row" hidden>
        <span id="loadingText">CodeMind is thinking...</span>
        <span class="dots"><span></span><span></span><span></span></span>
      </div>
    </main>

    <div class="composer-wrap">
      <form id="form" class="composer">
        <textarea id="input"
          placeholder="Ask CodeMind anything..."
          aria-label="Message"></textarea>
        <div class="actions">
          <span class="hint">Enter to send · Shift+Enter for newline</span>
          <button id="send" type="submit" title="Send message"
            aria-label="Send message">↑</button>
        </div>
      </form>
    </div>
  </div>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();

    const form = document.getElementById("form");
    const input = document.getElementById("input");
    const messages = document.getElementById("messages");
    const welcome = document.getElementById("welcome");
    const loading = document.getElementById("loading");
    const loadingText = document.getElementById("loadingText");
    const sendButton = document.getElementById("send");
    const conversation = document.getElementById("conversation");

    let waitingForResponse = false;
    const pendingApprovals = new Set();

    // Restore the chat when the view becomes hidden and visible again.
    const savedState = vscode.getState();
    if (savedState && typeof savedState.html === "string") {
      messages.innerHTML = savedState.html;
      welcome.hidden = savedState.welcomeHidden === true;
      pendingApprovals.clear();
      if (Array.isArray(savedState.approvals)) {
        savedState.approvals.forEach(id => pendingApprovals.add(id));
      }
    }

    function saveState() {
      vscode.setState({
        html: messages.innerHTML,
        welcomeHidden: welcome.hidden,
        approvals: Array.from(pendingApprovals)
      });
    }

    function scrollToBottom() {
      conversation.scrollTop = conversation.scrollHeight;
    }

    function addMessage(role, text) {
      welcome.hidden = true;

      const item = document.createElement("article");
      item.className = "message " + role;

      const avatar = document.createElement("div");
      avatar.className = "avatar";

      if (role === "assistant") {
        const image = document.createElement("img");
        image.src = "${logoUri}";
        image.alt = "CodeMind";
        avatar.appendChild(image);
      } else {
        avatar.textContent = "You";
      }

      const content = document.createElement("div");
      content.className = "message-content";

      const name = document.createElement("div");
      name.className = "message-name";
      name.textContent = role === "user" ? "You" : "CodeMind";

      const body = document.createElement("div");
      body.textContent = text;

      content.appendChild(name);
      content.appendChild(body);
      item.appendChild(avatar);
      item.appendChild(content);
      messages.appendChild(item);

      saveState();
      scrollToBottom();
      return content;
    }

    function setLoading(value, text) {
      waitingForResponse = value;
      loading.hidden = !value;
      loadingText.textContent = text || "CodeMind is thinking...";
      sendButton.disabled = value;
      input.disabled = value;
      if (value) scrollToBottom();
    }

    function sendMessage(text) {
      const value = text.trim();
      if (!value || waitingForResponse) return;

      addMessage("user", value);
      setLoading(true, "CodeMind is thinking...");

      vscode.postMessage({ type: "sendMessage", text: value });
      input.value = "";
      scrollToBottom();
    }

    function showApprovalCard(container, data) {
      const approvalId =
        typeof data.approval_id === "string" ? data.approval_id : "";

      if (!approvalId) {
        const warning = document.createElement("div");
        warning.className = "approval-card";
        warning.textContent =
          "Approval ID is missing. Check the backend response.";
        container.appendChild(warning);
        return;
      }

      if (pendingApprovals.has(approvalId)) return;
      pendingApprovals.add(approvalId);

      const card = document.createElement("div");
      card.className = "approval-card";

      const title = document.createElement("div");
      title.className = "approval-title";
      title.textContent = "⚠ Permission required";

      const description = document.createElement("div");
      description.className = "approval-description";
      description.textContent =
        "CodeMind wants to perform a risky action. Nothing has been executed yet. Review the planned actions before continuing.";

      card.appendChild(title);
      card.appendChild(description);

      const approvals = Array.isArray(data.pending_approvals)
        ? data.pending_approvals : [];

      if (approvals.length) {
        const list = document.createElement("ul");
        list.className = "approval-list";

        approvals.forEach(approval => {
          const li = document.createElement("li");

          if (typeof approval === "string") {
            li.textContent = approval;
          } else if (approval && typeof approval === "object") {
            const item = approval;
            li.textContent = [
              item.tool, item.action, item.description, item.path, item.command
            ].filter(value => typeof value === "string").join(" — ")
              || JSON.stringify(item);
          } else {
            li.textContent = String(approval);
          }

          list.appendChild(li);
        });

        card.appendChild(list);
      }

      const actions = document.createElement("div");
      actions.className = "approval-actions";

      const allowButton = document.createElement("button");
      allowButton.className = "approval-button approve-button";
      allowButton.textContent = "✓ Allow";
      allowButton.type = "button";

      const denyButton = document.createElement("button");
      denyButton.className = "approval-button deny-button";
      denyButton.textContent = "✕ Deny";
      denyButton.type = "button";

      const status = document.createElement("div");
      status.className = "approval-status";
      status.hidden = true;

      function submitDecision(type) {
        if (waitingForResponse) return;

        allowButton.disabled = true;
        denyButton.disabled = true;
        status.hidden = false;
        status.textContent = type === "approve"
          ? "Approval submitted..." : "Cancellation submitted...";

        setLoading(true, type === "approve"
          ? "Executing approved actions..." : "Cancelling actions...");

        vscode.postMessage({ type, approvalId });
      }

      allowButton.addEventListener("click", () => submitDecision("approve"));
      denyButton.addEventListener("click", () => submitDecision("deny"));

      actions.appendChild(allowButton);
      actions.appendChild(denyButton);
      card.appendChild(actions);
      card.appendChild(status);
      container.appendChild(card);

      saveState();
      scrollToBottom();
    }

    function getResponseText(data) {
      if (typeof data.response === "string" && data.response.trim()) {
        return data.response;
      }

      if (typeof data.message === "string" && data.message.trim()) {
        return data.message;
      }

      if (Array.isArray(data.results)) {
        const parts = [];

        data.results.forEach(result => {
          if (!result || typeof result !== "object") return;

          if (typeof result.result === "string" && result.result.trim()) {
            parts.push(result.result);
          } else if (
            result.result &&
            typeof result.result === "object"
          ) {
            parts.push(JSON.stringify(result.result, null, 2));
          } else if (typeof result.message === "string") {
            parts.push(result.message);
          } else if (result.status === "success") {
            parts.push("Completed: " + String(result.tool || "action"));
          } else if (result.status === "failed") {
            parts.push(
              "Failed: " + String(result.error || result.tool || "action")
            );
          }
        });

        if (parts.length) return parts.join("\\n\\n");
      }

      if (data.status === "approval_required") {
        return "This action requires your approval before execution.";
      }

      if (data.status === "blocked") {
        return typeof data.reason === "string"
          ? data.reason : "This action was blocked by the permission policy.";
      }

      if (data.status === "completed") {
        return "Task completed, but the backend did not return any result text.";
      }

      return "";
    }

    function displayApiResponse(data, action) {
      const status = typeof data.status === "string" ? data.status : "";
      const responseText = getResponseText(data);

      if (action === "sendMessage" && status === "approval_required") {
        const content = addMessage("assistant", responseText);
        showApprovalCard(content, data);
        return;
      }

      if (action === "approve" || action === "deny") {
        const approvalId =
          typeof data.approval_id === "string" ? data.approval_id : "";

        if (approvalId) pendingApprovals.delete(approvalId);

        if (status === "approval_required") {
          const content = addMessage("assistant", responseText);
          showApprovalCard(content, data);
          return;
        }

        addMessage(
          "assistant",
          responseText || (
            action === "approve"
              ? "Approval processed. Check the result above."
              : "The planned actions were cancelled."
          )
        );
        saveState();
        return;
      }

      addMessage(
        "assistant",
        responseText || "The backend returned no response text."
      );
    }

    form.addEventListener("submit", event => {
      event.preventDefault();
      sendMessage(input.value);
    });

    input.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage(input.value);
      }
    });

    document.querySelectorAll("[data-prompt]").forEach(button => {
      button.addEventListener("click", () => {
        sendMessage(button.dataset.prompt || "");
      });
    });

    document.getElementById("newChat").addEventListener("click", () => {
      if (waitingForResponse) return;

      messages.replaceChildren();
      input.value = "";
      welcome.hidden = false;
      pendingApprovals.clear();
      saveState();
      input.focus();
      scrollToBottom();
    });

    window.addEventListener("message", event => {
      const message = event.data;

      if (message.type === "loading") {
        setLoading(true, message.text);
      } else if (message.type === "apiResponse") {
        const data =
          message.data && typeof message.data === "object"
            ? message.data : {};

        displayApiResponse(data, message.action);
      } else if (message.type === "assistantMessage") {
        addMessage(
          "assistant",
          typeof message.text === "string"
            ? message.text : "No response received."
        );
      } else if (message.type === "requestFinished") {
        setLoading(false);
        saveState();
        input.focus();
      }
    });

    vscode.postMessage({ type: "ready" });
  </script>
</body>
</html>`;
  }
}
