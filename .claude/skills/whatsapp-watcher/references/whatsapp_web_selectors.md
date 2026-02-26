# WhatsApp Web CSS Selectors

Selectors used by `whatsapp_monitor.py` to interact with WhatsApp Web DOM.

**Warning**: WhatsApp Web updates frequently. If selectors break, inspect the live DOM and update this file.

## Chat List

| Element | Selector | Purpose |
|---------|----------|---------|
| Chat list container | `div[aria-label="Chat list"]` | Confirms page is loaded |
| Unread badge | `span[aria-label*="unread message"]` | Find chats with unread messages |
| Chat row | `div[role="listitem"]` | Individual chat entry |
| Chat title | `span[title]` | Contact/group name |

## Messages (inside open chat)

| Element | Selector | Purpose |
|---------|----------|---------|
| Message row | `div[role="row"]` | Individual message container |
| Message text | `span.selectable-text` | Text content of a message |

## Media Detection

| Type | Selector | Notes |
|------|----------|-------|
| Image | `img[src*="blob:"]` | Inline image preview |
| Document | `a[href*="blob:"]` | Downloadable file attachment |
| Voice note | `button[aria-label="Play"]` | Audio playback button |

## Troubleshooting

If selectors stop working:

1. Open WhatsApp Web in Chrome
2. Right-click the element → Inspect
3. Find the closest stable attribute (`aria-label`, `role`, `data-*`)
4. Update the `SELECTORS` dict in `whatsapp_monitor.py`
5. Update this file to match

Prefer `aria-label` and `role` attributes — they are more stable than class names which are obfuscated and change between builds.
