'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'settings-panel.js'),'utf8');
function harness(saved,reduce=false){
 const storage=new Map(saved===undefined?[]:[['jjrvis-display-v1',JSON.stringify(saved)]]),events=[];
 const document={documentElement:{dataset:{},classList:{toggle(name,on){this[name]=on;}}}};
 const context={document,localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},window:{matchMedia:()=>({matches:reduce,addEventListener(){}}),dispatchEvent:event=>events.push(event)},CustomEvent:function(type,options){this.type=type;this.detail=options.detail;}};
 vm.createContext(context);vm.runInContext(source,context);return {settings:context.window.JJSettings,document,events,storage};
}
test('Sky replaces the old implicit default while an explicit Midnight choice survives',()=>{
 assert.equal(harness().document.documentElement.dataset.appearance,'sky');
 assert.equal(harness({appearance:'midnight',density:'compact'}).settings.preferences().appearance,'sky');
 assert.equal(harness({appearance:'midnight',appearanceChosen:true}).settings.preferences().appearance,'midnight');
 assert.equal(harness({appearance:'slate'}).settings.preferences().appearance,'midnight');
});
test('palette and presence choices persist and dispatch without changing voice volume',()=>{
 const h=harness({volume:.45});
 assert.equal(h.settings.setAppearance('lavender'),true);
 assert.equal(h.settings.setPresence('jarvis'),true);
 assert.equal(h.document.documentElement.dataset.presenceMode,'jarvis');
 assert.equal(h.settings.preferences().volume,.45);
 assert.equal(h.events.at(-1).detail.presence,'jarvis');
 assert.equal(JSON.parse(h.storage.get('jjrvis-display-v1')).appearanceChosen,true);
 assert.equal(h.settings.setPresence('unknown'),false);
 assert.equal(h.settings.setAppearance('<script>'),false);
 assert.equal(h.settings.preferences().presence,'jarvis');
});
test('device reduced-motion overrides animation while keeping the saved choice',()=>{
 const h=harness({motion:true,motionChosen:true},true);
 h.settings.setPresence('moneypenny');
 assert.equal(h.document.documentElement.classList['jj-reduced-motion'],true);
 assert.equal(h.settings.preferences().motion,true);
 assert.equal(h.events.at(-1).detail.effectiveMotion,false);
});

const chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
test('light palettes, native keyboard choices and reduced motion work in the actual CSS',{skip:!fs.existsSync(chrome)||Number(process.versions.node.split('.')[0])<20},async()=>{
 const {chromium}=require('playwright-core');
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--disable-background-networking']});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 const weather=`<section class="sky-observatory"><div class="sky-art" data-night="true"></div><div class="sky-content"><div class="sky-heading"><h2>Weather & sky</h2></div><p class="sky-place">Forecast test place</p><div class="sky-current"><strong>11<span>°C</span></strong><div><b>Light drizzle</b><span>Feels like 10°</span></div></div><p data-sky-status>Forecast test status</p><small class="sky-disclosure">Sky illustration <a href="/">Weather source</a></small><details><summary>Change weather location</summary><form class="sky-place-form"><input placeholder="Town or city"><button>Find town</button></form></details></div></section>`;
 const html=`<!doctype html><html><head><link rel="stylesheet" href="/workspace.css"><link rel="stylesheet" href="/settings-panel.css"><link rel="stylesheet" href="/lifestyle.css"><link rel="stylesheet" href="/fixture.css"><script src="/settings-panel.js" defer></script></head><body data-hud-theme="stark" class="orbital-view"><aside><nav><button class="active"><span>Overview</span></button><button>Rooms</button></nav></aside><main><section class="presence-hub"><header class="presence-heading"><h2>Your world. <em>In good hands.</em></h2><span class="owner-chip">PRIVATE OWNER WORKSPACE</span></header><div class="presence-scene-caption"><button>Speak with me</button></div></section><article class="panel"><h3>Next actions</h3><p>Choose what matters today.</p></article><div class="hud-desk"><article class="hud-window"><div class="hud-data"><p>Connected devices</p></div></article></div><div class="motion-test">Motion sample</div>${weather}</main></body></html>`;
 const assets=new Map([['/workspace.css',fs.readFileSync(path.join(root,'workspace.css'),'utf8')],['/settings-panel.css',fs.readFileSync(path.join(root,'settings-panel.css'),'utf8')],['/lifestyle.css',fs.readFileSync(path.join(root,'lifestyle.css'),'utf8')],['/settings-panel.js',source],['/fixture.css','@keyframes sample-motion{to{opacity:.7}}.motion-test{animation:sample-motion 1s infinite}']]);
 try{
  await page.route('http://display.test/**',route=>{
   const pathname=new URL(route.request().url()).pathname,asset=assets.get(pathname);
   return route.fulfill({status:200,contentType:asset?(pathname.endsWith('.js')?'text/javascript':'text/css'):'text/html',headers:{'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'none'"},body:asset||html});
  });
  await page.goto('http://display.test/');
  assert.equal(await page.locator('html').getAttribute('data-appearance'),'sky');
  await page.evaluate(()=>window.JJSettings.open({api:async()=>({devices:[]})}));
  assert.equal(await page.locator('[data-palette]').count(),5);
  const previews=await page.locator('.palette-preview').evaluateAll(elements=>elements.map(element=>({background:getComputedStyle(element).backgroundColor,accent:getComputedStyle(element.querySelector('i:nth-child(2)')).backgroundColor,height:element.getBoundingClientRect().height})));
  assert.equal(new Set(previews.map(preview=>preview.background)).size,5,'Every swatch must show its own background under production CSP');
  assert.equal(new Set(previews.map(preview=>preview.accent)).size,5,'Every swatch must show its own accent under production CSP');
  assert.ok(previews.every(preview=>preview.height>=40&&preview.background!=='rgba(0, 0, 0, 0)'), 'Preview artwork must be visible');
  assert.equal(await page.locator('[data-palette][style]').count(),0,'Palette previews cannot depend on CSP-blocked inline styles');
  const colors=[];
  for(const palette of ['sky','pearl','sage','lavender']){
   await page.locator('[data-display="appearance"]').selectOption(palette);
   const styles=await page.evaluate(()=>{
    const rgb=value=>(value.match(/[\d.]+/g)||[]).slice(0,3).map(Number);
    const luminance=value=>rgb(value).map(channel=>{channel/=255;return channel<=.04045?channel/12.92:((channel+.055)/1.055)**2.4;}).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);
    const samples=['body','aside','.panel','.presence-hub','.hud-window','.jj-settings','.settings-tabs','.settings-body select','.settings-body .settings-palette'];
    const rows=samples.map(selector=>{const style=getComputedStyle(document.querySelector(selector));return {selector,background:style.backgroundColor,color:style.color,lightness:luminance(style.backgroundColor),contrast:(Math.max(luminance(style.backgroundColor),luminance(style.color))+.05)/(Math.min(luminance(style.backgroundColor),luminance(style.color))+.05)};});
    return rows;
   });
   for(const sample of styles){assert.ok(sample.lightness>.65,palette+' should provide a light '+sample.selector);assert.ok(sample.contrast>=4.5,palette+' needs readable '+sample.selector+' ('+sample.contrast+')');}
   colors.push(styles[0].background);
   const chip=await page.locator('.owner-chip').evaluate(element=>({color:getComputedStyle(element).color,ink:getComputedStyle(document.querySelector('.panel h3')).color,size:getComputedStyle(element).fontSize}));
   assert.equal(chip.size,'10px');
   assert.equal(chip.color,chip.ink,'Owner label uses the same strong ink as the main headings');
   for(const selector of ['.sky-current>strong','.sky-place','.sky-disclosure','.sky-content [data-sky-status]','.sky-content summary','.sky-disclosure a']){
    assert.equal(await page.locator(selector).evaluate(element=>getComputedStyle(element).color),'rgb(245, 250, 255)',palette+' must keep light weather copy on its illustration: '+selector);
   }
   const field=await page.locator('.sky-place-form input').evaluate(element=>getComputedStyle(element).color);
   assert.equal(field,chip.ink,'Weather form fields retain dark readable input text');
  }
  assert.equal(new Set(colors).size,4,'The light palettes have distinct backgrounds');
  await page.locator('[data-palette="pearl"]').focus();await page.keyboard.press('Space');
  assert.equal(await page.locator('html').getAttribute('data-appearance'),'pearl');
  assert.equal(await page.locator('[data-palette="pearl"]').getAttribute('aria-pressed'),'true');
  await page.locator('[data-display="presence"]').selectOption('moneypenny');
  assert.equal(await page.locator('html').getAttribute('data-presence-mode'),'moneypenny');
  await page.locator('[data-section="appearance"]').focus();await page.keyboard.press('ArrowDown');
  assert.equal(await page.locator('[data-section="panels"]').getAttribute('aria-selected'),'true');
  await page.keyboard.press('Home');
  assert.equal(await page.locator('[data-section="appearance"]').getAttribute('aria-selected'),'true');
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.waitForFunction(()=>document.documentElement.classList.contains('jj-reduced-motion'));
  assert.equal(await page.locator('.motion-test').evaluate(el=>getComputedStyle(el).animationName),'none');
 }finally{await browser.close();}
});
