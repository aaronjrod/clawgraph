# ClawGraph Quickstart Example

This is a beginner-friendly example demonstrating how to run ClawGraph with real LLM inference and a live visualization HUD!

It uses `google-genai` and `gemini-3.1-flash-lite-preview` to execute a simple 3-node graph:
1. **Researcher**: Gathers information about a topic.
2. **Analyzer**: Synthesizes the research into a strategic plan.
3. **Writer**: Authors a final markdown report based on the plan.

As ClawGraph routes between these nodes, you can watch the state updates live in your browser using the built-in FastAPI visualizer.

## Setup

1. **Install Dependencies**
   Make sure you have installed ClawGraph with the `examples` extra so the required packages (FastAPI, uvicorn, google-genai, etc.) are available.
   ```bash
   pip install -e ".[examples]"
   ```

2. **API Keys**
   Create a `.env` file in the root directory (or export it in your shell) with your Google Gemini API Key:
   ```bash
   GEMINI_API_KEY=your_api_key_here
   ```

## Running the Demo

Execute the runner script from the root of the repository:

```bash
python examples/quickstart/run.py
```

1. The script will boot up a background FastAPI server on port 8000.
2. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
3. Watch the terminal and the browser live as ClawGraph dynamically guides the LLMs through the research task!
