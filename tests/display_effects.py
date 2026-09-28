"""GPU effects and unobtrusive mobile fullscreen controls, with a supplied ROM."""
import functools,http.server,json,sys,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build';OUT.mkdir(exist_ok=True)
ROM=Path(sys.argv[1]);results=[]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  if self.path=='/test.ngp':
   data=ROM.read_bytes();self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  else:super().do_GET()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'public')))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='msedge',headless=True)
  context=browser.new_context(viewport={'width':812,'height':375},has_touch=True,is_mobile=True)
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def check(name,value):
   results.append({'test':name,'pass':bool(value)})
   assert value,name
  def state(js):return page.evaluate('()=>{const p=document.querySelector("ngpcraft-embed");'+js+'}')
  page.goto(f'http://127.0.0.1:{server.server_port}/integrated.html?rom=/test.ngp')
  page.locator('.start').tap();page.wait_for_function("document.querySelector('ngpcraft-embed').running")
  check('effects off by default',state("return !p.effects&&p.settings.effect==='off'"))
  # A reproducible high-contrast image makes orientation and GPU output observable.
  state('''p.pause();for(let y=0;y<152;y++)for(let x=0;x<160;x++){const i=(y*160+x)*4;p.frame.data.set(y<76?[220,80+x,40,255]:[30,80,220,255],i);}p.context.putImageData(p.frame,0,0);window.raw=p.captureFrame().toDataURL();''')
  page.locator('.full').tap()
  check('toolbar hidden in mobile maximize',not page.locator('#player-toolbar').is_visible())
  check('discreet menu is accessible',page.locator('.quick-menu').is_visible())
  check('landscape image recovers full height',page.locator('.game-screen').bounding_box()['height']>=374)
  page.locator('.quick-menu').tap()
  check('menu pauses game',state('return !p.running'))
  check('commands appear at the top',page.locator('#player-toolbar').bounding_box()['y']<100)
  page.locator('.options').tap()
  check('settings close popup',not state("return p.hasAttribute('menu-open')"))
  hashes={}
  for mode in ['lcd','crt']:
   page.locator('.effect').select_option(mode)
   page.wait_for_function("document.querySelector('ngpcraft-embed').effects?.canvas.width>0")
   data=state('''const e=p.effects,g=e.gl,a=new Uint8Array(e.canvas.width*e.canvas.height*4);g.readPixels(0,0,e.canvas.width,e.canvas.height,g.RGBA,g.UNSIGNED_BYTE,a);
    const index=(Math.floor(e.canvas.height*.75)*e.canvas.width+Math.floor(e.canvas.width*.5))*4;
    return {effect:p.settings.effect,url:e.canvas.toDataURL(),error:g.getError(),upper:Array.from(a.slice(index,index+4)),width:e.canvas.width,height:e.canvas.height,raw:p.captureFrame().toDataURL()};''')
   check(mode+' compiles and draws',data['effect']==mode and data['error']==0 and data['upper'][0]>data['upper'][2])
   check(mode+' preserves raw capture',data['raw']==state('return window.raw'))
   check(mode+' bounds GPU resolution',data['width']<=640 and data['height']<=608)
   hashes[mode]=data['url']
   page.locator('.close-options').tap();page.screenshot(path=str(OUT/f'effect-{mode}-landscape.png'))
   page.locator('.quick-menu').tap();page.locator('.options').tap()
  check('LCD and CRT render differently',hashes['lcd']!=hashes['crt'])
  page.locator('.close-options').tap();page.locator('.quick-menu').tap();page.locator('.play').tap()
  check('Play dismisses menu',not state("return p.hasAttribute('menu-open')"))
  page.wait_for_function("document.querySelector('ngpcraft-embed').running")
  page.locator('.quick-menu').tap();page.locator('.quick-menu').tap()
  page.wait_for_function("document.querySelector('ngpcraft-embed').running")
  check('closing menu resumes play',state('return p.running'))
  page.set_viewport_size({'width':375,'height':812})
  check('rotation retains maximize',state("return p.hasAttribute('expanded')"))
  check('portrait keeps touch controls accessible',page.locator('[data-bit="16"]').bounding_box()['y']<812)
  page.locator('.quick-menu').tap();page.locator('.options').tap()
  page.locator('.show-touch').uncheck();page.locator('.close-options').tap()
  check('portrait without touch uses full height',page.locator('.game-screen').bounding_box()['height']>=811)
  page.reload();page.wait_for_selector('ngpcraft-embed')
  check('effect persists across reload',state("return p.settings.effect==='crt'&&!!p.effects"))
  # GPU loss must retain a usable original display and not stop emulation.
  state("p.effects.gl.getExtension('WEBGL_lose_context').loseContext()")
  page.wait_for_function("document.querySelector('ngpcraft-embed').settings.effect==='off'")
  check('context loss falls back to original',state('return !p.effects'))
  check('no JavaScript errors',not errors)
  # Environments without WebGL must still load/play, even with a saved effect.
  fallback=browser.new_context()
  fallback.add_init_script("localStorage.setItem('ngpcraft-player-settings-v1',JSON.stringify({effect:'lcd'}));const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(t,...args){return t==='webgl'?null:get.call(this,t,...args)}")
  f=fallback.new_page();f.goto(f'http://127.0.0.1:{server.server_port}/integrated.html?rom=/test.ngp');f.locator('.start').click();f.wait_for_function("document.querySelector('ngpcraft-embed').running")
  check('no WebGL still plays',f.evaluate("document.querySelector('ngpcraft-embed').settings.effect==='off'"))
  (OUT/'display-effects-results.json').write_text(json.dumps(results,indent=2));print(f'PASS: {len(results)} effects/mobile menu checks');browser.close()
finally:server.shutdown()
