# WebSocket Notes (Optional)

Use `WS /stream` for high-rate data that would be inefficient with polling.

Recommended behavior:

- Keep message envelope consistent with HTTP action/capture responses.
- Include sequence numbers and timestamps.
- Support backpressure or rate limiting.
- Allow client-side filtering by capability/channel.
