# AI Credentials & Desktop (EXE) Distribution

## Non-negotiable security rule
**Do not embed long-lived cloud secrets (AWS/OpenAI/Anthropic keys) inside the EXE/installer.**

If you ship `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` inside a desktop binary (or inside an installed `.env`), they will be extractable:
- installers can be unpacked
- Electron/PyInstaller bundles can be inspected
- environment files on disk can be copied

Once leaked, anyone can call Bedrock on your AWS account and you will pay for it.

## What GitHub Secrets are for (and not for)
- ✅ Use **GitHub Secrets** for CI/CD: signing builds, deploying your hosted services, pushing releases.
- ❌ GitHub Secrets are **not** a runtime secret store for an EXE. End-users’ machines cannot securely access GitHub Secrets.

## Recommended production approach (works on any computer)
### Option A (recommended): Hosted “AI Gateway” service
**Goal:** EXE works out-of-the-box for customers without giving them AWS keys.

Architecture:
1. **You run an AI Gateway** (small backend service) in your cloud/VPC.
2. The gateway holds the real AWS credentials (or better: uses an IAM role) and calls Bedrock.
3. The EXE authenticates to the gateway using a **customer license key** (or a device-bound token).
4. Gateway enforces:
   - per-customer rate limits and quotas
   - logging/traceability
   - rapid revocation if a license is leaked

Where secrets live:
- AWS credentials live only on the gateway (ENV + AWS Secrets Manager / Parameter Store).
- The desktop app stores only a revocable token/license (not AWS keys).

Benefits:
- AI works for every EXE install
- you can rotate AWS credentials without re-shipping the app
- you can revoke a customer token/license without affecting others

Tradeoffs:
- requires internet for AI features
- requires you to operate the gateway service

### Suggested auth model
- User installs EXE and enters license key.
- EXE requests a short-lived JWT from the gateway: `POST /auth/exchange-license`.
- EXE uses JWT to call `POST /ai/chat`, `POST /ai/nta`, `POST /ai/nanofacs`.

## Acceptable alternatives
### Option B: BYOK (Bring Your Own Key)
Each customer provides their own AWS credentials and places them in:
- `%APPDATA%\BioVaram\.env` (Windows) for desktop builds, or
- `backend/.env` for dev

This is easiest operationally, but it shifts setup burden to customers.

### Option C: Offline mode (demo/testing only)
Use the built-in offline fallback for local UI testing when no credentials are configured.
This cannot provide real Bedrock reasoning.

## What NOT to do
- Do not ship shared AWS credentials in:
  - the EXE
  - installer scripts
  - a bundled `.env`
  - frontend config

If you *absolutely* must do it temporarily (not recommended), limit blast radius:
- create a dedicated IAM principal with minimum permissions
- apply strict AWS budgets/quotas/alarms
- rotate keys frequently
- expect the keys to leak

## Current repo support
- Desktop builds can load a local env file at `%APPDATA%\BioVaram\.env`.
- Backend supports alias env vars (`CRMIT_ENV`/`CRMIT_ENVIRONMENT`, `CRMIT_DB_URL`/`CRMIT_DATABASE_URL`).

## Next step (implementation)
If you want, we can implement an `AI_PROVIDER=gateway` mode that:
- reads `CRMIT_AI_GATEWAY_URL`
- authenticates with license/JWT
- proxies the existing AI endpoints to the hosted gateway
