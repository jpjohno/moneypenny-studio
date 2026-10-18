import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// These are actual additional skinned garment meshes. The original outfit stays
// underneath as a coverage layer; a future complete body asset can replace it.
export class Wardrobe {
  constructor(head){
    this.head=head;this.layers=[];this.shoes=[];this.original=[];this.reference=null;
    head.armature.traverse(node=>{if(node.isSkinnedMesh&&node.name.includes('female_casualsuit')){this.reference=node;for(const mat of [node.material].flat())this.original.push({mat,map:mat.map,color:mat.color.clone()});}});
    this.tagged=[];
    head.armature.traverse(node=>{if(node.isMesh&&typeof node.userData.wardrobeSlot==='string')this.tagged.push(node);});
    if(!this.reference)return;
    this.createGarments();
  }
  material(color){return new THREE.MeshPhysicalMaterial({color,roughness:.82,metalness:0,side:THREE.DoubleSide,sheen:.3,sheenRoughness:.8,sheenColor:new THREE.Color(color)});}
  skin(geometry,material,name){
    const ref=this.reference,position=geometry.getAttribute('position'),indices=[],weights=[];
    const source=ref.geometry.getAttribute('position'),skinIndex=ref.geometry.getAttribute('skinIndex'),skinWeight=ref.geometry.getAttribute('skinWeight');
    for(let i=0;i<position.count;i++){
      const x=position.getX(i),y=position.getY(i),z=position.getZ(i);let best=Infinity,nearest=0;
      for(let j=0;j<source.count;j++){const dx=x-source.getX(j),dy=y-source.getY(j),dz=z-source.getZ(j);const d=dx*dx+dy*dy+dz*dz;if(d<best){best=d;nearest=j;}}
      for(let j=0;j<4;j++){indices.push(skinIndex.array[nearest*4+j]);weights.push(skinWeight.array[nearest*4+j]);}
    }
    geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(indices,4));geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute(weights,4));
    geometry.computeVertexNormals();
    const mesh=new THREE.SkinnedMesh(geometry,material);mesh.name=name;mesh.frustumCulled=false;
    mesh.position.copy(ref.position);mesh.quaternion.copy(ref.quaternion);mesh.scale.copy(ref.scale);
    mesh.bind(ref.skeleton,ref.bindMatrix);ref.parent.add(mesh);this.layers.push(mesh);return mesh;
  }
  tube(rings,name,color,openFront=false){
    const vertices=[],uvs=[],indices=[],segments=48;
    rings.forEach(([y,xradius,zradius,centerz=0],r)=>{for(let s=0;s<=segments;s++){const t=(openFront?.12:0)+(s/segments)*(Math.PI*2-(openFront?.24:0));vertices.push(Math.sin(t)*xradius,y,Math.cos(t)*zradius+centerz);uvs.push(s/segments,r/(rings.length-1));if(r&&s){const a=(r-1)*(segments+1)+s-1,b=r*(segments+1)+s-1;indices.push(a,b,a+1,a+1,b,b+1);}}});
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));g.setIndex(indices);return this.skin(g,this.material(color),name);
  }
  createGarments(){
    this.skirt=this.tube([[1.05,.20,.16,.025],[.96,.225,.17,.025],[.83,.235,.18,.025],[.65,.25,.185,.025],[.51,.26,.19,.025]],'Studio_Skirt','#23334a');
    this.vest=this.tube([[1.03,.195,.16,.03],[1.14,.18,.155,.035],[1.28,.225,.185,.035],[1.4,.235,.16,.025]],'Studio_Waistcoat','#273444',true);
    this.dress=this.tube([[1.06,.20,.16,.03],[1.01,.22,.17,.03],[.91,.24,.18,.03],[.75,.26,.19,.03],[.59,.29,.20,.03],[.46,.32,.22,.03]],'Studio_Dress_Skirt','#743a4c');
    this.shoes=[];
    for(const style of ['flats','trainers','heels'])for(const side of ['Left','Right']){
      const footIndex=this.reference.skeleton.bones.findIndex(b=>b.name===side+'Foot');
      if(footIndex<0)continue;
      // The sample's bind pose has widely spaced feet. Use its inverse-bind
      // translation so shoes stay centred when TalkingHead brings the feet in.
      const bindPosition=new THREE.Vector3().setFromMatrixPosition(this.reference.skeleton.boneInverses[footIndex].clone().invert());
      const x=bindPosition.x;
      const upper=new THREE.SphereGeometry(1,24,14);
      upper.scale(style==='trainers'?.049:.045,style==='trainers'?.052:.047,style==='trainers'?.14:.135);upper.translate(x,style==='heels'?.065:.042,.085);
      const sole=new THREE.BoxGeometry(style==='trainers'?.085:.075,style==='trainers'?.025:.018,.235);sole.translate(x,style==='trainers'?.012:.009,.085);
      const parts=[upper,sole];
      if(style==='heels'){const heel=new THREE.BoxGeometry(.027,.06,.032);heel.translate(x,.035,-.005);parts.push(heel);}
      const geometry=mergeGeometries(parts);parts.forEach(g=>g.dispose());
      const mesh=this.skin(geometry,this.material('#222529'),`Studio_${side}_${style}`);mesh.userData.footwear=style;
      const index=geometry.getAttribute('skinIndex'),weight=geometry.getAttribute('skinWeight');
      for(let i=0;i<index.count;i++){index.setXYZW(i,footIndex,0,0,0);weight.setXYZW(i,1,0,0,0);}
      index.needsUpdate=true;weight.needsUpdate=true;
      this.shoes.push(mesh);
    }
    this.set('office','flats');
  }
  set(outfit,footwear='flats'){
    if(!this.reference)return false;
    if(outfit!=='base')for(const item of this.original){item.mat.map=outfit==='original'?item.map:null;item.mat.color.set(outfit==='dress'?'#743a4c':outfit==='casual'?'#c4b294':'#34465d');if(outfit==='original')item.mat.color.copy(item.color);item.mat.needsUpdate=true;}
    this.skirt.visible=outfit==='office';this.vest.visible=outfit==='office';this.dress.visible=outfit==='dress';
    this.shoes.forEach(mesh=>{mesh.visible=mesh.userData.footwear===footwear;mesh.material.color.set(footwear==='trainers'?'#dcd8cb':'#1c2024');});
    this.current=outfit;return true;
  }
  garments(){return [...this.layers.filter(mesh=>!mesh.userData.footwear),...this.tagged].map(mesh=>({id:mesh.name,name:mesh.userData.wardrobeLabel||mesh.name.replace(/^Studio_/,'').replaceAll('_',' '),visible:mesh.visible}));}
  setGarment(id,visible){const mesh=[...this.layers,...this.tagged].find(item=>item.name===id);if(!mesh)throw new Error('This character has no matching garment.');mesh.visible=!!visible;return true;}
  dispose(){for(const mesh of new Set([...this.layers,...this.shoes])){mesh.removeFromParent();mesh.geometry.dispose();mesh.material.dispose();}}
}
