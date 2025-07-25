# MCP-workshop-MS

This repository is for the MCP workshop. It contains MCP demo servers, an MCP client, and step-by-step examples on how to use them.


## Prerequisites

- Python 3.8+ installed

## 1. Install `uv`

Follow the [official instructions](https://github.com/astral-sh/uv#installation) or use one of the following commands:

**With pipx:**
```bash
pipx install uv
```

**Or with pip:**
```bash
pip install uv
```

## 2. Clone the Repository

```bash
git clone https://github.com/motzik88/MCP-workshop-MS.git
cd MCP-workshop-MS
```

## 3. Create a New uv Environment

```bash
uv venv 
```

Activate the environment:

- **On Linux/macOS:**
  ```bash
  source .venv/bin/activate
  ```
- **On Windows:**
  ```cmd
  .venv\Scripts\activate
  ```

## 4. Install fastagent

```bash
uv pip install fastmcp
```

You are now ready to use the project!
