'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../globe-surface.js'),'utf8');
function harness(){
 const calls={paint:0,draw:0,requests:[],polygons:0},gradient={addColorStop(){}};
 const ctx={createLinearGradient:()=>gradient,fillRect(){},beginPath(){},moveTo(){},lineTo(){},closePath(){},fill(){calls.polygons++;},clearRect(){},save(){},restore(){},drawImage(){calls.draw++;},createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),getImageData:(x,y,w,h)=>({data:new Uint8ClampedArray(w*h*4).fill(100)}),putImageData(){calls.paint++;}};
 const document={hidden:false,createElement:()=>({width:0,height:0,getContext:()=>ctx})};
 const window={document,performance:{now:()=>1000},location:{href:'https://owner.invalid/workspace',origin:'https://owner.invalid'},Image:class{set src(value){calls.requests.push(value);}}};
 const sandbox={window,URL,console};vm.createContext(sandbox);vm.runInContext(source,sandbox);
 return {api:window.JJGlobeSurface,document,calls,ctx};
}
test('surface centre and inverse projection preserve device longitude/latitude',()=>{
 const h=harness(),rad=Math.PI/180;
 for(const yaw of [-170,-75,0,95,179])for(const pitch of [-70,-20,0,50,80]){
  const middle=h.api.uvAt(0,0,yaw,pitch);
  assert.ok(Math.abs(middle.u-(((yaw/360+.5)%1+1)%1))<1e-12);
  assert.ok(Math.abs(middle.v-(.5-pitch/180))<1e-12);
  // Cross-check an independently projected visible device against map sampling.
  const longitude=yaw+15,latitude=pitch-10,p=latitude*rad,l=(longitude-yaw)*rad,a=pitch*rad;
  const x=Math.cos(p)*Math.sin(l),y=Math.sin(p)*Math.cos(a)-Math.cos(p)*Math.cos(l)*Math.sin(a);
  const uv=h.api.uvAt(x,y,yaw,pitch);
  assert.ok(Math.abs(uv.u-(((longitude/360+.5)%1+1)%1))<1e-10);
  assert.ok(Math.abs(uv.v-(.5-latitude/180))<1e-10);
 }
 assert.equal(h.api.uvAt(2,0),null);
});
test('rasterisation is once, surfaces update at most30fps, unchanged views use cache',()=>{
 const h=harness(),land=[[[0,0],[20,0],[20,20],[0,0]]],surface=h.api.create(land,{textureURL:false,resolution:128,maxFps:60});
 assert.equal(h.calls.polygons,3,'Only one initial wrapped map is rasterised');
 surface.draw(h.ctx,210,210,166,0,20,0);
 surface.draw(h.ctx,210,210,166,2,20,20);
 assert.equal(surface.stats().renderedFrames,1);
 surface.draw(h.ctx,210,210,166,2,20,70);
 surface.draw(h.ctx,210,210,166,2,20,1000);
 assert.equal(surface.stats().renderedFrames,2);
 assert.equal(surface.stats().maxFps,30);
 assert.equal(h.calls.polygons,3,'No land vertices are re-projected while rotating');
 assert.equal(h.calls.draw,4,'Cached sphere remains available after caller clears its canvas');
});
test('hidden, disconnected or destroyed surfaces stop work and release pitch cache',()=>{
 const h=harness(),element={isConnected:true},surface=h.api.create([],{textureURL:false,resolution:128,element});
 for(let i=0;i<4;i++)surface.draw(h.ctx,210,210,166,10,i*5,i*100);
 assert.equal(surface.stats().cachedPitches,2);
 const frames=surface.stats().renderedFrames;
 h.document.hidden=true;assert.equal(surface.draw(h.ctx,210,210,166,50,20,1000),false);
 h.document.hidden=false;surface.setVisible(false);assert.equal(surface.draw(h.ctx,210,210,166,50,20,1000),false);
 surface.setVisible(true);element.isConnected=false;assert.equal(surface.draw(h.ctx,210,210,166,50,20,1000),false);
 assert.equal(surface.stats().renderedFrames,frames);
 surface.destroy();assert.equal(surface.stats().cachedPitches,0);assert.equal(surface.isVisible(),false);
});
test('external image URLs are rejected without runtime requests and labels remain honest',async()=>{
 const h=harness(),surface=h.api.create([],{textureURL:'https://third-party.invalid/earth.jpg',resolution:128});
 assert.equal(await surface.ready,false);assert.deepEqual(h.calls.requests,[]);
 assert.match(surface.label(),/static coastline illustration/);assert.equal(surface.stats().static,true);
});
test('bundled NASA image metadata matches the original small historical source',()=>{
 const metadata=JSON.parse(fs.readFileSync(path.join(__dirname,'../globe-surface-source.json'),'utf8'));
 const data=fs.readFileSync(path.join(__dirname,'../globe-earth.jpg'));
 assert.equal(require('node:crypto').createHash('sha256').update(data).digest('hex'),metadata.sha256);
 assert.ok(data.length<300000);assert.match(metadata.source,/^https:\/\/eoimages\.gsfc\.nasa\.gov\//);
 assert.match(metadata.description,/not a live satellite or weather feed/);assert.match(metadata.conditions,/Do not imply NASA endorsement/);
});
