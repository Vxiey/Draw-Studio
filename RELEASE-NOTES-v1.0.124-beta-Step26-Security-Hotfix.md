# Draw Studio v1.0.124-beta Step 26 — Security Hotfix

This hotfix keeps the existing Step 26 Detail Fidelity, Pixel Accurate and Named Color Intelligence release intact while applying the URL-hostname validation security fix.

## Fixed

- Fixes GitHub CodeQL alert #2: `py/incomplete-url-substring-sanitization`.
- Replaces substring-based Bing/Google hostname recognition with exact domain/subdomain validation.
- Prevents deceptive hostnames such as `bing.com.evil.example` and `notbing.com` from being treated as Bing.
- Prevents a domain name appearing only in a URL path or query from being treated as a trusted image-search host.
- Applies the same hostname-label validation to supported Google image/CDN domains.
- Adds `test_canvas_drop_payload_security.py` regression coverage.

## Verification

- Security regression tests pass.
- `CanvasDropPayload.py` compiles successfully.
- GitHub CodeQL marked alert #2 as `fixed` on 2026-09-08.
- The packaged hotfix is checked for ZIP integrity and for removal of the vulnerable substring check.

## Unchanged

The application version remains `1.0.124-beta`. Pixel Accurate planning, Named Color Intelligence, calibrated palettes, CanvasGuard, profile isolation and renderer behavior are otherwise unchanged.
