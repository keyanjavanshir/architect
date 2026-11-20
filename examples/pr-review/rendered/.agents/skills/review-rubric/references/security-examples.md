# Security severity examples

- **blocker** — user input concatenated into SQL, shell or file paths; auth check
  removed or bypassable; secret committed; TLS verification disabled.
- **major** — missing rate limit on a login or token endpoint; overly broad CORS;
  new dependency with a known critical CVE; logging of personal data.
- **minor** — verbose error messages exposing stack traces in non-prod paths;
  missing security headers on internal tools.
