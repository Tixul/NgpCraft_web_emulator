"""Compact embedding: delayed boot, capture, maximize, options and cleanup."""
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
    def do_GET(self):
        if self.path=='/test.ngp':
            data=rom.read_bytes();self.send_response(200)
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        else: super().do_GET()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root/'public')))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1100,'height':850})
        errors=[];requests=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url))
        page.goto(f'http://127.0.0.1:{server.server_port}/integrated.html?rom=/test.ngp&title=NgpCraft')
        page.wait_for_selector('ngpcraft-embed')
        assert not any('/test.ngp'==x.split(f':{server.server_port}')[-1] or '.wasm' in x for x in requests), 'no ROM/core before click'
        box=page.locator('#game').bounding_box()
        assert abs(box['width']/box['height']-160/152)<.01
        page.locator('.start').click()
        page.wait_for_function("document.querySelector('ngpcraft-embed').running")
        page.wait_for_timeout(2000)
        assert page.locator('.status').is_hidden(), 'ROM title must not cover gameplay'
        assert page.evaluate("document.querySelector('ngpcraft-embed').audio.state==='running'")
        page.locator('.capture').click()
        page.wait_for_selector('#preview canvas')
        assert page.locator('#preview canvas').get_attribute('width')=='160'
        assert page.locator('#preview canvas').get_attribute('height')=='152'
        page.screenshot(path=str(root/'build/integrated-desktop.png'))
        page.locator('.options').click()
        assert not page.evaluate("document.querySelector('ngpcraft-embed').running")
        assert page.locator('.settings').is_visible()
        page.locator('.close-options').click()
        page.locator('.full').click()
        assert page.evaluate("document.querySelector('ngpcraft-embed').hasAttribute('expanded')")
        assert page.evaluate("document.documentElement.style.overflow==='hidden'")
        # Capture is native and independent of the CSS scale, while paused.
        page.evaluate("window.before=document.querySelector('ngpcraft-embed').captureFrame().toDataURL()")
        page.locator('.capture').click()
        assert page.evaluate("document.querySelector('#preview canvas').toDataURL()===window.before")
        page.keyboard.press('Escape')
        assert page.evaluate("!document.querySelector('ngpcraft-embed').hasAttribute('expanded')")
        assert page.evaluate("document.documentElement.style.overflow!== 'hidden'")
        page.locator('.play').click()
        page.keyboard.down('z')
        assert page.evaluate("document.querySelector('ngpcraft-embed').input() & 16")
        page.keyboard.up('z')
        page.locator('.full').click()
        page.evaluate("document.querySelector('ngpcraft-embed').remove()")
        assert page.evaluate("document.documentElement.style.overflow!=='hidden'")
        # Mobile layout; no assumed native Fullscreen API.
        mobile=browser.new_context(viewport={'width':375,'height':812},has_touch=True,is_mobile=True)
        touch=mobile.new_page()
        touch.on('pageerror',lambda e:errors.append(str(e)))
        touch.goto(f'http://127.0.0.1:{server.server_port}/integrated.html?rom=/test.ngp')
        touch.locator('.start').tap()
        touch.wait_for_function("document.querySelector('ngpcraft-embed').running")
        assert touch.locator('.touch').is_visible()
        touch.locator('.full').tap()
        assert touch.evaluate("document.querySelector('ngpcraft-embed').hasAttribute('expanded')")
        touch.wait_for_timeout(1000)
        touch.screenshot(path=str(root/'build/integrated-mobile.png'))
        touch.locator('.options').tap()
        for tab in ['general','keys','saves']:
            touch.locator(f'[data-tab="{tab}"]').tap()
            for selector in ['.close-options','.back-game']:
                button=touch.locator(selector).bounding_box()
                assert button and button['y']>=0 and button['y']+button['height']<=812
        touch.locator('.close-options').tap()
        touch.locator('.full').tap()
        assert touch.evaluate('document.documentElement.scrollWidth<=innerWidth')
        # Standalone compact iframe document: default capture downloads a PNG.
        page.goto(f'http://127.0.0.1:{server.server_port}/compact.html?rom=/test.ngp')
        page.locator('.start').click()
        page.wait_for_function("document.querySelector('ngpcraft-embed').running")
        with page.expect_download() as shot:
            page.locator('.capture').click()
        assert shot.value.suggested_filename=='ngpcraft-capture.png'
        assert not errors,errors
        print('PASS: deferred ROM/WASM, compact layout, audio/play, native capture, options, CSS maximize/Escape, input, scroll cleanup, mobile')
        browser.close()
finally: server.shutdown()
