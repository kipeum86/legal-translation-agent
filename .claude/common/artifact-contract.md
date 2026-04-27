# Artifact Contract Capsule

A step is complete only when every required output exists, is non-empty, validates against its schema when JSON, and is recorded in `manifest.json` with sha256, byte size, timestamp, producing step, and schema path.

Use `.claude/scripts/translate-job.py record-artifact` for produced sidecars and `record-failure` for blocking failures.

Use `.claude/scripts/translate-job.py validate-gate` for schema and semantic gates. Rollout policy is `warn`, `enforce-new-jobs`, or `enforce-all`; set it with `--validation-policy` or `LEGAL_TRANSLATION_VALIDATION_POLICY`.
