import * as THREE from 'three';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
export class RigView {
  constructor(head,rig,onChange){
    Object.assign(this,{head,rig,onChange});this.selected='RightHand';this.visible=false;
    this.marker=new THREE.Mesh(new THREE.SphereGeometry(.025,12,8),new THREE.MeshBasicMaterial({color:0xcde7a4,depthTest:false}));this.marker.renderOrder=20;head.scene.add(this.marker);
    this.gizmo=new TransformControls(head.camera,head.renderer.domElement);this.gizmo.setMode('translate');this.gizmo.setSpace('world');this.gizmo.setSize(.6);head.scene.add(this.gizmo.getHelper());this.gizmo.attach(this.marker);
    this.skeleton=new THREE.SkeletonHelper(head.armature);this.skeleton.material.depthTest=false;this.skeleton.material.transparent=true;this.skeleton.material.opacity=.65;head.scene.add(this.skeleton);
    this.gizmo.addEventListener('dragging-changed',event=>{if(head.controls)head.controls.enabled=!event.value;});
    this.gizmo.addEventListener('objectChange',()=>{
      const local=this.marker.position.clone().applyMatrix4(rig.space.clone().invert());const target=rig.setTarget(this.selected,local.toArray());this.onChange(this.selected,target,true);
    });
    this.show(false);this.select(this.selected);
  }
  select(name){if(!this.rig.neutral[name])return;this.selected=name;const target=this.rig.targets.get(name)||this.rig.neutral[name];this.marker.position.copy(this.rig.world(target));this.onChange(name,target,this.rig.targets.has(name));}
  show(value){this.visible=value;this.marker.visible=value;this.skeleton.visible=value;this.gizmo.enabled=value;this.gizmo.getHelper().visible=value;}
  update(){if(!this.gizmo.dragging){const target=this.rig.targets.get(this.selected);if(target)this.marker.position.copy(this.rig.world(target));else this.rig.bones[this.selected]?.getWorldPosition(this.marker.position);}this.skeleton.updateMatrixWorld(true);}
  dispose(){this.gizmo.detach();this.gizmo.dispose();this.gizmo.getHelper().removeFromParent();this.marker.removeFromParent();this.marker.geometry.dispose();this.marker.material.dispose();this.skeleton.removeFromParent();this.skeleton.geometry.dispose();this.skeleton.material.dispose();}
}
