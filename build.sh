#!/bin/bash

echo "🐳 Building Obsidian MCP Server Docker Image"
echo "============================================="

docker build -t obsidian-mcp:local .
