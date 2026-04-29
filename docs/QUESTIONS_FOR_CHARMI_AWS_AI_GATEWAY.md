# Questions for Charmi — AWS + AI Gateway (BioVaram / CRMIT)

## Goal (what we want to finish)
We want **real AI (AWS Bedrock)** to work:
1) on Sumit’s local machine for development/testing, and
2) inside the **release EXE** on end-user machines **without shipping AWS credentials**.

We are using the **Gateway approach**:
- The desktop/backend calls a hosted gateway using:
  - `AI_PROVIDER=gateway`
  - `CRMIT_AI_GATEWAY_URL=<hosted base url>`
  - `CRMIT_AI_GATEWAY_LICENSE_KEY=<client key>`
- The hosted gateway is the only place that has AWS auth (IAM role/credentials) and calls Bedrock.

---

## A) Gateway service (hosted) — URL, endpoints, contract
1) What is the **hosted gateway base URL** we should use for production?
   - Example format: `https://ai-gateway.<domain>`

2) Do we also have a **staging/dev gateway URL** for testing from local machines?

3) Confirm the **API endpoints and payloads** the gateway must support:
   - `GET  /api/v1/ai/gateway/health`
   - `POST /api/v1/ai/gateway/chat`
   - `POST /api/v1/ai/gateway/complete`

4) Confirm the **response shape** we should rely on (fields, names, error format):
   - For `/chat`: should it return `{ content, model, provider }`?
   - For `/complete`: should it return `{ text, model, provider }`?
   - What’s the standard error response for auth failures / throttling / Bedrock errors?

5) Is **streaming** required (server-sent events / chunked output), or is non-streaming enough?

---

## B) Authentication / licensing (EXE-safe auth)
6) What authentication method should the gateway enforce?
   - Confirm we use `X-License-Key: <key>` header.

7) How will license keys be **issued**?
   - Per customer? Per user? Per device? Per site?

8) How will license keys be **rotated / revoked**?
   - Who generates keys and where are they stored?

9) What are the desired **rate limits** per license key?
   - Requests/minute, burst limits, max tokens/day, etc.

10) Should the gateway reject requests without `X-License-Key` (401), or allow anonymous access for now?

---

## C) AWS Bedrock configuration (this is the “real AI” dependency)
11) Which **AWS account** and **region** is Bedrock enabled in?

12) Which **Bedrock model IDs** are approved/allowed?
   - Example: `amazon.nova-lite-v1:0`

13) Is model access already granted in the account (Bedrock model access approvals)?

14) What compute is the gateway running on (EC2 / ECS / EKS / Lambda / other)?

15) How does the gateway authenticate to AWS?
   - Preferred: IAM role attached to the compute (instance profile / task role)
   - If not role-based: how are credentials provided securely?

16) Can you share the **minimal IAM policy** for the gateway role to call Bedrock for the allowed models?
   - Also confirm if we need access to:
     - `bedrock:InvokeModel`
     - `bedrock:InvokeModelWithResponseStream` (only if streaming is needed)

17) Any expected **quotas/limits** we should plan around?
   - Throttling behavior, provisioned throughput requirements (if any)

---

## D) Network & security posture
18) Is the gateway **publicly reachable** from end-user machines?
   - If not, what network (VPN/VPC/peering) is required?

19) Do we need **IP allowlisting**?
   - If yes, what IPs should be allowed (office/VPN/hosted NAT, etc.)?

20) TLS/SSL details:
   - Confirm gateway must be `https://`.
   - Who owns the domain + certificate renewal?

21) Data handling:
   - Are we allowed to log prompts/responses? If yes, what should be redacted?

---

## E) Observability & debugging (so we can fix issues quickly)
22) Where do gateway logs live (CloudWatch / Datadog / Sentry / other)?

23) Do we have a **correlation/request ID**?
   - If yes, can the gateway return it in responses/headers for support?

24) What are the most common failure modes you’ve seen?
   - Missing model access, missing IAM perms, throttling, wrong region, etc.

25) Can you provide 2–3 example failing responses and what they mean?

---

## F) “Local dev” enablement (Sumit’s machine)
We need one of these two paths:

### Option 1 — Use a staging gateway (recommended)
26) Provide a **staging gateway URL** + **one test license key** that can call real Bedrock.

### Option 2 — Run gateway locally with AWS auth
27) What is the correct way for Sumit to get AWS credentials locally?
   - AWS SSO? Named profile? Environment variables?

28) What exact steps should Sumit run to verify AWS auth works?
   - Example: a minimal `boto3` test snippet or AWS CLI command.

---

## G) EXE distribution (end-user install experience)
29) Confirm: end-user machines will **NOT** have AWS keys.

30) How will the EXE get the gateway config?
   - We support `%APPDATA%\\BioVaram\\.env` on the client machine.

31) What should we ship as defaults?
   - Production gateway URL prefilled in installer? Or user/customer-specific config file?

32) How will the end-user receive their `CRMIT_AI_GATEWAY_LICENSE_KEY`?
   - Included in a license file? Entered on first run? Delivered by admin?

33) Any customer onboarding steps we must document?

---

## H) Definition of Done (DoD) — please confirm these acceptance tests
Please confirm you can provide everything needed so we can pass these tests:

1) From a machine with only gateway config (no AWS keys), set:
   - `AI_PROVIDER=gateway`
   - `CRMIT_AI_GATEWAY_URL=<prod-or-staging-url>`
   - `CRMIT_AI_GATEWAY_LICENSE_KEY=<valid-key>`

2) Run:
   - `GET  <gateway>/api/v1/ai/gateway/health` → 200 OK
   - `POST <gateway>/api/v1/ai/gateway/complete` with prompt → returns real model output and `provider=bedrock`
   - `POST <gateway>/api/v1/ai/gateway/chat` with messages → returns real model output and `provider=bedrock`

3) End-to-end in our app:
   - App chat features work on local dev machine.
   - Same works after packaging into EXE (no AWS secrets on client).

---

## Quick “what we need from you” list (copy/paste)
- [ ] Production gateway base URL
- [ ] (Optional) Staging gateway base URL
- [ ] One test `X-License-Key`
- [ ] Confirmed AWS region
- [ ] Confirmed Bedrock model ID(s)
- [ ] Gateway hosting type (EC2/ECS/EKS/Lambda) + how IAM role is attached
- [ ] Minimal IAM policy for Bedrock invoke
- [ ] Any rate limits / expected throttling behavior
- [ ] Logging/retention guidance for prompts/responses
