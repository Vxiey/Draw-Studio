# Security policy

## Supported versions

Security fixes are applied to the latest published Image Draw Bot release and current `main` when appropriate.

## Reporting a security issue

Do not post secrets, API keys, tokens, private paths or other sensitive information in a public issue.

For non-sensitive bugs, use the GitHub issue templates. For a potentially sensitive security problem, contact the repository owner privately through an available GitHub contact method and include:

- Image Draw Bot version
- Windows version
- affected component
- clear reproduction steps
- impact
- relevant logs with secrets and personal information removed

## Scope

Useful security reports include unsafe file handling, update/download verification problems, privilege-boundary issues, unintended network access, secret exposure, dependency vulnerabilities and unsafe automation behavior.

Image Draw Bot should not require disabling Windows security protections. Published Windows builds are currently unsigned, so Windows may show publisher or SmartScreen warnings; that alone is not a vulnerability.
