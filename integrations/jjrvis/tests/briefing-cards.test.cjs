const test=require('node:test'),assert=require('node:assert/strict');
const {briefingCards}=require('../scene-layout');
test('news prefers regional headlines, deduplicates sources and keeps supplied text inert',()=>{
 const cards=briefingCards('news',{items:[{title:'World',url:'https://example.com/world'},{title:'<script>bad()</script>',category:'local',url:'https://example.com/local',source:'Publisher'},{title:'Duplicate',url:'https://example.com/local'}]});
 assert.equal(cards.length,2);assert.equal(cards[0].regional,true);assert.equal(cards[0].title,'<script>bad()</script>');
});
test('market and mail connection failures cannot become live prices or empty inbox claims',()=>{
 assert.match(briefingCards('markets',{})[0].detail,/unavailable/);
 assert.match(briefingCards('mail',{state:'unavailable',messages:[{subject:'Unverified'}]})[0].detail,/unavailable/);
 assert.match(briefingCards('mail',{state:'connected',messages:[]})[0].detail,/Other inboxes have not been checked/);
 const quote=briefingCards('markets',{markets:[{symbol:'EURUSD',price:null,state:'stale_broker'}]})[0];
 assert.match(quote.detail,/No usable price/);assert.match(quote.source,/stale_broker/);
});
