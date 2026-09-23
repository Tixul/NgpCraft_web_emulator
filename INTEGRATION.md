# Website integration

Copy `public/` to a static directory such as `/ngpc/`. Keep modules, WASM and license notices together. Serve over HTTPS or localhost. Cross-origin ROMs require CORS permission.

## Compact component

```html
<div style="width:100%;max-width:480px;aspect-ratio:160/152">
  <ngpcraft-embed rom="/games/example.ngp" game-title="Example"></ngpcraft-embed>
</div>
<script type="module" src="/ngpc/integrated.js"></script>
```

Play starts the deferred ROM and WASM download. The toolbar sits below the image. The ROM name is hidden during normal play. Settings pause the game; their close and Resume buttons remain visible while contents scroll.

The compact player uses CSS maximize. Avoid ancestors with transforms, filters or restrictive clipping, which can constrain fixed positioning. The full `ngpcraft-player` uses the browser Fullscreen API where available.

## JavaScript mounting and capture

```javascript
import { mountNgpCraft } from '/ngpc/integrated.js';
const player = mountNgpCraft(document.querySelector('#game'), {
  rom: '/games/example.ngp',
  title: 'Example',
  onCapture(canvas, player) {
    document.querySelector('#preview').replaceChildren(canvas);
    // Pass pixels to your own QR decoder or screenshot workflow.
  }
});
// When leaving the view: player.remove();
```

Use a sized container as in the HTML example. `onCapture` receives a new native-resolution canvas (160 by 152) and suppresses the default PNG download. `player.captureFrame()` returns a canvas synchronously once a game is loaded, including while paused.

For declarative mounting, listen for the bubbling, cancelable `ngpc-capture` event. Call `event.preventDefault()` to suppress downloading; the canvas is in `event.detail.canvas`. Set `capture-label` before connecting the component to customize its button text. `ngpc-ready` signals a loaded game.

Keep authentication, QR validation and score submission in the host website. Mount after the site's access check. Remove the component on navigation or logout to release audio, listeners and expanded-page scrolling. Capturing does not submit scores.

## Iframe

```html
<iframe title="Example game"
  src="/ngpc/compact.html?rom=%2Fgames%2Fexample.ngp&title=Example"
  style="width:100%;max-width:480px;aspect-ratio:160/152;border:0"
  allow="autoplay; fullscreen; gamepad" allowfullscreen></iframe>
```

ROM URLs resolve relative to the iframe document. CSS maximize stays inside the iframe. Use direct mounting to cover the host viewport or hand canvases directly to a host callback. No cross-origin postMessage protocol is implemented.

## Replacing an existing emulator

1. Preserve the site's game container, ROM URL, authentication and score UI.
2. Remove its old emulator loader and emulator-specific globals.
3. Mount the compact component in the existing container.
4. Connect `onCapture` to the site's QR or screenshot handler.
5. Remove the component when the view is destroyed.

`integrated.html` provides a working example with local ROM selection and capture preview. `index.html` demonstrates the full player. Neither requires a backend or npm.

## Storage and input

Saves belong to the page origin and the ROM SHA-256. Use export/import to move saves between origins. Iframe storage may be restricted by browser policy. Focus the game canvas for keyboard input. Escape cancels key assignment first, then closes settings, then exits expanded mode. Focus loss and hidden tabs pause emulation. See the README for controls and save-format limits.
