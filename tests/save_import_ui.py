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
        for document,host in [('index.html','ngpcraft-player'),('integrated.html?rom=/test.ngp','ngpcraft-embed')]:
            page=browser.new_page(viewport={'width':1100,'height':850})
            page.goto(f'http://127.0.0.1:{server.server_port}/'+document)
            if host=='ngpcraft-player':page.locator('.rom').set_input_files(str(rom))
            else:page.locator('.start').click()
            page.wait_for_function('h=>document.querySelector(h)?.loaded',arg=host)
            page.locator('.full').click()
            page.locator('.options').click()
            if host=='ngpcraft-embed':page.locator('[data-tab="saves"]').click()
            assert page.locator('.import-save').is_visible()
            with page.expect_file_chooser() as picker:page.locator('.import-save').click()
            data=page.evaluate('h=>Array.from(document.querySelector(h).saveBytes())',host)
            picker.value.set_files({'name':'roundtrip.ngpsav','mimeType':'application/octet-stream','buffer':bytes(data)})
            page.wait_for_function("h=>document.querySelector(h).shadowRoot.querySelector('.status').textContent.includes('Save imported')",arg=host)
            assert page.evaluate('h=>Array.from(document.querySelector(h).saveBytes())',host)==data
            assert page.locator('.import-save').is_visible()
            print('PASS:',host,'fullscreen import picker and save roundtrip')
            page.close()
        browser.close()
finally:server.shutdown()
