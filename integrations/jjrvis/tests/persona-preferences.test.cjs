const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'..','workspace.js'),'utf8');
const start=source.indexOf('function personaPreferenceLabel('),end=source.indexOf('async function mountAssistantPreferences(',start);
assert.ok(start>0&&end>start);
const api={esc:value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;')};
vm.createContext(api);vm.runInContext(source.slice(start,end),api);
const persona={state:'saved',id:'fixture-id',name:'Rowan',source:'Studio · saved on this Mac',choices:[{id:'fixture-id',name:'Rowan'}]};
test('saved character status identifies source without implying model or voice replacement',()=>{
 const label=api.personaPreferenceLabel(persona);
 assert.match(label,/Rowan.*Studio/);assert.match(label,/Voice and answer model are selected separately/);
});
test('built-in and unavailable states give an explicit recovery path',()=>{
 assert.match(api.personaPreferenceLabel({state:'built_in'}),/built-in character/);
 assert.match(api.personaPreferenceLabel({state:'unavailable'}),/unavailable.*Reselect.*no other saved personality was substituted/);
});
test('selected saved record remains selected alongside the explicit built-in choice',()=>{
 const options=api.personaPreferenceOptions(persona);
 assert.match(options,/<option value="" >JJRVIS built-in character/);
 assert.match(options,/<option value="fixture-id" selected>Rowan · saved in Studio/);
});
test('missing saved record is retained visibly rather than silently selecting built-in',()=>{
 const options=api.personaPreferenceOptions({...persona,state:'unavailable',choices:[]});
 assert.match(options,/<option value="fixture-id" selected>Saved persona unavailable/);
 assert.doesNotMatch(options,/<option value="" selected>/);
});
test('names and ids are escaped instead of being treated as markup',()=>{
 const options=api.personaPreferenceOptions({...persona,id:'<id>',choices:[{id:'<id>',name:'<img src=x>'}]});
 assert.doesNotMatch(options,/<img/);assert.match(options,/&lt;img/);assert.match(options,/value="&lt;id>/);
});
