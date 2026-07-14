# Connecting an LLM to a DBMaker Database via ODBC MCP Server

This project is based on the original [`tylerstoltz/mcp-odbc`](https://github.com/tylerstoltz/mcp-odbc) project, with modifications and additional DBMaker-specific MCP tools for database monitoring, administration, and ODBC integration.

> The original MCP server code is licensed under the MIT License and belongs to the original author. This repository contains modifications and extensions based on the original project, including DBMaker-specific MCP tools and integration examples.

**OS:** AlmaLinux 8.9 (Midnight Oncilla)  
**DBMaker:** 5.4.8 bundle (#32453, 20260701)  
**AI Client:** Claude Desktop, Cursor Desktop  
**Base MCP Server:** [`tylerstoltz/mcp-odbc`](https://github.com/tylerstoltz/mcp-odbc)  
**Database Integration:** DBMaker via ODBC

⚠️ **Security note**: In the examples below, the database password field is left blank, which is only suitable for internal testing environments. For production environments, always set a password and consider restricting the database to local-only connections.

---

## 1. ODBC Configuration

Two files are required: `odbcinst.ini` (driver definition) and `odbc.ini` (connection settings). Both must exist — `odbc.ini`'s `Driver = DBMaker` line references the driver name registered in `odbcinst.ini`.

### 1. Add the following to `/etc/odbcinst.ini`

(Replace the `Driver` paths with the actual location of your DBMaker library)

```ini
[DBMaker]
Description = DBMaker ODBC Driver
Driver = /path/to/dbmaker/bundle/libdmapic.so
Setup = /path/to/dbmaker/bundle/libdmapic.so
Driver64 = /path/to/dbmaker/bundle/libdmapic.so
Setup64 = /path/to/dbmaker/bundle/libdmapic.so
FileUsage = 1
UsageCount = 1
```

> `FileUsage` and `UsageCount` are conventional unixODBC fields, mainly used by GUI management tools. When manually editing config files via CLI, these can be omitted without affecting driver loading or connection functionality.

### 2. Add the following to `/etc/odbc.ini` (create the file if it doesn't exist)

```ini
[MYDB]
Description = DBMaker MYDB
Driver = DBMaker
Server = <YOUR DBMAKER SERVER IP>
Port = <YOUR DBMAKER PORT NUMBER>
Database = MYDB
User = SYSADM
Password =
```

`MYDB` is the database name — replace it with your own.

### 3. Test the ODBC Connection

```bash
isql -v MYDB SYSADM ""
```

A successful connection shows:

```
+---------------------------------------+
| Connected!                            |
|                                        |
| sql-statement                         |
| help [tablename]                      |
| quit                                  |
|                                        |
+---------------------------------------+
SQL>
```

---

## 2. Python MCP Environment

Per the GitHub project description, the environment requires Python 3.10+, an ODBC driver for your database, and git.

### 1. Check the installed Python version

```bash
ls -1 /usr/bin/python*
```

Confirm you have Python 3.10 or above. This guide uses 3.12 as an example.

### 2. Install packages (commands vary by Linux distribution)

```bash
dnf install -y python3.12 python3.12-pip python3.12-devel git unixODBC unixODBC-devel
```

### 3. Verify the version

```bash
python3.12 --version
# Python 3.12.13
```

---

## 3. Create a Dedicated MCP User Account

### 1. As root, create a new user (the name is not fixed — `mcpdev` is used here as an example)

```bash
useradd -m mcpdev
```

### 2. Confirm the home directory exists

```bash
ls /home/mcpdev
```

### 3. Switch to the mcpdev user

```bash
su -l mcpdev
```

---

## 4. Download and Install MCP ODBC Server

```bash
git clone https://github.com/tylerstoltz/mcp-odbc.git
cd mcp-odbc/
```

### 1. Create a Python 3.12 virtual environment (venv)

```bash
python3.12 -m venv .venv312
```

### 2. Activate the venv

```bash
source .venv312/bin/activate
```

### 3. Confirm the Python version

```bash
python --version
# Python 3.12.13
```

### 4. Install MCP ODBC

```bash
pip install -e .
```

---

## 5. Create `config.ini`

```ini
[SERVER]
default_connection = dbmaker
max_rows = 1000
timeout = 30

[dbmaker]
dsn = MYDB
username = SYSADM
password =
readonly = true

[DBMAKER_CLI]
dmsqlc_path=/path/to/dbmaker/bundle/dmsqlc
database=MYDB
```

> `readonly = true`: Only SELECT queries are allowed — any INSERT / UPDATE / DELETE will be blocked by the MCP server. To allow write access, change this to `false`, but carefully weigh the risk (the AI could accidentally delete or modify data).

---

## 6. Test the MCP Server

```bash
source .venv312/bin/activate
odbc-mcp-server --config config.ini
```

A successful connection shows:

```
2026-07-06 01:57:01,041 - odbc-mcp-server - INFO - Initialized ODBC MCP Server with 1 connections
2026-07-06 01:57:01,086 - odbc-mcp-server - INFO - Starting ODBC MCP Server
```

---

## 7. Generate an SSH Key on Windows (so the AI can SSH into Linux without a password)

### 1. Generate the key pair (press Enter through all prompts)

```powershell
ssh-keygen
```

This example generates `id_ed25519` and `id_ed25519.pub`.

### 2. Copy the public key to Linux

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh -p <YOUR PORT NUMBER> mcpdev@<YOUR LINUX IP> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

You'll be prompted for the password once during this step.

### 3. Test passwordless SSH from Windows to Linux

```powershell
ssh -p <YOUR PORT NUMBER> mcpdev@<YOUR LINUX IP>
```

### 4. Test whether the MCP Server can be started from Windows

```powershell
ssh -p <YOUR PORT NUMBER> mcpdev@<YOUR LINUX IP> "/home/mcpdev/mcp-odbc/.venv312/bin/odbc-mcp-server --config /home/mcpdev/mcp-odbc/config.ini"
```

A successful connection shows:

```
2026-07-06 02:14:07,265 - odbc-mcp-server - INFO - Initialized ODBC MCP Server with 1 connections
2026-07-06 02:14:07,279 - odbc-mcp-server - INFO - Starting ODBC MCP Server
```

---

## 8. Claude Desktop MCP Configuration

Open Settings in Claude Desktop, select **Developer** in the left sidebar, and click **Edit Config** to open `claude_desktop_config.json` (this file will be empty if not yet configured).

Add the following (**paths must be adjusted per device, and must be absolute paths**):

```json
{
  "mcpServers": {
    "dbmaker": {
      "command": "C:\\Users\\<username>\\AppData\\Local\\GitHubDesktop\\app-<version>\\resources\\app\\git\\usr\\bin\\ssh.exe",
      "args": [
        "-p", "<YOUR PORT NUMBER>",
        "mcpdev@<YOUR LINUX IP>",
        "/home/mcpdev/mcp-odbc/.venv312/bin/odbc-mcp-server",
        "--config", "/home/mcpdev/mcp-odbc/config.ini"
      ]
    }
  }
}
```

After saving this config, fully restart Claude Desktop. If there are no errors on restart, the config change was successful. If unsuccessful, a warning dialog will appear on launch and the config will roll back to its previous state.

If the change was successful and the config is correct, you should see a `dbmaker running` entry under Settings → Developer.

If Linux or dmserver is shut down or restarted, it's best to fully quit and restart Claude Desktop as well to keep the connection alive — then you can query the database directly through the AI. By default this runs in read-only mode, meaning only SELECT is allowed; any write action will be blocked.

### ⚠️ Notice: Windows built-in ssh.exe compatibility issue

Unlike Cursor, Claude Desktop cannot use Windows' built-in ssh — the connection disconnects immediately after receiving the first MCP message (`initialize`), resulting in `Server disconnected`. Replacing it with the **ssh.exe bundled with GitHub Desktop** instead of the Windows system's built-in ssh.exe resolves this issue.

**The root cause is not yet confirmed.** It's suspected to be related to differences in how the two handle stdio pipes when spawning child processes, but this has not been verified further with `ssh -vvv`, so it should not be treated as a confirmed root cause. This behavior may change with future updates to Windows OpenSSH or Claude Desktop.

Common paths:
```
C:\Program Files\Git\usr\bin\ssh.exe
```
or (if installed via GitHub Desktop):
```
C:\Users\<username>\AppData\Local\GitHubDesktop\app-<version>\resources\app\git\usr\bin\ssh.exe
```

> ⚠️ This path depends on the installed GitHub Desktop version. If the app auto-updates, the folder name may change and break this config. Installing Git for Windows standalone is recommended for a more stable path.

You can search File Explorer for available `ssh.exe` files on your device.

---

## 9. Cursor MCP Configuration

In the Cursor desktop app, click **Customize** in the top-left corner, then select **MCPs** in the middle of the screen.

Click **New MCP Server** to open `mcp.json`, and edit it according to your device's IP, port number, and `config.ini` path.

### Example `mcp.json`:

```json
{
  "mcpServers": {
    "dbmaker": {
      "command": "ssh",
      "args": [
        "-p", "<YOUR PORT NUMBER>",
        "mcpdev@<YOUR LINUX IP>",
        "/home/mcpdev/mcp-odbc/.venv312/bin/odbc-mcp-server",
        "--config", "/home/mcpdev/mcp-odbc/config.ini"
      ]
    }
  }
}
```

A successful connection will show the DBMaker MCP tools enabled. The exact number of available tools depends on your customized MCP server implementation.

---

## 10. DBMaker Extensions

The following DBMaker-specific tools have been added on top of the original `mcp-odbc` project:

| Tool | Description |
|------|-------------|
| `health-check` | Display DBMaker health information, including CPU usage, memory usage, active connections, and peak connections. |
| `list-active-users` | List current database sessions, including login time, client host, current SQL statement, and transaction count. |
| `list-locks` | Display the current database locks from `SYSLOCK`, including lock granularity, status, and lock modes. |
| `list-waits` | Display waiting lock relationships from `SYSWAIT` to help diagnose blocking sessions. |
| `list-user-stored-procedures` | List all user-defined stored procedures. |
| `list-system-stored-procedures` | List all built-in DBMaker stored procedures. |
| `get-stored-procedure-definition` | Retrieve the complete definition of a specified stored procedure. |
| `list-triggers` | List all triggers, including their associated tables and trigger events. |
| `list-foreign-keys` | Display foreign key relationships between tables. |

---

### Implementation Notes
`get-stored-procedure-definition` retrieves stored procedure definitions through the DBMaker CLI instead of ODBC.

This approach is used because DBMaker's ODBC interface does not provide a direct method for retrieving stored procedure source definitions. The tool invokes DBMaker CLI commands to obtain the procedure definition and returns the result through MCP.

These extensions are implemented specifically for DBMaker and are not part of the original `mcp-odbc` project.

Supported DBMaker system tables/views include:

- `SYSINFO`
- `SYSUSER`
- `SYSLOCK`
- `SYSWAIT`
- `SYSPROCINFO`
- `SYSTRIGGER`
- `SYSFOREIGNKEY`

These extensions provide AI assistants with richer database administration, monitoring, troubleshooting, and schema exploration capabilities.