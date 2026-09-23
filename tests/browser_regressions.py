"""Failure-path and lifecycle checks, using the actual WASM in Edge."""
import functools
import http.server
import threading
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
(root/'build').mkdir(exist_ok=True)
rom=Path(sys.argv[1]).resolve()
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root/'public')))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page()
        errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{server.server_port}')
        page.locator('input.rom').set_input_files(str(rom))
        page.wait_for_function("document.querySelector('ngpcraft-player').loaded")
        # Invalid base64 must not be silently overwritten by autosave.
        key=page.evaluate("document.querySelector('ngpcraft-player').key")
        page.reload()
        page.evaluate("key=>localStorage.setItem(key,'%%%broken-base64%%%')",key)
        page.locator('input.rom').set_input_files(str(rom))
        page.wait_for_function("document.querySelector('ngpcraft-player').loaded")
        page.evaluate("document.querySelector('ngpcraft-player').persist()")
        assert page.evaluate('key=>localStorage.getItem(key)',key)=='%%%broken-base64%%%', 'corrupt save overwritten'
        assert page.evaluate("document.querySelector('ngpcraft-player').saveBlocked")
        # Space triggers native button activation on keyup: remapping must not rearm capture.
        page.locator('.options').click()
        page.locator('[data-bind="16"]').click()
        page.keyboard.press('Space')
        assert page.evaluate("document.querySelector('ngpcraft-player').settings.keys.Space===16")
        assert page.evaluate("document.querySelector('ngpcraft-player').captureBit===null"), 'space rearmed capture'
        # Zero-volume mute button must be able to restore audible volume.
        page.locator('.volume').fill('0')
        page.locator('.close-options').click()
        page.locator('.mute').click()
        assert page.evaluate("!document.querySelector('ngpcraft-player').muted && document.querySelector('ngpcraft-player').settings.volume>0"), 'mute stuck at zero'
        page.set_viewport_size({'width':844,'height':390})
        page.locator('.full').click()
        page.wait_for_function('!!document.fullscreenElement')
        page.wait_for_timeout(100)
        assert page.locator('canvas').bounding_box()['height']>200, 'landscape fullscreen shrank game'
        page.screenshot(path=str(root/'build'/'player-landscape.png'))
        page.locator('.full').click()
        page.wait_for_function('!document.fullscreenElement')
        page.set_viewport_size({'width':900,'height':1100})
        # Unsupported gamepad API (e.g. iframe Permissions Policy) must not stop keyboard play.
        page.evaluate("Object.defineProperty(navigator,'getGamepads',{configurable:true,value:()=>{throw new DOMException('Blocked','SecurityError')}})")
        page.locator('.play').click()
        page.wait_for_timeout(200)
        assert page.evaluate("document.querySelector('ngpcraft-player').running"), 'gamepad denial stopped playback'
        # A removed/reinserted component has no live core and must reset its controls.
        page.evaluate("window.player=document.querySelector('ngpcraft-player');player.remove();document.querySelector('main').append(player)")
        assert page.locator('.play').is_disabled()
        assert page.locator('.export').is_disabled()
        # A URL request that completes after removal must not resurrect the emulator.
        page.evaluate("""() => {
          window.realFetch=window.fetch;
          window.fetch=()=>new Promise(resolve=>window.finishFetch=resolve);
          window.pending=player.loadURL('/slow.ngp');
          player.remove();document.querySelector('main').append(player);
        }""")
        data=list(rom.read_bytes())
        page.evaluate("data=>finishFetch(new Response(new Uint8Array(data)))",data)
        page.evaluate('pending')
        assert page.evaluate('!player.loaded && !player.module'), 'stale request resurrected core'
        page.evaluate('window.fetch=realFetch')
        # Exercise a real embedded player, including iframe fullscreen permission.
        page.evaluate("""() => {
          const frame=document.createElement('iframe');frame.src='/embed.html';
          frame.title='Embedded player';frame.allow='fullscreen; gamepad';
          frame.style='width:600px;height:1000px';document.body.replaceChildren(frame);
        }""")
        embedded=page.frame_locator('iframe')
        embedded.locator('input.rom').set_input_files(str(rom))
        embedded.locator('.play').wait_for()
        embedded.locator('.play').click()
        page.wait_for_timeout(250)
        frame=page.frames[1]
        assert frame.evaluate("document.querySelector('ngpcraft-player').running"), 'iframe failed to play'
        embedded.locator('.full').click()
        page.wait_for_function("document.fullscreenElement?.tagName==='IFRAME'")
        embedded.locator('.full').click()
        page.wait_for_function('!document.fullscreenElement')
        assert not errors,errors
        print('PASS: corrupt storage, Space remapping, zero volume, landscape fullscreen, blocked gamepad API, detach/reconnect, stale URL request, real iframe playback/fullscreen')
        browser.close()
finally:
    server.shutdown()
