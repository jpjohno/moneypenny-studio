import * as THREE from 'three';

// Closed, opaque support for the clothed step study. No hygiene animation.
export class SeatSupport {
  constructor(scene,rig) {
    this.rig=rig;this.group=new THREE.Group();scene.add(this.group);
    this.material=new THREE.MeshStandardMaterial({color:0xeae8e0,roughness:.3});
    const mesh=(geometry,position,scale)=>{
      const item=new THREE.Mesh(geometry,this.material);item.position.set(...position);item.scale.set(...scale);
      item.castShadow=true;item.receiveShadow=true;this.group.add(item);
    };
    mesh(new THREE.CylinderGeometry(1,1,1,48),[0,-.018,0],[.19,.036,.255]);
    mesh(new THREE.CylinderGeometry(.14,.11,.34,32),[0,-.205,.045],[1,1,1]);
    mesh(new THREE.BoxGeometry(.34,.36,.12),[0,.04,.27],[1,1,1]);
    this.group.visible=false;
  }
  update(motion) {
    const active=motion?.active;
    this.group.visible=active?.skill==='supported_step';
    if(!this.group.visible)return;
    const step=this.rig.supportedStep(active.side),anchor=step.target.clone();
    anchor.y=step.height;anchor.z+=.08*step.scale;
    this.group.position.copy(this.rig.world(anchor));
    this.rig.space.decompose(new THREE.Vector3(),this.group.quaternion,this.group.scale);
    this.group.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),step.raised==='LeftFoot'?Math.PI/2:-Math.PI/2));
    this.group.scale.multiplyScalar(step.scale);
  }
  dispose(){this.group.traverse(node=>node.geometry?.dispose());this.material.dispose();this.group.removeFromParent();}
}
