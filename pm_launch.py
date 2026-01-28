import requests

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from typing import List, Optional, Union, Dict
from datetime import datetime


# --------------------- #
# Define MCP Servers    #
# --------------------- #
# Bearer token and base URL for MCP server  [OpenProject MCP Server]
PM_BASE_URL = "http://172.18.33.132:8034"
pm_headers = {"Content-Type": "application/json"}


# --------------------- #
# Define tool functions #
# --------------------- #

def list_projects(filters: Optional[dict] = None) -> dict:
    """
    Retrieves a list of all available projects. 
    Useful for finding project IDs before looking up specific work packages.
    """
    url = f"{PM_BASE_URL}/list_projects"
    
    # Even if no filters are provided, we send an empty dict 
    # as the API expects a POST body.
    payload = filters if filters else {}

    try:
        response = requests.post(url, headers=pm_headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to retrieve projects list: {str(e)}"}

def get_project_work_packages(
    project_id: int, 
    offset: Optional[int] = 1, 
    page_size: Optional[int] = 20, 
    filters: Optional[Union[List, Dict]] = None, 
    sort_by: Optional[List[Dict]] = None
) -> dict:
    """Retrieves work packages for a specific project."""
    url = f"{PM_BASE_URL}/get_project_work_packages"
    payload = {"project_id": project_id, "offset": offset, "page_size": page_size}
    if filters: payload["filters"] = filters
    if sort_by: payload["sort_by"] = sort_by

    try:
        response = requests.post(url, headers=pm_headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def create_project(
    name: str, 
    public: bool = True, 
    description: Optional[str] = None, 
    identifier: Optional[str] = None, 
    status_explanation: Optional[str] = None
) -> dict:
    """Creates a new project in OpenProject."""
    url = f"{PM_BASE_URL}/create_project"
    payload = {"name": name, "public": public}
    if description: payload["description"] = description
    if identifier: payload["identifier"] = identifier
    if status_explanation: payload["status_explanation"] = status_explanation

    try:
        response = requests.post(url, headers=pm_headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def create_work_package(
    project_id: int, 
    subject: str, 
    notify: bool = True, 
    description: Optional[str] = None, 
    status_id: Optional[int] = None, 
    type_id: Optional[int] = None, 
    priority_id: Optional[int] = None
) -> dict:
    """Creates a new work package within a project."""
    url = f"{PM_BASE_URL}/create_work_package"
    payload = {"project_id": project_id, "subject": subject, "notify": notify}
    if description: payload["description"] = description
    if status_id: payload["status_id"] = status_id
    if type_id: payload["type_id"] = type_id
    if priority_id: payload["priority_id"] = priority_id

    try:
        response = requests.post(url, headers=pm_headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def update_work_package(
    work_package_id: int, 
    lock_version: int, 
    notify: bool = True, 
    status_id: Optional[int] = None, 
    description: Optional[str] = None, 
    percentage_done: Optional[int] = None
) -> dict:
    """Updates an existing work package using lock_version."""
    url = f"{PM_BASE_URL}/update_work_package"
    payload = {"work_package_id": work_package_id, "lock_version": lock_version, "notify": notify}
    if status_id: payload["status_id"] = status_id
    if description: payload["description"] = description
    if percentage_done is not None: payload["percentage_done"] = percentage_done

    try:
        response = requests.post(url, headers=pm_headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def view_work_package(work_package_id: int = None) -> dict:
    """
    Retrieves the details of a specific work package. 
    Essential for obtaining the 'lockVersion' before performing updates.
    """
    url = f"{PM_BASE_URL}/view_work_package"
    current_time = datetime.now().isoformat()
    
    # Construct payload
    payload = {
        "work_package_id": work_package_id,
        "timestamps": [current_time]
    }
    
    try:
        response = requests.post(url, headers=pm_headers, json=payload)
        response.raise_for_status() # Raises an error for 4xx/5xx responses
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to retrieve work package: {str(e)}"}

def comment_work_package(work_package_id: int, comment_text: str, notify: bool = True) -> dict:
    """
    Adds a comment or activity log to a specific work package.
    """
    url = f"{PM_BASE_URL}/comment_work_package"
    
    payload = {
        "work_package_id": work_package_id,
        "comment_text": comment_text,
        "notify": notify
    }

    try:
        response = requests.post(url, headers=pm_headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to add comment to WP {work_package_id}: {str(e)}"}

def list_statuses() -> dict:
    """
    Retrieves all available work package statuses.
    Use this to find the correct status_id (e.g., 'to be scheduled') 
    before creating or updating a work package.
    """
    url = f"{PM_BASE_URL}/list_statuses"
    
    # Sending an empty payload as it's a POST request with no params
    payload = {}

    try:
        response = requests.post(url, headers=pm_headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to retrieve statuses: {str(e)}"}

def is_done(msg):
    content = (msg.get("content") or "").lower()
    return "task complete" in content



# --------------------- #
# DEFINE AGENTS TO USE #
# --------------------- #

# Initialize AutoGen agents
# define their roles, etc.
assistant = AssistantAgent(
    name="Astra-Mini",
    system_message="You are Astra-Mini, your job is to follow the user's instructions carefully and use the provided tools to get the current time. Remember to add 'TASK COMPLETE' at the end of your response, when the task is completed.",
    is_termination_msg=is_done,
    llm_config={
        "config_list": [
            {
                "model": "/models/LFM2-8B-A1B-Q4_K_M.gguf",
                "base_url": "http://172.18.33.245:8085/v1",
                "api_key": "NULL",
                "price": [0, 0]
            }
        ]
    }
)

assistantGM = AssistantAgent(
    name="GraniteMan",
    system_message=(
        "You are GraniteMan. Validate whether Astra-Mini correctly completed the user's request. "
        "If validation is complete, you MUST end your message with exactly: TASK COMPLETE. "
        "Do not send any additional follow-up messages after that."
    ),
    is_termination_msg=is_done,
    llm_config={
        "config_list": [
            {
                "model": "/models/granite-4.0-h-1b-IQ4_NL.gguf",
                "base_url": "http://172.18.33.145:8084/v1",
                "api_key": "NULL",
                "price": [0, 0]
            }
        ]
    }
)









# --------------------- #
# REGISTER TOOLS FOR AGENTS #
# --------------------- #

# SIDE NOTE: You can adjust human_input_mode and max_consecutive_auto_reply as needed
# SIDENOTE2: assistantGM does not need to execute tools, we do not create a UserProxyAgent for it
# SIDENOTE3: If you want to have human input for the user proxy, change human_input_mode to "ALWAYS" or "ASK_USER"
# SIENOTE4: We must register the tools for execution for the UserProxyAgent to use them
# SIDENOTE5: To make tools avaiable to the LLMs, we must register them for LLM as well.

#user_proxy = UserProxyAgent(name="Automated Systems User", human_input_mode="NEVER", max_consecutive_auto_reply=3)
user_proxy = UserProxyAgent(name="Automated Systems User", human_input_mode="NEVER", is_termination_msg=is_done)



# Register for Astra-Mini (The Worker)
assistant.register_for_llm(
    name="view_work_package", 
    description="Retrieves work package details and lockVersion. Only requires work_package_id."
)(view_work_package)

# Register for GraniteMan (The Evaluator)
assistantGM.register_for_llm(
    name="view_work_package", 
    description="Retrieves work package details to verify Astra-Mini's work."
)(view_work_package)

# Register for Execution
user_proxy.register_for_execution(name="view_work_package")(view_work_package)



# Register for Astra-Mini (The Worker)
assistant.register_for_llm(
    name="update_work_package", 
    description="Updates a work package. You MUST provide the lock_version retrieved from view_work_package."
)(update_work_package)

# Register for GraniteMan (The Evaluator)
assistantGM.register_for_llm(
    name="update_work_package", 
    description="Evaluates the success of the work package update."
)(update_work_package)

# Register for Execution
user_proxy.register_for_execution(name="update_work_package")(update_work_package)



# Register for Astra-Mini
assistant.register_for_llm(
    name="list_projects", 
    description="Lists all projects. Use this to find project IDs."
)(list_projects)

# Register for GraniteMan
assistantGM.register_for_llm(
    name="list_projects", 
    description="Lists all projects to verify project existence."
)(list_projects)

# Register for Execution
user_proxy.register_for_execution(name="list_projects")(list_projects)



# Register for Astra-Mini (Primary Researcher)
assistant.register_for_llm(
    name="get_project_work_packages", 
    description="Fetch tasks/bugs within a project. Use filters to narrow down by status or priority."
)(get_project_work_packages)

# Register for GraniteMan (Validator)
assistantGM.register_for_llm(
    name="get_project_work_packages", 
    description="Fetch project tasks to verify work package lists."
)(get_project_work_packages)

# Register for Execution
user_proxy.register_for_execution(name="get_project_work_packages")(get_project_work_packages)



# Register for Astra-Mini (The Creator)
assistant.register_for_llm(
    name="create_work_package", 
    description="Create a new task or bug in a specific project. Requires project_id and subject."
)(create_work_package)

# Register for GraniteMan (The Auditor)
assistantGM.register_for_llm(
    name="create_work_package", 
    description="Verifies the creation parameters for a new work package."
)(create_work_package)
# Register for Execution
user_proxy.register_for_execution(name="create_work_package")(create_work_package)

# Register for Astra-Mini (The Architect)
assistant.register_for_llm(
    name="create_project", 
    description="Create a new project. Requires a unique name."
)(create_project)

# Register for GraniteMan (The Quality Controller)
assistantGM.register_for_llm(
    name="create_project", 
    description="Verifies the creation of a new project and its settings."
)(create_project)

# Register for Execution
user_proxy.register_for_execution(name="create_project")(create_project)



# Register for Astra-Mini
assistant.register_for_llm(name="comment_work_package", description="Adds a comment to a work package.")(comment_work_package)
# Register for GraniteMan
assistantGM.register_for_llm(name="comment_work_package", description="Verifies comment addition.")(comment_work_package)
# Register for Execution
user_proxy.register_for_execution(name="comment_work_package")(comment_work_package)



# Register for Astra-Mini
assistant.register_for_llm(name="list_statuses", description="Lists all available work package statuses and their IDs.")(list_statuses)
# Register for GraniteMan
assistantGM.register_for_llm(name="list_statuses", description="Verifies status IDs.")(list_statuses)
# Register for Execution
user_proxy.register_for_execution(name="list_statuses")(list_statuses)







# --------------------- #
# Define conversation flow #
# --------------------- #

# Begin conversation Preperation
# Define the list of agents in the room
groupchat = GroupChat(
    agents=[user_proxy, assistant, assistantGM], 
    messages=[], 
    max_round=10
)
manager = GroupChatManager(groupchat=groupchat, llm_config=assistantGM.llm_config)

#Demo Workflow
#user_question = (
#    "Astra-Mini: We need to initialize the SACU IT Vulnerability Tracking for Feb 2026. \n"
#    "1. Create a project named 'SACU IT Vulnerability Tracking Feb 2026' (ID: sacu-it-vultrack-feb26). \n"
#    "2. Find the status_id for 'to be scheduled' using the list_statuses tool. \n"
#    "3. Create a work package labeled 'test' in that project using the correct status_id. \n"
#    "4. Add a comment to that work package: 'This was pushed via AutoGen!' \n\n"
#    "GraniteMan: Validate the project ID, the status used, and confirm the comment appears in the activity log."
#)
user_question = input("Enter your task for Astra-Mini and GraniteMan (Project Managers): ")

assistant_reply = user_proxy.initiate_chat(
    manager,
    message=user_question,
)
