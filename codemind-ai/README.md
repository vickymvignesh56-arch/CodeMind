# CodeMind AI

**A local AI coding assistant for Visual Studio Code, powered by Ollama.**

CodeMind AI connects your VS Code workspace to a local AI backend, helping you ask coding questions and understand your project.

## Features

- Chat with a local AI coding assistant from VS Code.
- Uses your currently opened workspace as the project context.
- Connects to the CodeMind FastAPI backend.
- Uses Ollama to generate AI responses.
- Designed for local development workflows.

## Requirements

Before using CodeMind AI, make sure you have:

- Visual Studio Code
- Python 3.11 or a compatible Python version
- Ollama installed and running
- A compatible model downloaded in Ollama
- The CodeMind backend configured and running

## Getting Started

### 1. Start Ollama

Make sure Ollama is running and your configured model is available.

### 2. Start the CodeMind backend

Open PowerShell in your CodeMind backend directory and run:

```powershell
cd "D:\python learn\CodeMind"
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### 3. Open your project

Open the project folder you want to work with in VS Code.

### 4. Open CodeMind AI

Click the CodeMind icon in the Activity Bar and open the CodeMind Chat view.

Type a question and send it to the assistant.

## Backend Configuration

The extension currently connects to:

`http://127.0.0.1:8000/api/chat`

The backend must be running locally for chat functionality to work.

## Troubleshooting

- **Cannot connect:** Confirm that the FastAPI backend is running.
- **AI response fails:** Check that Ollama is running and the configured model is available.
- **No workspace detected:** Open a project folder in VS Code before chatting.
- **Backend error:** Open `http://127.0.0.1:8000/docs` to check the API.

## Development

To compile the extension:

```powershell
npm install
npm run compile
```

To package the extension:

```powershell
npx @vscode/vsce package
```

## Privacy

Chat messages are sent to the locally configured CodeMind backend. The backend uses Ollama according to its configuration. Review your backend settings before using the extension with sensitive project files.

## License

License information will be added before public release.
