from typing import Any
import httpx
import sqlite3
import json
from mcp.server.fastmcp import FastMCP
from typing import Optional, Union, Dict, List, Any
from config import host
from config import xcred as api_key

import mimetypes
import os

# Initialize FastMCP server
mcp = FastMCP("openproject-api-proxy")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Function to make requests to API
async def make_request(url: str, method: str, headers: dict = None, data: dict = None, params: dict = None) -> dict[str, Any] | None:
    """
    Makes an HTTP request to a specified Open Project (Project MGMT) API endpoint, handles errors, and returns the response.
    
    Args:
        url (str): The URL of the API endpoint.
        method (str): The HTTP method to be used for the request (GET, POST, PUT, DELETE, etc.).
        headers (Optional[Dict[str, str]]): A dictionary containing headers like Authorization.
        data (Optional[Dict[str, Any]]): The request body data for POST, PUT, or PATCH methods.
        params (Optional[Dict[str, Any]]): Query parameters for GET requests.

    Returns:
        Optional[Dict[str, Any]]: The parsed JSON response from the API, or an error message if the request fails.
    
    Description:
        This function makes asynchronous API requests using the `httpx` library. It supports common HTTP
        methods (GET, POST, PUT, DELETE) and includes error handling for both network issues and HTTP errors.
        It raises exceptions for non-2xx HTTP responses and provides detailed error messages for debugging.
    """
    headers = headers or {}
    headers["User-Agent"] = USER_AGENT
    async with httpx.AsyncClient(verify=False) as client:
        try:
            method_lower = method.lower()
            request_args = {"headers": headers, "timeout": 30.0}

            if method_lower in ["get", "delete", "head", "options"]:
                # For methods that do not send JSON body, use params for query parameters
                request_args["params"] = data or params
            else:
                # For methods that can send a JSON body
                request_args["json"] = data
                if params:
                    request_args["params"] = params

            response = await getattr(client, method_lower)(url, **request_args)
            response.raise_for_status()
            #return json.dumps(response).json()
            return response.json()

        except httpx.HTTPStatusError as e:
            return {
                "error": "HTTP error",
                "status": e.response.status_code,
                "details": e.response.text,
            }
        except Exception as e:
            return {
                "error": "Request failed",
                "details": str(e),
            }

@mcp.tool()
async def run_api(query: str, method: str) -> str:
    """
    RUN API, or run_api Forwards the query to the external Open Project (Project MGMT) REST API using the provided method and query.
    
    Args:
        query (str): The path or query to search for in the external Open Project (Project MGMT) API.
        method (str): The HTTP method to use (GET, POST, PUT, DELETE, etc.).
    
    Returns:
        str: The JSON string of the API response or an error message if the request fails.
    
    Description:
        This function forwards the provided query and method to the external API, adds the necessary
        authentication token to the request headers, and handles the request asynchronously.
        It also handles response formatting and error handling to return a clean response.
    """
    # Prepare headers
    host = "pm.v.spaceagecu.org/api/v3"
    api_url = f"https://{host}{query}"
    api_key = f"Basic {api_key}"
    headers = {"Authorization": api_key, "Content-Type": "application/json", "Connection": "keep-alive"}
    
    data = None  # This would depend on your API's request body
    params = None  # Query parameters, if any

    # Forward the request to the external API and return the response
    response = await make_request(f"{api_url}", method, headers=headers, data=data, params=params)
    return json.dumps(response)

@mcp.tool()
async def create_project(name: str, description: Optional[str] = None, identifier: Optional[str] = None, public: bool = True,status_explanation: Optional[str] = None) -> str:
    """
    Creates a new project in OpenProject via the API.
    
    Args:
        name (str): The display name of the project.
        description (str, optional): A description of the project.
        identifier (str, optional): A unique, URL-friendly identifier (e.g., 'my-project'). 
                                    If not provided, it will be generated from the name.
        public (bool): Whether the project is visible to everyone. Defaults to True.
        status_explanation (str, optional): A text explanation of the project status.
    
    Returns:
        str: The JSON response from the API containing the created project details, or an error message.
    """
    
    
    # Prepare headers
    method = "POST"
    api_url = f"https://{host}/api/v3/projects"
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # OpenProject uses nested objects for text fields (e.g., { "raw": "text" })
    payload = {
        "name": name,
        "identifier": identifier,
        "public": public,
        "active": True,
        "_type": "Project"
    }

    if description:
        payload["description"] = { 
            "format": "markdown", 
            "raw": description 
        }

    if status_explanation:
        payload["statusExplanation"] = { 
            "format": "markdown", 
            "raw": status_explanation 
        }
    
    try:
        response = await make_request(
            url=api_url, 
            method="POST", 
            headers=headers, 
            json=payload
        )
        return json.dumps(response)
    except Exception as e:
        return f"Error creating project: {str(e)}"

@mcp.tool()
async def view_project(project_id: int) -> str:
    """
    Retrieves the details of a specific project from OpenProject by its numeric ID.
    
    Args:
        project_id (int): The unique numeric ID of the project to view (e.g., 123).
    
    Returns:
        str: The JSON string containing the project details (name, description, status, etc.) 
             or an error message if the project is not found.
    """
    # 1. Configuration (Load from environment variables/shared state)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/projects/{id}
    api_url = f"https://{host}/api/v3/projects/{project_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        # GET requests usually don't have a body (data/json=None)
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving project {project_id}: {str(e)}"

@mcp.tool()
async def list_projects() -> Dict[str, Any]:
    """
    Retrieves a list of projects from OpenProject, optionally filtering and sorting the results.
    
    Returns:
        str: The JSON collection of projects matching the criteria or an error message.
    """
    api_url = f"https://{host}/api/v3/projects"

    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }

    return await make_request(
        url=api_url,
        method="GET",
        headers=headers
    )

@mcp.tool()
async def list_statuses() -> str:
    """
    Retrieves a collection of all available work package statuses (e.g., New, In Progress, Closed).
    
    Returns:
        str: The JSON collection of work package statuses or an error message.
    """
    
    # 1. Configuration

    
    # 2. Construct the URL
    # URL pattern: GET /api/v3/statuses
    api_url = f"https://{host}/api/v3/statuses"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        # make_request returns a Python dictionary (deserialized JSON)
        response_dict = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        
        # 5. CONVERT DICT TO JSON STRING BEFORE RETURNING
        return json.dumps(response_dict) # <-- THE FIX
        
    except Exception as e:
        return f"Error retrieving work package statuses: {str(e)}"

@mcp.tool()
async def update_project(
    project_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    identifier: Optional[str] = None,
    public: Optional[bool] = None,
    active: Optional[bool] = None,
    status_explanation: Optional[str] = None
) -> str:
    """
    Updates an existing project in OpenProject. Only the fields provided will be updated.

    Args:
        project_id (int): The numeric ID of the project to update.
        name (str, optional): New name for the project.
        description (str, optional): New description.
        identifier (str, optional): New URL identifier (careful: this changes URLs).
        public (bool, optional): Update visibility (True for public, False for private).
        active (bool, optional): Update status (True for active, False for archived).
        status_explanation (str, optional): Update the status explanation text.

    Returns:
        str: JSON string of the updated project or error message.
    """

    # 1. Configuration
    api_url = f"https://{host}/api/v3/projects/{project_id}"

    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }

    # 2. Build Payload Dynamically
    # We only want to include keys that are NOT None.
    # Sending "name": null might erase the name or cause an error, 
    # so we iterate and check.
    payload = {}

    if name is not None:
        payload["name"] = name

    if identifier is not None:
        payload["identifier"] = identifier

    if public is not None:
        payload["public"] = public

    if active is not None:
        payload["active"] = active
    
    # Handle nested text fields
    if description is not None:
        payload["description"] = { "raw": description }

    if status_explanation is not None:
        payload["statusExplanation"] = { "raw": status_explanation }

    # If no fields were provided to update, return early
    if not payload:
        return "No update fields provided. Please specify at least one field to change."

    # 3. Send Request (PATCH)
    try:
        response = await make_request(
            url=api_url,
            method="PATCH",
            headers=headers,
            json=payload
        )
        return json.dumps(response)

    except Exception as e:
        return f"Error updating project {project_id}: {str(e)}"

@mcp.tool()
async def view_project_status(status_id: Union[int, str]) -> str:
    """
    Retrieves the definition and details of a specific project status (e.g., 'On track', 'Archived').

    Args:
        status_id (Union[int, str]): The unique ID of the project status to view.
                                     This is typically an integer ID, but sometimes OpenProject 
                                     APIs allow the string identifier as well.

    Returns:
        str: The JSON string containing the project status details or an error message.
    """
    
    # 1. Configuration (Load from environment variables/shared state)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/project_statuses/{id}
    api_url = f"https://{host}/api/v3/project_statuses/{status_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        # GET requests typically use method="GET" and do not require a request body (json/data)
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving project status {status_id}: {str(e)}"

@mcp.tool()
async def get_project_work_packages(
    project_id: int,
    offset: Optional[int] = None,
    page_size: Optional[int] = None,
    filters: Optional[Union[List, Dict]] = None,
    sort_by: Optional[List[Dict[str, str]]] = None,
    group_by: Optional[str] = None,
    show_sums: Optional[bool] = None,
    select: Optional[List[str]] = None
) -> str:
    """
    Retrieves a collection of work packages (tasks, bugs, etc.) for a specific project.
    
    Args:
        project_id (int): The numeric ID of the project.
        offset (int, optional): Page number (1-based) for pagination.
        page_size (int, optional): Number of items per page.
        filters (Union[List, Dict], optional): JSON-compatible filter conditions.
                                               Example: [{"status": {"operator": "=", "values": ["1"]}}]
        sort_by (List[Dict], optional): JSON-compatible sort criteria.
                                        Example: [{"updatedAt": "desc"}]
        group_by (str, optional): The column name to group results by (e.g., "priority").
        show_sums (bool, optional): Whether to sum up numerical properties.
        select (List[str], optional): Specific properties to include in the response (e.g., ["id", "subject"]).
    
    Returns:
        str: JSON string containing the list of work packages.
    """
    
    # 1. Configuration
    
    # 2. Construct URL (Path Parameter)
    api_url = f"https://{host}/api/v3/projects/{project_id}/work_packages"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Construct Query Parameters
    params = {}
    
    if offset is not None:
        params['offset'] = offset
        
    if page_size is not None:
        params['pageSize'] = page_size
        
    if filters is not None:
        # OpenProject expects a JSON string for filters
        params['filters'] = json.dumps(filters)
        
    if sort_by is not None:
        # OpenProject expects a JSON string for sorting
        params['sortBy'] = json.dumps(sort_by)
        
    if group_by is not None:
        params['groupBy'] = group_by
        
    if show_sums is not None:
        params['showSums'] = "true" if show_sums else "false"
        
    if select is not None:
        # Join list into comma-separated string
        params['select'] = ",".join(select)

    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers,
            params=params
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving work packages for project {project_id}: {str(e)}"

@mcp.tool()
async def get_project_available_assignees(project_id: int) -> str:
    """
    Retrieves a collection of users who can be assigned to work packages 
    within the specified project. This includes project members and users 
    with appropriate permissions.
    
    Args:
        project_id (int): The numeric ID of the project.

    Returns:
        str: The JSON collection of available assignees (users) or an error message.
    """
    
    # 1. Configuration
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/projects/{id}/available_assignees
    api_url = f"https://{host}/api/v3/projects/{project_id}/available_assignees"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving available assignees for project {project_id}: {str(e)}"

@mcp.tool()
async def view_work_package(
    work_package_id: int,
    timestamps: Optional[List[str]] = None
) -> str:
    """
    Retrieves the details of a specific work package by its ID. 
    This is often the first step before updating the work package to retrieve its 'lockVersion'.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package to view.
        timestamps (List[str], optional): A list of ISO-8601 timestamps (e.g., ["2025-01-01"]) 
                                          for performing a baseline comparison of attributes.

    Returns:
        str: The JSON string containing the work package details, including the mandatory 
             'lockVersion' needed for updates, or an error message.
    """
    
    # 1. Configuration
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/work_packages/{id}
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }

    # 4. Construct Query Parameters
    params = {}
    if timestamps is not None:
        # Join list into comma-separated string for baseline comparison
        params['timestamps'] = ",".join(timestamps)
    
    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers,
            params=params
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving work package {work_package_id}: {str(e)}"

@mcp.tool()
async def create_work_package(
    project_id: int,
    subject: str,
    description: Optional[str] = None,
    type_id: Optional[int] = None,
    priority_id: Optional[int] = None,
    status_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    start_date: Optional[str] = None,
    due_date: Optional[str] = None,
    estimated_time: Optional[str] = None,
    notify: bool = True
) -> str:
    """
    Creates a new work package (Task, Bug, Feature, etc.) within a specific project.
    
    Args:
        project_id (int): The numeric ID of the project where this work package belongs.
        subject (str): The title or subject of the work package.
        description (str, optional): The detailed description of the work.
        type_id (int, optional): The ID of the work package type (e.g., 1 for Task, 2 for Bug). 
                                 Crucial for defining workflow.
        priority_id (int, optional): The ID of the priority (e.g., 4 for High).
        status_id (int, optional): The ID of the status (e.g., 1 for New).
        assignee_id (int, optional): The numeric user ID of the person assigned to this work.
        start_date (str, optional): Start date in 'YYYY-MM-DD' format.
        due_date (str, optional): Due date in 'YYYY-MM-DD' format.
        estimated_time (str, optional): Estimated time format (e.g., "PT5H" for 5 hours).
        notify (bool): Whether to send email notifications to watchers/assignees. Defaults to True.
    
    Returns:
        str: JSON string of the created work package or an error message.
    """
    
    # 1. Configuration

    # 2. URL and Query Params
    # POST /api/v3/projects/{id}/work_packages
    api_url = f"https://{host}/api/v3/projects/{project_id}/work_packages"
    
    # 3. Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Construct Query String for notification
    params = {"notify": "true" if notify else "false"}

    # 5. Build the Payload
    # Basic fields
    payload = {
        "subject": subject
    }
    
    if description:
        payload["description"] = { "raw": description }
        
    if start_date:
        payload["startDate"] = start_date
        
    if due_date:
        payload["dueDate"] = due_date
        
    if estimated_time:
        payload["estimatedTime"] = estimated_time

    # 6. Build the _links object (OpenProject's way of setting relationships)
    links = {}
    
    if type_id:
        links["type"] = { "href": f"/api/v3/types/{type_id}" }
        
    if priority_id:
        links["priority"] = { "href": f"/api/v3/priorities/{priority_id}" }
        
    if status_id:
        links["status"] = { "href": f"/api/v3/statuses/{status_id}" }
        
    if assignee_id:
        links["assignee"] = { "href": f"/api/v3/users/{assignee_id}" }

    # Only add _links to payload if we actually added any links
    if links:
        payload["_links"] = links

    # 7. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="POST", 
            headers=headers,
            params=params,
            json=payload
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error creating work package in project {project_id}: {str(e)}"

@mcp.tool()
async def list_work_packages(
    filters: Optional[Union[List, Dict]] = None
) -> str:
    """
    Retrieves a global collection of work packages (tasks, bugs, etc.) across all projects.
    Can be filtered by project, assignee, status, etc.
    
    Args:
        filters (Union[List, Dict], optional): JSON-compatible filter conditions.
            Examples:
            - Find open bugs: [{"type": {"operator": "=", "values": ["1"]}, "status": {"operator": "o", "values": []}}]
            - Specific Project: [{"project": {"operator": "=", "values": ["5"]}}]
        sort_by (List[Dict], optional): JSON-compatible sort criteria. Example: [{"id": "desc"}]
    
    Returns:
        str: JSON string containing the list of work packages.
    """
    
    # 1. Configuration
    
    # 2. URL (Global endpoint)
    api_url = f"https://{host}/api/v3/work_packages"
    
    # 3. Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    

    default_status_filter = {
        "status_id": {
            "operator": "o",
            "values": None
        }
    }

    if filters is None:
        effective_filters = [default_status_filter]
    elif filters == []:
        effective_filters = []
    else:
        effective_filters = [default_status_filter, *filters]

    effective_sort_by = [["id", "asc"]]
    effective_timestamps = "PT0S"
    
    params = {
        "offset": 1,
        "pageSize": 20,
        "filters": json.dumps(effective_filters),
        "sortBy": json.dumps(effective_sort_by),

        "showSums": "false",

        "timestamps": effective_timestamps
    }

    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers,
            params=params
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error listing work packages: {str(e)}"

@mcp.tool()
async def list_work_package_activities(work_package_id: int) -> str:
    """
    Retrieves the chronological list of activities (history, comments, status changes) 
    related to a specific work package.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package.

    Returns:
        str: The JSON collection of activities/events associated with the work package 
             or an error message.
    """
    
    # 1. Configuration
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/work_packages/{id}/activities
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/activities"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving activities for work package {work_package_id}: {str(e)}"

@mcp.tool()
async def update_work_package(
    work_package_id: int,
    lock_version: int,
    subject: Optional[str] = None,
    description: Optional[str] = None,
    percentage_done: Optional[int] = None,
    type_id: Optional[int] = None,
    priority_id: Optional[int] = None,
    status_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    start_date: Optional[str] = None,
    due_date: Optional[str] = None,
    estimated_time: Optional[str] = None,
    notify: bool = True
) -> str:
    """
    Updates an existing work package (Task, Bug, etc.) with specified fields.
    
    Args:
        work_package_id (int): The numeric ID of the work package to update.
        lock_version (int): The lockVersion received from the last GET request 
                            on this work package. REQUIRED for optimistic locking.
        subject (str, optional): The new title of the work package.
        description (str, optional): The new detailed description.
        percentage_done (int, optional): Completion percentage (0 to 100).
        type_id (int, optional): ID of the new work package type.
        priority_id (int, optional): ID of the new priority.
        status_id (int, optional): ID of the new status (e.g., to close the work package).
        assignee_id (int, optional): ID of the new user assigned to this work.
        start_date (str, optional): New start date in 'YYYY-MM-DD' format.
        due_date (str, optional): New due date in 'YYYY-MM-DD' format.
        estimated_time (str, optional): New estimated time (e.g., "PT5H").
        notify (bool): Whether to send email notifications. Defaults to True.
    
    Returns:
        str: JSON string of the updated work package or an error message.
    """
    
    # 1. Configuration

    
    # 2. URL and Query Params
    # PATCH /api/v3/work_packages/{id}
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}"
    
    # 3. Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Construct Query String for notification
    params = {"notify": "true" if notify else "false"}

    # 5. Build the Payload (Optimistic Locking is MANDATORY)
    payload = {
        "lockVersion": lock_version 
    }
    
    # Simple fields
    if subject is not None:
        payload["subject"] = subject
        
    if percentage_done is not None:
        payload["percentageDone"] = percentage_done
        
    if start_date is not None:
        payload["startDate"] = start_date
        
    if due_date is not None:
        payload["dueDate"] = due_date
        
    if estimated_time is not None:
        payload["estimatedTime"] = estimated_time

    # Nested fields
    if description is not None:
        payload["description"] = { "raw": description }
        
    # 6. Build the _links object (for relationship updates)
    links = {}
    
    if type_id is not None:
        links["type"] = { "href": f"/api/v3/types/{type_id}" }
        
    if priority_id is not None:
        links["priority"] = { "href": f"/api/v3/priorities/{priority_id}" }
        
    if status_id is not None:
        links["status"] = { "href": f"/api/v3/statuses/{status_id}" }
        
    if assignee_id is not None:
        links["assignee"] = { "href": f"/api/v3/users/{assignee_id}" }

    if links:
        payload["_links"] = links
        
    # 7. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="PATCH",  # Use PATCH for partial update
            headers=headers,
            params=params,
            json=payload
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error updating work package {work_package_id}: {str(e)}"

@mcp.tool()
async def comment_work_package(
    work_package_id: int,
    comment_text: str,
    notify: bool = True
) -> str:
    """
    Adds a new comment (activity) to a specific work package.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package to comment on.
        comment_text (str): The content of the comment to be added.
        notify (bool): Indicates whether change notifications (e.g., via email) should be sent. 
                       Defaults to True.

    Returns:
        str: The JSON string containing the newly created activity/comment or an error message.
    """
    
    # 1. Configuration

    # 2. Construct the URL with the Path Parameter
    # URL pattern: POST /api/v3/work_packages/{id}/activities
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/activities"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Construct Query Parameters
    params = {"notify": "true" if notify else "false"}
    
    # 5. Build the Payload
    # The API documentation implies the body should contain a 'comment' object 
    # to add a comment (text entry).
    payload = {
        "_type": "Comment",
        "comment": {
            "raw": comment_text
        }
    }

    # 6. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="POST", 
            headers=headers,
            params=params,
            json=payload
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error commenting on work package {work_package_id}: {str(e)}"

@mcp.tool()
async def get_work_package_available_assignees(work_package_id: int) -> str:
    """
    Retrieves a collection of users who are available and eligible to be assigned 
    to the specific work package. This considers the work package's project and type 
    for permission filtering.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package.

    Returns:
        str: The JSON collection of available assignees (users) or an error message.
    """
    
    # 1. Configuration
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/work_packages/{id}/available_assignees
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/available_assignees"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving available assignees for work package {work_package_id}: {str(e)}"

@mcp.tool()
async def get_work_package_available_watchers(work_package_id: int) -> str:
    """
    Retrieves a collection of users who are eligible to be watchers (subscribers to notifications) 
    for the specified work package.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package.

    Returns:
        str: The JSON collection of available watchers (users) or an error message.
    """
    
    # 1. Configuration
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/work_packages/{id}/available_watchers
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/available_watchers"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving available watchers for work package {work_package_id}: {str(e)}"

@mcp.tool()
async def list_work_package_watchers(work_package_id: int) -> str:
    """
    Retrieves a collection of users who are currently set as watchers for the specified work package.
    These users receive notifications about changes.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package.

    Returns:
        str: The JSON collection of current watchers (users) or an error message.
    """
    
    # 1. Configuration

    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/work_packages/{id}/watchers
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/watchers"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving watchers for work package {work_package_id}: {str(e)}"

@mcp.tool()
async def add_work_package_watcher(work_package_id: int, user_id: int) -> str:
    """
    Adds a specified user as a watcher to a work package, enabling them to receive 
    notifications about changes.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package.
        user_id (int): The numeric ID of the user to be added as a watcher.

    Returns:
        str: The JSON object of the user who was added as a watcher, 
             or an error message. Returns success even if the user was already a watcher.
    """
    
    # 1. Configuration

    # 2. Construct the URL with the Path Parameter
    # URL pattern: POST /api/v3/work_packages/{id}/watchers
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/watchers"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Build the Payload
    # The request body requires a link object under the 'user' key.
    payload = {
        "_links": {
            "user": {
                "href": f"/api/v3/users/{user_id}"
            }
        }
    }

    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="POST", 
            headers=headers,
            json=payload
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error adding watcher to work package {work_package_id}: {str(e)}"

@mcp.tool()
async def remove_work_package_watcher(work_package_id: int, user_id: int) -> str:
    """
    Removes a specified user from the list of watchers for a work package.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package.
        user_id (int): The numeric ID of the user to be removed as a watcher.

    Returns:
        str: A success message (typically an empty body with HTTP 204 No Content) 
             or an error message.
    """
    
    # 1. Configuration

    
    # 2. Construct the URL with the Path Parameters
    # URL pattern: DELETE /api/v3/work_packages/{id}/watchers/{user_id}
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/watchers/{user_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        # DELETE requests typically do not have a body
        response = await make_request(
            url=api_url, 
            method="DELETE", 
            headers=headers
        )
        # HTTP DELETE requests usually return 204 No Content on success
        return f"Successfully removed user {user_id} as watcher from work package {work_package_id}. Response: {response}"
        
    except Exception as e:
        return f"Error removing watcher from work package {work_package_id}: {str(e)}"

@mcp.tool()
async def view_activity(activity_id: int) -> str:
    """
    Retrieves the details of a specific activity (e.g., a comment, a work package history entry) 
    by its unique ID.
    
    Args:
        activity_id (int): The unique numeric ID of the activity.

    Returns:
        str: The JSON object containing the activity details or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/activities/{id}
    api_url = f"https://{host}/api/v3/activities/{activity_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving activity {activity_id}: {str(e)}"

@mcp.tool()
async def update_activity(activity_id: int, new_comment_text: str) -> str:
    """
    Updates the comment text of a specific activity by its ID. 
    This is generally used to edit comments previously posted to a work package.
    
    Args:
        activity_id (int): The unique numeric ID of the activity (comment) to update.
        new_comment_text (str): The new raw text content for the comment.

    Returns:
        str: The JSON object containing the updated activity details or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: PATCH /api/v3/activities/{id}
    api_url = f"https://{host}/api/v3/activities/{activity_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Build the Payload
    payload = {
        "comment": {
            "raw": new_comment_text
        }
    }
    
    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="PATCH", 
            headers=headers,
            json=payload
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error updating activity {activity_id}: {str(e)}"

@mcp.tool()
async def list_work_package_attachments(work_package_id: int) -> str:
    """
    Retrieves a collection of all attachments (files) associated with a specific work package.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package.

    Returns:
        str: The JSON collection of attachments or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/work_packages/{id}/attachments
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/attachments"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving attachments for work package {work_package_id}: {str(e)}"

@mcp.tool()
async def create_work_package_attachment(
    work_package_id: int,
    file_path: str,
    file_name: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Uploads a file and immediately attaches it to the specified work package.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package to attach the file to.
        file_path (str): The local system path to the file you want to upload.
        file_name (str, optional): The name of the file as it will appear in OpenProject. 
                                   Defaults to the filename from the path.
        description (str, optional): A description of the file.

    Returns:
        str: JSON string containing the new attachment's details or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Endpoint
    # URL pattern: POST /api/v3/work_packages/{id}/attachments
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/attachments"
    
    # 3. Validation
    if not os.path.exists(file_path):
        return f"Error: File not found at path: {file_path}"
        
    if file_name is None:
        file_name = os.path.basename(file_path)
        
    # 4. Prepare Metadata (Part 1 of Multipart)
    metadata = {
        "fileName": file_name
    }
    if description:
        # Note: OpenProject sometimes expects description as a link object {raw: ...}
        # Based on other endpoints, using the structure below is a safe bet for compatibility.
        metadata["description"] = { "raw": description }
        
    # 5. Prepare File Data (Part 2 of Multipart)
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "application/octet-stream"
        
    # 6. Send Request
    try:
        # We need to read the file binary
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        # The 'files' dictionary structures the multipart request
        files = {
            'metadata': (None, json.dumps(metadata), 'application/json'),
            'file': (file_name, file_content, mime_type)
        }
        
        headers = {
            "Authorization": f"Basic {api_key}"
            # Do NOT set Content-Type here; the library will set it to multipart/form-data with boundary
        }

        response = await make_request(
            url=api_url, 
            method="POST", 
            headers=headers,
            files=files
        )
        return json.dumps(response)

    except Exception as e:
        return f"Error creating attachment for work package {work_package_id}: {str(e)}"

@mcp.tool()
async def create_attachment(
    file_path: str,
    file_name: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Uploads a file to OpenProject. The uploaded attachment is initially 'containerless'.
    To link it to a work package, you must use the ID returned by this tool in a 
    subsequent request (e.g., when creating or updating a work package).
    
    Args:
        file_path (str): The local system path to the file you want to upload.
        file_name (str, optional): The name of the file as it will appear in OpenProject. 
                                   Defaults to the filename from the path.
        description (str, optional): A description of the file.

    Returns:
        str: JSON string containing the new attachment's details (including its ID) 
             or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Endpoint
    api_url = f"https://{host}/api/v3/attachments"
    
    # 3. Validation
    if not os.path.exists(file_path):
        return f"Error: File not found at path: {file_path}"
        
    if file_name is None:
        file_name = os.path.basename(file_path)
        
    # 4. Prepare Metadata (Part 1 of Multipart)
    metadata = {
        "fileName": file_name
    }
    if description:
        metadata["description"] = { "raw": description }
        
    # 5. Prepare File Data (Part 2 of Multipart)
    # We need to detect the mime type or default to binary
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "application/octet-stream"
        
    # 6. Send Request
    # Note: Using httpx/requests 'files' parameter usually handles the multipart boundaries automatically.
    # However, OpenProject is strict about the order and naming: 'metadata' first, then 'file'.
    try:
        # We need to read the file binary
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        files = {
            'metadata': (None, json.dumps(metadata), 'application/json'),
            'file': (file_name, file_content, mime_type)
        }
        
        headers = {
            "Authorization": f"Basic {api_key}"
            # Do NOT set Content-Type here; the library will set it to multipart/form-data with boundary
        }

        response = await make_request(
            url=api_url, 
            method="POST", 
            headers=headers,
            files=files
        )
        return json.dumps(response)

    except Exception as e:
        return f"Error uploading attachment: {str(e)}"

@mcp.tool()
async def view_attachment(attachment_id: int) -> str:
    """
    Retrieves the details (metadata) of a specific attachment by its ID.
    This includes the filename, file size, content type, and links to download the file.
    
    Args:
        attachment_id (int): The unique numeric ID of the attachment.

    Returns:
        str: The JSON object containing the attachment metadata or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/attachments/{id}
    api_url = f"https://{host}/api/v3/attachments/{attachment_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving attachment {attachment_id}: {str(e)}"

@mcp.tool()
async def delete_attachment(attachment_id: int) -> str:
    """
    Permanently deletes a specified attachment by its ID.
    
    Args:
        attachment_id (int): The unique numeric ID of the attachment to delete.

    Returns:
        str: A success message (typically an empty body with HTTP 204 No Content) 
             or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: DELETE /api/v3/attachments/{id}
    api_url = f"https://{host}/api/v3/attachments/{attachment_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="DELETE", 
            headers=headers
        )
        # Successful DELETE requests often return a 204 No Content status
        return f"Successfully deleted attachment {attachment_id}. Response: {response}"
        
    except Exception as e:
        return f"Error deleting attachment {attachment_id}: {str(e)}"





@mcp.tool()
async def get_custom_action(custom_action_id: int) -> str:
    """
    Retrieves the details and configuration of a specific custom action by its ID.
    
    Args:
        custom_action_id (int): The unique numeric ID of the custom action to fetch.

    Returns:
        str: The JSON object containing the custom action details or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/custom_actions/{id}
    api_url = f"https://{host}/api/v3/custom_actions/{custom_action_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving custom action {custom_action_id}: {str(e)}"

@mcp.tool()
async def execute_custom_action(
    custom_action_id: int, 
    work_package_id: int, 
    lock_version: int
) -> str:
    """
    Executes a specific custom action on a given work package, returning the 
    updated work package details. Requires the work package's current lockVersion.
    
    Args:
        custom_action_id (int): The unique numeric ID of the custom action to execute.
        work_package_id (int): The ID of the work package the action should be applied to.
        lock_version (int): The current lock version of the work package for optimistic locking.

    Returns:
        str: The JSON object of the altered work package or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: POST /api/v3/custom_actions/{id}/execute
    api_url = f"https://{host}/api/v3/custom_actions/{custom_action_id}/execute"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Build the Payload
    # The payload links to the work package and provides the lock version
    payload = {
        "_links": {
            "workPackage": {
                "href": f"/api/v3/work_packages/{work_package_id}"
            }
        },
        "lockVersion": lock_version
    }

    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="POST", 
            headers=headers,
            json=payload
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error executing custom action {custom_action_id} on work package {work_package_id}: {str(e)}"

@mcp.tool()
async def get_work_package_file_links(
    work_package_id: int, 
    storage_filter: Optional[str] = None
) -> str:
    """
    Retrieves all external file links associated with a work package, optionally filtering by storage.
    Note: This endpoint performs a side-effect, contacting the storage origin to retrieve 
    live data and user permissions.
    
    Args:
        work_package_id (int): The unique numeric ID of the work package.
        storage_filter (str, optional): The name of the storage to filter by (e.g., 'google-drive'). 
                                        This is passed in the 'filters' query parameter.

    Returns:
        str: The JSON collection of file links or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/work_packages/{id}/file_links
    api_url = f"https://{host}/api/v3/work_packages/{work_package_id}/file_links"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Construct Query Parameters
    params = {}
    if storage_filter:
        # The 'filters' parameter expects a JSON string.
        # Format: [{"storage":{"operator":"=","values":["<storage_name>"]}}]
        filter_json = json.dumps([
            {
                "storage": {
                    "operator": "=",
                    "values": [storage_filter]
                }
            }
        ])
        params['filters'] = filter_json
    
    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers,
            params=params
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving file links for work package {work_package_id}: {str(e)}"

@mcp.tool()
async def get_file_link(file_link_id: int) -> str:
    """
    Retrieves the details of a single file link resource by its unique ID.
    
    Args:
        file_link_id (int): The unique numeric ID of the file link.

    Returns:
        str: The JSON object containing the file link details or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameter
    # URL pattern: GET /api/v3/file_links/{id}
    api_url = f"https://{host}/api/v3/file_links/{file_link_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving file link {file_link_id}: {str(e)}"

@mcp.tool()
async def list_groups(
    sort_by: Optional[str] = None, 
    select_fields: Optional[str] = None, 
    filters: Optional[str] = None
) -> str:
    """
    Retrieves a collection of groups, optionally filtering and sorting the results.
    The client must have sufficient permissions (view_members, manage_members) for the groups returned.
    
    Args:
        sort_by (str, optional): JSON string specifying sort criteria (e.g., '[["id", "asc"]]'). 
                                 Supported sorts: id, created_at, updated_at.
        select_fields (str, optional): Comma separated list of properties to include.
        filters (str, optional): JSON string specifying filter conditions (e.g., '[{"name": {"operator": "=", "values": ["Management"]}}]').

    Returns:
        str: The JSON collection of groups or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL
    # URL pattern: GET /api/v3/groups
    api_url = f"https://{host}/api/v3/groups"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Construct Query Parameters
    params = {}
    if sort_by:
        # Note: 'sortBy' requires JSON input, but it's passed as a query string parameter.
        params['sortBy'] = sort_by 
    if select_fields:
        params['select'] = select_fields
    if filters:
        # 'filters' requires JSON input, passed as a query string parameter.
        params['filters'] = filters
    
    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers,
            params=params
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving groups: {str(e)}"

@mcp.tool()
async def list_users(
    offset: Optional[int] = 1, 
    page_size: Optional[int] = 20,
    filters: Optional[str] = None, 
    sort_by: Optional[str] = None, 
    select_fields: Optional[str] = None
) -> str:
    """
    Retrieves a collection of users, with options for pagination, filtering, and sorting.
    Access is generally restricted to users with administrative or specific management permissions.
    
    Args:
        offset (int, optional): Page number (1-based). Defaults to 1.
        page_size (int, optional): Number of elements per page. Defaults to 20.
        filters (str, optional): JSON string specifying filter conditions. Supported filters: 
                                 status, group, name, login.
        sort_by (str, optional): JSON string specifying sort criteria.
        select_fields (str, optional): Comma separated list of properties to include.

    Returns:
        str: The JSON collection of users or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL
    # URL pattern: GET /api/v3/users
    api_url = f"https://{host}/api/v3/users"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Construct Query Parameters
    params = {
        'offset': offset,
        'pageSize': page_size
    }
    if filters:
        # 'filters' requires JSON input, passed as a query string parameter.
        params['filters'] = filters
    if sort_by:
        # 'sortBy' requires JSON input, passed as a query string parameter.
        params['sortBy'] = sort_by 
    if select_fields:
        params['select'] = select_fields
    
    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers,
            params=params
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving user list: {str(e)}"

@mcp.tool()
async def get_notification_collection(
    offset: Optional[int] = 1, 
    page_size: Optional[int] = 20,
    sort_by: Optional[str] = None, 
    group_by: Optional[str] = None,
    filters: Optional[str] = None
) -> str:
    """
    Retrieves a paginated and filtered collection of in-app notifications for the user.
    The response includes embedded schemas for notification details as an optimization.
    
    Args:
        offset (int, optional): Page number (1-based). Defaults to 1.
        page_size (int, optional): Number of elements per page. Defaults to 20.
        sort_by (str, optional): JSON string for sorting (e.g., '[["id", "desc"]]'). 
                                 Supported: id, reason, readIAN.
        group_by (str, optional): Field to group results by (e.g., 'reason', 'project').
        filters (str, optional): JSON string for filtering (e.g., '[{"readIAN": {"operator": "=", "values": ["false"]}}]').
                                 Supported: id, project, readIAN, reason, resourceId, resourceType.

    Returns:
        str: The JSON collection of notifications or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL
    # URL pattern: GET /api/v3/notifications
    api_url = f"https://{host}/api/v3/notifications"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Construct Query Parameters
    params = {
        'offset': offset,
        'pageSize': page_size
    }
    if sort_by:
        params['sortBy'] = sort_by 
    if group_by:
        params['groupBy'] = group_by
    if filters:
        params['filters'] = filters
    
    # 5. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers,
            params=params
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving notifications: {str(e)}"

@mcp.tool()
async def get_notification_detail(notification_id: int, detail_id: int) -> str:
    """
    Retrieves an individual detail resource associated with a specific notification.
    
    Args:
        notification_id (int): The unique numeric ID of the parent notification.
        detail_id (int): The unique numeric ID of the detail item to fetch.

    Returns:
        str: The JSON object containing the notification detail or an error message.
    """
    
    # 1. Configuration
    host = os.getenv("OPENPROJECT_HOST", "pm.v.spaceagecu.org")
    api_key = os.getenv("OPENPROJECT_API_KEY", api_key)
    
    # 2. Construct the URL with the Path Parameters
    # URL pattern: GET /api/v3/notifications/{notification_id}/details/{id}
    api_url = f"https://{host}/api/v3/notifications/{notification_id}/details/{detail_id}"
    
    # 3. Prepare Headers
    headers = {
        "Authorization": f"Basic {api_key}", 
        "Content-Type": "application/json"
    }
    
    # 4. Send Request
    try:
        response = await make_request(
            url=api_url, 
            method="GET", 
            headers=headers
        )
        return json.dumps(response)
        
    except Exception as e:
        return f"Error retrieving detail {detail_id} for notification {notification_id}: {str(e)}"

# Function to search for the endpoint in the database
def search_endpoint(query: str):
    """
    Searches for a matching API endpoint in the local SQLite database.

    Args:
        query (str): The query string to search for in the API schema's paths.

    Returns:
        list[Dict[str, Any]]: A list of endpoint data (paths, methods, descriptions, etc.) that match the query.
        
    Description:
        This function queries the local Open Project (Project MGMT) API database (sqlite) for API endpoints that match a given query string.
        It returns a structured list containing the path, HTTP method, description, request body, and response details
        for each endpoint that matches the query. Useful for dynamically finding relevant API documentation.
    """
    sqliteDB = "openproject_schema.db"
    conn = sqlite3.connect(sqliteDB)
    cursor = conn.cursor()
    cursor.execute("SELECT path, method, description, request_body, responses FROM api_endpoints WHERE path LIKE ?", (f"%{query}%",))
    results = cursor.fetchall()
    conn.close()

    return [{"path": path, "method": method, "description": description,
             "request_body": json.loads(request_body) if request_body != "None" else None,
             "responses": json.loads(responses)} for path, method, description, request_body, responses in results]

@mcp.tool()
async def query_api(query: str) -> str:
    """
    Queries the local Open Project (Project MGMT) REST API schema for matching endpoints and returns them in JSON format.

    Args:
        query (str): The path or query to search for in the local API schema.

    Returns:
        str: A JSON string containing all matching API paths or an error message if no matches are found.
    
    Description:
        This function performs a local database search to find API endpoints based on the given query string.
        It formats the results into a structured JSON response, making it easy for external clients to access
        the available API paths, methods, and descriptions.
    """
    # Search for the endpoint in the local schema database
    results = search_endpoint(query)

    if not results:
        return json.dumps({"error": "No matching endpoints found"})

    # Return all paths as available options
    available_paths = [{"path": endpoint_info["path"], "description": endpoint_info["description"], "method": endpoint_info["method"], "request_body": endpoint_info["request_body"], "response": endpoint_info["responses"]} for endpoint_info in results]
    return json.dumps({"available_paths": available_paths})




if __name__ == "__main__":
    # Run the MCP server on stdio transport
    mcp.run(transport='stdio')
    # command to run this mcp-server from terminal for use with open-webui: ` uvx mcpo --port 5085 -- uv run 03_mcpserver.py `
