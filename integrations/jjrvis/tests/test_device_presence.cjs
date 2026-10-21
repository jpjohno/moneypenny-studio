const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const script = fs.readFileSync(path.join(__dirname, '../workspace.js'), 'utf8');
const start = script.indexOf('function reportDevicePresence()');
const end = script.indexOf('\nsetInterval(', start);
assert(start >= 0 && end > start, 'Presence function is available for isolated behaviour checks');
const reportFunction = script.slice(start, end);
const device = {device_id: 'test-mac-device', name: 'Test Mac', kind: 'Mac'};
function fixture({watch = 7, stopped = false, gps = () => {}} = {}) {
 const posts = [];
 const context = vm.createContext({
  stopped, deviceLocationWatch: watch,
  deviceIdentity: () => device,
  api: (url, body) => {posts.push({url, body}); return Promise.resolve({});},
  navigator: {geolocation: {getCurrentPosition: gps}},
 });
 vm.runInContext(reportFunction, context);
 return {posts, context, run: () => vm.runInContext('reportDevicePresence()', context)};
}
function assertPresenceOnly(posts) {
 assert.equal(posts.length, 1);
 assert.equal(posts[0].url, '/v1/workspace/devices');
 assert.deepEqual(JSON.parse(JSON.stringify(posts[0].body)), device);
 assert(!('share_location' in posts[0].body), 'A heartbeat does not revoke or renew the location fix');
}
let success;
const pending = fixture({gps: callback => {success = callback;}});
pending.run();
assertPresenceOnly(pending.posts); // No GPS callback: still online immediately.
success({coords: {latitude: 52.5, longitude: -0.5, accuracy: 25}});
assert.equal(pending.posts.length, 2);
assert.deepEqual(JSON.parse(JSON.stringify(pending.posts[1].body)), {
 ...device, share_location: true, latitude: 52.5, longitude: -0.5, accuracy: 25,
});
const failed = fixture({gps: (_success, error) => error({code: 3})});
failed.run(); assertPresenceOnly(failed.posts);
const thrown = fixture({gps: () => {throw new Error('GPS unavailable');}});
thrown.run(); assertPresenceOnly(thrown.posts);
const noWatch = fixture({watch: null, gps: () => assert.fail('No GPS request without a location watch')});
noWatch.run(); assertPresenceOnly(noWatch.posts);
const signedOut = fixture({stopped: true, gps: () => assert.fail('No GPS while signed out')});
signedOut.run(); assert.equal(signedOut.posts.length, 0);
const logoutPending = fixture({gps: callback => {success = callback;}});
logoutPending.run(); logoutPending.context.stopped = true;
success({coords: {latitude: 52.5, longitude: -0.5, accuracy: 25}});
assertPresenceOnly(logoutPending.posts);
console.log('Device presence stays current through GPS failure; only a fresh GPS callback updates coordinates.');
