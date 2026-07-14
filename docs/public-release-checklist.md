# Public release checklist

Run this against a fresh export of the entire Git history, not only the current
working tree.

- No ROM, save state, memory dump, archive, screenshot, recording, or extracted
  game asset is tracked.
- No reference disassembly checkout or copied assembly listing is tracked.
- No private scenario database or game-specific generated map is in GBRE.
- Known ROM hashes appear only as compatibility identifiers and tests.
- Large and binary tracked files have been manually reviewed.
- A public port builds and starts without the private `-re` sibling.
- Incompatible ROM revisions are rejected before extraction.
- Runtime outputs go only to ignored directories.
- Dependency revisions are pinned and their licenses/notices are present.
- Names are plain-text compatibility references; official logos and confusing
  presentation are absent.
- README, NOTICE, release notes, and UI clearly say the project is unofficial.
- Repository visibility is checked through GitHub after the push.

If questionable material ever entered public Git history, deleting it in a new
commit is insufficient. Rewrite the affected history before publication, rotate
any exposed credentials, and verify from a brand-new clone.
