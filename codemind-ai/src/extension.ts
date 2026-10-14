import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext): void {
  const provider = new CodeMindChatProvider();

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("codemind-ai.chatView", provider),
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
  resolveWebviewView(webviewView: vscode.WebviewView): void {
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this.getHtml();

    webviewView.webview.onDidReceiveMessage(
      async (message: { type?: string; text?: string }) => {
        if (message.type !== "sendMessage") return;

        const text = message.text?.trim();
        if (!text) return;

        try {
          const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
          if (!workspaceFolder) {
            throw new Error("Please open a project folder in VS Code first.");
          }

          webviewView.webview.postMessage({
            type: "loading",
            text: "Thinking...",
          });

          const response = await fetch("http://127.0.0.1:8000/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message: text,
              workspace: workspaceFolder.uri.fsPath,
            }),
          });

          const rawData: unknown = await response.json();

          if (typeof rawData !== "object" || rawData === null) {
            throw new Error("Invalid response received from backend.");
          }

          const data = rawData as Record<string, unknown>;

          if (!response.ok) {
            throw new Error(
              typeof data.detail === "string"
                ? data.detail
                : `API error: ${response.status}`,
            );
          }

          webviewView.webview.postMessage({
            type: "assistantMessage",
            text:
              typeof data.response === "string"
                ? data.response
                : "Backend response did not contain a valid answer.",
          });
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : "Unknown error";

          webviewView.webview.postMessage({
            type: "assistantMessage",
            text: `CodeMind error: ${errorMessage}`,
          });
        } finally {
          webviewView.webview.postMessage({
            type: "requestFinished",
          });
        }
      },
    );
  }

  private getHtml(): string {
    return /* html */ `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta
          http-equiv="Content-Security-Policy"
          content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';"
        >
        <title>CodeMind Chat</title>

        <style>
          * {
            box-sizing: border-box;
          }

          html,
          body {
            width: 100%;
            height: 100%;
            margin: 0;
            overflow: hidden;
          }

          body {
            padding: 0;
            color: var(--vscode-foreground);
            background: var(--vscode-sideBar-background);
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
          }

          button,
          textarea {
            font: inherit;
          }

          button {
            color: inherit;
          }

          .app {
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100vh;
            min-height: 0;
            overflow: hidden;
          }

          .header {
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            border-bottom: 1px solid var(--vscode-panel-border);
          }

          .logo {
            width: 36px;
            height: 36px;
            flex: 0 0 36px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            background: #2878e8;
            color: #ffffff;
            font-size: 17px;
            font-weight: 700;
          }

          .brand {
            flex: 1;
            min-width: 0;
          }

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
            width: 30px;
            height: 30px;
            display: grid;
            place-items: center;
            border: 1px solid var(--vscode-button-border, transparent);
            border-radius: 6px;
            color: var(--vscode-foreground);
            background: transparent;
            cursor: pointer;
            font-size: 19px;
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
            padding: 24px 14px;
          }

          .welcome-center {
            text-align: center;
          }

          .hero-logo {
            width: 58px;
            height: 58px;
            margin: 0 auto 16px;
            display: grid;
            place-items: center;
            border-radius: 18px;
            background: #2878e8;
            color: #ffffff;
            font-size: 25px;
            font-weight: 700;
            box-shadow: 0 8px 26px #2878e833;
          }

          .welcome h2 {
            margin: 0 0 10px;
            font-size: 20px;
            line-height: 1.3;
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
            color: var(--vscode-foreground);
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
            width: 27px;
            height: 27px;
            flex: 0 0 27px;
            display: grid;
            place-items: center;
            border-radius: 8px;
            background: var(--vscode-textBlockQuote-background);
            font-size: 10px;
            font-weight: 700;
          }

          .message.user .avatar {
            background: #2878e8;
            color: #ffffff;
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

          .dots {
            display: inline-flex;
            gap: 4px;
          }

          .dots span {
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: var(--vscode-progressBar-background, #2878e8);
            animation: pulse 1s infinite ease-in-out;
          }

          .dots span:nth-child(2) {
            animation-delay: 0.15s;
          }

          .dots span:nth-child(3) {
            animation-delay: 0.3s;
          }

          @keyframes pulse {
            0%, 80%, 100% {
              opacity: 0.25;
              transform: translateY(0);
            }
            40% {
              opacity: 1;
              transform: translateY(-3px);
            }
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
            width: 30px;
            height: 30px;
            border: 0;
            border-radius: 7px;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            cursor: pointer;
            font-size: 17px;
          }

          #send:hover {
            background: var(--vscode-button-hoverBackground);
          }

          #send:disabled {
            opacity: 0.5;
            cursor: wait;
          }

          [hidden] {
            display: none !important;
          }

          @media (max-height: 500px) {
            .welcome {
              padding-top: 12px;
              padding-bottom: 12px;
            }

            .hero-logo {
              width: 42px;
              height: 42px;
              margin-bottom: 9px;
            }

            .suggestions {
              margin-top: 12px;
            }
          }
        </style>
      </head>

      <body>
        <div class="app">
          <header class="header">
            <div class="logo">&lt;/&gt;</div>

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
                <div class="hero-logo">⌘</div>
                <h2>What can I help you build?</h2>
                <div class="muted">
                  Ask questions about your code, debug errors, or explore your project.
                </div>
              </div>

              <div class="suggestions">
                <button
                  class="suggestion"
                  type="button"
                  data-prompt="Explain my current project"
                >
                  <span class="suggestion-icon">⌕</span>
                  <span>
                    <div class="suggestion-title">Explain my project</div>
                    <div class="suggestion-desc">Understand the files and folders</div>
                  </span>
                </button>

                <button
                  class="suggestion"
                  type="button"
                  data-prompt="Help me find and fix a bug in my project"
                >
                  <span class="suggestion-icon">⚒</span>
                  <span>
                    <div class="suggestion-title">Find and fix a bug</div>
                    <div class="suggestion-desc">Investigate a coding issue</div>
                  </span>
                </button>

                <button
                  class="suggestion"
                  type="button"
                  data-prompt="Help me create a REST API"
                >
                  <span class="suggestion-icon">⌘</span>
                  <span>
                    <div class="suggestion-title">Create a REST API</div>
                    <div class="suggestion-desc">Plan an endpoint and its code</div>
                  </span>
                </button>
              </div>
            </section>

            <section id="messages" aria-live="polite"></section>

<div id="loading" class="loading hidden">
    <span>CodeMind is thinking</span>
    <span class="dots">
        <span>.</span>
        <span>.</span>
        <span>.</span>
    </span>
           </div>
          </main>

          <div class="composer-wrap">
            <form id="form" class="composer">
              <textarea
                id="input"
                placeholder="Ask CodeMind anything..."
                aria-label="Message"
              ></textarea>

              <div class="actions">
                <span class="hint">Enter to send · Shift+Enter for newline</span>
                <button id="send" type="submit" title="Send message" aria-label="Send message">↑</button>
              </div>
            </form>
          </div>
        </div>

        <script>
          const vscode = acquireVsCodeApi();
          const form = document.getElementById("form");
          const input = document.getElementById("input");
          const messages = document.getElementById("messages");
          const welcome = document.getElementById("welcome");
          const loading = document.getElementById("loading");
          const sendButton = document.getElementById("send");
          const conversation = document.getElementById("conversation");

          let waitingForResponse = false;

          function scrollToBottom() {
            conversation.scrollTop = conversation.scrollHeight;
          }

          function addMessage(role, text) {
            welcome.hidden = true;

            const item = document.createElement("article");
            item.className = "message " + role;

            const avatar = document.createElement("div");
            avatar.className = "avatar";
            avatar.textContent = role === "user" ? "You" : "C";

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

            scrollToBottom();
          }

          function setLoading(value) {
            waitingForResponse = value;
            loading.hidden = !value;
            sendButton.disabled = value;
            input.disabled = value;

            if (value) scrollToBottom();
          }

          function sendMessage(text) {
            const value = text.trim();

            if (!value || waitingForResponse) return;

            addMessage("user", value);
            setLoading(true);

            vscode.postMessage({
              type: "sendMessage",
              text: value
            });

            input.value = "";
            scrollToBottom();
          }

          form.addEventListener("submit", (event) => {
            event.preventDefault();
            sendMessage(input.value);
          });

          input.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              sendMessage(input.value);
            }
          });

          document.querySelectorAll("[data-prompt]").forEach((button) => {
            button.addEventListener("click", () => {
              sendMessage(button.dataset.prompt || "");
            });
          });

          document.getElementById("newChat").addEventListener("click", () => {
            messages.replaceChildren();
            input.value = "";
            welcome.hidden = false;
            setLoading(false);
            input.focus();
            scrollToBottom();
          });

          window.addEventListener("message", (event) => {
            const message = event.data;

            if (message.type === "loading") {
              setLoading(true);
            } else if (message.type === "assistantMessage") {
              setLoading(false);
              addMessage(
                "assistant",
                typeof message.text === "string"
                  ? message.text
                  : "No response received.",
              );
              input.focus();
            }
          });
        </script>
      </body>
      </html>
    `;
  }
}
