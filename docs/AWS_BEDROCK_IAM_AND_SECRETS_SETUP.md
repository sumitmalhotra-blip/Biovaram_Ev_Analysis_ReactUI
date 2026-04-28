# AWS Bedrock: IAM + Secrets Setup (CRMIT)

This document explains how to enable **real** Bedrock-backed AI in a way that is safe for:
- local developers
- CI/release builds
- customer desktop EXEs

It also describes the **codebase changes** needed so we do **not** hardcode `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in the app.

---

## 1) Key point: don’t embed AWS keys in the EXE
A desktop EXE runs on an untrusted machine. Any long-lived AWS key placed inside the EXE/installer (or a bundled `.env`) can be extracted.

If you promised “AI works everywhere”, the secure way is:
- run an **AI Gateway service** (server) that holds AWS permissions
- the EXE authenticates to the gateway using a license/token

See: [docs/AI_CREDENTIALS_AND_DESKTOP_DISTRIBUTION.md](docs/AI_CREDENTIALS_AND_DESKTOP_DISTRIBUTION.md)

---

## 2) Recommended production model: IAM Role (no AWS access keys at all)
If your Bedrock-calling backend runs on AWS (EC2/ECS/Lambda), **use an IAM role**.

### 2.1 Create an IAM policy for Bedrock invoke
Create a policy, for example: `CRMITBedrockInvokePolicy`.

At minimum, it needs permission to invoke the Bedrock model(s) you use.

Example (tighten resources to the exact model ARNs if possible):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:
- Some accounts/regions also require `bedrock:ListFoundationModels` for discovery tooling (optional).
- Prefer least privilege: restrict `Resource` to the model ARN(s) you actually call.

### 2.2 Attach the policy to the compute role
Pick your compute target:

**ECS (recommended for a small gateway)**
- Create/choose a Task Role (not the execution role) e.g. `CRMITAIGatewayTaskRole`
- Attach `CRMITBedrockInvokePolicy`

**EC2**
- Create an instance profile role e.g. `CRMITAIGatewayInstanceRole`
- Attach `CRMITBedrockInvokePolicy`

**Lambda**
- Lambda execution role e.g. `CRMITAIGatewayLambdaRole`
- Attach `CRMITBedrockInvokePolicy`

### 2.3 Runtime configuration
With IAM roles:
- do **not** set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- set only region:

```env
AWS_REGION=us-east-1
```

Boto3 will automatically fetch credentials from the role.

---

## 3) Alternative: Secrets Manager (when you truly need stored secrets)
Secrets Manager is useful when:
- you are running outside AWS but still need to store secrets centrally
- you need to store API keys for non-AWS providers (OpenAI/Anthropic)

For Bedrock specifically, if you run on AWS, IAM roles are preferred and Secrets Manager is often unnecessary.

### 3.1 Store a secret
Create a secret e.g. `crmit/prod/ai`.

Example JSON value:
```json
{
  "AWS_REGION": "us-east-1"
}
```

(If you *must* store long-lived access keys, store them here, but it’s still inferior to roles.)

### 3.2 Allow your service to read it
Attach a policy to your service role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:crmit/prod/ai*"
    }
  ]
}
```

### 3.3 Load secrets at startup
Two common patterns:
- best: load from Secrets Manager at startup and set environment variables in-memory
- simpler: your infrastructure injects values into env vars (ECS task definition, Lambda env)

---

## 4) Local developer setup (no shared long-lived keys)
For developers, prefer AWS SSO or named profiles.

### 4.1 AWS CLI install + login
- Install AWS CLI v2
- Configure SSO (recommended):

```powershell
aws configure sso
aws sso login
```

### 4.2 Use an AWS profile
Set:
```env
AWS_PROFILE=your-profile-name
AWS_REGION=us-east-1
```

The codebase should use the standard AWS credential chain, so the profile works without putting keys in `.env`.

---

## 5) Codebase requirements (what needs to exist in this repo)
### 5.1 Use the standard AWS credential provider chain
Boto3 already supports the right behavior:
1. `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` env vars
2. shared config/credentials files (~/.aws/credentials)
3. `AWS_PROFILE`
4. ECS/EC2/Lambda role credentials

**The code should not pass access keys explicitly.**
It should create the client like:

```python
import boto3
client = boto3.client("bedrock-runtime", region_name=region)
```

Optionally, for local dev profiles:
```python
session = boto3.Session(profile_name=os.getenv("AWS_PROFILE"))
client = session.client("bedrock-runtime", region_name=region)
```

### 5.2 What env vars are required
Minimum for Bedrock:
- `AWS_REGION` (or `AWS_DEFAULT_REGION`)

Only if you are using env-var credentials:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Optional:
- `AWS_PROFILE` (dev machines)

### 5.3 App behavior
- In dev: allow offline fallback (already supported) if AWS isn’t configured
- In production gateway: fail fast if Bedrock is required and credentials are missing

---

## 6) Suggested next implementation step: “AI Gateway provider”
To deliver AI in the EXE without shipping AWS credentials:
- add `AI_PROVIDER=gateway`
- add `CRMIT_AI_GATEWAY_URL=https://...`
- gateway holds IAM role permissions

If you want, we can implement the `gateway` provider mode next.
