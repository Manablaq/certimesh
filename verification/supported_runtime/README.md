# Supported runtime evidence

This directory is intentionally empty until the real multi-validator runtime
campaign is run. The campaign must persist raw leader/validator results before
parsing, the exact test command, network/chain metadata, and a manifest of all
result hashes. A leader-only run cannot populate this proof package.

## Controlled campaign setup

The repository includes `gltest.config.example.yaml` and `.env.example`.
Copy them to `gltest.config.yaml` and `.env`, then replace the placeholders
with three temporary, funded Bradbury test-account keys. Keep both copied
files local; they are ignored by Git. Do not paste keys into the repository,
chat, logs, or evidence artifacts.

Run the full validator campaign from the repository root with the pinned
environment:

```bash
gltest --network testnet_bradbury --chain-type testnet_bradbury \
  --contracts-dir contracts --artifacts-dir artifacts tests
```

Do not use `--leader-only`. Before committing this directory, preserve the
raw leader and validator outputs, the exact command and network metadata, and
their SHA-256 values in `manifest.json`. The bundle gate remains fail-closed
until those real artifacts exist.
