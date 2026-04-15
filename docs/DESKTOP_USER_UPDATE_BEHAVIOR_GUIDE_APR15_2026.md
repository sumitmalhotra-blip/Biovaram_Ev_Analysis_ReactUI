# Desktop User Update Behavior Guide (Apr 15, 2026)

## Purpose
This one-page guide explains how desktop updates behave in production for BioVaram EV Analysis.

## What Users Should Expect
1. The app checks for updates on startup.
2. If a newer version is available, an update dialog appears with version and release notes.
3. Download is mandatory for supported rollout channels (no defer option).
4. A progress window shows download percentage and transferred size.
5. When download completes, user is prompted to install and restart.
6. App restarts into the new version.

## Typical Update Flow
1. Launch app.
2. Update prompt appears.
3. Click Download Update.
4. Wait for progress to complete.
5. Click Install and Restart.
6. Confirm new version in header badge and About/version indicator.

## If Update Fails
1. App remains on last successful version.
2. A failure dialog indicates update stage and last known error.
3. Retry by relaunching app and allowing update flow again.

## Support Quick Checks
1. Confirm internet connectivity.
2. Confirm GitHub releases for the expected version contains:
   - installer EXE
   - installer blockmap
   - latest.yml
3. Ensure no old installer process is still running.

## Known User-Safe Actions
1. Close and reopen app to retry update check.
2. Reinstall latest installer manually if prompted by support.
3. Share screenshot of update dialog/error message with support.

## Escalation Data to Share with Engineering
1. Current visible app version.
2. Target version shown in update dialog.
3. Exact error text (if any).
4. Approximate time of failure.
