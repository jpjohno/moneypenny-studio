import {studioFetch as fetch} from './studio-paths.js';

// These are the existing body director's ordinary, bounded skills. Sequences
// contain data only; they do not ask a model to write or execute animation code.
export const ANIMATION_ACTIONS=[
 {skill:'wave',label:'Wave hello',duration:4},
 {skill:'bow',label:'Take a bow',duration:4},
 {skill:'stretch',label:'Gentle stretch',duration:5},
 {skill:'turn',label:'Turn around',duration:5},
 {skill:'bend_forward',label:'Bend forward',duration:6},
 {skill:'walk',label:'Walk in place',duration:6},
 {skill:'dance',label:'Dance',duration:8},
 {skill:'jig',label:'Dance a jig',duration:8},
 {skill:'idle',label:'Pause and settle',duration:3},
];
const actions=new Map(ANIMATION_ACTIONS.map(action=>[action.skill,action]));
const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));

export function validateAnimationSequence(value){
 if(!value||value.version!==1||value.kind!=='sequence')throw new Error('Choose a Studio sequence JSON file.');
 if(typeof value.name!=='string'||!value.name.trim()||value.name.trim().length>80)throw new Error('Give the animation a name of 1–80 characters.');
 if(!Array.isArray(value.steps)||!value.steps.length||value.steps.length>8)throw new Error('Add between 1 and 8 movements.');
 const steps=value.steps.map(step=>{
  if(!step||!actions.has(step.skill))throw new Error('That movement is not supported by the animation builder.');
  const duration=step.duration??actions.get(step.skill).duration,intensity=step.intensity??.6;
  if(typeof duration!=='number'||!Number.isFinite(duration)||typeof intensity!=='number'||!Number.isFinite(intensity))throw new Error('Each movement needs a valid duration and energy.');
  return {skill:step.skill,duration:clamp(duration,1,20),intensity:clamp(intensity,.1,1),side:step.side==='left'?'left':'right'};
 });
 return {version:1,kind:'sequence',name:value.name.trim(),steps};
}

export class AnimationDraft {
 constructor(value={name:'My animation',steps:[]}){this.name=value.name;this.steps=(value.steps||[]).map(step=>({...step}));}
 add(skill,duration=actions.get(skill)?.duration){
  const next=validateAnimationSequence({version:1,kind:'sequence',name:this.name,steps:[...this.steps,{skill,duration,intensity:.6,side:'right'}]});
  this.steps=next.steps;return this;
 }
 update(index,changes){
  if(!Number.isInteger(index)||index<0||index>=this.steps.length)throw new Error('Choose an existing movement.');
  const steps=this.steps.map((step,i)=>i===index?{...step,...changes}:step);
  this.steps=validateAnimationSequence({version:1,kind:'sequence',name:this.name,steps}).steps;return this;
 }
 move(index,offset){
  if(!Number.isInteger(index)||![-1,1].includes(offset)||!this.steps[index]||!this.steps[index+offset])return false;
  [this.steps[index],this.steps[index+offset]]=[this.steps[index+offset],this.steps[index]];return true;
 }
 remove(index){if(Number.isInteger(index)&&index>=0&&index<this.steps.length)this.steps.splice(index,1);}
 replace(value){const next=validateAnimationSequence(value);this.name=next.name;this.steps=next.steps;return this;}
 data(){return validateAnimationSequence({version:1,kind:'sequence',name:this.name,steps:this.steps});}
 get duration(){return this.steps.reduce((sum,step)=>sum+step.duration,0);}
}

export function sequenceFilename(name){return (name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'animation')+'.sequence.json';}

export async function saveAnimationSequence(value,request=fetch){
 const data=validateAnimationSequence(value),form=new FormData();
 form.append('name',data.name);
 form.append('file',new Blob([JSON.stringify(data)],{type:'application/json'}),sequenceFilename(data.name));
 const response=await request('/api/motion/library',{method:'POST',headers:{'X-Studio-Client':'moneypenny'},body:form});
 const record=await response.json();if(!response.ok)throw new Error(record.error||'The animation could not be saved.');return record;
}

export class AnimationBuilder {
 constructor(panel,api){
  this.panel=panel;this.api=api;this.document=panel.ownerDocument;this.draft=new AnimationDraft();this.epoch=0;
  this.$=name=>panel.querySelector('[data-animation="'+name+'"]');
  this.bind();this.render();
 }
 say(message){this.$('status').textContent=message;}
 async start(){await this.refreshSaved();}
 async refreshSaved(selected=''){
  const library=this.api.getLibrary();if(!library)return;
  const items=await library.refresh(),select=this.$('saved');select.replaceChildren();
  const option=(label,value)=>{const node=this.document.createElement('option');node.textContent=label;node.value=value;select.append(node);};
  option('Choose a saved animation','');
  items.filter(item=>item.format==='sequence').forEach(item=>option(item.name,item.id));select.value=selected;
 }
 async preview(){
  this.draft.name=this.$('name').value;const data=this.draft.data(),epoch=++this.epoch;
  this.say('Preparing the animation…');await this.api.stopConversation();
  if(epoch!==this.epoch)return false;
  const library=this.api.getLibrary();if(!library)throw new Error('Wait for the character to finish loading.');
  this.api.getRig()?.clear();library.loop=false;library.playSequence(data,'animation-builder');
  this.api.frame('full',data);this.say(`Playing ${data.steps.length} movements · ${data.steps.reduce((sum,step)=>sum+step.duration,0)} seconds. Stop at any time.`);
  return true;
 }
 stop(){this.epoch++;this.api.getLibrary()?.stop();this.say('Animation stopped. Edit the steps or press Preview to replay.');}
 render(){
  this.$('name').value=this.draft.name;
  const list=this.$('steps');list.replaceChildren();
  this.draft.steps.forEach((step,index)=>{
   const row=this.document.createElement('li');row.className='animation-step';
   const title=this.document.createElement('span');title.className='animation-step-title';title.textContent=`${index+1}. ${actions.get(step.skill).label}`;row.append(title);
   const controls=this.document.createElement('div');controls.className='animation-step-controls';
   const duration=this.document.createElement('input');duration.type='number';duration.min='1';duration.max='20';duration.step='.5';duration.value=step.duration;
   duration.setAttribute('aria-label',`Seconds for movement ${index+1}`);duration.addEventListener('change',()=>{try{this.draft.update(index,{duration:Number(duration.value)});this.render();}catch(error){this.say(error.message);}});
   const seconds=this.document.createElement('span');seconds.textContent='sec';controls.append(duration,seconds);
   if(step.skill==='wave'){
    const side=this.document.createElement('select');side.setAttribute('aria-label',`Hand for movement ${index+1}`);
    for(const [value,label] of [['right','Right hand'],['left','Left hand']]){const item=this.document.createElement('option');item.value=value;item.textContent=label;side.append(item);}
    side.value=step.side;side.addEventListener('change',()=>this.draft.update(index,{side:side.value}));controls.append(side);
   }
   for(const [label,accessible,action,disabled] of [
    ['↑',`Move movement ${index+1} earlier`,()=>this.draft.move(index,-1),index===0],
    ['↓',`Move movement ${index+1} later`,()=>this.draft.move(index,1),index===this.draft.steps.length-1],
    ['×',`Remove movement ${index+1}`,()=>this.draft.remove(index),false],
   ]){const button=this.document.createElement('button');button.type='button';button.className='animation-step-button';button.textContent=label;button.setAttribute('aria-label',accessible);button.disabled=disabled;button.addEventListener('click',()=>{action();this.render();});controls.append(button);}
   row.append(controls);list.append(row);
  });
  this.$('empty').hidden=!!this.draft.steps.length;
  this.$('summary').textContent=`${this.draft.steps.length} / 8 movements · ${this.draft.duration} seconds`;
  this.$('preview').disabled=this.$('save').disabled=this.$('download').disabled=!this.draft.steps.length;
  this.$('add').disabled=this.draft.steps.length>=8;
 }
 bind(){
  const run=fn=>()=>Promise.resolve().then(fn).catch(error=>this.say(error.message));
  const select=this.$('action');select.replaceChildren();
  for(const action of ANIMATION_ACTIONS){const option=this.document.createElement('option');option.value=action.skill;option.textContent=action.label;select.append(option);}
  select.addEventListener('change',()=>{this.$('duration').value=actions.get(select.value).duration;});
  this.$('name').addEventListener('input',()=>{this.draft.name=this.$('name').value;});
  this.$('add').addEventListener('click',run(()=>{this.draft.add(select.value,Number(this.$('duration').value));this.render();this.say('Movement added. Reorder the steps, then Preview.');}));
  this.$('preview').addEventListener('click',run(()=>this.preview()));
  this.$('stop').addEventListener('click',()=>this.stop());
  this.$('new').addEventListener('click',()=>{this.stop();this.draft=new AnimationDraft();this.$('saved').value='';this.render();this.say('New animation. Choose a movement to begin.');});
  this.$('save').addEventListener('click',run(async()=>{
   this.draft.name=this.$('name').value;const data=this.draft.data();this.$('save').disabled=true;
   try{const record=await saveAnimationSequence(data,this.api.request||fetch);await this.refreshSaved(record.id);await this.api.onSaved?.(record);this.say('Saved in Motion library. Choose it here to reopen and edit.');}
   finally{this.$('save').disabled=!this.draft.steps.length;}
  }));
  this.$('saved').addEventListener('change',run(async()=>{
   const id=this.$('saved').value;if(!id)return;
   const epoch=++this.epoch,entries=await this.api.getLibrary().load(id);if(epoch!==this.epoch)return;
   this.draft.replace(entries[0].sequence);this.render();this.say('Saved animation opened. Edit it or press Preview.');
  }));
  this.$('download').addEventListener('click',run(()=>{
   this.draft.name=this.$('name').value;const data=this.draft.data(),url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
   const link=this.document.createElement('a');link.href=url;link.download=sequenceFilename(data.name);link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);this.say('Animation JSON exported. Use Open JSON to edit it later.');
  }));
  this.$('import').addEventListener('change',run(async()=>{
   const input=this.$('import'),file=input.files[0];if(!file)return;
   try{if(file.size>32_000)throw new Error('Choose a sequence JSON smaller than 32 KB.');const epoch=++this.epoch,data=JSON.parse(await file.text());if(epoch!==this.epoch)return;this.draft.replace(data);this.render();this.say('Animation opened. Preview it, then Save to keep it in Motion library.');}
   finally{input.value='';}
  }));
 }
}
