'''
Regression test for server startup with the installed MCP dependency.
'''

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_startup(vault_path):
    '''Start a fresh server process and verify the MCP handshake and tools.'''
    async def connect():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[
                '-c',
                'from obsidian_mcp import run; run()',
                '--vault',
                str(vault_path),
            ],
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    'read_file', 'write_file', 'get_current_date',
                    'list_todays_journal_entry', 'start_daily_notes_session',
                    'list_journal_entries_by_year_and_month', 'list_projects',
                    'list_project_content', 'create_project', 'list_wiki',
                }
                result = await session.call_tool('get_current_date', {})
                assert result.isError is False
                assert result.content

    asyncio.run(asyncio.wait_for(connect(), timeout=30))

