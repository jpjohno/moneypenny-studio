// A bounded render loop is independent of voice and microphone lifetimes.
export function renderProfile({pixelRatio=1,narrow=false,embedded=false}={}){
  const displayRatio=Number.isFinite(pixelRatio)&&pixelRatio>0?pixelRatio:1;
  const ratio=Math.min(displayRatio,narrow?1:1.25);
  return {pixelRatio:ratio,pixelRatioScale:ratio/displayRatio,activeFPS:narrow?24:30,idleFPS:narrow?12:15,shadows:!embedded,shadowSize:1024};
}

export class StageActivity {
  constructor(head,profile,{cancelFrame=frame=>globalThis.cancelAnimationFrame(frame),onChange=()=>{}}={}){
    Object.assign(this,{head,profile,cancelFrame,onChange,documentVisible:true,parentVisible:true,inView:true,active:false});
    this.update();
  }
  update(state={}){
    for(const key of ['documentVisible','parentVisible','inView','active'])if(key in state)this[key]=!!state[key];
    const running=this.documentVisible&&this.parentVisible&&this.inView;
    const fps=this.active?this.profile.activeFPS:this.profile.idleFPS;
    this.head.opt.modelFPS=fps;this.head.animFrameDur=1000/fps;
    if(!running){
      // TalkingHead.stop() also suspends the AudioContext. Stop only its RAF so
      // an offscreen assistant can keep speaking/listening and can be interrupted.
      this.head.isRunning=false;
      if(this.head._raf!=null){this.cancelFrame(this.head._raf);this.head._raf=null;}
    }else if(this.head.armature&&!this.head.isRunning)this.head.start();
    if(running!==this.running||fps!==this.fps){this.running=running;this.fps=fps;this.onChange(this.status());}
    return this.status();
  }
  status(){return {running:!!this.running,fps:this.fps,pixelRatio:this.profile.pixelRatio,shadowSize:this.profile.shadows?this.profile.shadowSize:0};}
}
