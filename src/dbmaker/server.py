"""
MCP Server implementation for ODBC connections.
Provides tools for database querying via the Model Context Protocol.
"""

import asyncio
import os
import re
import sys
import json
import logging
from typing import Dict, List, Any, Optional

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

from .config import load_config, ServerConfig
from .odbc import ODBCHandler


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger("odbc-mcp-server")


class ODBCMCPServer:
    """
    MCP Server that provides tools for ODBC database connectivity.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the server with configuration."""
        try:
            self.config = load_config(config_path)
            self.odbc = ODBCHandler(self.config)
            if self.config.dbmaker_cli:
                from .dbmaker_cli import DBMakerCLI
                self.dbmaker_cli = DBMakerCLI(self.config)
            else:
                self.dbmaker_cli = None
                
            self.server = Server("odbc-mcp-server")
            
            # Register tool handlers
            self._register_tools()
            
            logger.info(f"Initialized ODBC MCP Server with {len(self.config.connections)} connections")
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            raise
            
    def _register_tools(self):
        """Register all MCP tools."""
        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List available tools for the MCP client."""
            return [
                types.Tool(
                    name="list-connections",
                    description="List all configured database connections",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                types.Tool(
                    name="list-available-dsns",
                    description="List all available DSNs on the system",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                types.Tool(
                    name="test-connection",
                    description="Test a database connection and return information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to test (optional, uses default if not specified)"
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="list-tables",
                    description="List all tables in the database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use (optional, uses default if not specified)"
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="get-table-schema",
                    description="Get schema information for a table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to describe (required)"
                            },
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use (optional, uses default if not specified)"
                            }
                        },
                        "required": ["table_name"]
                    }
                ),
                types.Tool(
                    name="execute-query",
                    description="Execute an SQL query and return results",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "SQL query to execute (required)"
                            },
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use (optional, uses default if not specified)"
                            },
                            "max_rows": {
                                "type": "integer",
                                "description": "Maximum number of rows to return (optional, uses default if not specified)"
                            }
                        },
                        "required": ["sql"]
                    }
                ),
                types.Tool(
                    name="health-check",
                    description="Get DBMaker health metrics: CPU usage, memory, connections, transaction success rate, lock waits",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use (optional, uses default if not specified)"
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="list-user-stored-procedures",
                    description="List user-created stored procedures in DBMaker",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use (optional, uses default if not specified)"
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="list-system-stored-procedures",
                    description="List DBMaker system stored procedures",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use (optional, uses default if not specified)"
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="get-stored-procedure-definition",
                    description="Get DBMaker stored procedure definition",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "procedure_name": {
                                "type": "string",
                                "description": "Stored procedure name"
                            }
                        },
                        "required": ["procedure_name"]
                    }
                ),
                types.Tool(
                    name="list-triggers",
                    description="List all triggers in the database, showing which table changes automatically execute which stored procedures",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use (optional, uses default if not specified)"
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="list-foreign-keys",
                    description="List all foreign key relationships between tables in the database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use (optional, uses default if not specified)"
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="list-locks",
                    description="List current DBMaker locks",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use"
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="list-active-users",
                    description="List current active DBMaker user connections",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use"
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="list-waits",
                    description="List current DBMaker waiting connections caused by lock or transaction waits",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_name": {
                                "type": "string",
                                "description": "Name of the connection to use"
                            }
                        },
                        "required": []
                    }
                )
                
            ]
            
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool execution requests."""
            arguments = arguments or {}
            
            try:
                if name == "list-connections":
                    connections = self.odbc.list_connections()
                    result = {
                        "connections": connections,
                        "default_connection": self.config.default_connection
                    }
                    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                    
                elif name == "list-available-dsns":
                    dsns = self.odbc.get_available_dsns()
                    return [types.TextContent(type="text", text=json.dumps(dsns, indent=2))]
                    
                elif name == "test-connection":
                    connection_name = arguments.get("connection_name")
                    result = self.odbc.test_connection(connection_name)
                    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                    
                elif name == "list-tables":
                    connection_name = arguments.get("connection_name")
                    tables = self.odbc.list_tables(connection_name)
                    
                    # Format the results for better readability
                    result_text = "### Tables:\n\n"
                    for table in tables:
                        schema_prefix = f"{table['schema']}." if table['schema'] else ""
                        result_text += f"- {schema_prefix}{table['name']}\n"
                        
                    return [types.TextContent(type="text", text=result_text)]
                    
                elif name == "get-table-schema":
                    table_name = arguments.get("table_name")
                    if not table_name:
                        raise ValueError("Table name is required")
                        
                    connection_name = arguments.get("connection_name")
                    columns = self.odbc.get_table_schema(table_name, connection_name)
                    
                    # Format the results for better readability
                    result_text = f"### Schema for table {table_name}:\n\n"
                    result_text += "| Column | Type | Size | Nullable |\n"
                    result_text += "| ------ | ---- | ---- | -------- |\n"
                    
                    for column in columns:
                        result_text += f"| {column['name']} | {column['type']} | {column['size']} | {'Yes' if column['nullable'] else 'No'} |\n"
                        
                    return [types.TextContent(type="text", text=result_text)]
                    
                elif name == "execute-query":
                    sql = arguments.get("sql")
                    if not sql:
                        raise ValueError("SQL query is required")
                        
                    connection_name = arguments.get("connection_name")
                    max_rows = arguments.get("max_rows")
                    
                    column_names, rows = self.odbc.execute_query(sql, connection_name, max_rows)
                    
                    # Format the results as a markdown table
                    if not column_names:
                        return [types.TextContent(type="text", text="Query executed successfully, but no results were returned.")]
                        
                    # Create the results table
                    result_text = "### Query Results:\n\n"
                    
                    # Add the header row
                    result_text += "| " + " | ".join(column_names) + " |\n"
                    
                    # Add the separator row
                    result_text += "| " + " | ".join(["---"] * len(column_names)) + " |\n"
                    
                    # Add the data rows
                    for row in rows:
                        result_text += "| " + " | ".join(str(value) if value is not None else "NULL" for value in row) + " |\n"
                        
                    # Add the row count
                    result_text += f"\n\n_Returned {len(rows)} rows_"
                    
                    # Check if we hit the row limit
                    if max_rows and len(rows) >= max_rows:
                        result_text += f" _(limited to {max_rows} rows)_"
                        
                    return [types.TextContent(type="text", text=result_text)]
                
                elif name == "health-check":
                    connection_name = arguments.get("connection_name")
                    column_names, rows = self.odbc.health_check(connection_name)
                    
                    metrics = {row[1]: row[2] for row in rows}
                    
                    result_text = "### DBMaker Health Check:\n\n"
                    result_text += f"- CPU Usage: {metrics.get('CPU_USAGE', 'N/A')}%\n"
                    result_text += f"- Active Connections: {metrics.get('NUM_CONNECT', 'N/A')}\n"
                    result_text += f"- Peak Connections: {metrics.get('NUM_PEAK_CONNECT', 'N/A')}\n"
                    result_text += f"- Total Memory: {metrics.get('TOTAL_MEMORY', 'N/A')} bytes\n"
                    result_text += f"- Free Memory: {metrics.get('TOTAL_FREE_MEMORY', 'N/A')} bytes\n"
                    
                    return [types.TextContent(type="text", text=result_text)]
                    
                elif name == "list-user-stored-procedures":
                    connection_name = arguments.get("connection_name")
                    column_names, rows = self.odbc.list_user_stored_procedures(connection_name)
                    result_text = "### DBMaker User Stored Procedures:\n\n"

                    result_text += "| Owner | Procedure Name |\n"
                    result_text += "| ----- | -------------- |\n"

                    for row in rows:
                        result_text += f"| {row[0].strip()} | {row[1].strip()} |\n"

                    result_text += f"\n_Total {len(rows)} procedures_"
                          
                    return [types.TextContent(type="text", text=result_text)]
                
                elif name == "list-system-stored-procedures":
                    connection_name = arguments.get("connection_name")
                    column_names, rows = self.odbc.list_system_stored_procedures(connection_name)
                    result_text = "### DBMaker System Stored Procedures:\n\n"

                    result_text += "| Owner | Procedure Name |\n"
                    result_text += "| ----- | -------------- |\n"

                    for row in rows:
                        result_text += f"| {row[0].strip()} | {row[1].strip()} |\n"

                    result_text += f"\n_Total {len(rows)} procedures_"
                    
                    
                    return [types.TextContent(type="text", text=result_text)]
                    
                elif name == "get-stored-procedure-definition":

                    procedure_name = arguments.get("procedure_name")

                    if not procedure_name:
                        raise ValueError("Procedure name is required")

                    definition = self.dbmaker_cli.get_procedure_definition(
                        procedure_name
                    )

                    return [
                        types.TextContent(
                            type="text",
                            text=definition
                        )
                    ]
                
                elif name == "list-triggers":
                    connection_name = arguments.get("connection_name")
                    column_names, rows = self.odbc.list_triggers(connection_name)
                    
                    event_map = {1: "INSERT", 2: "DELETE", 3: "UPDATE"}
                    status_map = {1: "Enabled", 0: "Disabled"}
                    
                    result_text = "### Triggers:\n\n"
                    result_text += "| Table | Trigger Name | Event | Status | Definition |\n"
                    result_text += "| ----- | ------------ | ----- | ------ | ---------- |\n"
                    
                    for row in rows:
                        table_name, trig_name, event, status = row[0].strip(), row[1].strip(), row[2], row[3]
                        event_text = event_map.get(event, f"Unknown({event})")
                        status_text = status_map.get(status, f"Unknown({status})")
                        result_text += f"| {table_name} | {trig_name} | {event_text} | {status_text} | (see full definition) |\n"
                    
                    return [types.TextContent(type="text", text=result_text)]
                
                elif name == "list-foreign-keys":
                    connection_name = arguments.get("connection_name")
                    column_names, rows = self.odbc.list_foreign_keys(connection_name)
                    
                    result_text = "### Foreign Keys:\n\n"
                    result_text += "| Child Table | References Table | Constraint Name |\n"
                    result_text += "| ----------- | ----------------- | ---------------- |\n"
                    
                    for row in rows:
                        fk_table, pk_table, fk_name = row[0].strip(), row[1].strip(), row[2].strip()
                        result_text += f"| {fk_table} | {pk_table} | {fk_name} |\n"
                    
                    return [types.TextContent(type="text", text=result_text)]
                    
                elif name == "list-locks":
                    connection_name = arguments.get("connection_name")

                    column_names, rows = self.odbc.list_locks(connection_name)

                    result_text = "### DBMaker Current Locks:\n\n"

                    result_text += "| Object ID | Table ID | Granularity | Connection | Status | Current Mode | New Mode |\n"
                    result_text += "| --------- | -------- | ----------- | ---------- | ------ | ------------ | ------- |\n"

                    for row in rows:
                        result_text += (
                            f"| {row[0]} | {row[1]} | {row[2]} | "
                            f"{row[3]} | {row[4]} | {row[5]} | {row[6]} |\n"
                        )

                    result_text += f"\n_Total {len(rows)} locks_"

                    return [
                        types.TextContent(
                            type="text",
                            text=result_text
                        )
                    ]
                    
                elif name == "list-active-users":
                    connection_name = arguments.get("connection_name")

                    column_names, rows = self.odbc.list_active_users(connection_name)

                    result_text = "### DBMaker Active Sessions:\n\n"

                    result_text += "| Connection | User | Login Time | Host | Transactions | Current SQL |\n"
                    result_text += "| ---------- | ---- | ---------- | ---- | ------------ | ----------- |\n"

                    for row in rows:

                        connection_id = row[0]
                        user = str(row[1]).strip()
                        login_time = row[2]
                        host = str(row[4]).strip()
                        num_tranx = row[5]

                        sql_cmd = str(row[6]).strip() if row[6] else ""

                        sql_cmd = re.sub(r'\s+', ' ', sql_cmd)

                        if len(sql_cmd) > 100:
                            sql_cmd = sql_cmd[:100] + "..."

                        sql_cmd = re.sub(r'\s+', ' ', sql_cmd).strip()

                        result_text += (
                            f"| {connection_id} | {user} | "
                            f"{login_time} | {host} | "
                            f"{num_tranx} | {sql_cmd} |\n"
                        )

                    result_text += f"\n_Total {len(rows)} active sessions_"

                    return [
                        types.TextContent(
                            type="text",
                            text=result_text
                        )
                    ]
                
                elif name == "list-waits":

                    connection_name = arguments.get("connection_name")

                    column_names, rows = self.odbc.list_waits(connection_name)

                    result_text = "### DBMaker Waiting Connections:\n\n"

                    result_text += "| Waiting Connection | Waited Connection |\n"
                    result_text += "| ------------------ | ----------------- |\n"

                    for row in rows:
                        result_text += f"| {row[0]} | {row[1]} |\n"

                    result_text += f"\n_Total {len(rows)} waits_"

                    return [
                        types.TextContent(
                            type="text",
                            text=result_text
                        )
                    ]
                    
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                error_message = f"Error executing {name}: {str(e)}"
                return [types.TextContent(type="text", text=error_message)]
                
    async def run(self):
        """Run the MCP server."""
        try:
            initialization_options = InitializationOptions(
                server_name="odbc-mcp-server",
                server_version="0.1.0",
                capabilities=self.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
            
            async with stdio_server() as (read_stream, write_stream):
                logger.info("Starting ODBC MCP Server")
                await self.server.run(
                    read_stream,
                    write_stream,
                    initialization_options,
                )
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            # Clean up connections
            self.odbc.close_all_connections()