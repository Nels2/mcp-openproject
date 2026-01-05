# OpenProject MCP API Server

This repository contains a **Model Context Protocol (MCP) tool server** that exposes the OpenProject REST API as structured MCP tools.  
It is designed to be consumed by MCP-compatible clients (such as Open WebUI via `mcpo`) and **runs over stdio**, not HTTP.

The server provides comprehensive coverage of OpenProject functionality including projects, work packages, users, groups, notifications, attachments, custom actions, and schema discovery.

---

## Architecture Overview

- **Protocol:** Model Context Protocol (MCP)
- **Transport:** stdio (JSON-RPC)
- **Server Framework:** `FastMCP`
- **Execution Model:** CLI process (no ASGI, no FastAPI, no Uvicorn)
- **Integration:** MCP OpenAPI Proxy (`mcpo`)

This server is **not** a web service. It does not expose HTTP endpoints directly.

---

## Features

### Project Management
- Create, view, list, update projects
- Retrieve project statuses
- Query project members and assignees

### Work Packages
- Create, view, list, update work packages
- Manage work package activities and comments
- Retrieve available assignees and watchers
- Add and remove watchers
- Execute custom actions on work packages

### Attachments
- Upload attachments (containerless or directly attached)
- List, view, and delete attachments
- Attach files to work packages

### Users and Groups
- List users with filtering and pagination
- List groups with filtering and sorting

### Notifications
- List notifications
- Retrieve notification details

### Custom Actions
- Retrieve custom action definitions
- Execute custom actions on work packages

### Schema Search
- Query a local SQLite OpenProject schema database
- Discover available API endpoints dynamically

---

## Requirements

- Python 3.11 or newer (3.12 recommended)
- `uv`
- `mcpo`
- Network access to the OpenProject instance
- OpenProject API key (Basic Auth)

---

## Installation

```bash
pip install mcp mcpo httpx
```

## Configuration
### Environment Variables (Recommended)
```bash
export OPENPROJECT_HOST=pm.v.spaceagecu.org
export OPENPROJECT_API_KEY=<base64-encoded-api-key>
```
## Running the MCP Server

This server **must be run over stdio.**

### Correct Command
```bash
uvx mcpo --port 8034 -- python 03_mcpserver_agent.py
```
