# Model Context Protocol (MCP) Modular Architecture

This directory modularizes all MCP server configurations, registries, and inspection tooling for the **Buddy Voice AI** project.

---

## 📊 Overview of Configured MCP Servers

Buddy Voice AI integrates **10 MCP Servers** across 3 functional categories:

| Server | Category | Transport | Purpose & Capabilities |
| :--- | :--- | :--- | :--- |
| **`shadcn`** | Design & UI | `stdio` (`npx shadcn@latest mcp`) | Search and pull accessible headless primitives (Radix, Lucide, Framer Motion) |
| **`shadcn-ui`** | Design & UI | `stdio` (`npx shadcn-ui-mcp-server`) | Direct component token schemas, variants, and dark-mode compositions |
| **`tailgrids`** | Design & UI | `stdio` (`npx @tailgrids/mcp`) | 600+ pre-built React Tailwind layout templates and cards |
| **`livekit-docs`** | Framework Docs | `sse` (`docs.livekit.io/mcp`) | LiveKit Python/TS agents, WebRTC streaming, and protocol documentation |
| **`langgraph-docs`** | Framework Docs | `sse` (`docs.langchain.com/mcp`) | LangGraph StateGraph, SqliteSaver checkpointers, and multi-agent coordination |
| **`filesystem`** | System & IDE | `stdio` | Workspace file tree inspection, safe reading, and editing |
| **`github`** | System & IDE | `stdio` | GitHub PRs, commits, branches, issues, and diff reviews |
| **`memory`** | System & IDE | `stdio` | Knowledge graph entity/relation tracking for lifelong user preferences |
| **`puppeteer`** | System & IDE | `stdio` | Headless browser execution for UI screenshot verification and DOM auditing |
| **`sequential-thinking`**| System & IDE | `stdio` | Dynamic multi-step reasoning and hypothesis verification |

---

## 🔍 Running the Inspector

Inspect the entire MCP architecture and tool count directly from your terminal:

```bash
python mcp/inspect_mcp.py
```

---

## ⚙️ Configuration Files

- Workspace Config: [`mcp_config.json`](../mcp_config.json)
- Authoritative Registry: [`mcp/mcp_registry.json`](mcp_registry.json)
- IDE Global MCP Root: `~/.gemini/antigravity-ide/mcp/`
