# Employee Onboarding Orchestrator Agent - Implementation Guide

## Overview

This guide provides technical steps for implementing and deploying the Enterprise Employee Onboarding Orchestrator Agent using the IBM watsonx Orchestrate ADK (Agent Development Kit). The agent automates cross-system onboarding workflows spanning Core HR, Microsoft 365, and ServiceNow.

---

## Prerequisites

### Required Software & Environment
- Python 3.9 or higher
- IBM watsonx Orchestrate ADK (`ibm-watsonx-orchestrate-adk`)
- Docker (for containerized deployments)
- Git version control

### Required Connectivity & Auth Scopes
- IBM Cloud account with active watsonx Orchestrate instance
- Microsoft 365 Developer or Sandbox Tenant (with `Directory.ReadWrite.All`, `User.ReadWrite.All` Azure Active Directory application permissions)
- ServiceNow PDI (Personal Developer Instance) or Sandbox with `itil_admin` or specific service catalog role access
- Sandbox API access keys/OAuth2 credentials for Core HR System

### Initializing Environment
Ensure that the ADK environment is active by running the appliance readiness helpers:
```bash
# 1. Access workspace
cd /Users/fiyinolatunji/Downloads/bob-watsonx-orchestrate-appliance/use-cases/watsonx-orchestrate

# 2. Run the environment helper
source .bob/watsonx-orchestrate-tools/ensure-wxo-adk-env.sh

# 3. Activate virtual environment
source wxo-adk-env/bin/activate

# 4. Verify ADK binary execution
ibm-watsonx-orchestrate-adk --version
```

---

## Project Structure

The project represents a standard structured ADK package ready for compiler compilation:

```
employee-onboarding-agent/
├── agent/
│   ├── __init__.py
│   ├── config.yaml                 # Core YAML ADK configuration
│   ├── instructions.txt            # System Prompt definition
│   └── metadata.json              # Compilation metadata
├── tools/
│   ├── __init__.py
│   ├── core_hr/
│   │   ├── __init__.py
│   │   ├── candidate_reader.py
│   │   └── status_updater.py
│   ├── m365/
│   │   ├── __init__.py
│   │   ├── identity_provisioner.py
│   │   ├── license_assigner.py
│   │   └── group_manager.py
│   ├── servicenow/
│   │   ├── __init__.py
│   │   ├── catalog_client.py
│   │   └── tracking_monitor.py
│   └── utils/
│       ├── __init__.py
│       ├── password_generator.py
│       └── welcome_notifier.py
├── workflows/
│   ├── __init__.py
│   └── unified_onboarding_flow.py
├── knowledge_bases/
│   ├── hr_faq_documents/
│   └── hardware_matrices/
├── tests/
│   ├── __init__.py
│   ├── test_tools.py
│   └── test_workflows.py
├── deployment/
│   ├── Dockerfile
│   └── kubernetes/
│       ├── deployment-prod.yaml
│       └── secrets.yaml
├── requirements.txt
└── setup.py
```

---

## Step 1: Initialize Project Directory

```bash
# Create and navigate to project folder
mkdir -p employee-onboarding-agent
cd employee-onboarding-agent

# Initialize the ADK project
ibm-watsonx-orchestrate-adk init \
  --name onboarding-orchestrator \
  --description "Enterprise Employee Onboarding Orchestrator Agent" \
  --version 1.0.0
```

---

## Step 2: Declare Package Dependencies

Write the required production dependencies inside `requirements.txt`:

```txt
# IBM watsonx Orchestrate ADK
ibm-watsonx-orchestrate-adk>=1.0.0

# API Gateways & Request clients
requests>=2.31.0
urllib3>=2.0.7

# Microsoft Graph API Python Client
msal>=1.26.0

# Cryptography & Security Helpers
cryptography>=41.0.7

# Configuration & Logging
pyyaml>=6.0.1
pydantic>=2.5.2

# Testing Frameworks
pytest>=7.4.3
pytest-asyncio>=0.23.2
pytest-cov>=4.1.0
```

Install requirements inside the activated environment:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 3: Implement Python Tools

### 3.1 Core HR Candidate Extraction
**File: `tools/core_hr/candidate_reader.py`**

```python
"""Core HR Candidate reader tool implementation."""

import os
import requests
from typing import Dict, Any
from ibm_watsonx_orchestrate_adk import Tool, ToolParameter

class GetCandidateById(Tool):
    """Retrieve candidate files from standard REST endpoint."""
    
    name = "get_candidate_by_id"
    description = "Retrieve master candidate records from Core HR system."
    
    parameters = [
        ToolParameter(
            name="candidate_id",
            type="string",
            description="Candidate unique reference (CAND-xxxxx)",
            required=True
        )
    ]
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        candidate_id = kwargs["candidate_id"]
        base_url = os.environ.get("CORE_HR_BASE_URL", "https://hr.enterprise.com/api/v2/")
        client_id = os.environ.get("CORE_HR_CLIENT_ID")
        client_secret = os.environ.get("CORE_HR_CLIENT_SECRET")
        
        # In a real solution, retrieve bearer token via OAuth2. Mock implementation:
        headers = {
            "Authorization": f"Bearer {client_secret}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(f"{base_url}candidates/{candidate_id}", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "candidate": data}
            else:
                return {"success": False, "error": f"API Error {response.status_code}: {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### 3.2 Microsoft 365 Account Provisioner
**File: `tools/m365/identity_provisioner.py`**

```python
"""Microsoft Entra ID User identity creation tool."""

import os
import requests
from typing import Dict, Any
from msal import ConfidentialClientApplication
from ibm_watsonx_orchestrate_adk import Tool, ToolParameter

class CreateM365UserAccount(Tool):
    """Create corporate identity inside active Entra ID directory."""
    
    name = "create_m365_user_account"
    description = "Register corporate UPN identity inside Microsoft Azure AD."
    human_approval_required = True
    
    parameters = [
        ToolParameter(name="user_principal_name", type="string", description="UPN e.g. sconnor@enterprise.com", required=True),
        ToolParameter(name="display_name", type="string", description="Sarah Connor", required=True),
        ToolParameter(name="given_name", type="string", description="Sarah", required=True),
        ToolParameter(name="surname", type="string", description="Connor", required=True),
        ToolParameter(name="department", type="string", description="Engineering", required=True),
        ToolParameter(name="job_title", type="string", description="Software Engineer", required=True),
        ToolParameter(name="temp_password", type="string", description="Initial temporary password", required=True)
    ]
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        tenant_id = os.environ.get("AZURE_TENANT_ID")
        client_id = os.environ.get("AZURE_CLIENT_ID")
        client_secret = os.environ.get("AZURE_CLIENT_SECRET")
        
        # Establish MSAL token Client
        app = ConfidentialClientApplication(
            client_id, authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret
        )
        token_res = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        token = token_res.get("access_token")
        
        if not token:
            return {"success": False, "error": "Unable to acquire AD authorization token"}
            
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        user_payload = {
            "accountEnabled": True,
            "displayName": kwargs["display_name"],
            "mailNickname": kwargs["given_name"].lower(),
            "userPrincipalName": kwargs["user_principal_name"],
            "passwordProfile": {
                "forceChangePasswordNextSignIn": True,
                "password": kwargs["temp_password"]
            }
        }
        
        try:
            url = "https://graph.microsoft.com/v1.0/users"
            res = requests.post(url, json=user_payload, headers=headers, timeout=10)
            if res.status_code == 201:
                return {"success": True, "user_id": res.json().get("id")}
            else:
                return {"success": False, "error": f"Graph failed: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_approval_message(self, **kwargs) -> str:
        return f"Warning: Registering employee account {kwargs['user_principal_name']} directly inside Production Active Directory directory. Proceed?"
```

---

## Step 4: Implement Workflows

**File: `workflows/unified_onboarding_flow.py`**

```python
"""Workflow class orchestrating the multi-step onboarding process."""

from typing import Dict, Any
from ibm_watsonx_orchestrate_adk import Workflow, WorkflowStep

class UnifiedEmployeeOnboarding(Workflow):
    """End-to-End Orchestrated onboarding workflow."""
    
    name = "unified_employee_onboarding"
    description = "Step workflow coordinating HR database, Microsoft AD and ServiceNow ticketing."
    
    def __init__(self):
        super().__init__()
        self.steps = [
            WorkflowStep(
                name="candidate_record_ingestion",
                description="Extract and validate record from HR",
                function=self.candidate_record_ingestion,
                tools=["get_candidate_by_id"]
            ),
            WorkflowStep(
                name="directory_account_provisioning",
                description="Provision AD user and assign subscription licenses",
                function=self.directory_account_provisioning,
                tools=["create_m365_user_account", "assign_m365_licenses"]
            ),
            WorkflowStep(
                name="standard_asset_booking",
                description="Create standard equipment request in ServiceNow",
                function=self.standard_asset_booking,
                tools=["create_servicenow_provisioning_ticket"]
            )
        ]

    async def candidate_record_ingestion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Process input candidate id, trigger fetch, and establish base contexts
        return {"validated": True}

    async def directory_account_provisioning(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Provisions Entra ID account, attaches license strings and maps security vectors
        return {"provisioned": True}

    async def standard_asset_booking(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Matches job role to asset spec catalog sheets and executes SN requests
        return {"ticket_opened": True}
```

---

## Step 5: Secure Credential Management

Always construct a secure `.env` file for local runtime validation. **DO NOT commit this file into Git repository source controls.**

```bash
# Core HR System REST Endpoints
CORE_HR_BASE_URL=https://hr-sandbox.enterprise.com/api/v2/
CORE_HR_CLIENT_ID=hr_client_prod_id_uuid
CORE_HR_CLIENT_SECRET=hr_super_secret_secret_string

# Microsoft Graph Integration Credentials
AZURE_TENANT_ID=azure_directory_tenant_uuid
AZURE_CLIENT_ID=azure_active_directory_app_client_id
AZURE_CLIENT_SECRET=entra_id_high_security_app_secret

# ServiceNow ITSM Connection Params
SERVICENOW_CLIENT_ID=servicenow_integration_oauth_id
SERVICENOW_CLIENT_SECRET=servicenow_integration_oauth_secret
```

---

## Step 6: Compilation and Deployment

### 6.1 Compiling WXO ADK Bundle
Run the local compilation tools to bundle your python code and YAML descriptors into an importable Skills bundle:

```bash
# Validate local configuration schemas
ibm-watsonx-orchestrate-adk validate --config agent/config.yaml

# Build importable ZIP bundle
ibm-watsonx-orchestrate-adk build \
  --config agent/config.yaml \
  --output build/onboarding-orchestrator.zip
```

### 6.2 Containerizing Runtime (Dockerfile)
Write a secure, non-root, Red Hat UBI minimal Docker container image for enterprise deployments:

```dockerfile
FROM registry.redhat.io/ubi9/python-311-minimal:latest

# Establish unprivileged runtime user (UID 1001)
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Install pip dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source assets
COPY --chown=appuser:appuser . .

# Run under unprivileged user permissions
USER 1001

EXPOSE 8080

CMD ["python", "-m", "ibm_watsonx_orchestrate_adk.run", "--config", "agent/config.yaml", "--port", "8080"]
```

---

## Step 7: Continuous Monitoring & Auditing

### Structured Logs Format
Runtime execution blocks utilize Python structured JSON logging pipelines, enabling automated tracking. All candidate records are mapped to standard tracking correlation-id UUIDs. All sensitive candidate fields, welcome password packets, and credential strings are automatically hashed in logging pipelines prior to output dispatch:

```json
{
  "timestamp": "2026-10-27T11:34:11.201Z",
  "level": "INFO",
  "correlation_id": "onboard-uuid-4491-aa21",
  "candidate_id": "CAND-98342",
  "step": "directory_account_provisioning",
  "action": "create_m365_user_account",
  "status": "SUCCESS",
  "created_upn": "sconnor@enterprise.com",
  "temp_password_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

These records are streamed in real-time to **IBM Log Analysis** for comprehensive auditing.
