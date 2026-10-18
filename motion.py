"""Bounded motion data. Model-generated plans can never execute program code."""
import math
import re
import requests

SKILLS={'reach','jig','dance','walk','turn','stretch','bow','sit','kneel','lie_back','splits','idle','custom'}
TARGETS={'shoulder','head','chin','chest','belly','hip','knee','ear','nose'}
BONES={'Hips','Spine','Spine1','Spine2','Neck','Head'} | {side+name for side in ('Left','Right') for name in ('Shoulder','Arm','ForeArm','Hand','UpLeg','Leg','Foot')}


def validate_plan(value):
    if not isinstance(value,dict) or not isinstance(value.get('steps'),list) or not 0<len(value['steps'])<=8:
        raise ValueError('A movement plan needs 1–8 steps.')
    steps=[]
    for item in value['steps']:
        if not isinstance(item,dict) or item.get('skill') not in SKILLS:raise ValueError('Unknown movement skill.')
        duration=item.get('duration',4)
        intensity=item.get('intensity',.6)
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (duration,intensity)):
            raise ValueError('Invalid movement timing.')
        step={'skill':item['skill'],'duration':max(1,min(20,duration)),'intensity':max(.1,min(1,intensity)),
              'side':'left' if item.get('side')=='left' else 'right'}
        if step['skill']=='reach':
            if item.get('target') not in TARGETS:raise ValueError('Unknown body target.')
            step['target']=item['target']
        if step['skill']=='custom':
            frames=item.get('frames')
            if not isinstance(frames,list) or not 2<=len(frames)<=12:raise ValueError('Custom motion needs 2–12 keyframes.')
            cleaned=[];last=-1
            for frame in frames:
                if not isinstance(frame,dict):raise ValueError('Invalid keyframe.')
                at=frame.get('at');joints=frame.get('joints')
                if isinstance(at,bool) or not isinstance(at,(int,float)) or not math.isfinite(at) or not 0<=at<=1 or at<last or not isinstance(joints,dict):raise ValueError('Invalid keyframe timing.')
                pose={}
                for name,angles in joints.items():
                    if name not in BONES or not isinstance(angles,list) or len(angles)!=3:raise ValueError('Invalid joint.')
                    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or abs(x)>2.8 for x in angles):raise ValueError('Joint rotation exceeds the motion envelope.')
                    pose[name]=angles
                cleaned.append({'at':at,'joints':pose});last=at
            step['frames']=cleaned
        steps.append(step)
    return {'steps':steps}


def direct_plan(text):
    lower=text.lower();steps=[]
    if re.search(r"\b(?:don't|do not|avoid|without|stop)\b",lower):return None
    for match in re.finditer(r'(?:touch|rest|place|put|reach)[^.?!]{0,45}?(shoulder|belly button|belly|navel|head|chin|chest|hip|knee|ear|nose)',lower):
        target=match.group(1);target='belly' if target in {'belly button','navel'} else target
        steps.append({'_at':match.start(),'skill':'reach','target':target,'side':'left' if 'left hand' in match.group() else 'right','duration':4})
    for pattern,skill in [(r'\bjig\b','jig'),(r'\bdanc(?:e|ing)\b','dance'),(r'\bsplits\b','splits'),(r'lie (?:down |on (?:your|her) )?back|lying on.*back','lie_back'),(r'\bkneel','kneel'),(r'\bsit\b','sit'),(r'\bstretch','stretch'),(r'\bwalk','walk'),(r'\bturn around|\bspin','turn'),(r'\bbow\b','bow')]:
        if re.search(pattern,lower) and not (skill=='dance' and any(s['skill']=='jig' for s in steps)):
            steps.append({'_at':re.search(pattern,lower).start(),'skill':skill,'duration':8 if skill in {'jig','dance','walk'} else 5})
    return validate_plan({'steps':sorted(steps,key=lambda x:x['_at'])[:8]}) if steps else None


def generate_plan(prompt,persona,model,ollama):
    direct=None if prompt.startswith('Choose') else direct_plan(prompt)
    if direct:return direct
    response=requests.post(ollama+'/api/chat',json={'model':model,'stream':False,'format':'json','messages':[
        {'role':'system','content':'You plan physical movement for an adult 3D character. Return a short sequence of body skills. For a new movement use custom with 2-6 frames: at is a normalised time 0 to 1, joints map bone names to relative XYZ Euler angles in radians between -2.8 and 2.8. Mixamo rig, arms relaxed at rest. Prefer modest rotations. Movement must fit the persona. No claims of real-world action. Persona: '+persona},
        {'role':'user','content':prompt+' Return {"steps":[{"skill":"...","duration":4,"intensity":0.5}]}. Available skills: '+', '.join(sorted(SKILLS))+'. For reach include target and side. Return 1–3 short steps.'}], 'options':{'num_predict':192,'num_ctx':4096,'temperature':.5}},timeout=(5,12))
    response.raise_for_status()
    import json
    return validate_plan(json.loads(response.json()['message']['content']))
