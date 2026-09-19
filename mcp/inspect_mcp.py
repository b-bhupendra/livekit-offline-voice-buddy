#!/usr/bin/env python3
"""
inspect_mcp.py — Modular MCP Inspector for Buddy Voice AI.

Provides a unified overview of all Model Context Protocol (MCP) servers
registered in the project workspace and IDE environment.
"""

import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_FILE = os.path.join(SCRIPT_DIR, "mcp_registry.json")
CONFIG_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "mcp_config.json")


def load_registry():
    if not os.path.exists(REGISTRY_FILE):
        print(f"Error: Registry file not found at {REGISTRY_FILE}")
        sys.exit(1)
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    data = load_registry()
    servers = data.get("servers", {})
    total_servers = len(servers)
    total_tools = sum(len(s.get("tools", [])) for s in servers.values())

    print("\n" + "=" * 78)
    print(" 🌐 BUDDY VOICE AI — MODEL CONTEXT PROTOCOL (MCP) ARCHITECTURE")
    print("=" * 78)
    print(f" Total Registered MCP Servers: {total_servers}")
    print(f" Total Available MCP Tools:   {total_tools}")
    print(f" Registry Location:           {REGISTRY_FILE}")
    print("=" * 78 + "\n")

    # Group servers by category
    categories = {}
    for sid, s in servers.items():
        cat = s.get("category", "General")
        categories.setdefault(cat, []).append((sid, s))

    cat_order = [
        "Design & UI Primitives",
        "Framework & Real-Time Docs",
        "System & IDE Utilities"
    ]

    for cat in cat_order:
        items = categories.get(cat, [])
        if not items:
            continue
        print(f"┌─ 📁 {cat.upper()} ({len(items)} Servers)")
        for idx, (sid, s) in enumerate(items):
            is_last = (idx == len(items) - 1)
            branch = "└──" if is_last else "├──"
            transport = s.get("transport", "stdio").upper()
            tools = s.get("tools", [])
            tool_cnt = len(tools)
            print(f"│  {branch} 🔌 [{sid}] (Transport: {transport} | {tool_cnt} Tools)")
            print(f"│     • Description: {s.get('description')}")
            if "command" in s:
                cmd_str = f"{s['command']} {' '.join(s.get('args', []))}"
                print(f"│     • Command:     {cmd_str}")
            elif "serverUrl" in s:
                print(f"│     • Remote URL:  {s['serverUrl']}")
            print(f"│     • Key Tools:   {', '.join(tools[:5])}{' ...' if tool_cnt > 5 else ''}")
            if not is_last:
                print("│")
        print("└" + "─" * 77 + "\n")

    print("Tip: Run this inspector anytime with: python mcp/inspect_mcp.py\n")


if __name__ == "__main__":
    main()
