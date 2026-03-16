Manage Library profiles and assets.

Execute WF2 — Library Management:

Parse $ARGUMENTS for sub-command and execute:

| Sub-command | Action |
|-------------|--------|
| `list` | List all Library profiles with asset counts |
| `show {profile}` | Display profile details and asset manifest |
| `ingest {profile}` | Ingest new assets from `/library/{profile}/inbox/` — validate, classify, move to correct subfolder, update profile.json |
| `create-profile {name}` | Create new profile with empty directory structure and profile.json |
| `validate {profile}` | Validate all assets — glossary schema, file readability, style guide format |

If no sub-command provided, default to `list`.

Note: The Library is user-managed. The agent reads Library assets but never modifies reference translations, custom glossaries, or style guides directly. Only the `ingest` command moves files from inbox to their proper locations.
