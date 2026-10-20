'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../workspace.js'),'utf8');
const start=source.indexOf(' form.onsubmit=async e=>'),end=source.indexOf("\n if($('#assistant-speak'))",start);
function harness(){
 const nodes=new Map(),calls=[];
 const node=()=>({value:'Explain the selected document',checked:false,textContent:'',dataset:{},removeAttribute(){},setAttribute(){},replaceChildren(){},append(){},appendChild(){},after(){}});
 const ctx={document:{createElement:node},form:{},$:id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);},assistantFile:'fixture-selected-key',assistantHistory:[],assistantRequest:0,voiceReplyRequested:false,assistantController:null,streamingSpeech:null,commandBriefing:{pause(){}},mutedSpeechRequest:null,stopped:false,
  showAssistant:()=>true,stopVoice(){},voiceState(){},engineState(){},resumeWake(){},checkAssistantEngine(){},deviceIdentity:()=>({device_id:'fixture'}),
  setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,clearInterval(){},AbortController,Date,
  streamAssistantAnswer:async payload=>{calls.push(payload);throw Error('fixture interrupted');}};
 vm.createContext(ctx);vm.runInContext(source.slice(start,end),ctx);return {ctx,calls};
}
test('selected document survives a failed answer and stays attached to the next request',async()=>{
 const h=harness();await h.ctx.form.onsubmit({preventDefault(){}});assert.equal(h.ctx.assistantFile,'fixture-selected-key');
 await h.ctx.form.onsubmit({preventDefault(){}});assert.equal(h.calls.length,2);assert.ok(h.calls.every(x=>x.file_id==='fixture-selected-key'));
 assert.equal(h.ctx.$('#assistant-submit').disabled,false);
});

test('document attachment uses a separate row and leaves a usable question at desktop and phone widths',{skip:!fs.existsSync('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')||Number(process.versions.node.split('.')[0])<20},async()=>{
 const {chromium}=require('playwright-core'),path=require('node:path');
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--disable-background-networking']});
 try{
  const page=await browser.newPage();
  const styles=['workspace.css','command-scene.css'].map(name=>fs.readFileSync(path.join(__dirname,'..',name),'utf8')).join('\n');
  await page.setContent('<style>'+styles+'</style><body data-hud-theme="stark"><section class="assistant-dock" style="position:static;width:min(520px,calc(100vw - 24px));margin:12px;padding:16px"><form id="assistant-form"><textarea id="assistant-input" aria-label="Question"></textarea><div class="actions assistant-document"><small>Selected document: A long document filename for a useful layout check.pdf</small><button type="button">Remove document</button></div><button id="assistant-submit">Ask</button></form></section></body>');
  for(const width of [1280,390]){
   await page.setViewportSize({width,height:800});
   const input=await page.locator('#assistant-input').boundingBox(),chip=await page.locator('.assistant-document').boundingBox(),ask=await page.locator('#assistant-submit').boundingBox();
   assert.ok(input.width>180,'question remains usable at '+width);assert.ok(chip.y>=input.y+input.height-1,'attachment belongs below question');
   assert.ok(chip.height<95,'attachment remains compact');assert.ok(ask.x>=input.x+input.width-1,'Ask stays beside question');
  }
 }finally{await browser.close();}
});
