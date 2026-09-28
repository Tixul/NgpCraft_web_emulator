"""Real Chromium touch events: multitouch, sliding, maximize and mobile sizing."""
import functools,http.server,json,sys,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path(__file__).resolve().parents[1]
out=Path(__file__).resolve().parents[1]/'build'
if len(sys.argv)>2:out=out/'baseline'
out.mkdir(parents=True,exist_ok=True)
rom=Path(sys.argv[1]);checks=[]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  if self.path=='/test.ngp':
   data=rom.read_bytes();self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  else:super().do_GET()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root/'public')))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(channel='msedge',headless=True)
  context=browser.new_context(viewport={'width':375,'height':812},has_touch=True,is_mobile=True)
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(f'http://127.0.0.1:{server.server_port}/integrated.html?rom=/test.ngp')
  page.locator('.start').tap();page.wait_for_function("document.querySelector('ngpcraft-embed').running")
  page.wait_for_timeout(2000)
  def check(name,value):checks.append({'test':name,'pass':bool(value)})
  def point(selector,id=1,dx=0):
   b=page.locator(selector).bounding_box();return {'x':b['x']+b['width']/2+dx,'y':b['y']+b['height']/2,'id':id}
  def mask():return page.evaluate("document.querySelector('ngpcraft-embed').input()")
  for name in ['.dpad [data-bit="4"]','.actions [data-bit="16"]']:
   b=page.locator(name).bounding_box();check('inline target >=44px '+name,min(b['width'],b['height'])>=44)
  page.locator('.full').tap()
  canvas=page.locator('canvas').bounding_box();x=canvas['x']+canvas['width']/2;y=canvas['y']+canvas['height']*.25
  page.touchscreen.tap(x,y);page.wait_for_timeout(50);page.touchscreen.tap(x,y)
  check('double tap canvas keeps maximized',page.evaluate("document.querySelector('ngpcraft-embed').hasAttribute('expanded')"))
  page.evaluate("document.querySelector('ngpcraft-embed').setExpanded(true)")
  cdp=context.new_cdp_session(page)
  def touches(kind,points):
   cdp.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':points})
   # Chromium may coalesce pointermove until the next animation frame.
   page.wait_for_timeout(40)
  a=point('[data-bit="16"]',1);left=point('[data-bit="4"]',2);right=point('[data-bit="8"]',2)
  touches('touchStart',[a,left]);check('A plus left',mask()==20)
  touches('touchMove',[a,right]);check('slide left to right while holding A',mask()==24)
  touches('touchEnd',[right]);check('release direction keeps A',mask()==16)
  touches('touchEnd',[]);check('release all clears',mask()==0)
  up=point('[data-bit="1"]',2);diagonal={**right,'y':up['y']}
  touches('touchStart',[left]);touches('touchMove',[diagonal]);check('slide to up-right diagonal',mask()==9)
  touches('touchMove',[{'x':200,'y':20,'id':2}]);check('leaving pad releases direction',mask()==0)
  touches('touchEnd',[])
  b=point('[data-bit="32"]',1)
  touches('touchStart',[a]);touches('touchMove',[b]);check('slide A to B',mask()==32)
  touches('touchCancel',[])
  # Two fingers on A: lifting one must not clear the held-button indicator.
  a2=point('[data-bit="16"]',2,dx=5)
  touches('touchStart',[a,a2]);touches('touchEnd',[a]);check('remaining finger keeps pressed styling',page.locator('[data-bit="16"]').get_attribute('aria-pressed')=='true')
  touches('touchCancel',[]);check('cancel clears',mask()==0)
  touches('touchStart',[point('[data-bit="16"]',1)])
  page.evaluate("window.dispatchEvent(new Event('blur'))")
  check('blur clears controls',mask()==0)
  check('blur keeps maximized',page.evaluate("document.querySelector('ngpcraft-embed').hasAttribute('expanded')"))
  touches('touchCancel',[])
  for width,height in [(375,667),(812,375),(320,568)]:
   page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(100)
   check(f'resize keeps maximized {width}',page.evaluate("document.querySelector('ngpcraft-embed').hasAttribute('expanded')"))
   check(f'no horizontal overflow {width}',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
   for selector in ['[data-bit="4"]','[data-bit="8"]','[data-bit="16"]','[data-bit="32"]','[data-bit="64"]','.quick-menu']:
    b=page.locator(selector).bounding_box();check(f'visible target {width} {selector}',b and b['x']>=0 and b['y']>=0 and b['x']+b['width']<=width+1 and b['y']+b['height']<=height+1)
   page.screenshot(path=str(out/f'mobile-{width}x{height}.png'))
  # A mouse double-click still provides the desktop shortcut.
  desktop=browser.new_page(viewport={'width':1100,'height':850})
  desktop.goto(f'http://127.0.0.1:{server.server_port}/integrated.html?rom=/test.ngp')
  desktop.locator('.start').click();desktop.wait_for_function("document.querySelector('ngpcraft-embed').running")
  desktop.locator('canvas').dblclick()
  check('mouse double click maximizes',desktop.evaluate("document.querySelector('ngpcraft-embed').hasAttribute('expanded')"))
  desktop.locator('canvas').dblclick()
  check('mouse double click restores',desktop.evaluate("!document.querySelector('ngpcraft-embed').hasAttribute('expanded')"))
  check('no JavaScript errors',not errors)
  result={'checks':checks,'errors':errors}
  (out/'mobile-touch-results.json').write_text(json.dumps(result,indent=2))
  print(json.dumps({'passed':sum(c['pass'] for c in checks),'total':len(checks),'failed':[c['test'] for c in checks if not c['pass']],'errors':errors}));browser.close()
finally:server.shutdown()
assert all(c['pass'] for c in checks),[c['test'] for c in checks if not c['pass']]
