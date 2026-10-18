import * as THREE from 'three';

const looks={
  daylight:{ambient:.16,key:1.75,fill:.55,exposure:.84,keyColor:'#fff6ed',fillColor:'#e5edff'},
  portrait:{ambient:.12,key:1.95,fill:.5,exposure:.84,keyColor:'#fff0e2',fillColor:'#e1ebff'},
  neutral:{ambient:.35,key:1.3,fill:.7,exposure:.88,keyColor:'#ffffff',fillColor:'#ffffff'},
};

const hairOriginals=new WeakMap();
export function setHairTone(root,tone='darkblonde'){
  const tint=new THREE.Color(({original:'#ffffff',warm:'#e4c9a4',darkblonde:'#b8a591',brunette:'#82634d'})[tone]||'#ffffff');
  root.traverse(node=>{
    if(!node.isMesh)return;
    for(const material of [node.material].flat()){
      if(!material?.color||!['VitHair','Soft blonde root underlayer'].includes(material.name))continue;
      if(!hairOriginals.has(material))hairOriginals.set(material,material.color.clone());
      material.color.copy(hairOriginals.get(material)).multiply(tint);
    }
  });
}

// Material-only sample improvements preserve all original rig and mouth geometry.
// Imported production materials remain untouched.
export function prepareSampleMaterials(root){
  const originals=new Map(),created=[];
  root.traverse(node=>{
    if(!node.isMesh)return;
    node.castShadow=true;node.receiveShadow=true;
    const convert=source=>{
      if(originals.has(source))return originals.get(source);
      const name=source.name||'';
      if(!/Human\.(body|high-poly)$/.test(name))return source;
      const material=new THREE.MeshPhysicalMaterial();
      THREE.MeshStandardMaterial.prototype.copy.call(material,source);
      material.name=name;
      if(name.endsWith('.body')){
        material.roughness=.53;material.ior=1.4;material.specularIntensity=.4;
        material.clearcoat=.06;material.clearcoatRoughness=.55;material.envMapIntensity=.42;
      }else{
        material.roughness=.23;material.ior=1.38;material.clearcoat=.8;
        material.clearcoatRoughness=.08;material.envMapIntensity=.7;
      }
      originals.set(source,material);created.push(material);return material;
    };
    node.material=Array.isArray(node.material)?node.material.map(convert):convert(node.material);
  });
  return ()=>created.forEach(material=>material.dispose());
}

// The local asset already owns its textures, skin rig and facial shapes. Improve
// sampling and light response without replacing those production data.
export function prepareCharacterMaterials(root,renderer){
  const anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());
  const seen=new Set();
  root.traverse(node=>{
    if(!node.isMesh)return;
    const materials=[node.material].flat().filter(Boolean);
    // Transmission shells and blended eyelashes cannot cast physically correct
    // shadows with the standard shadow map; keep the iris and face unobscured.
    node.castShadow=materials.some(material=>material.alphaTest>0||(!material.transparent&&!(material.transmission>0)));
    node.receiveShadow=materials.some(material=>!(material.transmission>0));
    for(const material of materials){
      if(!material||seen.has(material))continue;
      seen.add(material);material.dithering=true;
      for(const key of ['map','normalMap','roughnessMap','metalnessMap','alphaMap']){
        if(material[key]){material[key].anisotropy=anisotropy;material[key].needsUpdate=true;}
      }
      if(material.name==='VitHair'&&material.alphaTest>0){
        // Coverage antialiasing softens cutout strand edges in the MSAA canvas.
        // Keep depth writing and the authored alpha threshold for card sorting.
        material.alphaToCoverage=true;
        material.roughness=Math.max(material.roughness,.66);
      }
      if(material.name==='Corneal optical surface'&&material.isMeshPhysicalMaterial){
        // A thin corneal highlight does not need a full-scene transmission
        // capture every frame. The detailed iris remains in the original atlas.
        material.transmission=0;material.transparent=true;material.opacity=.08;
        material.depthWrite=false;material.clearcoat=.35;material.clearcoatRoughness=.12;
        material.envMapIntensity=.65;
      }
      if(material.name.startsWith('Performance skin')){
        material.envMapIntensity=.8;
        if(material.isMeshPhysicalMaterial)material.specularIntensity=Math.min(material.specularIntensity,.5);
      }
      material.needsUpdate=true;
    }
  });
}

export function setLook(head,name='daylight',brightness=1){
  const look=looks[name]||looks.daylight;
  const value=Number(brightness);
  const exposure=Number.isFinite(value)?Math.max(.65,Math.min(1.25,value)):1;
  head.setLighting({lightAmbientIntensity:look.ambient,lightDirectIntensity:look.key,
    lightDirectColor:look.keyColor,lightDirectPhi:.9,lightDirectTheta:1,
    lightSpotIntensity:look.fill,lightSpotColor:look.fillColor,lightSpotPhi:.45,lightSpotTheta:4.2});
  head.renderer.toneMappingExposure=look.exposure*exposure;
}
