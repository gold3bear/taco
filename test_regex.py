import re

with open('scripts/build_taco_database.py') as f:
    content = f.read()

eid = 'TACO-006'
escaped = re.escape(eid)

# The block looks like:
#     {
#         "event_id": "TACO-006",
#         ...all fields...
#     },

# Try matching from { to },
block_pat = r'\{[^}]+\},\s*\n'
matches = list(re.finditer(block_pat, content))
print(f'Block pattern found {len(matches)} matches')
for m in matches[:5]:
    snippet = m.group()[:80]
    print(' ', repr(snippet))

# Find TACO-006 block
t006_idx = content.find('"event_id": "TACO-006"')
if t006_idx >= 0:
    # Find the { before it
    before = content[:t006_idx]
    last_brace = before.rfind('{')
    print(f'\nTACO-006 starts at char {t006_idx}')
    print(f'Opening {{ at char {last_brace}')
    # Find the closing } after it
    after = content[t006_idx:]
    next_brace = after.find('},')
    print(f'Closing }} at char {next_brace} (relative to TACO-006 start)')
    block = content[last_brace:t006_idx+next_brace+2]
    print(f'Block: {repr(block[:100])}')
