# Deployment trigger probe — 2026-10-31

This documentation-only commit intentionally triggers the existing GitHub Actions
`Publish images` workflow on `main` without modifying application behavior.

Purpose: check whether published Docker images are automatically deployed
to the running OCI service at fast-livery.r3soluciones.com.

A successful image build does **not** by itself demonstrate an OCI deployment.
Confirm the running image digest or a separately deployed version marker before
concluding that production is updated.

No credentials or infrastructure configuration are included.
