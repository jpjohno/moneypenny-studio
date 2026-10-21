/* Accelerated globe with a cached Canvas2D fallback. NASA Blue Marble is a historic composite, never live.
   Credit and source conditions: globe-surface-source.json. No external renderer or CDN. */
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
 function createCPU(land,options={}){
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
 function createGPU(land,options={}){
  const size=Math.round(clamp(Number(options.detailResolution)||768,256,1024)),sphere=canvas(size,size);
  const gl=sphere.getContext('webgl',{alpha:true,antialias:true,premultipliedAlpha:false,preserveDrawingBuffer:true,powerPreference:'low-power'});
  if(!gl||typeof gl.createShader!=='function')return null;
  try{
  const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error('Globe shader unavailable');return s;};
  const vs=shader(gl.VERTEX_SHADER,'attribute vec2 point;void main(){gl_Position=vec4(point,0.,1.);}');
  const fs=shader(gl.FRAGMENT_SHADER,`precision highp float;uniform sampler2D earth;uniform vec2 angle;uniform float size;
  void main(){vec2 p=gl_FragCoord.xy/size*2.-1.;float r=dot(p,p);if(r>1.){gl_FragColor=vec4(0.);return;}float z=sqrt(max(0.,1.-r));float c=cos(angle.y),s=sin(angle.y);float latitude=asin(clamp(p.y*c+z*s,-1.,1.));float longitude=atan(p.x,z*c-p.y*s)+angle.x;vec2 uv=vec2(fract(longitude/6.28318530718+.5),clamp(.5-latitude/3.14159265359,0.,1.));vec3 color=texture2D(earth,uv).rgb;float light=.32+.7*max(0.,dot(vec3(p,z),normalize(vec3(-.35,.4,.9))));float rim=pow(1.-z,3.);color=color*light+vec3(.005,.018,.028)*rim;float alpha=smoothstep(0.,3./size,1.-sqrt(r));gl_FragColor=vec4(color,alpha);}`);
  const program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('Globe program unavailable');gl.useProgram(program);
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);const point=gl.getAttribLocation(program,'point');gl.enableVertexAttribArray(point);gl.vertexAttribPointer(point,2,gl.FLOAT,false,0,0);
  const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
  const initial=canvas(2048,1024);fallbackTexture(initial.getContext('2d'),2048,1024,land);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,initial);initial.width=initial.height=1;
  const angle=gl.getUniformLocation(program,'angle');gl.uniform1f(gl.getUniformLocation(program,'size'),size);gl.uniform1i(gl.getUniformLocation(program,'earth'),0);gl.viewport(0,0,size,size);
  let destroyed=false,lost=false,visible=true,frames=0,last=-Infinity,key='',version=0,mode='coastline-fallback',photo=null,observer=null;const fps=clamp(Number(options.maxFps)||30,1,30);
  sphere.addEventListener('webglcontextlost',event=>{event.preventDefault();lost=true;options.onReady?.();});
  if(options.element&&typeof root.IntersectionObserver==='function'){observer=new root.IntersectionObserver(entries=>{visible=entries[0]?.isIntersecting!==false;options.onVisibilityChange?.(visible);},{rootMargin:'80px'});observer.observe(options.element);}
  const ready=new Promise(resolve=>{
   if(options.textureURL===false||typeof root.Image!=='function'){resolve(false);return;}
   let url;try{url=new URL(options.textureURL||'/globe-earth.jpg',root.location.href);if(url.origin!==root.location.origin)throw Error();}catch{resolve(false);return;}
   photo=new root.Image();photo.decoding='async';photo.onload=()=>{if(destroyed||lost){resolve(false);return;}try{gl.bindTexture(gl.TEXTURE_2D,texture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,photo);mode='nasa-static';version++;last=-Infinity;options.onReady?.();resolve(true);}catch{resolve(false);}};photo.onerror=()=>resolve(false);photo.src=url.href;
  });
  return {ready,isVisible:()=>!destroyed&&visible&&!root.document.hidden&&(!options.element||options.element.isConnected!==false),setVisible(value){visible=!!value;},
   draw(ctx,cx,cy,radius,yaw,pitch,stamp=root.performance.now()){
    if(lost||!this.isVisible()||![cx,cy,radius,yaw,pitch,stamp].every(Number.isFinite)||radius<=0)return false;
    const next=yaw.toFixed(4)+':'+pitch.toFixed(4)+':'+version;if(next!==key&&stamp-last>=1000/fps){gl.uniform2f(angle,yaw*RAD,clamp(pitch,-89.5,89.5)*RAD);gl.drawArrays(gl.TRIANGLES,0,6);frames++;key=next;last=stamp;}
    ctx.save();ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(sphere,cx-radius,cy-radius,radius*2,radius*2);ctx.restore();return true;
   },stats:()=>({mode,renderer:'webgl',static:true,maxFps:fps,resolution:size,renderedFrames:frames,cachedPitches:0}),label:()=>mode==='nasa-static'?'Earth · NASA Blue Marble · static imagery':'Earth · static coastline illustration',
   destroy(){destroyed=true;observer?.disconnect();if(photo){photo.onload=null;photo.onerror=null;}gl.deleteTexture(texture);gl.deleteBuffer(buffer);gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);gl.getExtension('WEBGL_lose_context')?.loseContext();sphere.width=sphere.height=1;}};
  }catch(error){gl.getExtension('WEBGL_lose_context')?.loseContext();throw error;}
 }
 function create(land,options={}){
  let gpu=null,cpu=null;try{if(options.renderer!=='cpu')gpu=createGPU(land,options);}catch{/* Use the bounded CPU path if graphics acceleration is unavailable. */}
  if(!gpu)return createCPU(land,options);
  return {ready:gpu.ready,draw(...args){if(!gpu.isVisible())return false;if(gpu.draw(...args))return true;cpu ||= createCPU(land,{...options,resolution:256});return cpu.draw(...args);},isVisible:()=>gpu.isVisible()||(cpu?.isVisible()??false),setVisible(value){gpu.setVisible(value);cpu?.setVisible(value);},stats:()=>cpu?.stats()||gpu.stats(),label:()=>cpu?.label()||gpu.label(),destroy(){gpu.destroy();cpu?.destroy();}};
 }

 const api={create,uvAt};root.JJGlobeSurface=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
