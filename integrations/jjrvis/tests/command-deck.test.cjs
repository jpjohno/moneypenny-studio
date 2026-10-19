'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../command-deck.js'),'utf8');
function harness(){
 const timers=new Map(),windowListeners=new Map();let timerId=0;
 class Node{
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.ownerDocument=document;this.childNodes=[];this.parentNode=null;this.attributes={};this.dataset={};this.listeners=new Map();this.className='';this.open=false;this.hidden=false;this.isConnected=true;this._text='';this._html='';}
  get classList(){const self=this;return {contains:name=>self.className.split(/\s+/).includes(name),add(...names){self.className=[...new Set([...self.className.split(/\s+/).filter(Boolean),...names])].join(' ');},remove(...names){self.className=self.className.split(/\s+/).filter(name=>!names.includes(name)).join(' ');},toggle(name,on){if(on===undefined)on=!this.contains(name);on?this.add(name):this.remove(name);return on;}};}
  set textContent(value){this._text=String(value);this.childNodes=[];}get textContent(){return this._text+this.childNodes.map(node=>node.textContent).join('');}
  set innerHTML(value){this._html=value;this.replaceChildren();const stack=[this],parts=String(value).match(/<[^>]+>|[^<]+/g)||[];for(const part of parts){if(part.startsWith('</')){if(stack.length>1)stack.pop();continue;}if(part.startsWith('<')){const tag=part.match(/^<([\w-]+)/)?.[1];if(!tag)continue;const node=new Node(tag);for(const attr of part.matchAll(/([\w-]+)="([^"]*)"/g))node.setAttribute(attr[1],attr[2]);stack.at(-1).append(node);if(!['input','br','img','hr','meta','link'].includes(tag))stack.push(node);}else stack.at(-1)._text+=part;}}get innerHTML(){return this._html;}
  setAttribute(name,value){value=String(value);if(name==='class')this.className=value;else if(name==='id')this.id=value;this.attributes[name]=value;if(name.startsWith('data-'))this.dataset[name.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=value;}
  getAttribute(name){if(name==='class')return this.className||null;return Object.hasOwn(this.attributes,name)?this.attributes[name]:null;}
  removeAttribute(name){delete this.attributes[name];}
  append(...nodes){for(const node of nodes){if(node.parentNode)node.parentNode.childNodes=node.parentNode.childNodes.filter(child=>child!==node);node.parentNode=this;this.childNodes.push(node);}}
  replaceChildren(...nodes){for(const node of this.childNodes)node.parentNode=null;this.childNodes=[];this._text='';this.append(...nodes);}
  contains(node){return node===this||this.childNodes.some(child=>child.contains(node));}
  matches(selector){if(selector==='[hidden]')return this.hidden;const tag=selector.match(/^[a-z]+/i)?.[0];if(tag&&this.tagName!==tag.toUpperCase())return false;const cls=selector.match(/\.([\w-]+)/)?.[1];if(cls&&!this.classList.contains(cls))return false;const attr=selector.match(/\[([\w-]+)(?:="([^"]*)")?\]/);if(attr){const value=this.getAttribute(attr[1]);if(value===null||attr[2]!==undefined&&value!==attr[2])return false;}return Boolean(tag||cls||attr);}
  querySelectorAll(selector){const found=[];for(const node of this.childNodes){if(node.matches(selector))found.push(node);found.push(...node.querySelectorAll(selector));}return found;}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  closest(selector){return this.matches(selector)?this:this.parentNode?.closest?.(selector)||null;}
  addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,new Set());this.listeners.get(type).add(fn);}
  removeEventListener(type,fn){this.listeners.get(type)?.delete(fn);}
  focus(){document.activeElement=this;}
 }
 const document={hidden:false,activeElement:null,listeners:new Map(),createElement:tag=>new Node(tag),addEventListener:Node.prototype.addEventListener,removeEventListener:Node.prototype.removeEventListener};
 document.body=new Node('body');document.querySelector=selector=>document.body.querySelector(selector);
 const window={document,setInterval(fn,ms){const id=++timerId;timers.set(id,{fn,ms});return id;},clearInterval:id=>timers.delete(id),addEventListener(type,fn){if(!windowListeners.has(type))windowListeners.set(type,new Set());windowListeners.get(type).add(fn);},removeEventListener(type,fn){windowListeners.get(type)?.delete(fn);}};
 const context={window,Intl,Date,module:{exports:{}}};vm.createContext(context);vm.runInContext(source,context);
 function dispatch(target,type,fields={}){const event={target,key:'',preventDefault(){this.defaultPrevented=true;},...fields};for(let node=target;node;node=node.parentNode){if(type==='click')node.onclick?.(event);for(const fn of node.listeners?.get(type)||[])fn(event);}for(const fn of document.listeners.get(type)||[])fn(event);return event;}
 return {document,window,Node,timers,windowListeners,api:context.module.exports,dispatch};
}
function navigation(h){const nav=new h.Node('nav');nav.setAttribute('aria-label','Workspace navigation');h.document.body.append(nav);const buttons={};for(const view of ['overview','communications','junomo','trading','rooms','home','news','music','jarvis','research','library','connections','plan']){const button=new h.Node('button');button.setAttribute('data-view',view);button.textContent=view;if(view==='overview')button.classList.add('active');buttons[view]=button;nav.append(button);}return {nav,buttons};}
test('clocks use real local date and UTC with an explicit timezone',()=>{
 const {api}=harness(),clock=api.clockText(new Date('2026-07-01T23:04:05Z'),'Europe/London');
 assert.equal(clock.local,'00:04:05');assert.equal(clock.utc,'23:04:05');assert.match(clock.date,/Thursday,? 2 July/);assert.equal(clock.zone,'Europe/London');
 assert.equal(api.clockText(new Date('invalid')).date,'Time unavailable');
});
test('device and engine states distinguish unknown, reporting, stale, and configured untested',()=>{
 const {api}=harness(),now=Date.parse('2026-10-19T12:00:00Z');
 assert.equal(api.viewModel({},now).registered,null);
 const model=api.viewModel({devices:{devices:[{name:'Mac',kind:'Mac',online:true,last_seen:now/1000-20},{name:'Phone',kind:'iPhone',online:true,last_seen:now/1000-190},{name:'Unknown'}]},connections:{ai:{state:'configured_unverified'},moneypenny:{state:'ready'}}},now);
 assert.equal(model.registered,3);assert.equal(model.reporting,1);assert.equal(model.devices[1].state,'offline');assert.equal(model.devices[2].state,'unknown');assert.equal(model.services[0].detail,'Configured · not tested');
 const markup=api.renderDevices(api.viewModel({devices:[{name:'<img src=x onerror=alert(1)>',online:false}],connections:{ai:{state:'ready'}}},now));
 assert.match(markup,/&lt;img/);assert.doesNotMatch(markup,/<img/);assert.match(markup,/Selected model available/);assert.doesNotMatch(markup,/inference verified/i);
});
test('reported device count includes all supplied rows while the panel shows only three',()=>{
 const {api}=harness(),model=api.viewModel({devices:Array.from({length:8},(_,i)=>({name:'Device '+i,online:true}))});
 assert.equal(model.registered,8);assert.equal(model.reporting,8);assert.equal(model.devices.length,3);assert.match(api.renderDevices(model),/5 more in Home &amp; devices|5 more in Home & devices/);
});
test('currently reporting devices lead the bounded panel ahead of old phones and recent saved reports',()=>{
 const {api}=harness(),now=Date.parse('2026-10-19T12:00:00Z'),seconds=now/1000;
 const model=api.viewModel({devices:[{name:'Old phone',online:false,last_seen:seconds-16*86400},{name:'Earlier phone',online:false,last_seen:seconds-86400},{name:'Recent inactive',online:false,last_seen:seconds-10},{name:'Current Mac',online:true,last_seen:String(seconds-30)},{name:'Unknown'}]},now);
 assert.deepEqual(Array.from(model.devices,item=>item.name),['Current Mac','Recent inactive','Earlier phone']);assert.equal(model.registered,5);assert.equal(model.reporting,1);assert.equal(model.devices[0].state,'ready');
});
test('HUD clock pauses while hidden or in companion, resumes, and cleans every listener and timer',()=>{
 const h=harness(),host=new h.Node(),calls=[];h.document.body.append(host);
 const handle=h.api.mount(host,{navigate:view=>calls.push(view),pair:()=>calls.push('pair'),connections:()=>calls.push('connections'),api:()=>assert.fail('HUD must never request data')});
 assert.equal(h.timers.size,1);assert.equal([...h.timers.values()][0].ms,1000);assert.match(host.querySelector('[data-command-clock="local"]').textContent,/\d\d:\d\d:\d\d/);
 handle.update({devices:{devices:[]},system:{voice:{state:'ready'}}});assert.match(host.querySelector('.command-device-body').innerHTML,/No devices have reported/);
 h.dispatch(host.querySelector('[data-command-action="pair"]'),'click');h.dispatch(host.querySelector('[data-command-action="connections"]'),'click');assert.deepEqual(calls,['pair','connections']);
 h.document.hidden=true;for(const fn of h.document.listeners.get('visibilitychange'))fn();assert.equal(h.timers.size,0);
 h.document.hidden=false;for(const fn of h.document.listeners.get('visibilitychange'))fn();assert.equal(h.timers.size,1);
 h.document.body.dataset.companion='open';for(const fn of h.windowListeners.get('jjrvis-companion-changed'))fn();assert.equal(h.timers.size,0);
 h.document.body.dataset.companion='workspace';for(const fn of h.windowListeners.get('jjrvis-companion-changed'))fn();assert.equal(h.timers.size,1);
 handle.destroy();handle.destroy();assert.equal(h.timers.size,0);assert.equal(h.document.listeners.get('visibilitychange').size,0);assert.equal(h.windowListeners.get('jjrvis-companion-changed').size,0);assert.equal(host.childNodes.length,0);assert.equal(host.listeners.get('click').size,0);
});
test('navigation moves every original button and retains its action without duplicating handlers',()=>{
 const h=harness(),{nav,buttons}=navigation(h),original=[...nav.childNodes],calls=[];for(const button of original)button.onclick=()=>calls.push(button.dataset.view);
 const handle=h.api.init({nav,navigate:()=>assert.fail('Existing buttons own navigation')});
 assert.equal(nav.querySelectorAll('button[data-view]').length,13);assert.equal(nav.querySelectorAll('summary').length,3);assert.equal(nav.querySelector('button[data-view="junomo"]'),buttons.junomo);assert.equal(h.api.init({nav}),handle);
 h.dispatch(buttons.junomo,'click');assert.deepEqual(calls,['junomo']);assert.equal(buttons.overview.getAttribute('aria-current'),'page');
 buttons.overview.classList.remove('active');buttons.junomo.classList.add('active');handle.update('junomo');assert.equal(buttons.junomo.getAttribute('aria-current'),'page');assert.equal(buttons.overview.getAttribute('aria-current'),null);assert.equal(nav.querySelector('summary').classList.contains('command-nav-current'),true);
 handle.destroy();assert.deepEqual(nav.childNodes,original);assert.equal(h.document.listeners.get('pointerdown').size,0);assert.equal(buttons.overview.getAttribute('aria-current'),null);h.dispatch(buttons.junomo,'click');assert.deepEqual(calls,['junomo','junomo']);
});
test('disclosures expose ARIA state, keyboard movement, Escape focus, outside click, and focus cleanup',()=>{
 const h=harness(),{nav,buttons}=navigation(h),handle=h.api.init({nav});const groups=nav.querySelectorAll('details'),summary=groups[0].querySelector('summary');
 summary.focus();const down=h.dispatch(summary,'keydown',{key:'ArrowDown'});assert.equal(down.defaultPrevented,true);assert.equal(groups[0].open,true);assert.equal(summary.getAttribute('aria-expanded'),'true');assert.equal(h.document.activeElement,buttons.communications);assert.equal(summary.getAttribute('aria-controls'),groups[0].querySelector('.command-nav-popover').id);
 h.dispatch(buttons.communications,'keydown',{key:'ArrowUp'});assert.equal(h.document.activeElement,buttons.plan);
 h.dispatch(buttons.plan,'keydown',{key:'Home'});assert.equal(h.document.activeElement,buttons.communications);
 h.dispatch(buttons.communications,'keydown',{key:'End'});assert.equal(h.document.activeElement,buttons.plan);
 h.dispatch(buttons.plan,'keydown',{key:'Escape'});assert.equal(groups[0].open,false);assert.equal(summary.getAttribute('aria-expanded'),'false');assert.equal(h.document.activeElement,summary);
 h.dispatch(summary,'keydown',{key:'ArrowDown'});h.dispatch(h.document.body,'pointerdown');assert.equal(groups[0].open,false);
 h.dispatch(summary,'keydown',{key:'ArrowDown'});h.dispatch(buttons.communications,'focusout',{relatedTarget:h.document.body});assert.equal(groups[0].open,false);
 h.dispatch(summary,'keydown',{key:'ArrowDown'});const second=groups[1].querySelector('summary');h.dispatch(second,'keydown',{key:'ArrowDown'});assert.equal(groups[0].open,false);assert.equal(groups[1].open,true);
 handle.destroy();assert.equal(nav.listeners.get('keydown').size,0);assert.equal(nav.listeners.get('focusout').size,0);assert.ok(groups.every(group=>group.listeners.get('toggle').size===0));
});
test('compact navigation has a mobile grid and no horizontal scrolling escape hatch',()=>{
 const css=fs.readFileSync(path.join(__dirname,'../command-deck.css'),'utf8');
 assert.match(css,/grid-template-columns:repeat\(4,minmax\(0,1fr\)\)/);assert.match(css,/command-nav\{[^}]*overflow:visible/);assert.match(css,/prefers-reduced-motion:reduce/);assert.doesNotMatch(css,/overflow-x\s*:\s*(auto|scroll)/);
});
