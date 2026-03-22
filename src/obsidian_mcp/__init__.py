'''
obsidian-mcp: MCP server for accessing an opinionated Obsidian vault.
'''

__version__ = '2.0.0'

from obsidian_mcp.server import run

__all__ = ['run', '__version__']
