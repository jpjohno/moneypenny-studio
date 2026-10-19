'use strict';
/* Isolated layout fixtures use production styles and view helpers only.
   They never load workspace.js, the avatar renderer, or an owner endpoint. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const hasWorkspace=fs.existsSync(path.join(root,'workspace.html'));
const canRun=hasWorkspace&&fs.existsSync(chrome)&&Number(process.versions.node.split('.')[0])>=20;
const source=hasWorkspace?fs.readFileSync(path.join(root,'workspace.html'),'utf8'):'';
const styles=[...source.matchAll(/<link rel="stylesheet" href="([^"]+)"/g)].map(match=>match[1]);
const nav=source.match(/<nav aria-label="Workspace navigation">([\s\S]*?)<\/nav>/)?.[0]||'<nav aria-label="Workspace navigation"></nav>';
const fixture=`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><script src="/fixture-preferences.js"></script><script src="/theme-init.js"></script>${styles.map(url=>`<link rel="stylesheet" href="${url}">`).join('')}<script src="/settings-panel.js" defer></script><script src="/companion.js" defer></script><script src="/command-deck.js" defer></script><script src="/scene-layout.js" defer></script><script src="/fixture.js" defer></script></head><body data-hud-theme="stark" class="orbital-view"><aside><div class="brand"><img src="/fixture-logo.svg" alt="JJRVIS"><small>COMMAND CENTRE</small></div>${nav}</aside><main><header><div><p class="eyebrow">JJRVIS / OVERVIEW</p><h1>Your command centre.</h1></div><div class="header-right"><span class="badge">Local fixture</span><details class="workspace-menu"><summary>Workspace</summary><button>Settings</button></details></div></header><div id="content"><section class="presence-hub command-scene" data-display-mode="together" aria-label="Your private assistant and connected world"><header class="presence-heading"><div><p class="eyebrow">PERSONAL OPERATIONS / JJRVIS</p><h2>Your world.<br><em>At your command.</em></h2></div><span class="owner-chip">PRIVATE WORKSPACE</span></header><div class="presence-controls"><button type="button" data-talk-character="moneypenny">Talk to Moneypenny</button><button type="button" data-talk-character="english">Talk to Jarvis</button><button type="button">Colour & appearance</button><label>Presence<select aria-label="Presence"><option>Both together</option><option>Moneypenny</option><option>Jarvis</option></select></label></div><div class="presence-scene"><section class="jarvis-presence"><div class="jarvis-core"><strong>JARVIS</strong></div></section><section class="moneypenny-presence" aria-label="Moneypenny 3D placeholder"><div class="presence-top"><span>MONEYPENNY</span><b>FIXTURE ONLY</b></div><iframe id="moneypenny-presence" title="Empty avatar fixture" src="about:blank"></iframe><div class="presence-footer"><div><button>Wave</button><a href="#customise">Customise Moneypenny ↗</a><button id="launch-companion">Companion view</button></div></div></section><div class="presence-atlas" aria-label="Your interactive world"><section class="command-world-stage"><div class="desk-reactor globe-reactor"><div class="globe-topline"><span>WORLD / DEVICE ATLAS</span><b>DRAG TO EXPLORE</b></div><canvas width="840" height="840" aria-label="Interactive Earth fixture" tabindex="0"></canvas><div class="globe-map" hidden></div><div class="globe-controls"><button aria-label="Zoom in">＋</button><button aria-label="Zoom out">−</button><button>My device</button><button>Map</button><button>World</button><button>Pause motion</button></div><select aria-label="Focus device"><option>Focus a device…</option></select><small class="globe-info">Drag to rotate · scroll to zoom</small><small class="globe-credit">Static Earth imagery</small></div></section></div><section class="command-telemetry"></section><div class="presence-scene-caption"><button>Talk to Moneypenny ↗</button><button class="quiet" aria-label="Connections & access">Connections</button></div></div><div class="presence-status"><div>Connection check fixture</div></div><div id="scene-sources" hidden><section id="source-brief"><h2>Saved tasks</h2><p>Fixture task; no owner data.</p><button id="source-action">Open task</button></section><section id="source-weather"><h2>Weather & sky</h2><p>Fixture content; no forecast is requested.</p></section><section id="source-devices"><h2>Reported devices</h2><p>Fixture content; no connection is made.</p></section></div></section><details class="command-workbench"><summary><span>YOUR WORKBENCH</span><b>Projects, tasks & saved panels</b><i>＋</i></summary><div class="command-workbench-content"></div></details></div></main><section id="assistant-panel" class="assistant-dock"><div class="assistant-intro"><h2>Moneypenny</h2></div><form><textarea id="assistant-input" aria-label="Message"></textarea><button>Ask</button></form><p id="assistant-answer">Fixture conversation.</p></section></body></html>`;
const script=`'use strict';
window.fixtureCalls=[];window.permissionRequests=0;window.sourceActions=0;window.mounted=[];
if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=()=>{permissionRequests++;throw Error('Unexpected capture request');};
window.originalFrame=document.querySelector('#moneypenny-presence');window.originalNavButtons=[...document.querySelectorAll('nav button[data-view]')];
for(const button of originalNavButtons)button.onclick=()=>{fixtureCalls.push(button.dataset.view);for(const item of originalNavButtons)item.classList.toggle('active',item===button);commandNav.update();};
window.commandNav=JJCommandDeck.init({navigate:()=>{throw Error('Original buttons must own navigation');}});
window.commandHud=JJCommandDeck.mount(document.querySelector('.command-telemetry'),{api:()=>{throw Error('Unexpected network request');},navigate:view=>fixtureCalls.push(view),pair:()=>fixtureCalls.push('pair'),connections:()=>fixtureCalls.push('connections')});
commandHud.update({system:{voice:{state:'ready'}},connections:{ai:{state:'ready'}},devices:[{name:'Fixture Mac',kind:'Mac',online:true,last_seen:Date.now()/1000},{name:'Fixture phone',kind:'iPhone',online:false,last_seen:Date.now()/1000-400}]});
window.sourceNodes=Object.fromEntries(['brief','weather','devices'].map(key=>[key,document.querySelector('#source-'+key)]));sourceNodes.brief.querySelector('button').onclick=()=>{sourceActions++;};
window.layout=JJSceneLayout.mount(document.querySelector('.presence-hub'),{mount(key,pane){mounted.push(key);pane.append(sourceNodes[key]);}});
JJCompanion.configure({showAssistant(){document.querySelector('#assistant-panel').classList.add('assistant-overlay');return true;},postToPresence(){},stopSpeaking(){}});
document.querySelector('#launch-companion').onclick=()=>JJCompanion.enter();
window.fixtureReady=true;`;
async function withFixture(run){
 const {chromium}=require('playwright-core'),browser=await chromium.launch({executablePath:chrome,headless:true,args:['--disable-background-networking']});
 const page=await browser.newPage({viewport:{width:1280,height:800}}),errors=[],requests=[];
 page.setDefaultTimeout(5000);page.on('pageerror',error=>errors.push(error.message));
 const assets=new Map();for(const url of styles)assets.set(url,fs.readFileSync(path.join(root,path.basename(url)),'utf8'));
 for(const name of ['theme-init.js','settings-panel.js','command-deck.js','scene-layout.js','companion.js'])assets.set('/'+name,fs.readFileSync(path.join(root,name),'utf8'));
 assets.set('/fixture.js',script);assets.set('/fixture-logo.svg','<svg xmlns="http://www.w3.org/2000/svg" width="142" height="40"><text x="0" y="28" fill="#79d9ec" font-size="27">JJRVIS</text></svg>');
 await page.route('**/*',route=>{
  const url=new URL(route.request().url());if(url.hostname!=='command-scene.test'){requests.push(url.origin);return route.abort();}
  let body=assets.get(url.pathname),contentType=url.pathname.endsWith('.css')?'text/css':url.pathname.endsWith('.svg')?'image/svg+xml':'text/javascript';
  if(url.pathname==='/fixture-preferences.js'){const palette=new URL(route.request().frame().url()).searchParams.get('palette');body=palette?`localStorage.setItem('jjrvis-display-v1',JSON.stringify({appearance:${JSON.stringify(palette)},appearanceChosen:true,motion:false}));`:'localStorage.clear();';}
  if(url.pathname==='/'){body=fixture;contentType='text/html';}
  if(body===undefined){requests.push(url.pathname);return route.fulfill({status:404,body:'Not in fixture'});}
  return route.fulfill({status:200,contentType,headers:{'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self' about:; connect-src 'none'; base-uri 'none'"},body});
 });
 try{await run(page,errors,requests);}finally{await browser.close();}
}
async function load(page,{width=1280,height=800,palette}={}){await page.setViewportSize({width,height});await page.goto('http://command-scene.test/'+(palette?'?palette='+palette:''));await page.waitForFunction(()=>window.fixtureReady);}
test('production styles keep all palette/viewport layouts and right-side navigation within the screen',{skip:!canRun},async()=>withFixture(async(page,errors,requests)=>{
 const failures=[];
 for(const viewport of [{width:1280,height:800},{width:1440,height:900},{width:390,height:844}])for(const palette of ['midnight','sky','pearl','sage','lavender']){
  await load(page,{...viewport,palette});
  const metrics=await page.evaluate(()=>{const rect=selector=>{const r=document.querySelector(selector).getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};};const nav=document.querySelector('aside nav');return {pageWidth:document.documentElement.scrollWidth,navWidth:nav.clientWidth,navScroll:nav.scrollWidth,globe:rect('.globe-reactor canvas'),frame:rect('#moneypenny-presence'),clock:rect('.command-clock'),panel:rect('.command-telemetry'),scene:rect('.command-scene'),appearance:document.documentElement.dataset.appearance,tone:document.documentElement.dataset.appearanceTone,clockValue:document.querySelector('.command-local-time').textContent,ink:getComputedStyle(document.querySelector('.command-local-time')).color,surface:getComputedStyle(document.documentElement).getPropertyValue('--display-surface')};});
  const label=palette+' '+viewport.width+'x'+viewport.height;
  const channels=value=>value.trim().startsWith('#')?(value.trim().length===4?value.trim().slice(1).split('').map(channel=>channel+channel):value.trim().slice(1).match(/../g)).map(channel=>parseInt(channel,16)):(value.match(/[\d.]+/g)||[]).slice(0,3).map(Number);
  const luminance=value=>channels(value).map(channel=>{channel/=255;return channel<=.04045?channel/12.92:((channel+.055)/1.055)**2.4;}).reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);
  const contrast=(Math.max(luminance(metrics.ink),luminance(metrics.surface))+.05)/(Math.min(luminance(metrics.ink),luminance(metrics.surface))+.05);
  if(contrast<4.5)failures.push(label+': telemetry text contrast below 4.5 ('+contrast.toFixed(2)+'; '+metrics.ink+' on '+metrics.surface+')');
  if(metrics.pageWidth>viewport.width+1)failures.push(label+': page horizontal overflow '+metrics.pageWidth);
  if(metrics.navScroll>metrics.navWidth+1)failures.push(label+': navigation horizontal overflow');
  if(viewport.width>760&&metrics.globe.width<570)failures.push(label+': desktop globe too small '+metrics.globe.width);
  if(metrics.panel.bottom>metrics.scene.bottom-70)failures.push(label+': telemetry exceeds reserved scene area '+Math.round(metrics.panel.height)+'px');
  if(metrics.frame.height<200||metrics.frame.width<180)failures.push(label+': avatar placeholder too small');
  if(!/^\d{2}:\d{2}:\d{2}$/.test(metrics.clockValue))failures.push(label+': clock missing');
  if(metrics.appearance!==palette||metrics.tone!==(palette==='midnight'?'dark':'light'))failures.push(label+': saved palette lost');
  const explore=page.locator('aside nav .command-nav-trigger').filter({hasText:'Explore'});await explore.click();
  const menu=await page.locator('aside nav details[open] .command-nav-popover').boundingBox();
  if(!menu||menu.x<0||menu.x+menu.width>viewport.width+1||menu.y<0||menu.y+menu.height>viewport.height)failures.push(label+': Explore disclosure outside viewport '+JSON.stringify(menu));
  await page.keyboard.press('Escape');
  const navStyles=await page.locator('aside nav').evaluate(node=>({overflowX:getComputedStyle(node).overflowX,overflowY:getComputedStyle(node).overflowY,position:getComputedStyle(node).position}));
  if(navStyles.overflowX!=='visible'||navStyles.overflowY!=='visible'||navStyles.position==='fixed')failures.push(label+': legacy scrolling navigation survived');
 }
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);assert.deepEqual(failures,[]);
}));
test('desktop Earth is larger than the preceding production styles and dark is the initial unsaved choice',{skip:!canRun},async()=>withFixture(async(page)=>{
 await load(page);assert.equal(await page.locator('html').getAttribute('data-appearance'),'midnight');
 const current=(await page.locator('.globe-reactor canvas').boundingBox()).width;
 await page.locator('link[href="/command-scene.css"]').evaluate(node=>node.disabled=true);
 const previous=(await page.locator('.globe-reactor canvas').boundingBox()).width;
 assert.ok(current>=570,'Current desktop globe is at least 570px');assert.ok(current>previous,'The globe must actually grow beyond the previous styles ('+current+' vs '+previous+')');
}));
test('drawer keyboard/focus behavior keeps the same mounted sources, buttons, and avatar DOM',{skip:!canRun},async()=>withFixture(async(page,errors)=>{
 await load(page);
 await page.locator('[data-scene-open="brief"]').click();assert.equal(await page.locator('.scene-drawer').isVisible(),true);assert.equal(await page.evaluate(()=>document.activeElement.className),'scene-drawer-close');
 assert.equal(await page.evaluate(()=>document.querySelector('.scene-pane-brief #source-brief')===sourceNodes.brief),true);await page.locator('#source-action').click();assert.equal(await page.evaluate(()=>sourceActions),1);
 await page.evaluate(()=>{const modal=document.createElement('dialog');modal.innerHTML='<button>Modal action</button>';document.body.append(modal);modal.showModal();});await page.keyboard.press('Escape');assert.equal(await page.locator('.scene-drawer').isVisible(),true,'A native modal owns Escape before the drawer');
 await page.keyboard.press('Escape');assert.equal(await page.locator('.scene-drawer').isVisible(),false);assert.equal(await page.evaluate(()=>document.activeElement.dataset.sceneOpen),'brief');
 await page.locator('[data-scene-open="weather"]').click();await page.locator('[data-scene-open="brief"]').click();await page.keyboard.press('Escape');
 assert.deepEqual(await page.evaluate(()=>mounted),['brief','weather']);assert.equal(await page.evaluate(()=>document.querySelector('#moneypenny-presence')===originalFrame),true);
 const summary=page.locator('aside nav summary').filter({hasText:'Work'});await summary.focus();await page.keyboard.press('ArrowDown');assert.equal(await page.evaluate(()=>document.activeElement.dataset.view),'communications');await page.keyboard.press('End');assert.equal(await page.evaluate(()=>document.activeElement.dataset.view),'plan');await page.keyboard.press('Escape');assert.equal(await summary.getAttribute('aria-expanded'),'false');
 await summary.click();await page.locator('aside nav [data-view="junomo"]').click();assert.deepEqual(await page.evaluate(()=>fixtureCalls),['junomo']);assert.equal(await page.evaluate(()=>originalNavButtons.every(button=>document.querySelector('aside nav').contains(button))),true);
 await page.evaluate(()=>{layout.destroy();commandHud.destroy();commandNav.destroy();});assert.equal(await page.locator('.scene-tools').count(),0);assert.equal(await page.locator('aside nav button[data-view]').count(),13);assert.deepEqual(errors,[]);
}));
test('touch controls have usable targets, focus names, and no accidental permission requests',{skip:!canRun},async()=>withFixture(async(page)=>{
 await load(page,{width:390,height:844});
 const targets=await page.locator('aside nav>button,aside nav summary,.scene-tools button,.command-panel-actions button,.presence-controls button,.presence-controls select,.presence-footer button,.presence-footer a').evaluateAll(nodes=>nodes.filter(node=>node.getClientRects().length).map(node=>{const r=node.getBoundingClientRect();return {name:(node.getAttribute('aria-label')||node.textContent).trim().replace(/\s+/g,' '),width:r.width,height:r.height};}));
 assert.ok(targets.every(target=>target.name&&target.width>=44&&target.height>=44),'Primary phone targets must be at least 44px: '+JSON.stringify(targets.filter(target=>target.width<44||target.height<44)));
 for(const key of ['brief','weather','devices']){
  const tool=page.locator('[data-scene-open="'+key+'"]');await tool.scrollIntoViewIfNeeded();
  const hit=await tool.evaluate(button=>{const r=button.getBoundingClientRect(),top=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2),caption=document.querySelector('.presence-scene-caption').getBoundingClientRect();return {reachable:top===button||button.contains(top),blocker:top?.className||top?.tagName,tool:{x:r.x,y:r.y,width:r.width,height:r.height},caption:{x:caption.x,y:caption.y,width:caption.width,height:caption.height}};});
  assert.equal(hit.reachable,true,'Phone '+key+' tool must receive a tap: '+JSON.stringify(hit));
  await tool.click();assert.equal(await page.locator('.scene-drawer').isVisible(),true);await page.keyboard.press('Escape');
 }
 await page.locator('[data-command-action="pair"]').click();assert.deepEqual(await page.evaluate(()=>fixtureCalls),['pair']);
 assert.equal(await page.evaluate(()=>permissionRequests),0);
}));
test('companion mode still fills desktop/phone and removes the dashboard instruments',{skip:!canRun},async()=>withFixture(async(page,errors)=>{
 const failures=[];
 for(const viewport of [{width:1280,height:800},{width:390,height:844}]){
  await load(page,viewport);await page.locator('#launch-companion').click();
  const bounds=await page.locator('.presence-hub').boundingBox();assert.equal(bounds.x,0);assert.equal(bounds.y,0);assert.equal(bounds.width,viewport.width);assert.equal(bounds.height,viewport.height);
  assert.equal(await page.evaluate(()=>document.querySelector('#moneypenny-presence')===originalFrame),true);
  for(const selector of ['.command-telemetry','.scene-tools','.scene-depth','.presence-atlas'])if(await page.locator(selector).isVisible())failures.push(viewport.width+': '+selector+' remains over fullscreen avatar');
  await page.keyboard.press('Escape');assert.equal(await page.locator('body').getAttribute('data-companion'),'workspace');
 }
 assert.deepEqual(errors,[]);assert.deepEqual(failures,[]);
}));
