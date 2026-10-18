'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
test('restoring from the icon or Hide retains dashboard focus, and dialogs own Escape',()=>{
 const listeners=new Map(),inertPanel={inert:false},elements=[],storage=new Map();let dialog=false;
 const document={body:{dataset:{},append(...nodes){elements.push(...nodes);}},querySelector(selector){return selector==='.presence-hub'?{}:selector==='#assistant-input'?input:selector==='dialog[open]'&&dialog?{}:null;},querySelectorAll(){return [inertPanel];},addEventListener(type,callback){listeners.set(type,callback);}};
 function node(){return {style:{},className:'',isConnected:true,hidden:false,buttons:new Map(),setAttribute(){},addEventListener(){},querySelector(selector){if(!this.buttons.has(selector))this.buttons.set(selector,node());return this.buttons.get(selector);},closest(){return this.className.startsWith('jj-companion')?this:null;},focus(){document.activeElement=this;}};}
 const input=node(),launch=node();document.activeElement=launch;document.createElement=node;
 const window={innerWidth:390,innerHeight:844,addEventListener(){},dispatchEvent(){}};
 const context={window,document,localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},CustomEvent:function(){}};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'companion.js'),'utf8'),context);
 const c=window.JJCompanion;c.configure({showAssistant:()=>true});c.enter();assert.equal(inertPanel.inert,true);c.shrink();c.enter();c.exit();assert.equal(document.activeElement,launch);
 c.enter();c.hide();c.enter();c.exit();assert.equal(document.activeElement,launch);assert.equal(inertPanel.inert,false);
 c.enter();dialog=true;listeners.get('keydown')({key:'Escape',preventDefault(){assert.fail('Native dialog owns Escape');}});assert.equal(c.state().mode,'open');
 dialog=false;let prevented=false;listeners.get('keydown')({key:'Escape',preventDefault(){prevented=true;}});assert.equal(prevented,true);assert.equal(c.state().mode,'workspace');assert.equal(document.activeElement,launch);
});
test('companion preserves the mounted iframe, handles focus, drag and phone layout, and never grants microphone access',{skip:!fs.existsSync(chrome)||Number(process.versions.node.split('.')[0])<20},async()=>{
 const {chromium}=require('playwright-core');
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--disable-background-networking']});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  const html='<!doctype html><html data-appearance="sky"><head><link rel="stylesheet" href="/workspace.css"><link rel="stylesheet" href="/settings-panel.css"><link rel="stylesheet" href="/companion.css"><script src="/companion.js" defer></script><script src="/fixture.js" defer></script></head><body data-hud-theme="stark"><aside><button id="launch">Open Moneypenny</button></aside><main><header><button>Dashboard action</button></header><div id="content"><section class="presence-hub"><header class="presence-heading"><h2>Your world</h2></header><div class="presence-scene"><section class="moneypenny-presence"><iframe id="moneypenny-presence" title="Fixture avatar" src="about:blank"></iframe></section><section class="presence-atlas">Globe fixture</section></div><div class="presence-scene-caption">Caption</div></section><article id="other-panel"><button>Other action</button></article><article id="already-inert" inert>Preserve this state</article></div><footer><a href="/">Footer</a></footer></main><section id="assistant-panel" class="assistant-dock"><div class="assistant-intro"><div><h2>Moneypenny</h2></div></div><form id="assistant-form"><textarea id="assistant-input" aria-label="Message"></textarea><button id="assistant-submit">Ask</button></form><div class="assistant-voice"><button>Speak</button></div><p id="assistant-answer">Your conversation stays here.</p></section><div class="assistant-launch"><button>Chat</button></div></body></html>';
  const fixture='window.messages=[];window.stops=0;window.micRequests=0;window.originalFrame=document.querySelector("#moneypenny-presence");navigator.mediaDevices={getUserMedia(){window.micRequests++;throw Error("Unexpected microphone request")}};window.JJCompanion.configure({showAssistant(){document.querySelector("#assistant-panel").classList.add("assistant-overlay");return true},postToPresence:m=>messages.push(m),stopSpeaking:()=>{window.stops++},navigate:()=>{throw Error("Existing presence must not navigate")}});document.querySelector("#launch").onclick=()=>JJCompanion.enter();window.open=(url,name,features)=>{window.popup={url,name,features};return {}};';
  const assets=new Map(['/workspace.css','/settings-panel.css','/companion.css','/companion.js'].map(url=>[url,fs.readFileSync(path.join(root,url.slice(1)),'utf8')]));assets.set('/fixture.js',fixture);
  await page.route('http://companion.test/**',route=>{const url=new URL(route.request().url()),asset=assets.get(url.pathname);return route.fulfill({status:200,contentType:asset?(url.pathname.endsWith('.js')?'text/javascript':'text/css'):'text/html',headers:{'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; frame-src 'self' about:; img-src 'self' data:; base-uri 'none'"},body:asset||html});});
  await page.goto('http://companion.test/');
  assert.equal(await page.evaluate(()=>JJCompanion.state().mode),'workspace');
  await page.locator('#launch').click();
  assert.equal(await page.locator('body').getAttribute('data-companion'),'open');
  assert.equal(await page.evaluate(()=>originalFrame===document.querySelector('#moneypenny-presence')),true);
  assert.equal(await page.evaluate(()=>document.activeElement.id),'assistant-input');
  assert.deepEqual(await page.evaluate(()=>['aside','main>header','#other-panel','#already-inert'].map(selector=>document.querySelector(selector).inert)),[true,true,true,true]);
  assert.equal(await page.locator('main>header').evaluate(element=>getComputedStyle(element).display),'none');
  const desktop=await page.locator('.presence-hub').boundingBox();assert.equal(desktop.x,0);assert.equal(desktop.y,0);assert.equal(desktop.width,1280);assert.equal(desktop.height,900);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight),'Fullscreen removes the old dashboard gap');
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('body').getAttribute('data-companion'),'workspace');
  assert.equal(await page.evaluate(()=>document.activeElement.id),'launch');
  assert.equal(await page.locator('#other-panel').evaluate(element=>element.inert),false);assert.equal(await page.locator('#already-inert').evaluate(element=>element.inert),true);
  await page.locator('#launch').click();await page.locator('[data-companion-action="shrink"]').click();
  assert.equal(await page.locator('body').getAttribute('data-companion'),'icon');assert.equal(await page.evaluate(()=>messages.at(-1).visible),false);
  const icon=page.locator('.jj-companion-icon');await icon.focus();const before=await page.evaluate(()=>JJCompanion.state().position);await page.keyboard.press('ArrowLeft');const after=await page.evaluate(()=>JJCompanion.state().position);assert.equal(after.x,before.x-10);
  await page.keyboard.press('Shift+ArrowDown');assert.ok((await page.evaluate(()=>JJCompanion.state().position)).y>=after.y);
  const bounds=await icon.boundingBox();await page.mouse.move(bounds.x+40,bounds.y+35);await page.mouse.down();await page.mouse.move(-80,-80,{steps:4});await page.mouse.up();
  assert.deepEqual(await page.evaluate(()=>JJCompanion.state().position),{x:8,y:8});assert.equal(await page.evaluate(()=>JJCompanion.state().mode),'icon','Drag never opens the companion');
  assert.deepEqual(await page.evaluate(()=>Object.keys(localStorage)),['jjrvis-companion-position-v1'],'Only icon position persists');
  await icon.click();await page.locator('[data-companion-action="hide"]').click();assert.equal(await page.locator('body').getAttribute('data-companion-hidden'),'true');assert.equal(await page.locator('.jj-companion-restore').isVisible(),true);assert.equal(await page.evaluate(()=>messages.at(-1).visible),false);
  await page.locator('.jj-companion-restore').click();assert.equal(await page.evaluate(()=>JJCompanion.state().mode),'open');assert.equal(await page.evaluate(()=>originalFrame===document.querySelector('#moneypenny-presence')),true);
  await page.locator('[data-companion-action="stop"]').click();assert.equal(await page.evaluate(()=>stops),1);assert.equal(await page.evaluate(()=>micRequests),0);
  await page.locator('[data-companion-action="popup"]').click();const popup=await page.evaluate(()=>window.popup);assert.equal(popup.url,'/workspace?companion=1');assert.match(popup.features,/width=420,height=650/);
  await page.setViewportSize({width:390,height:844});
  const mobile=await page.locator('.presence-hub').boundingBox(),chat=await page.locator('#assistant-panel').boundingBox(),stage=await page.locator('#moneypenny-presence').boundingBox();
  assert.equal(mobile.height,844);assert.equal(mobile.width,390);assert.ok(stage.height>350&&stage.width===390);assert.ok(chat.x>=0&&chat.x+chat.width<=390&&chat.y+chat.height<=844);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await icon.evaluate(element=>getComputedStyle(element).transitionDuration),'0s');
  await page.keyboard.press('Escape');await page.reload();assert.equal(await page.evaluate(()=>JJCompanion.state().mode),'workspace');assert.deepEqual(await page.evaluate(()=>JJCompanion.state().position),{x:8,y:8});assert.deepEqual(errors,[]);
 }finally{await browser.close();}
});
