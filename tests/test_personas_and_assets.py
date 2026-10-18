import json
from types import SimpleNamespace
import pytest
import app
import personas
import motion_assets


def test_named_personas_persist_and_saved_prompt_is_used(tmp_path,monkeypatch):
    monkeypatch.setattr(personas,'PATH',tmp_path/'personas.sqlite3')
    value=personas.save({'name':'Test tutor','model':'uncensored-3b:latest','system':'Explain astronomy clearly.','settings':{}})
    result=app.chat_payload({'prompt':'Hello','persona_id':value['id'],'model':'wrong','system':'wrong'})
    assert result['model']=='uncensored-3b:latest'
    assert result['messages'][0]['content'].startswith('Explain astronomy clearly.')
    assert personas.local()[0]['id']==value['id']


def test_webui_reads_only_the_model_catalogue(monkeypatch):
    def run(command,**kwargs):
        assert command[:5]==['docker','exec','open-webui','python','-c']
        query=command[-1]
        assert '?mode=ro' in query and 'SELECT id,name,base_model_id,params,meta FROM model' in query
        assert all(word not in query.lower() for word in ['update ','insert ','delete ',' from auth',' from user',' from chat'])
        return SimpleNamespace(stdout=json.dumps([{'id':'tutor','name':'Tutor','base_model_id':'uncensored-3b:latest','params':{'system':'Astronomy tutor'},'meta':{}}]))
    monkeypatch.setattr(personas.subprocess,'run',run)
    result,error=personas.webui();assert error is None
    assert result[0]['system']=='Astronomy tutor' and result[0]['model']=='uncensored-3b:latest'


def test_referenced_knowledge_is_never_silently_omitted(monkeypatch):
    monkeypatch.setattr(personas,'webui',lambda:([{'id':'webui:tutor','knowledge_count':1}],None))
    with pytest.raises(ValueError,match='authenticated'):personas.resolve('webui:tutor')


def test_uploaded_motion_persists_and_executable_data_is_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr(motion_assets,'DIRECTORY',tmp_path/'library')
    data={'version':1,'duration':2,'frames':[{'at':0,'joints':{'Spine':[0,0,0]}},{'at':1,'joints':{'Spine':[.2,0,0]}}]}
    record=motion_assets.add('Bow','bow.motion.json',json.dumps(data).encode())
    assert any(r['id']==record['id'] for r in motion_assets.library())
    assert (motion_assets.DIRECTORY/motion_assets.asset(record['id'])).is_file()
    data['frames'][1]['joints']={'execute_python':[0,0,0]}
    with pytest.raises(ValueError):motion_assets.add('Bad','bad.motion.json',json.dumps(data).encode())


def test_animation_assets_reject_external_resources(tmp_path,monkeypatch):
    import struct
    monkeypatch.setattr(motion_assets,'DIRECTORY',tmp_path/'library')
    value=json.dumps({'animations':[{}],'buffers':[{'uri':'https://example.com/private'}]}).encode();value+=b' '*((-len(value))%4)
    glb=b'glTF'+struct.pack('<IIII',2,20+len(value),len(value),0x4e4f534a)+value
    with pytest.raises(ValueError,match='external'):motion_assets.add('Unsafe','unsafe.glb',glb)
