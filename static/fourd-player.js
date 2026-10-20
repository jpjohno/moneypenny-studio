// Recorded volumetric playback, independent from the conversational body rig.
// A manifest is {fps, frames:["frame.glb", {url:"frame.glb"}], loop?}. Each
// decoded frame must own its resources; do not share textures between frames.
// Call update(deltaSeconds) from a visible viewer's RAF, not a hidden timer.
// showFrame must replace/detach the previous visible root without disposing it;
// the cache owns disposal. showFrame(null) hides the current frame on stop.
export class FourDPlayer {
  constructor(manifest,{loadFrame,showFrame=()=>{},disposeFrame=disposeThreeFrame,
    onState=()=>{},onError=()=>{},prefetch=2,maxCached=3,loop=manifest?.loop??true}={}){
    if(!manifest||!Number.isFinite(manifest.fps)||manifest.fps<1||manifest.fps>60||
      !Array.isArray(manifest.frames)||!manifest.frames.length||manifest.frames.length>30000)
      throw new Error('Invalid recorded 4D sequence.');
    if(typeof loadFrame!=='function')throw new Error('A frame loader is required.');
    this.frames=manifest.frames.map(frame=>{
      const value=typeof frame==='string'?{url:frame}:{...frame};
      if(typeof value.url!=='string'||!value.url.trim()||value.url.length>4096)throw new Error('Invalid 4D frame URL.');
      return value;
    });
    this.fps=manifest.fps;this.duration=this.frames.length/this.fps;
    this.maxCached=Math.max(2,Math.min(4,Math.floor(Number(maxCached)||3)));
    this.prefetch=Math.max(0,Math.min(this.maxCached-1,Math.floor(Number(prefetch)||0)));
    Object.assign(this,{loadFrame,showFrame,disposeFrame,onState,onError,loop:!!loop});
    this.cache=new Map();this.failed=new Set();this.waiters=new Set();
    this.frame=null;this.requested=0;this.clock=0;this.playing=false;this.disposed=false;
    this.epoch=0;this.demand=false;this.flight=null;this.pump=null;
  }
  status(){
    return {kind:'recorded-4d',frame:this.frame,requested:this.requested,playing:this.playing,
      buffering:(this.playing||this.demand)&&this.frame!==this.requested,
      cached:this.cache.size,loading:this.flight?.index??null,frames:this.frames.length,
      fps:this.fps,duration:this.duration,disposed:this.disposed};
  }
  _notify(){this.onState(this.status());}
  _live(){if(this.disposed)throw new Error('This 4D player has been disposed.');}
  _settle(keep=null){
    for(const waiter of this.waiters)if(waiter.index!==keep){this.waiters.delete(waiter);waiter.resolve(false);}
  }
  _waiting(index){
    if(this.frame===index)return Promise.resolve(true);
    return new Promise(resolve=>this.waiters.add({index,resolve}));
  }
  _display(index){
    const asset=this.cache.get(index);if(!asset)return;
    if(this.frame===index){this.demand=false;return;}
    this.showFrame(asset,index);this.frame=index;this.demand=false;
    for(const waiter of this.waiters)if(waiter.index===index){this.waiters.delete(waiter);waiter.resolve(true);}
    this._trim();this._notify();
  }
  _window(){
    const indices=[this.requested];
    if(this.playing)for(let ahead=1;ahead<=Math.min(this.prefetch,this.frames.length-1);ahead++){
      const next=this.requested+ahead;
      if(next<this.frames.length)indices.push(next);else if(this.loop)indices.push(next%this.frames.length);
    }
    return indices;
  }
  _release(index){
    const asset=this.cache.get(index);if(!asset)return;
    this.cache.delete(index);this.disposeFrame(asset,index);
  }
  _trim(reserve=false){
    const wanted=new Set(this._window());if(this.frame!==null)wanted.add(this.frame);
    for(const index of this.cache.keys())if(!wanted.has(index))this._release(index);
    // Reserve the loader's decoded result before starting it: cached + incoming
    // never exceeds maxCached, even when a decoder cannot be cancelled.
    if(reserve)for(const index of this.cache.keys()){
      if(this.cache.size<this.maxCached)break;
      if(index!==this.frame&&index!==this.requested)this._release(index);
    }
  }
  _next(){
    if(this.disposed||(!this.playing&&!this.demand))return null;
    return this._window().find(index=>!this.cache.has(index)&&!this.failed.has(index))??null;
  }
  _ensure(){
    if(this.pump||this._next()===null)return;
    this.pump=this._run().finally(()=>{
      this.pump=null;
      if(this._next()!==null)this._ensure();
    });
  }
  async _run(){
    let index;
    while((index=this._next())!==null){
      this._trim(true);
      const epoch=this.epoch,controller=new AbortController();
      this.flight={index,controller};this._notify();
      try{
        const asset=await this.loadFrame(this.frames[index],{index,signal:controller.signal});
        if(asset==null)throw new Error('4D loader returned no frame.');
        const wanted=this._window().includes(index);
        if(this.disposed||epoch!==this.epoch||controller.signal.aborted||!wanted){
          this.disposeFrame(asset,index);continue;
        }
        this.cache.set(index,asset);
        if(index===this.requested)this._display(index);
        this._trim();
      }catch(error){
        if(epoch===this.epoch&&!controller.signal.aborted&&!this.disposed){
          this.failed.add(index);
          if(this.cache.has(index)&&this.frame!==index)this._release(index);
          if(index===this.requested){this.demand=false;this._settle();}
          this.onError({error,index,prefetch:index!==this.requested});
        }
      }finally{this.flight=null;this._notify();}
    }
  }
  play(){
    this._live();this.playing=true;
    if(this.clock>=this.duration)return this.seek(0);
    this.demand=true;this.failed.delete(this.requested);
    const ready=this._waiting(this.requested);this._display(this.requested);this._ensure();this._notify();return ready;
  }
  pause(){
    this._live();this.playing=false;this.demand=false;this.epoch++;
    this.flight?.controller.abort();this._settle();
    if(this.frame!==null){this.requested=this.frame;this.clock=this.frame/this.fps;}
    this._trim();this._notify();
  }
  // Seek uses a frame index. Await the boolean result when a visible result is
  // required; false means it was superseded, cancelled or failed to load.
  seek(index){
    this._live();
    if(!Number.isInteger(index)||index<0||index>=this.frames.length)throw new Error('4D frame is out of range.');
    this.epoch++;this.flight?.controller.abort();this._settle();this.failed.clear();
    this.requested=index;this.clock=index/this.fps;this.demand=true;
    const ready=this._waiting(index);this._display(index);this._trim();this._ensure();this._notify();return ready;
  }
  update(deltaSeconds){
    if(this.disposed||!this.playing||this.frame===null)return;
    if(!Number.isFinite(deltaSeconds)||deltaSeconds<0)throw new Error('Invalid playback interval.');
    // A slow decoder must not chase an ever-advancing target and discard every
    // result. Keep the previous frame visible and hold time while buffering.
    // Failed frames may be skipped on the next update instead of stalling.
    if(this.frame!==this.requested&&!this.failed.has(this.requested))return;
    this.clock+=deltaSeconds;
    const wasPlaying=this.playing;
    if(this.clock>=this.duration){
      if(this.loop)this.clock%=this.duration;
      else{this.clock=this.duration;this.playing=false;}
    }
    const index=Math.min(this.frames.length-1,Math.floor(this.clock*this.fps));
    if(index!==this.requested){
      this.requested=index;this.demand=true;this._settle(index);
      this._display(index);this._trim();this._ensure();this._notify();
    }
    if(wasPlaying!==this.playing){this._trim();this._notify();}
  }
  stop(){
    if(this.disposed)return;
    this.playing=false;this.demand=false;this.epoch++;this.flight?.controller.abort();this._settle();
    this.showFrame(null,null);this.frame=null;this.requested=0;this.clock=0;this.failed.clear();
    for(const index of this.cache.keys())this._release(index);
    this._notify();
  }
  dispose(){if(!this.disposed){this.stop();this.disposed=true;this._notify();}}
}

// A frame GLB should be self-contained. Fetching is abortable; GLTF parsing may
// not be, so late parse results are disposed before another frame is decoded.
export function createGLTFFrameLoader(loader,{fetch:fetchFrame=globalThis.fetch,baseURL=globalThis.location?.href}={}){
  if(typeof loader?.parseAsync!=='function'||typeof fetchFrame!=='function')throw new Error('A GLTF parser and fetch are required.');
  return async(frame,{signal})=>{
    const url=baseURL?new URL(frame.url,baseURL).href:frame.url;
    const response=await fetchFrame(url,{signal});
    if(!response.ok)throw new Error(`4D frame could not load (${response.status}).`);
    const bytes=await response.arrayBuffer();
    if(signal.aborted)throw new DOMException('Frame load cancelled.','AbortError');
    const base=url.slice(0,url.lastIndexOf('/')+1),asset=await loader.parseAsync(bytes,base);
    if(signal.aborted){disposeThreeFrame(asset);throw new DOMException('Frame load cancelled.','AbortError');}
    return asset;
  };
}

export function disposeThreeFrame(frame){
  const scene=frame?.scene??frame;if(!scene?.traverse)return;
  const geometries=new Set(),materials=new Set(),textures=new Set(),skeletons=new Set();
  scene.traverse(object=>{
    if(object.geometry)geometries.add(object.geometry);
    if(object.skeleton)skeletons.add(object.skeleton);
    for(const material of [object.material].flat().filter(Boolean)){
      materials.add(material);
      for(const value of Object.values(material))if(value?.isTexture)textures.add(value);
    }
  });
  scene.removeFromParent?.();
  for(const geometry of geometries)geometry.dispose?.();
  for(const skeleton of skeletons)skeleton.dispose?.();
  const images=new Set();
  for(const texture of textures){if(texture.source?.data)images.add(texture.source.data);texture.dispose?.();}
  for(const image of images)image.close?.();
  for(const material of materials)material.dispose?.();
}
