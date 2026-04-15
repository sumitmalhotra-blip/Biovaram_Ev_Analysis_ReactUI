# NanoFACS Compare 5-File Quick Sequence

## Purpose
Use this checklist to run a stable 5-file NanoFACS comparison in Flow Cytometry mode with predictable reference/peer selection and manual overlay control.

## Preconditions
- API status shows Connected.
- You have 5 valid .fcs files ready.
- Overlay mode is initially disabled by design.

## 30-Second Operator Sequence
1. Open the Flow Cytometry tab.
2. In the compare uploader, add all 5 files in one batch.
3. Click Upload to Compare Session.
4. Wait until each file row shows Ready.
5. In Compare Session, click Set Reference on your baseline file.
6. In Compare Session, click Set Peer on the file you want for pairwise comparison.
7. Keep Pairwise selected for strict one-to-one checking.
8. Optional: switch to Multi-overlay only if you want multi-file visual overlap.
9. In Overlay Mode, manually pick Primary Overlay File and Secondary Overlay File.
10. Turn Overlay Mode on only after selecting the two files.
11. Verify tabs:
- Reference tab shows baseline statistics/charts.
- Session Peer tab shows selected peer statistics/charts.
- Overlay tab shows the two selected files only.

## Recommended Settings For Stable Review
- Axis mode: Unified Axis for direct comparability.
- Render mode: merged points for quick screening.
- LOD: Settled (higher fidelity) after initial interaction.
- Use Show All or Reference Only intentionally before overlay checks.

## Fast Validation Checklist
- Replicates count equals 5.
- Exactly one file has the Reference badge.
- Peer selector matches intended comparator.
- Overlay Mode is Enabled only when you explicitly toggle it.
- Overlay labels match the two files you selected.
- No unexpected growth in warning types across uploads.

## Common Operator Mistakes
- Enabling overlay before choosing files.
- Assuming auto-assigned pair is correct.
- Mixing per-file axis with strict pairwise interpretation.
- Reading performance gate badges as data quality failures.

## If Something Looks Wrong
1. Click Clear Session.
2. Re-upload the batch.
3. Set Reference and Peer again.
4. Re-select overlay files manually.
5. Enable overlay only at the end.

## Why This Sequence Works
- It separates sample selection from overlay activation.
- It enforces explicit Reference and Peer ownership.
- It prevents random or stale pair assignment.
- It keeps comparisons reproducible for testing and reporting.
