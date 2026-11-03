# Choose and use a reference store

Keep the registry and project choices where the consumer wants them. Existing local paths remain valid; `.local` is optional. For a team database or cloud location, use `store://<profile>/<document-key>`. Registry metadata and connection state are separate JSON documents and may use different profiles. Real source bodies remain at their own sources.

Inspect existing connection settings first. If a material storage choice is missing, ask which local/remote destination and account to use, and whether the intended audience is personal or a team. Record the chosen location; do not repeatedly ask for the same choice. Do not create cloud resources or change service ACLs merely because a profile is configured. Reuse authorized host accounts or environment credentials. A profile name such as `personal` is not proof that the service is private.

Resolve `profiles-example` in the [storage index](../references/storage/index.json) for configuration fields. Copy only the selected profile into the consumer's chosen configuration location. Replace example destinations with observed real ones. Most drivers use Python's standard library. S3 alone uses a Python 3.10+ SDK environment with optional `boto3>=1.35.69`; never install it for unrelated stores. The source-specific API references in that index explain each service's actual permissions and limits.

Supported stores:

- File: pass any authorized local file path; file permissions remain authoritative.
- SQLite: a `sqlite` profile supplies a database path. Reads do not create the DB. Writes use an atomic revision check.
- HTTP: an `http` profile supplies a JSON endpoint base. Existing-document changes need a strong ETag and server-enforced conditional PUT. A plain JSON website can be read without claiming write support.
- GitHub: a `github` profile supplies API endpoint, repository, branch and optional key prefix. The Contents API's file SHA prevents stale replacement. Repository access and branch protection still apply.
- Supabase: a `supabase` profile supplies endpoint, table and credential environment variable names. The table uses unique `id`, `document` JSON and increasing `revision`; conditional PATCH and RLS apply. Resolve `supabase-schema-example` through the index only when provisioning a selected store. That example grants personal access to authenticated owners; team policies must be explicitly designed in the owning service.
- S3: an `s3` profile supplies bucket, optional prefix, region and AWS profile. The SDK's normal credential chain and IAM apply. Conditional object PUT uses the observed ETag.
- Confluence Cloud: a `confluence` profile supplies a wiki endpoint and existing page ID. Each key is a JSON content property on that page, using property version checks. This adapter does not replace page prose, create pages or modify restrictions. It does not claim Confluence Data Center compatibility.
- Other services: a `host` profile accepts an authorized adapter via `Stores(config, adapters={profile: adapter})`. The adapter implements `read(key)` and `write(key, document, expected_revision=...)` and returns document/digest/revision observations. The standalone CLI does not invent a host integration when one is absent.

`writable` defaults to false for configured stores and is a client-side write guard only. Even when true, the service must authorize the operation. Never store tokens, passwords or signed URLs in an index, connection state or profile file. An environment variable name is safe configuration; its value stays in the execution environment.

Create an empty registry only when the user intends a new document:

```sh
python3 <plugin>/scripts/references.py init --index store://team/references --store-config <profiles.json>
python3 <plugin>/scripts/references.py list --index store://team/references --store-config <profiles.json>
```

Use `add`, `update` and `remove` on that same index. Updates/removals require the observed `index_digest`; the storage layer additionally checks the write revision atomically. On conflict, read current state, reconcile the intended change and then retry deliberately. No forced overwrite or automatic local copy is a recovery strategy. Physical document deletion and permission changes remain service operations; `references.py remove` removes only the selected metadata entry.

Connection state can also stay remote:

```sh
python3 <plugin>/scripts/sources.py init --state store://team/project-choices --store-config <profiles.json>
python3 <plugin>/scripts/sources.py select --state store://team/project-choices --store-config <profiles.json> --intent knowledge --mode custom --index store://team/references --access connector
python3 <plugin>/scripts/sources.py discover --state store://team/project-choices --store-config <profiles.json> --intent knowledge
```

A store registry is an opaque connector location. Its entries use explicit file/web/connector addresses, not implicit relative filesystem paths. Each user supplies their own profile-to-account mapping. References to another profile require an explicit selected root; a shared connection to a local file requires the caller's `--source-root`. Do not transfer another user's credentials with shared choices.

Run source reads through the existing reference workflow. Use a separate trace/access context per caller. Registry and connection persistence may be remote, while current receipt traces remain local execution records. Transport tests and mocked provider contracts do not establish a real account's availability, RLS, IAM, page restrictions or branch permissions; report live verification separately.
