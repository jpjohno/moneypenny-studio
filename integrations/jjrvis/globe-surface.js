/* Cached Canvas2D globe. NASA Blue Marble is a historic composite, never live.
   Credit and source conditions: globe-surface-source.json. No WebGL or CDN. */
(function(root){
 'use strict';
 const RAD=Math.PI/180, TAU=Math.PI*2;
 const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
 const wrap=(v,n)=>((v%n)+n)%n;
 function uvAt(x,y,yaw=0,pitch=0){
  const zz=1-x*x-y*y;if(zz<0)return null;
  const z=Math.sqrt(zz),a=clamp(pitch,-89.5,89.5)*RAD;
  const latitude=Math.asin(clamp(y*Math.cos(a)+z*Math.sin(a),-1,1));
  const longitude=Math.atan2(x,z*Math.cos(a)-y*Math.sin(a))+yaw*RAD;
  return {u:wrap(longitude/TAU+.5,1),v:clamp(.5-latitude/Math.PI,0,1)};
 }
 function canvas(width,height){const c=root.document.createElement('canvas');c.width=width;c.height=height;return c;}
 function fallbackTexture(ctx,w,h,land){
  const water=ctx.createLinearGradient(0,0,0,h);water.addColorStop(0,'#152f47');water.addColorStop(.5,'#123a59');water.addColorStop(1,'#152f47');
  ctx.fillStyle=water;ctx.fillRect(0,0,w,h);
  const surface=ctx.createLinearGradient(0,0,0,h);surface.addColorStop(0,'#b0b6a1');surface.addColorStop(.35,'#74846a');surface.addColorStop(.6,'#899375');surface.addColorStop(1,'#c5cec7');ctx.fillStyle=surface;
  // Rasterise once. Unwrap dateline-crossing rings, then wrap the fill copies.
  for(const ring of Array.isArray(land)?land:[]){
   if(!Array.isArray(ring)||ring.length<3)continue;
   const points=[];let prior=null;
   for(const point of ring){if(!Array.isArray(point)||!point.slice(0,2).every(Number.isFinite))continue;let x=(point[0]+180)/360*w;const y=(90-clamp(point[1],-90,90))/180*h;
    if(prior!==null){while(x-prior>w/2)x-=w;while(x-prior<-w/2)x+=w;}points.push([x,y]);prior=x;}
   for(const shift of [-w,0,w]){ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x+shift,y):ctx.moveTo(x+shift,y));ctx.closePath();ctx.fill();}
  }
 }
 function create(land,options={}){
  const size=Math.round(clamp(Number(options.resolution)||320,128,640));
  const fps=clamp(Number(options.maxFps)||15,1,30),width=1024,height=512;
  const texture=canvas(width,height),tc=texture.getContext('2d',{willReadFrequently:true});
  const sphere=canvas(size,size),sc=sphere.getContext('2d',{willReadFrequently:true});
  fallbackTexture(tc,width,height,land);
  let pixels=tc.getImageData(0,0,width,height).data;
  const image=sc.createImageData(size,size),out=image.data;
  const nx=[],ny=[],nz=[],offsets=[],shade=[],rim=[],alpha=[];
  for(let row=0;row<size;row++)for(let col=0;col<size;col++){
   const x=(col+.5)*2/size-1,y=1-(row+.5)*2/size,z2=1-x*x-y*y;
   if(z2<=0)continue;const z=Math.sqrt(z2),dot=Math.max(0,-.45*x+.35*y+.82*z);
   nx.push(x);ny.push(y);nz.push(z);offsets.push((row*size+col)*4);
   shade.push(.25+.78*dot);rim.push((1-z)**3*19);alpha.push(Math.round(clamp((1-Math.hypot(x,y))*size/2,0,1)*255));
  }
  const count=offsets.length,normalX=Float32Array.from(nx),normalY=Float32Array.from(ny),normalZ=Float32Array.from(nz);
  const target=Uint32Array.from(offsets),light=Float32Array.from(shade),air=Float32Array.from(rim),opacity=Uint8Array.from(alpha);
  const projections=new Map();let currentKey='',lastPaint=-Infinity,paintCount=0,version=0,visible=true,destroyed=false,mode='coastline-fallback',observer=null,photo=null;
  function projection(pitch){
   if(projections.has(pitch))return projections.get(pitch);
   const a=pitch*RAD,s=Math.sin(a),c=Math.cos(a),u=new Uint16Array(count),rows=new Uint32Array(count);
   for(let i=0;i<count;i++){
    const latitude=Math.asin(clamp(normalY[i]*c+normalZ[i]*s,-1,1));
    u[i]=Math.floor((Math.atan2(normalX[i],normalZ[i]*c-normalY[i]*s)/TAU+.5)*width)%width;
    rows[i]=clamp(Math.floor((.5-latitude/Math.PI)*height),0,height-1)*width;
   }
   const value={u,rows};if(projections.size>=2)projections.delete(projections.keys().next().value);projections.set(pitch,value);return value;
  }
  function paint(yaw,pitch,stamp){
   const quantizedPitch=Math.round(clamp(pitch,-85,85)*2)/2,shift=Math.round(wrap(yaw,360)/360*width),key=shift+':'+quantizedPitch+':'+version;
   if(key===currentKey||stamp-lastPaint<1000/fps)return;
   const map=projection(quantizedPitch);
   for(let i=0;i<count;i++){
    const source=(map.rows[i]+(map.u[i]+shift)%width)*4,dest=target[i],brightness=light[i],haze=air[i];
    out[dest]=pixels[source]*brightness+haze*.15;out[dest+1]=pixels[source+1]*brightness+haze*.55;out[dest+2]=pixels[source+2]*brightness+haze;out[dest+3]=opacity[i];
   }
   sc.putImageData(image,0,0);currentKey=key;lastPaint=stamp;paintCount++;
  }
  function isVisible(){return !destroyed&&visible&&!root.document.hidden&&(!options.element||options.element.isConnected!==false);}
  if(options.element&&typeof root.IntersectionObserver==='function'){
   observer=new root.IntersectionObserver(entries=>{visible=entries[0]?.isIntersecting!==false;options.onVisibilityChange?.(visible);},{rootMargin:'80px'});observer.observe(options.element);
  }
  const ready=new Promise(resolve=>{
   if(options.textureURL===false||typeof root.Image!=='function'){resolve(false);return;}
   let url;try{url=new URL(options.textureURL||'/globe-earth.jpg',root.location.href);if(url.origin!==root.location.origin)throw new Error('Local texture required');}catch{resolve(false);return;}
   photo=new root.Image();photo.decoding='async';
   photo.onload=()=>{if(destroyed){resolve(false);return;}try{tc.clearRect(0,0,width,height);tc.drawImage(photo,0,0,width,height);pixels=tc.getImageData(0,0,width,height).data;mode='nasa-static';version++;lastPaint=-Infinity;options.onReady?.();resolve(true);}catch{resolve(false);}};
   photo.onerror=()=>resolve(false);photo.src=url.href;
  });
  return {
   ready,
   draw(ctx,cx,cy,radius,yaw,pitch,stamp=root.performance.now()){
    if(!isVisible()||![cx,cy,radius,yaw,pitch,stamp].every(Number.isFinite)||radius<=0)return false;
    paint(yaw,pitch,stamp);ctx.save();ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(sphere,cx-radius,cy-radius,radius*2,radius*2);ctx.restore();return true;
   },
   isVisible,
   setVisible(value){visible=!!value;},
   stats(){return {mode,static:true,maxFps:fps,resolution:size,renderedFrames:paintCount,cachedPitches:projections.size};},
   label(){return mode==='nasa-static'?'Earth · NASA Blue Marble · static imagery':'Earth · static coastline illustration';},
   destroy(){destroyed=true;observer?.disconnect();if(photo){photo.onload=null;photo.onerror=null;}projections.clear();texture.width=texture.height=sphere.width=sphere.height=1;pixels=null;},
  };
 }
 const api={create,uvAt};root.JJGlobeSurface=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
