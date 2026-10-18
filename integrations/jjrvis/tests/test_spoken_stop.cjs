const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(require('path').join(__dirname,'../workspace.js'),'utf8');
const start=source.indexOf('function isVoiceStopCommand('),end=source.indexOf('\nfunction voiceState',start);
const context={};vm.createContext(context);vm.runInContext(source.slice(start,end),context);
for(const text of ['stop','Stop!','Moneypenny, stop','please stop speaking','Jarvis stop please'])assert.equal(context.isVoiceStopCommand(text),true,text);
for(const text of ['do not stop','the next stop is London','stop music','what happens if I say stop'])assert.equal(context.isVoiceStopCommand(text),false,text);
console.log('Spoken stop: direct commands accepted, unrelated speech rejected');
