# Token Notes

v0.1 default model is local network first. Token auth is optional.

If token auth is enabled:

- Use a static pre-shared token for local setups.
- Require token in `Authorization: Bearer <token>`.
- Return clear unauthorized errors without exposing internals.
- Log failed auth attempts in bounded local logs.
