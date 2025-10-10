(.venv) mzim-mac:ResolveLight mzim$ adk run .
Log setup complete: /var/folders/sd/ldh_p7qj43vc5480l0dj6sfc01bg8p/T/agents_log/agent.20250905_144245.log
To access latest log: tail -F /var/folders/sd/ldh_p7qj43vc5480l0dj6sfc01bg8p/T/agents_log/agent.latest.log
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/cli/cli.py:143: UserWarning: [EXPERIMENTAL] InMemoryCredentialService: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  credential_service = InMemoryCredentialService()
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/auth/credential_service/in_memory_credential_service.py:33: UserWarning: [EXPERIMENTAL] BaseCredentialService: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  super().__init__()
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/cli/utils/agent_loader.py:181: UserWarning: [EXPERIMENTAL] _load_from_yaml_config: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  if root_agent := self._load_from_yaml_config(agent_name):
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/cli/utils/agent_loader.py:146: UserWarning: [EXPERIMENTAL] from_config: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  agent = config_agent_utils.from_config(config_path)
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/agents/config_agent_utils.py:72: UserWarning: [EXPERIMENTAL] resolve_fully_qualified_name: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  agent_class = resolve_fully_qualified_name(agent_class_name)
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/agents/config_agent_utils.py:63: UserWarning: [EXPERIMENTAL] from_config: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  return agent_class.from_config(agent_config, abs_path)
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/agents/base_agent.py:587: UserWarning: [EXPERIMENTAL] resolve_agent_reference: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  sub_agent = resolve_agent_reference(sub_agent_config, config_abs_path)
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/agents/config_agent_utils.py:133: UserWarning: [EXPERIMENTAL] from_config: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  return from_config(
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/agents/base_agent.py:543: UserWarning: [EXPERIMENTAL] _parse_config: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  kwargs = cls._parse_config(config, config_abs_path, kwargs)
/Users/mzim/ADK/.venv/lib/python3.13/site-packages/google/adk/agents/llm_agent.py:614: UserWarning: [EXPERIMENTAL] _resolve_tools: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  kwargs['tools'] = cls._resolve_tools(config.tools, config_abs_path)
Running agent SourceToPay, type exit to exit.
[user]: /Users/mzim/ADK/ResolveLight/json_files/invoices/invoice_Aegis_PO-2025-304A.json
[contract_matching_agent]: ```text
/Users/mzim/ADK/ResolveLight/json_files/invoices/invoice_Aegis_PO-2025-304A.json
/Users/mzim/ADK/ResolveLight/json_files/POs/POs_Aegis.json
/Users/mzim/ADK/ResolveLight/json_files/contracts/contract_Aegis.json

Invoice: invoice_id: INV-AEG-2025-001, purchase_order_number: PO-2025-304A
PO Item: po_number: PO-2025-304A, contract_id: CON-TECH-2025-004
Contract: contract_id: CON-TECH-2025-004, contract_title: 2025 Master Services Agreement - Project Aegis

```

[validation_agent]: supplier_match_tool: PASS
simple_overbilling_tool: PASS
date_check_tool: PASS
validation: PASS

[triage_agent]: APPROVED

[user]: /Users/mzim/ADK/ResolveLight/json_files/invoices/invoice_Nexus.json
[contract_matching_agent]: ```text
/Users/mzim/ADK/ResolveLight/json_files/invoices/invoice_Nexus.json
<not found>
<not found>

Invoice: invoice_id: INV-NEX-2025-001, purchase_order_number: <not found>
PO Item: po_number: <not found>, contract_id: <not found>
Contract: contract_id: <not found>, contract_title: <not found>

```

[validation_agent]: dependency_check: FAIL - reasons: po_item_not_found, contract_not_found
validation: FAIL

[triage_agent]: REJECTED - reasons: po_item_not_found, contract_not_found

[user]: exit
