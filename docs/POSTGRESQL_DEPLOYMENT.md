# Persistent PostgreSQL deployment

Catalyst AI uses PostgreSQL whenever `DATABASE_URL` is configured. If it is not
configured, the application falls back to `data/catalyst_ai.db` for local
development and automated tests.

## Streamlit Community Cloud

1. Create a PostgreSQL database in Supabase, Neon, Railway, or another managed
   PostgreSQL provider.
2. Copy the provider's pooled connection string when available.
3. Open the deployed Streamlit application settings.
4. Add the following secret, replacing the example value:

```toml
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
```

5. Save the secret and reboot the application once.
6. Create the initial Catalyst AI administrator. The account, projects,
   memberships, and workflow snapshots will now survive Streamlit reboots and
   redeployments.

Do not commit a real database URL to GitHub.

## Local development

No configuration is required. Catalyst AI uses SQLite by default:

```text
data/catalyst_ai.db
```

To test against PostgreSQL locally, set an environment variable before starting
Streamlit:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DATABASE"
streamlit run app.py
```

On Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DATABASE"
streamlit run app.py
```

## Schema migrations

Application startup runs idempotent schema migrations before authentication.
Applied versions are recorded in the `schema_migrations` table. Sprint 6 creates
and manages these durable tables:

- `users`
- `projects`
- `project_memberships`
- `project_workflow_snapshots`
- `schema_migrations`

Future knowledge-library, chunk, embedding, and retrieval tables should be added
as new numbered migrations rather than through ad hoc production SQL.

## Existing Streamlit SQLite data

Streamlit Community Cloud local SQLite files are ephemeral. Data already lost
during a reboot cannot be recovered unless a separate backup exists. Configure
PostgreSQL before recreating production users and projects that must be retained.
