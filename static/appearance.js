import * as THREE from 'three';

const looks={
  daylight:{ambient:.22,key:1.65,fill:.6,exposure:.83,keyColor:'#fff8f0',fillColor:'#e2ecff'},
  portrait:{ambient:.12,key:2.1,fill:.45,exposure:.82,keyColor:'#ffe9d5',fillColor:'#dce8ff'},
  neutral:{ambient:.35,key:1.3,fill:.7,exposure:.88,keyColor:'#ffffff',fillColor:'#ffffff'},
};

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

export function setLook(head,name='daylight',brightness=1){
  const look=looks[name]||looks.daylight;
  const value=Number(brightness);
  const exposure=Number.isFinite(value)?Math.max(.65,Math.min(1.25,value)):1;
  head.setLighting({lightAmbientIntensity:look.ambient,lightDirectIntensity:look.key,
    lightDirectColor:look.keyColor,lightDirectPhi:.9,lightDirectTheta:1,
    lightSpotIntensity:look.fill,lightSpotColor:look.fillColor,lightSpotPhi:.45,lightSpotTheta:4.2});
  head.renderer.toneMappingExposure=look.exposure*exposure;
}
