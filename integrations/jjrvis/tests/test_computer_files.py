import io,subprocess,zipfile
from pathlib import Path
import pytest
from fastapi import FastAPI,Depends,HTTPException,Request
from fastapi.testclient import TestClient
from computer_files import ComputerFiles,register_routes

def service(tmp_path):return ComputerFiles([tmp_path],runner=lambda *a,**k:subprocess.CompletedProcess(a,0,stdout=b''))
def test_current_search_registers_only_documents_and_excludes_symlinks_and_secrets(tmp_path):
    good=tmp_path/'Budget.txt';good.write_text('A budget');secret=tmp_path/'password.txt';secret.write_text('secret');link=tmp_path/'Alias.txt';link.symlink_to(good)
    s=service(tmp_path);s.runner=lambda *a,**k:subprocess.CompletedProcess(a,0,stdout=('\0'.join(map(str,[good,secret,link]))+'\0').encode())
    rows=s.search('Budget')['files'];assert [r['name'] for r in rows]==['Budget.txt'];assert s.preview(rows[0]['id'])['text']=='A budget'
    with pytest.raises(HTTPException):s.preview('unregistered')
def test_registered_path_cannot_be_replaced_by_a_symlink(tmp_path):
    p=tmp_path/'Readme.txt';p.write_text('safe');s=service(tmp_path);key=s.register(p)['id'];p.unlink();p.symlink_to(tmp_path/'outside.txt')
    with pytest.raises((HTTPException,OSError)):s.preview(key)
def test_word_and_excel_preview_extract_text_without_running_content(tmp_path):
    s=service(tmp_path);p=tmp_path/'Notes.docx'
    with zipfile.ZipFile(p,'w')as z:z.writestr('word/document.xml','<w:document xmlns:w="urn:w"><w:p><w:r><w:t>Meeting notes</w:t></w:r></w:p></w:document>')
    assert s.preview(s.register(p)['id'])['text']=='Meeting notes'
    p=tmp_path/'Costs.xlsx'
    with zipfile.ZipFile(p,'w')as z:
        z.writestr('xl/sharedStrings.xml','<sst><si><t>Cost</t></si></sst>')
        z.writestr('xl/worksheets/sheet1.xml','<worksheet><row><c t="s"><v>0</v></c><c><v>42</v></c></row></worksheet>')
    assert 'Cost\t42' in s.preview(s.register(p)['id'])['text']
def test_visual_preview_and_native_formats_are_explicit(tmp_path):
    s=service(tmp_path)
    for name,kind in [('scan.png','visual'),('sheet.numbers','native')]:
        p=tmp_path/name;p.write_bytes(b'fixture');result=s.preview(s.register(p)['id']);assert result['format']==kind

def test_document_routes_require_owner_and_pdf_frame_permission_is_scoped(tmp_path):
    app=FastAPI()
    def owner(request:Request):
        if request.headers.get('authorization')!='Bearer test-fixture':raise HTTPException(401)
    register_routes(app,[Depends(owner)]);actual=app.state.computer_files
    actual.roots=(tmp_path,);p=tmp_path/'scan.pdf';p.write_bytes(b'%PDF fixture');key=actual.register(p)['id']
    with TestClient(app)as client:
        assert client.get('/v1/workspace/computer/files?q=test').status_code==401
        assert client.get('/v1/workspace/computer/file/'+key).status_code==401
        result=client.get('/v1/workspace/computer/file/'+key+'/content',headers={'Authorization':'Bearer test-fixture'})
        assert result.status_code==200;assert result.headers['content-type']=='application/pdf';assert "frame-ancestors 'self'" in result.headers['content-security-policy']

def test_xml_entities_and_large_archives_are_not_expanded(tmp_path):
    s=service(tmp_path);p=tmp_path/'Danger.docx'
    with zipfile.ZipFile(p,'w')as z:z.writestr('word/document.xml','<!DOCTYPE x [<!ENTITY boom "expanded">]><document>&boom;</document>')
    with pytest.raises(HTTPException)as e:s.preview(s.register(p)['id'])
    assert e.value.status_code==415

def test_original_app_launch_is_explicit_and_uses_a_fixed_argument_list(tmp_path):
    p=tmp_path/'Costs with spaces.xlsx';p.write_text('fixture');calls=[];s=service(tmp_path);s.runner=lambda args,**kw:calls.append(args)
    key=s.register(p)['id'];assert calls==[];assert s.open(key)['state']=='open_requested';assert calls==[['/usr/bin/open',str(p)]]

def test_registered_visual_preview_keeps_owner_headers_without_weakening_workspace(tmp_path,monkeypatch):
    import jarvis_comm_broker as broker
    monkeypatch.setattr(broker,'HERE',tmp_path)
    (tmp_path/'workspace.html').write_text('<html><body>fixture workspace</body></html>')
    app=broker.create_app(broker.Settings(token='synthetic-computer-file-owner-token'),task_path=tmp_path/'tasks.sqlite')
    service=app.state.computer_files;service.roots=(tmp_path,);p=tmp_path/'Test.pdf';p.write_bytes(b'%PDF fixture');key=service.register(p)['id'];headers={'Authorization':'Bearer synthetic-computer-file-owner-token'}
    with TestClient(app,base_url='http://127.0.0.1:8766')as c:
        r=c.get('/v1/workspace/computer/file/'+key+'/content',headers=headers)
        assert r.headers['x-frame-options']=='SAMEORIGIN';assert "frame-ancestors 'self'" in r.headers['content-security-policy']
        assert c.get('/workspace').headers['x-frame-options']=='DENY'
        assert c.post('/v1/workspace/computer/file/'+key+'/open',json={}).status_code==401

def test_selected_office_document_context_is_available_even_when_old_index_is_text_only(tmp_path):
    from types import SimpleNamespace
    from jjrvis_core import Core
    # Read through the same production method without starting unrelated integrations.
    s=service(tmp_path);p=tmp_path/'Selected.docx'
    with zipfile.ZipFile(p,'w')as z:z.writestr('word/document.xml','<document><p>Selected project notes</p></document>')
    key=s.register(p)['id'];owner=SimpleNamespace(workspace=SimpleNamespace(inventory={'files':[{'path':str(p)}]}),computer_files=s)
    result=Core.read_file(owner,key);assert result['text']=='Selected project notes';assert result['mode']=='selected_local_read_only'


def test_pdf_pages_use_bounded_native_renderer_and_keep_owner_boundary(tmp_path):
    s=service(tmp_path);p=tmp_path/'Paper.pdf';p.write_bytes(b'%PDF fixture');key=s.register(p)['id']
    s.pdf=lambda raw,page=None: {'pages':3,'text':'Selected PDF words'} if page is None else b'png-fixture'
    result=s.preview(key);assert result['format']=='pdf';assert result['pages']==3;assert s.context(key)['text']=='Selected PDF words'
    app=FastAPI()
    def owner(request:Request):
        if request.headers.get('authorization')!='Bearer fixture':raise HTTPException(401)
    register_routes(app,[Depends(owner)]);app.state.computer_files.roots=(tmp_path,)
    registered=app.state.computer_files.register(p)['id'];app.state.computer_files.pdf=s.pdf
    with TestClient(app) as c:
        url='/v1/workspace/computer/file/'+registered+'/pdf/'
        assert c.get(url+'0').status_code==401
        assert c.get(url+'200',headers={'Authorization':'Bearer fixture'}).status_code==400
        r=c.get(url+'0',headers={'Authorization':'Bearer fixture'});assert r.content==b'png-fixture';assert r.headers['content-type']=='image/png'
