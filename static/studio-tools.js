const $=id=>document.getElementById(id);
export class StudioTools {
  constructor(api){this.api=api;this.records=[];this.loadedId=null;this.dirty=false;this.bind();}
  async start(){await Promise.all([this.refreshPersonas(),this.refreshMotions()]);this.api.getRigView()?.select('RightHand');this.refreshGarments();const active=localStorage.getItem('moneypenny-active-persona');if(active&&this.records.some(r=>r.id===active)){$('personaLibrary').value=active;await $('personaLibrary').onchange();}}
  refreshGarments(){const garments=this.api.getWardrobe()?.garments()||[];$('cueGarment').replaceChildren(...garments.map(item=>new Option(item.name,item.id)));}
  markDirty(){this.dirty=true;localStorage.removeItem('moneypenny-active-persona');}
  get personaId(){return this.dirty?null:this.loadedId;}
  async refreshPersonas(selected=''){
    const response=await fetch('/api/personas');if(!response.ok)throw new Error('Persona library unavailable.');const data=await response.json();this.records=data.personas;
    $('personaLibrary').replaceChildren(new Option('Current draft',''),...this.records.map(r=>new Option(`${r.name} · ${r.source==='openwebui'?'Open WebUI':'saved here'}`,r.id)));
    $('personaLibrary').value=selected;$('personaSource').textContent=data.webui_connected?'Connected to your existing Open WebUI persona catalogue':data.webui_error;
  }
  async refreshMotions(){
    const library=this.api.getLibrary();if(!library)return;
    const items=await library.refresh(),selected=$('motionLibrary').value;
    $('motionLibrary').replaceChildren(...items.map(r=>new Option(r.name,r.id)));if(items.some(r=>r.id===selected))$('motionLibrary').value=selected;
    $('autoLibraryMotion').checked=library.autoIds.includes($('motionLibrary').value);
    $('motionAliases').value=(library.aliasOverrides[$('motionLibrary').value]||items.find(item=>item.id===$('motionLibrary').value)?.aliases||[]).join(', ');
    $('libraryState').textContent=`${items.length} movements available · add your own animation clips`;
  }
  rigChanged(name,target,held){
    if($('rigTarget').value!==name)return;
    for(const [index,axis] of ['X','Y','Z'].entries()){$('rig'+axis).value=target.toArray()[index];$('rig'+axis+'Value').textContent=' '+target.toArray()[index].toFixed(2)+' m';}
    $('rigState').textContent=held?'Target held · move its sliders or drag the handle':'Target released · choose a position to hold';
  }
  bind(){
    const a=this.api;
    $('personaLibrary').onchange=async()=>{const record=this.records.find(r=>r.id===$('personaLibrary').value);if(!record)return;await a.resetConversation();a.applySettings({...record.settings,personaName:record.name,systemPrompt:record.system,modelSelect:record.model,personaPreset:'custom'});this.loadedId=record.id;this.dirty=false;localStorage.setItem('moneypenny-active-persona',record.id);$('personaSource').textContent=`${record.source==='openwebui'?'Using the saved Open WebUI persona':'Using your saved persona'} · ${record.model}`;};
    $('newPersona').onclick=async()=>{await a.resetConversation();this.loadedId=null;this.markDirty();$('personaLibrary').value='';a.applySettings({personaName:'New persona',systemPrompt:'',personaPreset:'custom',modelSelect:[...$('modelSelect').options].some(o=>o.value==='uncensored-3b:latest')?'uncensored-3b:latest':$('modelSelect').value});$('personaSource').textContent='New draft · set the name and personality, then Save persona';$('personaName').focus();};
    $('savePersona').onclick=async()=>{try{const value=a.settings();const response=await a.post('/api/personas',{id:this.loadedId,name:value.personaName,model:value.modelSelect,system:value.systemPrompt,settings:value});const record=await response.json();this.loadedId=record.id;this.dirty=false;localStorage.setItem('moneypenny-active-persona',record.id);await this.refreshPersonas(record.id);$('personaSource').textContent='Saved on this Mac · '+record.model;}catch(error){a.notify(error.message);}};
    $('exportWebUI').onclick=()=>{const value=a.settings();const record={id:'moneypenny-'+value.personaName.toLowerCase().replace(/[^a-z0-9]+/g,'-'),name:value.personaName,base_model_id:value.modelSelect,params:{system:value.systemPrompt,temperature:Number(value.temperature),num_predict:Number(value.maxTokens)},meta:{description:'Persona from Moneypenny Studio'}};a.download('open-webui-persona.json',[record]);};
    $('motionLibrary').onchange=async()=>{try{$('autoLibraryMotion').checked=a.getLibrary().autoIds.includes($('motionLibrary').value);$('motionAliases').value=(a.getLibrary().aliasOverrides[$('motionLibrary').value]||a.getLibrary().items.find(item=>item.id===$('motionLibrary').value)?.aliases||[]).join(', ');const clips=await a.getLibrary().load($('motionLibrary').value);$('motionClip').replaceChildren(...clips.map((entry,i)=>new Option(entry.clip.name||`Clip ${i+1}`,String(i))));$('libraryState').textContent=`${clips.length} animation clip${clips.length===1?'':'s'} ready`;}catch(error){a.notify(error.message);}};
    $('playMotion').onclick=async()=>{try{await a.stopConversation();a.getMotion().stop();a.getRig().clear();const library=a.getLibrary();library.loop=$('loopMotion').checked;await library.play($('motionLibrary').value,Number($('motionClip').value));a.frame('full');}catch(error){a.notify(error.message);}};
    $('pauseMotion').onclick=()=>{const library=a.getLibrary();library.paused=!library.paused;$('pauseMotion').textContent=library.paused?'Resume movement':'Pause movement';};
    $('stopLibraryMotion').onclick=()=>{a.getLibrary().stop();$('pauseMotion').textContent='Pause movement';};
    $('motionPosition').oninput=()=>{const library=a.getLibrary();library.paused=true;library.seek(Number($('motionPosition').value));$('pauseMotion').textContent='Resume movement';};
    $('motionSpeed').oninput=()=>{a.getLibrary().speed=Number($('motionSpeed').value);};$('motionBlend').oninput=()=>{a.getLibrary().blend=Number($('motionBlend').value);};
    $('autoLibraryMotion').onchange=()=>{const library=a.getLibrary(),id=$('motionLibrary').value;library.autoIds=library.autoIds.filter(x=>x!==id);if($('autoLibraryMotion').checked)library.autoIds.push(id);localStorage.setItem('moneypenny-autonomous-clips',JSON.stringify(library.autoIds));};
    $('saveMotionAliases').onclick=()=>{const library=a.getLibrary();library.aliasOverrides[$('motionLibrary').value]=$('motionAliases').value.split(',').map(x=>x.trim().toLowerCase()).filter(x=>x.length>2);localStorage.setItem('moneypenny-motion-aliases',JSON.stringify(library.aliasOverrides));$('libraryState').textContent='Movement words saved · ask for this movement in conversation';};
    $('addGarmentCue').onclick=()=>{const library=a.getLibrary(),id=$('motionLibrary').value,at=Number($('cueTime').value),garment=$('cueGarment').value;if(!garment||!Number.isFinite(at)||at<0||at>120)return;library.cueOverrides[id]||=[];library.cueOverrides[id].push({at,garment,visible:$('cueVisible').checked});localStorage.setItem('moneypenny-garment-cues',JSON.stringify(library.cueOverrides));$('cueState').textContent=`${library.cueOverrides[id].length} outfit changes saved for this movement`;};
    $('clearGarmentCues').onclick=()=>{const library=a.getLibrary();delete library.cueOverrides[$('motionLibrary').value];localStorage.setItem('moneypenny-garment-cues',JSON.stringify(library.cueOverrides));$('cueState').textContent='Outfit changes cleared';};
    $('motionUpload').onchange=async event=>{const file=event.target.files[0];if(!file)return;try{if(file.size>24*1024*1024)throw new Error('Use an animation under 24 MB.');const form=new FormData();form.append('file',file);form.append('name',$('motionName').value.trim()||file.name.replace(/\.(glb|bvh|motion\.json)$/i,''));const response=await fetch('/api/motion/library',{method:'POST',headers:{'X-Studio-Client':'moneypenny'},body:form});const data=await response.json();if(!response.ok)throw new Error(data.error);await this.refreshMotions();$('motionLibrary').value=data.id;await $('motionLibrary').onchange();}catch(error){a.notify(error.message);}event.target.value='';};
    $('saveBoneMap').onclick=()=>{const library=a.getLibrary(),value=$('mapSource').value.trim();if(value)library.mapping[$('mapTarget').value]=value;else delete library.mapping[$('mapTarget').value];library.cache.clear();localStorage.setItem('moneypenny-bone-map',JSON.stringify(library.mapping));$('libraryState').textContent='Mapping saved · reselect the animation to retarget it';};
    $('showRig').onchange=()=>a.getRigView().show($('showRig').checked);
    $('rigTarget').onchange=()=>a.getRigView().select($('rigTarget').value);
    for(const axis of ['X','Y','Z'])$('rig'+axis).oninput=()=>{const target=a.getRig().setTarget($('rigTarget').value,['X','Y','Z'].map(x=>Number($('rig'+x).value)));this.rigChanged($('rigTarget').value,target,true);};
    $('releaseTarget').onclick=()=>{a.getRig().release($('rigTarget').value);a.getRigView().select($('rigTarget').value);};
    $('resetRig').onclick=()=>{a.getRig().clear();a.getRigView().select($('rigTarget').value);};
    $('pinFeet').onclick=()=>{const rig=a.getRig();for(const name of ['LeftFoot','RightFoot'])rig.setTarget(name,rig.neutral[name].toArray());$('rigState').textContent='Both feet planted · hips and hands can move independently';};
  }
}
