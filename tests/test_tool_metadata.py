'''
Tests for what clients see about each tool: order, annotations and argument descriptions.
'''

import asyncio

import pytest

from obsidian_mcp import server


READ_ONLY = {
    'read_journal_entry', 'search_journal', 'get_todays_date',
    'list_journal_entries_by_year_and_month', 'list_projects', 'list_project_content',
    'list_wiki', 'read_file',
}
ADDS = {
    'add_note_to_journal_entry', 'prepend_to_journal_entry', 'append_to_journal_entry',
    'create_project',
}
REPLACES = {'write_journal_entry', 'write_file'}


@pytest.fixture(scope='module')
def tools():
    return asyncio.run(server.mcp.list_tools())


def test_tools_are_listed_usual_ones_first(tools):
    assert [tool.name for tool in tools] == [
        'add_note_to_journal_entry', 'read_journal_entry', 'search_journal', 'get_todays_date',
        'list_journal_entries_by_year_and_month', 'prepend_to_journal_entry',
        'append_to_journal_entry', 'write_journal_entry', 'list_projects',
        'list_project_content', 'create_project', 'list_wiki', 'read_file', 'write_file',
    ]


def test_every_tool_is_annotated(tools):
    assert {tool.name for tool in tools} == READ_ONLY | ADDS | REPLACES
    for tool in tools:
        hints = tool.annotations
        assert hints is not None, tool.name
        assert hints.openWorldHint is False, tool.name
        if tool.name in READ_ONLY:
            assert hints.readOnlyHint is True, tool.name
        else:
            assert hints.readOnlyHint is False, tool.name
            assert hints.destructiveHint is (tool.name in REPLACES), tool.name


def test_every_argument_is_described(tools):
    for tool in tools:
        for name, prop in tool.inputSchema.get('properties', {}).items():
            assert prop.get('description'), f'{tool.name}.{name}'


def test_descriptions_do_not_repeat_the_arguments(tools):
    # argument text lives in the schema; an Args: block in the docstring would send it twice
    for tool in tools:
        assert 'Args:' not in tool.description, tool.name


def test_optional_arguments_keep_their_defaults(tools):
    schemas = {tool.name: tool.inputSchema for tool in tools}
    assert schemas['add_note_to_journal_entry']['required'] == ['text']
    assert schemas['write_journal_entry']['required'] == ['content']
    assert schemas['search_journal']['required'] == ['query']
    assert schemas['search_journal']['properties']['max_results']['default'] == 20


def test_instructions_cover_projects_and_the_wiki():
    instructions = server.mcp.instructions
    for tool in ('list_project_content', 'list_wiki', 'read_file', 'write_file'):
        assert tool in instructions
    assert 'documented' in instructions


def test_descriptions_say_what_each_tool_returns(tools):
    # in prose, not a Returns: section, which fastmcp 4 strips from descriptions
    for tool in tools:
        assert 'Returns ' in tool.description, tool.name
        assert 'Returns:' not in tool.description, tool.name
