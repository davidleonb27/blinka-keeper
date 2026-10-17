"""The single write path. Routes, Telegram, the firewall, MCP, the challenge and the red team call these services;
the services call the lanes through their public functions and write every change to the ledger."""
