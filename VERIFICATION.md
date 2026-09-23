# Verification

The release uses desktop core commit `b2f8318b817dff486bf78c18c997459c36e0940c` (ABI 18), compiled with Emscripten 4.0.23. `public/build-info.json` records desktop source and public artifact hashes. No ROM is included.

## Automated checks

Run the README commands with your own ROM. Browser tests require Playwright and Microsoft Edge.

| Test | Coverage |
| --- | --- |
| `smoke.mjs` | 600 frames, framebuffer/audio output, reset/reload, save validation and flash round-trip where available |
| `browser_smoke.py` | Full player, options, save import/export and touch layout |
| `browser_regressions.py` | Invalid storage, remapping, zero volume, fullscreen layout, denied gamepad access, detach/reload and iframe behavior |
| `integrated_smoke.py` | Deferred loading, capture, settings, maximize, mobile layout and cleanup |
| `check_package.py` | Public hashes, license identity, absence of ROMs and optional ZIP contents |

The port has been exercised with StarGunner and Tetris homebrew. A smoke test confirms the tested interactions, not compatibility with every game.

## Release review

Serve the tracked public directory from a fresh checkout. Start a ROM, open and close settings, remap a key and resume. Check that controls and ROM status do not cover gameplay. Exercise capture, maximize and save import/export. Regenerate the manifest after modifying public assets, and rebuild after core changes. Keep SDKs, ROMs, build output and screenshots out of commits.

## Limits

Mobile checks emulate viewport and touch in desktop Edge. Physical phones and gamepads, Safari, long-session audio and exhaustive game compatibility have not been validated by this suite. Desktop core and HLE compatibility limits apply.
