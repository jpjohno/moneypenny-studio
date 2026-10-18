import concurrent.futures
import math
import pytest
import app as studio
import reminders
from motion import direct_plan,validate_plan


def test_reach_and_full_body_sequences():
    assert direct_plan('Touch your shoulder')['steps'][0]['target']=='shoulder'
    assert direct_plan('Touch your belly button')['steps'][0]['target']=='belly'
    assert [x['skill'] for x in direct_plan('Dance a jig and bow')['steps']]==['jig','bow']
    assert direct_plan('Lie on your back')['steps'][0]['skill']=='lie_back'
    assert direct_plan('Do the splits')['steps'][0]['skill']=='splits'


@pytest.mark.parametrize('plan',[
    {'steps':[{'skill':'execute_python'}]},
    {'steps':[{'skill':'dance','duration':float('nan')}]},
    {'steps':[{'skill':'reach','target':'unknown'}]},
    {'steps':[{'skill':'custom','frames':[{'at':0,'joints':{'Head':[0,0,0]}},{'at':1,'joints':{'Head':[9,0,0]}}]}]},
    {'steps':[{'skill':'custom','frames':[{'at':1,'joints':{}},{'at':0,'joints':{}}]}]},
])
def test_untrusted_motion_is_bounded(plan):
    with pytest.raises(ValueError):validate_plan(plan)


def test_authored_joint_animation_is_supported():
    result=validate_plan({'steps':[{'skill':'custom','duration':3,'frames':[
        {'at':0,'joints':{'LeftArm':[0,0,-.2],'RightUpLeg':[.2,0,0]}},
        {'at':1,'joints':{'LeftArm':[0,0,.2],'RightUpLeg':[-.2,0,0]}}]}]})
    assert result['steps'][0]['frames'][1]['joints']['RightUpLeg']==[-.2,0,0]


def test_reminder_survives_reopen_and_is_claimed_once(tmp_path,monkeypatch):
    monkeypatch.setattr(reminders,'PATH',tmp_path/'reminders.sqlite3')
    reminder=reminders.add('Ask whether I am ready',-1)
    assert reminders.pending()[0]['id']==reminder['id']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:reminders.claim(reminder['id']),range(4)))
    assert sum(results)==1
    assert reminders.pending()==[]


def test_followup_request_validation(tmp_path,monkeypatch):
    monkeypatch.setattr(reminders,'PATH',tmp_path/'reminders.sqlite3')
    client=studio.app.test_client();headers={'X-Studio-Client':'moneypenny'}
    assert client.post('/api/reminders',headers=headers,json={'text':'hello','delay':0}).status_code==400
    result=client.post('/api/reminders',headers=headers,json={'text':'Ask if I have finished','delay':600})
    assert result.status_code==200
    assert client.post('/api/reminders/'+result.json['id']+'/claim',headers=headers,json={}).json=={'claimed':False}
