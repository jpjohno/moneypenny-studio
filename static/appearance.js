import * as THREE from 'three';

const looks={
  daylight:{ambient:.28,key:1.5,fill:.85,environment:.65,exposure:.91,keyColor:'#fff8f3',fillColor:'#edf3ff'},
  portrait:{ambient:.22,key:1.65,fill:.8,environment:.58,exposure:.9,keyColor:'#fff5ef',fillColor:'#edf2ff'},
  neutral:{ambient:.35,key:1.3,fill:.7,environment:.75,exposure:.88,keyColor:'#ffffff',fillColor:'#ffffff'},
};

const hairOriginals=new WeakMap();
export function setHairTone(root,tone='darkblonde'){
  const tint=new THREE.Color(({original:'#ffffff',warm:'#e4c9a4',darkblonde:'#b5c4ad',brunette:'#82634d'})[tone]||'#ffffff');
  root.traverse(node=>{
    if(!node.isMesh)return;
    for(const material of [node.material].flat()){
      if(!material?.color||!['VitHair','Soft blonde root underlayer'].includes(material.name))continue;
      if(!hairOriginals.has(material))hairOriginals.set(material,material.color.clone());
      // This groom already carries its authored dark-blonde colour in glTF.
      // Applying the older green-grey sample tint again gives an olive cast.
      const authoredBlonde=tone==='darkblonde'&&/^v39\b/.test(node.userData?.groom_revision||'');
      material.color.copy(hairOriginals.get(material));
      if(!authoredBlonde)material.color.multiply(tint);
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
    // Cutout eyelashes/cards use no alpha-aware depth material here. Their
    // ordinary shadow pass creates jagged dark triangles across the face.
    const fineHair=materials.some(material=>/hair|brow|eyelash/i.test(material.name));
    node.castShadow=!fineHair&&materials.some(material=>!material.transparent&&!(material.transmission>0));
    node.receiveShadow=materials.some(material=>!(material.transmission>0));
    for(const material of materials){
      if(!material||seen.has(material))continue;
      seen.add(material);material.dithering=true;
      for(const key of ['map','normalMap','roughnessMap','metalnessMap','alphaMap']){
        if(material[key]){material[key].anisotropy=anisotropy;material[key].needsUpdate=true;}
      }
      if(/eyelash/i.test(material.name)){
        // Sort the fine lash silhouette by its actual alpha, not as a blended
        // rectangular card that can cover an eye or leave a cheek triangle.
        material.transparent=false;material.opacity=1;material.alphaTest=.35;
        material.alphaToCoverage=true;material.depthWrite=true;
        material.roughness=.7;material.envMapIntensity=.2;
      }
      if(material.name==='VitHair'&&material.alphaTest>0){
        // Coverage antialiasing softens cutout strand edges in the MSAA canvas.
        // Recover fine ends from the existing continuous mask, retaining depth
        // writing so overlapping cards cannot self-sort through the face.
        material.alphaTest=Math.min(material.alphaTest,.26);
        material.alphaToCoverage=true;
        material.roughness=.58;
        material.normalScale?.set(.08,.08);
        if(material.isMeshPhysicalMaterial){
          // Fibres run along V in this atlas. Broaden highlights across U while
          // keeping their longitudinal response restrained and non-metallic.
          material.anisotropy=.55;material.anisotropyRotation=0;
          material.specularIntensity=Math.min(material.specularIntensity,.28);
        }
      }
      if(material.name==='Corneal optical surface'&&material.isMeshPhysicalMaterial){
        // A thin corneal highlight does not need a full-scene transmission
        // capture every frame. The detailed iris remains in the original atlas.
        material.transmission=0;material.transparent=true;material.opacity=.08;
        material.depthWrite=false;material.clearcoat=.5;material.clearcoatRoughness=.08;
        material.envMapIntensity=.8;
      }
      if(material.name.startsWith('Performance skin')){
        material.envMapIntensity=.8;
        // The old procedural map carries large facial relief as well as pores.
        // Reduce that relief; the actual skin colour/UVs stay intact.
        material.normalScale?.set(.3,.3);
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
    lightDirectColor:look.keyColor,lightDirectPhi:1.05,lightDirectTheta:.35,
    lightSpotIntensity:look.fill,lightSpotColor:look.fillColor,lightSpotPhi:1.15,lightSpotTheta:-.65});
  // TalkingHead already owns one baked room reflection. Its default full-strength
  // fill flattens the face and groom; balance that existing light, without
  // generating another environment or changing the transparent background.
  if(head.scene?.environment)head.scene.environmentIntensity=look.environment;
  head.renderer.toneMappingExposure=look.exposure*exposure;
}
