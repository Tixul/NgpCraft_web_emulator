"""Run with Playwright installed; uses existing Edge, no browser download."""
import functools
import http.server
import json
from pathlib import Path
import sys
import threading
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
(root/'build').mkdir(exist_ok=True)
rom = Path(sys.argv[1]).resolve()
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path == '/test.ngc':
            data=rom.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','application/octet-stream')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else: super().do_GET()
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(root/'public')))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width':900,'height':1100})
        errors=[]
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{server.server_port}')
        page.locator('input.rom').set_input_files(str(rom))
        page.wait_for_function("document.querySelector('ngpcraft-player').loaded")
        page.locator('button.play').click()
        page.wait_for_timeout(2500)
        result=page.evaluate("""() => {
          const p=document.querySelector('ngpcraft-player');
          const colors=new Set(); const d=p.context.getImageData(0,0,160,152).data;
          for(let i=0;i<d.length;i+=4)colors.add(`${d[i]},${d[i+1]},${d[i+2]}`);
          return {running:p.running, colors:colors.size, audio:p.audio.state, sources:p.sources.size};
        }""")
        assert result['running'] and result['colors']>1, result
        assert result['audio']=='running' and result['sources']>0, result
        page.keyboard.down('z')
        assert page.evaluate("document.querySelector('ngpcraft-player').input() & 16")
        page.keyboard.up('z')
        assert not page.evaluate("document.querySelector('ngpcraft-player').input() & 16")
        page.locator('[data-bit="16"]').hover()
        page.mouse.down()
        assert page.evaluate("document.querySelector('ngpcraft-player').input() & 16")
        page.mouse.up()
        page.locator('button.play').click()
        assert page.evaluate("!document.querySelector('ngpcraft-player').running")
        assert page.evaluate("localStorage.length > 0")
        with page.expect_download() as download:
            page.locator('details').click()
            page.locator('button.export').click()
        saved=root/'build'/'browser-test.ngpsav'
        download.value.save_as(saved)
        page.locator('input.save').set_input_files(str(saved))
        page.wait_for_function("document.querySelector('ngpcraft-player').shadowRoot.querySelector('.status').textContent.includes('imported')")
        page.screenshot(path=str(root/'build'/'player-desktop.png'))
        page.reload()
        page.locator('input.rom').set_input_files(str(rom))
        page.wait_for_function("document.querySelector('ngpcraft-player').loaded")
        assert not page.evaluate("document.querySelector('ngpcraft-player').saveBlocked")
        page.locator('button.play').click()
        page.locator('button.options').click()
        assert not page.evaluate("document.querySelector('ngpcraft-player').running"), 'options pause emulation'
        page.locator('[data-bind="16"]').click()
        page.keyboard.press('ArrowUp')
        assert page.evaluate("document.querySelector('ngpcraft-player').captureBit === 16"), 'duplicate binding rejected'
        page.keyboard.press('q')
        page.locator('[data-bind="32"]').click()
        page.keyboard.press('Escape')
        assert page.evaluate("document.querySelector('ngpcraft-player').settings.keys.KeyX === 32"), 'escape cancels capture'
        page.locator('.volume').fill('35')
        page.locator('.display').select_option('smooth')
        page.locator('.show-touch').uncheck()
        assert abs(page.evaluate("document.querySelector('ngpcraft-player').gain.gain.value")-.35)<.001
        page.screenshot(path=str(root/'build'/'player-options.png'))
        page.locator('.close-options').click()
        page.locator('button.play').click()
        page.keyboard.down('q')
        assert page.evaluate("document.querySelector('ngpcraft-player').input() & 16"), 'new binding works'
        page.keyboard.up('q')
        page.keyboard.down('z')
        assert not page.evaluate("document.querySelector('ngpcraft-player').input() & 16"), 'old binding removed'
        page.keyboard.up('z')
        page.locator('button.full').click()
        page.wait_for_function('!!document.fullscreenElement')
        page.wait_for_function("document.querySelector('ngpcraft-player').shadowRoot.querySelector('.full').textContent === 'Exit fullscreen'")
        page.screenshot(path=str(root/'build'/'player-fullscreen.png'))
        page.locator('button.full').click()
        page.wait_for_function('!document.fullscreenElement')
        page.reload()
        page.wait_for_function("!!document.querySelector('ngpcraft-player').settings")
        assert page.evaluate("document.querySelector('ngpcraft-player').settings.keys.KeyQ === 16")
        assert page.evaluate("document.querySelector('ngpcraft-player').settings.volume === 35")
        assert page.evaluate("document.querySelector('ngpcraft-player').canvas.style.imageRendering === 'auto'")
        assert page.locator('.touch').is_hidden()
        page.locator('button.options').click()
        page.locator('button.defaults').click()
        assert page.evaluate("document.querySelector('ngpcraft-player').settings.keys.KeyZ === 16")
        assert page.locator('.touch').is_visible()
        page.locator('.close-options').click()
        page.goto(f'http://127.0.0.1:{server.server_port}/embed.html?rom=/test.ngc')
        page.wait_for_function("document.querySelector('ngpcraft-player').loaded")
        assert not page.evaluate("document.querySelector('ngpcraft-player').running"), 'URL must wait for user gesture'
        page.locator('button.play').click()
        page.wait_for_timeout(250)
        assert page.evaluate("document.querySelector('ngpcraft-player').running")
        page.evaluate("window.dispatchEvent(new Event('blur'))")
        assert not page.evaluate("document.querySelector('ngpcraft-player').running"), 'blur pauses'
        mobile=browser.new_context(viewport={'width':375,'height':900},has_touch=True,is_mobile=True)
        touch=mobile.new_page()
        touch.goto(f'http://127.0.0.1:{server.server_port}')
        touch.locator('input.rom').set_input_files(str(rom))
        touch.wait_for_function("document.querySelector('ngpcraft-player').loaded")
        touch.locator('button.play').tap()
        touch.wait_for_timeout(2000)
        touch.locator('[data-bit="16"]').tap()
        touch.wait_for_timeout(100)
        assert touch.evaluate("document.querySelector('ngpcraft-player').input() === 0"), 'touch release clears input'
        assert touch.evaluate("document.documentElement.scrollWidth <= innerWidth")
        touch.screenshot(path=str(root/'build'/'player-mobile.png'))
        assert not errors, errors
        print(json.dumps(result))
        browser.close()
finally:
    server.shutdown()
