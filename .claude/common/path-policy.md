# Path Policy Capsule

`input/`, `output/`, `library/`, `glossary/`, and `_private/` mean directories under `${LEGAL_TRANSLATION_PRIVATE_DIR}`. Use `.claude/scripts/private-path.py` or `private_path.resolve_private_path()` before reading or writing managed data paths.

Repo-internal managed data paths are rejected except `library/_example`.
