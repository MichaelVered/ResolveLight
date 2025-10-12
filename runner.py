import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import types as _types
from datetime import datetime
import json

# ----------------- Configuration -----------------
# Make sure the tool_library is accessible by Python
sys.path.append(str(Path(__file__).parent.resolve()))
# Provide a package alias so YAML can import tools as ResolveLight.* even if the
# project directory name differs (e.g., ResolveLightTest).
if 'ResolveLight' not in sys.modules:
    pkg = _types.ModuleType('ResolveLight')
    pkg.__path__ = [str(Path(__file__).parent.resolve())]
    sys.modules['ResolveLight'] = pkg

# Track which events have been persisted per session to avoid duplicates when appending
_PERSISTED_EVENT_IDS: Dict[str, set] = {}

from google.adk.agents.config_agent_utils import from_config as load_agent_from_yaml
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import google.generativeai as genai


# ----------------- Tool Imports -----------------
# Import the modules containing your tool functions
from tool_library import date_check_tool
from tool_library import fuzzy_matching_tool
from tool_library import line_item_validation_tool
from tool_library import po_contract_resolver_tool
from tool_library import simple_overbilling_tool
from tool_library import supplier_match_tool
from tool_library import triage_resolution_tool
from tool_library import validation_runner_tool

# ----------------- Tool Wrapper Classes -----------------
# Not required for this ADK version; tools are referenced directly in YAML via
# fully-qualified names (e.g., ResolveLight.tool_library.module.fn)


# ----------------- Main Application Logic -----------------

async def _dump_session_history(session_service: InMemorySessionService, app_name: str, user_id: str, session_id: str, memory_dir: str = "memory") -> str:
    os.makedirs(memory_dir, exist_ok=True)
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    filename = (session.id if getattr(session, "id", None) else session_id) + ".jsonl"
    out_path = os.path.join(memory_dir, filename)
    # Initialize persisted ids cache from existing file once per process/session
    persisted_ids = _PERSISTED_EVENT_IDS.setdefault(session_id, set())
    if os.path.exists(out_path) and not persisted_ids:
        try:
            with open(out_path, "r", encoding="utf-8") as rf:
                for line in rf:
                    try:
                        obj = json.loads(line)
                        ev_id = obj.get("id")
                        if ev_id:
                            persisted_ids.add(ev_id)
                    except Exception:
                        continue
        except Exception:
            pass

    with open(out_path, "a", encoding="utf-8") as f:
        if session and getattr(session, "events", None):
            for ev in session.events:
                ev_id_val = getattr(ev, "id", None)
                ev_id_str = str(ev_id_val) if ev_id_val is not None else None
                if ev_id_str and ev_id_str in persisted_ids:
                    continue
                ts_val = getattr(ev, "timestamp", None)
                try:
                    ts_iso = datetime.utcfromtimestamp(float(ts_val)).strftime("%Y-%m-%dT%H:%M:%SZ") if ts_val is not None else ""
                except Exception:
                    ts_iso = ""
                record: dict[str, Any] = {
                    "author": getattr(ev, "author", "agent"),
                    "timestamp": ts_val,
                    "timestamp_iso": ts_iso,
                    "id": ev_id_val,
                    "invocation_id": getattr(ev, "invocation_id", None),
                    "branch": getattr(ev, "branch", None),
                }
                # Actions
                actions = getattr(ev, "actions", None)
                try:
                    if actions is not None:
                        if hasattr(actions, "model_dump"):
                            record["actions"] = actions.model_dump()
                        else:
                            record["actions"] = str(actions)
                except Exception:
                    record["actions"] = "<unserializable>"

                # Parts
                content = getattr(ev, "content", None)
                parts = getattr(content, "parts", None) or []
                parts_rec: list[dict[str, Any]] = []
                for p in parts:
                    pr: dict[str, Any] = {}
                    txt = getattr(p, "text", None)
                    if txt:
                        pr["text"] = txt
                    fc = getattr(p, "function_call", None)
                    if fc is not None:
                        try:
                            name = getattr(fc, "name", None) or getattr(fc, "function_name", None) or "<unknown>"
                            args = getattr(fc, "args", None) or getattr(fc, "arguments", None)
                            pr["function_call"] = {"name": name, "args": args}
                        except Exception:
                            pr["function_call"] = "<unserializable>"
                    fr = getattr(p, "function_response", None)
                    if fr is not None:
                        try:
                            fr_name = getattr(fr, "name", None) or getattr(fr, "function_name", None) or "<unknown>"
                            response = getattr(fr, "response", None) or getattr(fr, "result", None)
                            pr["function_response"] = {"name": fr_name, "response": response}
                        except Exception:
                            pr["function_response"] = "<unserializable>"
                    cer = getattr(p, "code_execution_result", None)
                    if cer is not None:
                        try:
                            out = getattr(cer, "output", None)
                            err = getattr(cer, "error", None)
                            exit_code = getattr(cer, "exit_code", None)
                            pr["code_execution_result"] = {"output": out, "error": err, "exit_code": exit_code}
                        except Exception:
                            pr["code_execution_result"] = "<unserializable>"
                    parts_rec.append(pr)
                record["parts"] = parts_rec
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                if ev_id_str:
                    persisted_ids.add(ev_id_str)
    return out_path

async def main():
    """
    Main function to configure and run the multi-agent system.
    """
    print("🚀 Starting Agent Application...")

    # 1. (Deprecated) No manual tool wiring required; YAML references tools directly.

    # 2-5. Load the root agent (and its referenced sub-agents) directly from YAML
    # The YAML already references tools by fully-qualified names, so custom tool
    # wrappers here are optional; the config-driven load will wire tools itself.
    root_agent = load_agent_from_yaml("root_agent.yaml")
    print("✅ Root agent loaded from YAML.")

    # 6. Set up the Session and Runner for the entire application
    session_service = InMemorySessionService()
    app_name = "multi_agent_system"
    user_id = "user_001"
    session_id = "session_001"
    await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    runner = Runner(app_name=app_name, agent=root_agent, session_service=session_service)

    print("✨ Runner is ready. Starting interactive chat.")
    print("--------------------------------------------------")
    print("Enter your query below. Type 'quit' or 'exit' to end.")

    # 7. Start the interactive chat loop
    while True:
        try:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.lower() in ["quit", "exit"]:
                try:
                    out_path = await _dump_session_history(session_service, app_name, user_id, session_id)
                    print(f"Saved session history to: {out_path}")
                except Exception as _e:
                    pass
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

            # Automatically persist the session history after handling each message
            try:
                await _dump_session_history(session_service, app_name, user_id, session_id)
            except Exception:
                pass

        except (KeyboardInterrupt, EOFError):
            print("\nExiting application.")
            break

if __name__ == "__main__":
    # --- IMPORTANT: Configure your Gemini API key ---
    try:
        from dotenv import load_dotenv
        load_dotenv("../.env")
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