# NgpCraft Web Emulator

A lightweight Neo Geo Pocket / Neo Geo Pocket Color player for websites. It compiles the **NgpCraft desktop C++ core directly to WebAssembly**, with a small JavaScript frontend. No Libretro, RetroArch, EmulatorJS, Qt, SDL, npm packages or CDN are required at runtime.

**[▶ Try it online](https://tixul.github.io/NgpCraft_web_emulator/)** — open a ROM from your computer and play. Nothing is uploaded: the ROM stays in your browser.

The ready-to-host files are included in [`public/`](public/). You only need a compiler if you want to rebuild the emulator. No game ROMs or proprietary BIOS dumps are included; the desktop project's clean-room HLE firmware is embedded in the WASM module.

## Try it locally

```sh
python -m http.server 8080 --bind 127.0.0.1 --directory public
```

Open [localhost:8080](http://localhost:8080), choose a local ROM and click **Play**. Local ROMs stay in the browser and are not uploaded. Opening HTML through `file://` is not supported.

| Page | Purpose |
| --- | --- |
| `index.html` | Full player with a local ROM picker |
| `integrated.html` | Example of a compact player inside a site's content |
| `compact.html?rom=/games/my-game.ngp` | Compact iframe document |
| `embed.html?rom=/games/my-game.ngp` | Full-player iframe document |

The player interface and project documentation are in English.

## Embed a game

Upload `public/` to `/ngpc/` on your website:

```html
<div style="width:100%;max-width:480px;aspect-ratio:160/152">
  <ngpcraft-embed rom="/games/my-game.ngp" game-title="My game"></ngpcraft-embed>
</div>
<script type="module" src="/ngpc/integrated.js"></script>
```

The compact player downloads the ROM and emulator only after the user clicks Play. Its toolbar sits below the game image. The settings panel has General, Keys and Save tabs, a visible close button, and a fixed Resume button. Styles are isolated with Shadow DOM.

See [INTEGRATION.md](INTEGRATION.md) for JavaScript mounting, screenshots, QR-reader integration, iframe behavior and a migration example for an existing game site.

## Features

- Native 160 × 152 rendering, sharp or smooth scaling, stereo 44.1 kHz audio.
- Desktop silicon timing and approximately 59.95 emulated frames per second.
- Remappable keyboard controls, touch buttons and browser-standard gamepads.
- Pause, reset, mute/volume and fullscreen or CSS maximize, depending on the frontend.
- Persistent browser settings and in-game saves; save import/export with validation.
- Native screenshots for downloads or a host page's QR decoder.
- Automatic pause when the window loses focus or the tab becomes hidden.

Default keyboard controls: arrows for direction, physical Z/X positions for A/B, Enter for Option. Focus the game canvas to control it. Saved bindings follow physical key positions and show the label captured when assigning a key. Standard gamepad mapping: D-pad/left stick, buttons 0/1 and Start.

## Saves and limits

Saves contain the game's flash-save areas and emulated RTC, **not instant save states**. Browser storage is keyed by the ROM's SHA-256, so renaming the file retains its save. Autosave runs every five seconds, on pause, game changes and normal page exit. Export important saves: browser data can be cleared or storage may be unavailable.

The `.ngpsav` format is specific to this frontend. It stores the upper 64 KiB of each flash chip and the RTC. Homebrew that saves elsewhere needs an extended format. The RTC advances during emulation, without offline catch-up. Do not run the same ROM in several tabs simultaneously: cross-tab save ownership is not implemented. Invalid stored saves are preserved and block autosave until a valid save is imported.

This release is single-player and uses HLE handoff, English console language and the color-console setting. No link cable, rewind, save states, external BIOS selector or ZIP loading. Game compatibility remains bounded by the core and HLE firmware. ROMs must be 64 bytes to 4 MiB.

## Hosting

Use HTTPS in production or localhost for development. Serve `.wasm` as `application/wasm` and `.js`/`.mjs` as JavaScript. Keep the loader, WASM and frontend modules together. Cross-origin ROM URLs need appropriate CORS headers. A restrictive CSP must allow the module scripts and WebAssembly execution.

Enable gzip or Brotli on the server. The compact runtime is roughly **45 KB with gzip**, excluding ROMs, HTML and license notices. Exact sizes and hashes are in [`public/build-info.json`](public/build-info.json). Download size is not RAM usage: WASM memory starts at 32 MiB and can grow. Threads, SharedArrayBuffer and cross-origin isolation headers are not required.

## Rebuild from source

The C++ core is an external source dependency, deliberately shared with the desktop project rather than copied into a separate emulation fork:

```sh
git clone https://github.com/Tixul/Ngpcraft_emulator.git ../Ngpcraft_emulator
git -C ../Ngpcraft_emulator checkout b2f8318b817dff486bf78c18c997459c36e0940c
```

The shipped build was tested with **Emscripten 4.0.23**, the desktop core ABI 18, CMake and a CMake-supported build tool. Install and activate Emscripten separately; its SDK is not part of this repository. See the official [Emscripten build documentation](https://emscripten.org/docs/compiling/Building-Projects.html).

With the Emscripten environment active:

```sh
emcmake cmake -S . -B build -DNGPCRAFT_DESKTOP=../Ngpcraft_emulator -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
python package.py --desktop ../Ngpcraft_emulator --emscripten "$EMSDK/upstream/emscripten"
```

PowerShell helper (Ninja on PATH by default):

```powershell
.\build.ps1 -Emsdk 'C:\tools\emsdk'
# Or use a specific build tool:
.\build.ps1 -Emsdk 'C:\tools\emsdk' -Generator 'MinGW Makefiles' -Make 'C:\tools\mingw\bin\mingw32-make.exe'
```

`-DesktopSource` overrides the sibling core checkout. Use a fresh build directory when changing generators. The helper regenerates the compiled files and package; it does not modify the desktop repository or install tools globally.

`package.py` writes `dist/NgpCraft-Web-Player.zip` with the static site, documentation and license notices. `dist/` and local build/test output are ignored. The generated `.mjs` and `.wasm` in `public/` are intentionally tracked so a clone can be hosted immediately. Source hashes, the desktop commit and runtime file hashes are recorded in the manifest; rebuild before packaging if core sources change.

## Tests

Supply your own ROM; none is included:

```sh
node tests/smoke.mjs /path/to/game.ngp
python -m pip install -r requirements-test.txt
python tests/browser_smoke.py /path/to/game.ngp
python tests/browser_regressions.py /path/to/game.ngp
python tests/integrated_smoke.py /path/to/game.ngp
python tests/check_package.py
```

Browser tests use an installed Microsoft Edge through Playwright. `check_package.py` validates the tracked public files without a ROM, and also verifies the ZIP if it has been built. Browser screenshots are written to ignored `build/`. See [VERIFICATION.md](VERIFICATION.md) for coverage and limitations.

## Repository contents

| Path | Purpose |
| --- | --- |
| `bridge.cpp` | Web-facing adapter to the desktop core's C API |
| `CMakeLists.txt`, `build.ps1` | WASM build configuration and Windows helper |
| `public/` | Frontends, demos, compiled runtime, notices and manifest |
| `package.py` | Release ZIP and build-manifest generation |
| `tests/` | Core, browser and artifact checks |

## License

The project uses the [MIT license](LICENSE), copyright 2026 Tixul. Compiler runtime notices are included in [`public/THIRD_PARTY_NOTICES.txt`](public/THIRD_PARTY_NOTICES.txt). Retain both when distributing the compiled player. No third-party emulator frontend or proprietary SNK firmware is included.
