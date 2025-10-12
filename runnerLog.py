import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import types as _types

# ----------------- Configuration -----------------
# Make sure the tool_library is accessible by Python
sys.path.append(str(Path(__file__).parent.resolve()))
# Provide a package alias so YAML can import tools as ResolveLight.* even if the
# project directory name differs (e.g., ResolveLightTest).
if 'ResolveLight' not in sys.modules:
    pkg = _types.ModuleType('ResolveLight')
    pkg.__path__ = [str(Path(__file__).parent.resolve())]
    sys.modules['ResolveLight'] = pkg

from google.adk.agents.config_agent_utils import from_config as load_agent_from_yaml
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.plugins import BasePlugin
from google.genai import types
import google.generativeai as genai

# ----------------- Tool Imports -----------------
# Import the modules containing your tool functions
from tool_library import date_check_tool
from tool_library import duplicate_invoice_check_tool
from tool_library import fuzzy_matching_tool
from tool_library import line_item_validation_tool
from tool_library import po_contract_resolver_tool
from tool_library import services_report_tool
from tool_library import simple_overbilling_tool
from tool_library import supplier_match_tool
from tool_library import triage_resolution_tool
from tool_library import validation_runner_tool

# ----------------- Event Logging Plugin -----------------
class JsonlLoggerPlugin(BasePlugin):
    def __init__(self, memory_dir: str = "memory"):
        # Register with base plugin (required by PluginManager)
        super().__init__(name="jsonl_logger")
        self.description = "Writes raw ADK events to a per-session JSONL file"
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)

    async def on_event_callback(self, *, invocation_context, event):
        # one line per event, raw JSON from ADK's pydantic model
        try:
            session = getattr(invocation_context, "session", None)
            sid = getattr(session, "id", None) or "session_001"
            path = os.path.join(self.memory_dir, f"{sid}.jsonl")
            line = None
            try:
                if hasattr(event, "model_dump_json"):
                    line = event.model_dump_json()
                elif hasattr(event, "model_dump"):
                    import json as _json
                    line = _json.dumps(event.model_dump(), ensure_ascii=False)
            except Exception:
                pass
            if line is None:
                line = str(event)
            with open(path, "a", encoding="utf-8") as f:
                # Write one JSON object per line, plus an extra blank line for readability
                f.write(line + "\n\n")
        except Exception:
            pass
        return None

# ----------------- Main Application Logic -----------------

async def main():
    """
    Main function to configure and run the multi-agent system (with event logging plugin).
    """
    print("🚀 Starting Agent Application (runnerLog)...")

    # Load the root agent (and its referenced sub-agents) directly from YAML
    root_agent = load_agent_from_yaml("root_agent.yaml")
    print("✅ Root agent loaded from YAML.")

    # Set up the Session and Runner for the entire application
    session_service = InMemorySessionService()
    app_name = "multi_agent_system"
    user_id = "user_001"
    session_id = "session_001"
    await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    runner = Runner(
        app_name=app_name,
        agent=root_agent,
        session_service=session_service,
        plugins=[JsonlLoggerPlugin("memory")],
    )

    print("✨ Runner is ready. Starting interactive chat.")
    print("--------------------------------------------------")
    print("Enter your query below. Type 'quit' or 'exit' to end.")

    # Start the interactive chat loop
    while True:
        try:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.lower() in ["quit", "exit"]:
                print("Exiting application.")
                break

            content = types.Content(role="user", parts=[types.Part(text=user_input)])

            print("\nAgent: ", end="", flush=True)
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                # Print any available text content parts as they arrive
                if event and getattr(event, "content", None):
                    parts = getattr(event.content, "parts", None) or []
                    for p in parts:
                        txt = getattr(p, "text", None)
                        if txt:
                            print(txt, end="", flush=True)
            print("\n")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting application.")
            break

if __name__ == "__main__":
    # --- IMPORTANT: Configure your Gemini API key ---
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing API key. Set GOOGLE_API_KEY or GEMINI_API_KEY.")
        genai.configure(api_key=api_key)
    except (ImportError, ValueError) as e:
        print(f"ERROR: Could not configure API key. {e}")
        sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
