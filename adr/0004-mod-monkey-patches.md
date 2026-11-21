# Monkey-patches live in `mod/`

Upstream Brightway and related libraries sometimes need Qt integration, bugfixes, or AB-specific behavior before (or instead of) forking. Those patches live under `activity_browser/mod/` and are applied via import-time patching utilities. Keep patches minimally invasive, document why each exists, test carefully, and prefer contributing upstream when practical rather than growing silent forks inside AB. When revisiting a patch, check whether a newer dependency version already removes the need for it.
