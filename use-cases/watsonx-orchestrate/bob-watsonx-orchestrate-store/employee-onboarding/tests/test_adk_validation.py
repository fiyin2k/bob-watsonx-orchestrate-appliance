"""ADK Asset and Configuration Validator.

Validates that:
- employee-onboarding-adk-config.yaml is valid YAML and conforms to ADK schema structure
- All declared tools in YAML correspond to callable Python implementations in the tools module
- Tool parameter schemas match function signatures
- Security & governance requirements are defined and compliant
"""

import sys
import os
import inspect
import yaml
import pytest

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tools


CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "employee-onboarding-adk-config.yaml"
)


@pytest.fixture(scope="module")
def adk_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestADKAssetValidation:

    def test_config_structure(self, adk_config):
        assert "agent" in adk_config
        assert "tools" in adk_config
        assert "workflows" in adk_config
        assert "knowledge_bases" in adk_config
        assert "connections" in adk_config
        assert "governance" in adk_config

    def test_agent_model_configuration(self, adk_config):
        agent = adk_config["agent"]
        assert agent["name"] == "onboarding-orchestrator"
        assert agent["version"] == "1.0.0"
        
        config = agent["config"]
        assert config["model"]["provider"] == "watsonx"
        assert config["model"]["model_id"] == "ibm/granite-3-1-8b-instruct"
        assert config["model"]["parameters"]["temperature"] == 0.2
        assert config["fallback_model"]["model_id"] == "meta-llama/llama-3-1-70b-instruct"

    def test_tools_alignment_with_python_modules(self, adk_config):
        declared_tools = adk_config["tools"]
        assert len(declared_tools) >= 7

        tool_mapping = {
            "get_candidate_by_id": tools.fetch_candidate,
            "update_hr_onboarding_status": tools.update_status,
            "create_m365_user_account": tools.create_ad_user,
            "assign_m365_licenses": tools.apply_licenses,
            "manage_m365_group_membership": tools.add_user_to_groups,
            "create_servicenow_provisioning_ticket": tools.book_equipment_ticket,
            "get_servicenow_ticket_status": tools.query_ticket,
            "generate_secure_password": tools.get_crypto_password,
            "send_external_welcome_email": tools.dispatch_welcome_letter,
        }

        for tool_def in declared_tools:
            tool_name = tool_def["name"]
            assert tool_name in tool_mapping, f"Tool '{tool_name}' in YAML is not mapped to Python implementation."
            
            py_func = tool_mapping[tool_name]
            assert callable(py_func), f"Target for '{tool_name}' is not callable."
            
            # Check function docstring exists for ADK auto-discovery
            assert py_func.__doc__ is not None, f"Function for '{tool_name}' missing docstring."
            
            # Validate parameters in YAML match Python function signature
            sig = inspect.signature(py_func)
            declared_params = set(tool_def.get("parameters", {}).keys())
            func_params = set(sig.parameters.keys())
            
            # All required YAML params should exist in Python function signature
            for param_name, param_meta in tool_def.get("parameters", {}).items():
                if param_meta.get("required", False):
                    assert param_name in func_params, f"Required parameter '{param_name}' for '{tool_name}' missing in function signature."

    def test_workflows_definition(self, adk_config):
        workflows = {w["name"]: w for w in adk_config["workflows"]}
        assert "unified_employee_onboarding" in workflows
        assert "onboarding_status_monitoring" in workflows
        
        unified = workflows["unified_employee_onboarding"]
        assert len(unified["steps"]) >= 6

    def test_governance_and_security_compliance(self, adk_config):
        gov = adk_config["governance"]
        assert gov["security"]["mfa_required"] is True
        assert gov["security"]["credential_storage"] == "ibm_secrets_manager"
        assert "GDPR" in gov["compliance"]["standards"]
        assert "SOC2_TYPE_II" in gov["compliance"]["standards"]
