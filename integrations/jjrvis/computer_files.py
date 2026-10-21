"""Fresh, owner-only Mac document search; explicit read and open actions."""
import hashlib,io,json,os,stat,subprocess,time,zipfile
from pathlib import Path
from datetime import datetime,timezone
from xml.etree import ElementTree as ET
from fastapi import HTTPException,Request
from fastapi.responses import Response
from jjrvis_core import SENSITIVE,redact,open_indexed_file

TYPES={'.txt','.md','.csv','.json','.pdf','.docx','.xlsx','.doc','.xls','.numbers','.pages','.pptx','.key','.png','.jpg','.jpeg','.webp'}
PREVIEW={'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}
APPS={'Excel':['/Applications/Microsoft Excel.app'],'Numbers':['/Applications/Numbers.app'],'Word':['/Applications/Microsoft Word.app'],'Pages':['/Applications/Pages.app'],'Acrobat':['/Applications/Adobe Acrobat/Adobe Acrobat.app','/Applications/Adobe Acrobat Reader.app'],'Preview':['/System/Applications/Preview.app'],'Safari':['/Applications/Safari.app'],'Notes':['/System/Applications/Notes.app']}

class ComputerFiles:
    def __init__(self,roots=None,runner=subprocess.run):
        self.roots=tuple(Path(p).absolute() for p in (roots or [Path.home()/x for x in ('Documents','Desktop','Downloads')]))
        self.runner=runner;self.entries={}
    def valid(self,path):
        root=next((r for r in self.roots if path.is_absolute() and path.is_relative_to(r)),None)
        if root is None:return False
        relative=path.relative_to(root)
        return path.suffix.lower() in TYPES and not SENSITIVE.search(str(relative)) and not any(p.startswith('.') for p in relative.parts) and not any(p in {'node_modules','Library','CloudStorage','Mobile Documents'} for p in relative.parts)
    def register(self,path):
        path=Path(path)
        if not self.valid(path):return None
        try:
            if path.resolve(strict=True)!=path:return None
            meta=path.stat()
            if not stat.S_ISREG(meta.st_mode):return None
        except OSError:return None
        key=hashlib.sha256(str(path).encode()).hexdigest()[:24]
        self.entries[key]=(path,time.monotonic())
        if len(self.entries)>500:self.entries.pop(next(iter(self.entries)))
        return {'id':key,'name':path.name,'folder':str(path.parent),'bytes':meta.st_size,'modified_at':meta.st_mtime,'type':path.suffix.lower().lstrip('.')}
    def search(self,query):
        query=query.strip()
        if len(query)<2:return {'files':[],'detail':'Enter at least two letters. Search covers Documents, Desktop and Downloads on the Mac running JJRVIS.','roots':[str(p) for p in self.roots]}
        if len(query)>160:raise HTTPException(400,'Search is limited to 160 characters')
        term=query.replace('\\','\\\\').replace('"','\\"').replace('*','').replace('?','')
        args=['/usr/bin/mdfind','-0','-onlyin',os.path.commonpath(self.roots)]
        args += [f'(kMDItemFSName == "*{term}*"cd || kMDItemTextContent == "*{term}*"cd)']
        try:r=self.runner(args,capture_output=True,timeout=8,check=False)
        except (OSError,subprocess.TimeoutExpired):return {'files':[],'detail':'Mac search is unavailable or timed out. Choose a file below instead.','roots':[str(p) for p in self.roots]}
        rows=[]
        for value in r.stdout[:2_000_000].decode('utf8','replace').split('\0'):
            if value and (row:=self.register(value)):rows.append(row)
            if len(rows)>=60:break
        rows.sort(key=lambda p:p['modified_at'],reverse=True)
        return {'files':rows,'detail':'Fresh Spotlight results · locally downloaded documents only. Cloud-only, unindexed or protected files may be missing.','roots':[str(p) for p in self.roots]}
    def path(self,key):
        value=self.entries.get(key)
        if not value or time.monotonic()-value[1]>1800:raise HTTPException(404,'Search again to reopen this document')
        path=value[0]
        try:
            if not self.valid(path) or path.resolve(strict=True)!=path:raise OSError('Path changed')
        except OSError:raise HTTPException(404,'Document is no longer available')
        return path
    def data(self,key):
        try:
            path=self.path(key);fd=open_indexed_file(path)
            with os.fdopen(fd,'rb') as f:
                meta=os.fstat(f.fileno())
                if not stat.S_ISREG(meta.st_mode) or meta.st_size>20_000_000:raise HTTPException(413,'Preview is limited to 20 MB. Open the document on the Mac instead.')
                raw=f.read(20_000_001)
            return path,raw
        except OSError:raise HTTPException(404,'Document unavailable. Download it locally or check Mac permissions.')
    def pdf(self,raw,page=None):
        helper=Path(__file__).parent/".runtime/mac-pdf-preview"
        if not helper.is_file():raise HTTPException(503,"PDF preview is unavailable. Open the original on this Mac.")
        try:
            result=self.runner([str(helper)]+([] if page is None else [str(page)]),input=raw,capture_output=True,timeout=8,check=True)
            return json.loads(result.stdout) if page is None else result.stdout
        except (OSError,ValueError,subprocess.SubprocessError):raise HTTPException(415,"PDF is locked or cannot be previewed. Open the original on this Mac.")
    def preview(self,key):
        path,raw=self.data(key);ext=path.suffix.lower()
        if ext=='.pdf':
            info=self.pdf(raw)
            if not info.get('pages'):raise HTTPException(415,'This PDF has no pages')
            return {'name':path.name,'format':'pdf','text':redact(info.get('text','')),'truncated':info.get('truncated',False),'pages':min(info['pages'],200),'url':'/v1/workspace/computer/file/'+key+'/pdf/','detail':'Read-only page preview · up to 200 pages · open the original for search and full detail'}
        if ext in PREVIEW:return {'name':path.name,'format':'visual','url':'/v1/workspace/computer/file/'+key+'/content','mime':PREVIEW[ext]}
        if ext in {'.docx','.xlsx','.pptx'}:
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    if sum(x.file_size for x in z.infolist())>30_000_000:raise ValueError('Oversized document')
                    names=['word/document.xml'] if ext=='.docx' else sorted(n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'))[:5] if ext=='.xlsx' else sorted(n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml'))[:20]
                    def xml(name):
                        data=z.read(name)
                        if len(data)>6_000_000 or b'<!DOCTYPE' in data or b'<!ENTITY' in data:raise ValueError('Unsupported XML')
                        return ET.fromstring(data)
                    strings=[]
                    if ext=='.xlsx' and 'xl/sharedStrings.xml' in z.namelist():strings=[''.join(n.itertext()) for n in xml('xl/sharedStrings.xml')]
                    parts=[]
                    for name in names:
                        doc=xml(name)
                        if ext=='.xlsx':
                            parts.append(name.rsplit('/',1)[-1])
                            for row in doc.findall('.//{*}row')[:200]:
                                cells=[]
                                for cell in list(row)[:30]:
                                    val=cell.find('{*}v');text=val.text if val is not None else ''.join(cell.itertext());text=text or ''
                                    if cell.get('t')=='s' and text.isdigit():text=strings[int(text)] if int(text)<len(strings) else ''
                                    cells.append(text)
                                parts.append('\t'.join(cells))
                        else:parts.extend(''.join(n.itertext()) for n in doc.findall('.//{*}p'))
                    text='\n'.join(parts)
            except (ValueError,KeyError,zipfile.BadZipFile,ET.ParseError):raise HTTPException(415,'This document cannot be previewed here. Open it in its original app.')
        elif ext in {'.txt','.md','.csv','.json'}:text=raw[:250_000].decode('utf8','replace')
        else:return {'name':path.name,'format':'native','text':'Use Open on this Mac to view this format in its original application.'}
        return {'name':path.name,'format':'text','text':redact(text[:60_000]),'truncated':len(text)>60_000,'detail':'Read-only extracted text; original formatting, formulas and macros are not executed.'}
    def context(self,key):
        preview=self.preview(key)
        if not preview.get('text') or preview['format'] not in {'text','pdf'}:raise HTTPException(415,'This document needs its original application or a text export for AI reading')
        path=self.path(key)
        return {**preview,'path':str(path),'modified_at':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),'mode':'selected_local_read_only'}
    def open(self,key):
        path=self.path(key)
        self.runner(['/usr/bin/open',str(path)],check=True,timeout=8,capture_output=True)
        return {'state':'open_requested','detail':'Asked macOS to open the original document. This does not confirm an edit or save.'}

def register_routes(app,secure):
    service=ComputerFiles();app.state.computer_files=service
    @app.get('/v1/workspace/computer/files',dependencies=secure)
    def search(q:str=''):return service.search(q)
    @app.get('/v1/workspace/computer/file/{key}',dependencies=secure)
    def preview(key:str):return service.preview(key)
    @app.get('/v1/workspace/computer/file/{key}/content',dependencies=secure)
    def content(key:str,request:Request):
        path,data=service.data(key);mime=PREVIEW.get(path.suffix.lower())
        request.state.presence_frame=True
        request.state.presence_csp="default-src 'none'; frame-ancestors 'self'; sandbox"
        if not mime:raise HTTPException(415,'No visual preview for this document')
        return Response(data,media_type=mime,headers={'Cache-Control':'private, no-store','Content-Disposition':'inline','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; frame-ancestors 'self'; sandbox"})
    @app.get('/v1/workspace/computer/file/{key}/pdf/{page}',dependencies=secure)
    def pdf_page(key:str,page:int):
        if page<0 or page>=200:raise HTTPException(400,'Page outside preview range')
        path,data=service.data(key)
        if path.suffix.lower()!='.pdf':raise HTTPException(415,'Not a PDF')
        return Response(service.pdf(data,page),media_type='image/png',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
    @app.post('/v1/workspace/computer/file/{key}/open',dependencies=secure)
    def open_file(key:str):
        try:return service.open(key)
        except (OSError,subprocess.SubprocessError):raise HTTPException(503,'macOS could not open this file')
    @app.get('/v1/workspace/computer/apps',dependencies=secure)
    def apps():return {'apps':[{'name':name,'installed':any(Path(p).exists() for p in paths)} for name,paths in APPS.items()],'detail':'Open a search result to launch its default Mac app. Reading and editing app accounts require separate integrations.'}

    @app.post('/v1/workspace/computer/apps/{name}/open',dependencies=secure)
    def open_app(name:str):
        candidate=next((p for p in APPS.get(name,[]) if Path(p).exists()),None)
        if not candidate:raise HTTPException(404,'This application is not installed in a supported location')
        try:service.runner(['/usr/bin/open','-a',candidate],check=True,timeout=8,capture_output=True)
        except (OSError,subprocess.SubprocessError):raise HTTPException(503,'macOS could not open the application')
        return {'state':'open_requested','name':name}
