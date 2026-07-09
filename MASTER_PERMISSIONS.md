# MASTER PERMISSIONS

The Master controls all elevated capabilities. Defaults are conservative.

## Currently ENABLED
- Read project files
- Create notes, tasks, plans, drafts
- Analyze business knowledge
- Suggest (not execute) trading ideas

## Currently DISABLED (require explicit enable)
- External API connections (Gmail, Shopify, Meta, broker, etc.)
- Sending email / posting content / changing ads
- Spending money / placing trades (paper or live)
- Running shell commands / installing packages / system changes
- Autonomous anything

## How to enable a capability
Add its key to `enabled_overrides` in `config/permissions.json` AND confirm in-session.
Both are required. Removing the key revokes it.

## Hard rule
Storing passwords or API keys is never enabled.
