import test from 'node:test';
import assert from 'node:assert/strict';
import {normaliseStudioBase,studioURL,parentOrigins} from '../static/studio-paths.js';
test('the authenticated presence prefix applies to local assets and API calls only',()=>{
 assert.equal(normaliseStudioBase('/presence'),'/presence/');
 assert.equal(normaliseStudioBase('https://other.example/presence/'),'/');
 assert.equal(studioURL('/api/character/default','/presence/'),'/presence/api/character/default');
 assert.equal(studioURL('/vendor/vad/','/presence/'),'/presence/vendor/vad/');
 assert.equal(studioURL('blob:private-avatar','/presence/'),'blob:private-avatar');
 assert.equal(studioURL('https://other.example/file','/presence/'),'https://other.example/file');
 assert.equal(studioURL('/api/status','/'),'/api/status');
});
test('same-origin remote parent is trusted only in the explicit proxied presence deployment',()=>{
 assert.ok(parentOrigins('/presence/','https://owner.example').includes('https://owner.example'));
 assert.equal(parentOrigins('/','https://other.example').includes('https://other.example'),false);
});
