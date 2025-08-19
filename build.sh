#!/bin/bash
# Build script for Obsidian MCP Server Docker image

echo "🐳 Building Obsidian MCP Server Docker Image"
echo "============================================="

docker build -t obsidian-mcp:local .
