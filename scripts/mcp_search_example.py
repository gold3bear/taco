"""
scripts/mcp_search_example.py — MCP Playwright Web Search Examples

Demonstrates using MCP Playwright for web search as Level 1 of the
web-search-fallback protocol.

Usage:
    # This script shows the MCP Playwright commands to use
    # Run these via the MCP Playwright tool in Claude Code

MCP Commands:
    browser_navigate(url)
    browser_snapshot(depth)
    browser_take_screenshot()
    browser_console_messages(level)
"""

# Example MCP Playwright commands for web search:

"""
# ============================================
# Example 1: Google Search
# ============================================

# Navigate to Google search
browser_navigate(url: "https://www.google.com/search?q=Trump+Iran+threat+2026")

# Take snapshot to see results
browser_snapshot(depth: 3)

# Take screenshot
browser_take_screenshot()

# ============================================
# Example 2: X.com (Twitter) Search
# ============================================

# Search for Trump Iran tweets
browser_navigate(url: "https://x.com/search?q=Trump+Iran+from:realDonaldTrump&src=typed_query")

browser_snapshot(depth: 3)

# ============================================
# Example 3: Google News
# ============================================

browser_navigate(url: "https://news.google.com/search?q=Iran+nuclear+deal+Trump&hl=en-US&gl=US&ceid=US%3Aen")

browser_snapshot(depth: 3)

# ============================================
# Example 4: Polymarket
# ============================================

browser_navigate(url: "https://polymarket.com/event/iran-war")

browser_snapshot(depth: 3)

# ============================================
# Example 5: Truth Social (if public)
# ============================================

browser_navigate(url: "https://truthsocial.com/@realDonaldTrump")

browser_snapshot(depth: 3)
"""

print("MCP Playwright Web Search Examples")
print("=" * 50)
print()
print("Use these MCP commands in Claude Code:")
print()
print("1. Google Search:")
print('   browser_navigate(url: "https://www.google.com/search?q=Trump+Iran+2026")')
print('   browser_snapshot(depth: 3)')
print()
print("2. X.com Search:")
print('   browser_navigate(url: "https://x.com/search?q=Trump+Iran")')
print('   browser_snapshot(depth: 3)')
print()
print("3. Google News:")
print('   browser_navigate(url: "https://news.google.com/search?q=Iran+nuclear+Trump")')
print('   browser_snapshot(depth: 3)')
print()
print("4. Polymarket:")
print('   browser_navigate(url: "https://polymarket.com")')
print('   browser_snapshot(depth: 3)')
print()
print("See .claude/skills/web-search-fallback/SKILL.md for full protocol")
