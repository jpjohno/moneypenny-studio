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
test('private cards show supplied text and keep body reads tied to their registered source',()=>{
 const mail=briefingCards('mail',{state:'connected',messages:[{id:'opaque/id',subject:'A message',sender:'Fixture',preview:'Actual preview'}]})[0];
 assert.equal(mail.detail,'Actual preview');assert.equal(mail.bodyPath,'/v1/workspace/mail/message?id=opaque%2Fid');
 const local=briefingCards('mail',{state:'connected',messages:[{id:42,accountKey:'fixture',preview:'Mac preview'}]})[0];
 assert.equal(local.bodyPath,'/v1/workspace/native/mail/message?account=fixture&id=42');
 for(const kind of ['messages','whatsapp']){
  const card=briefingCards(kind,{state:'available',messages:[{participant:'Fixture',text:'Real stored text',id:1}]})[0];
  assert.equal(card.detail,'Real stored text');assert.equal(card.private,true);assert.equal(card.bodyPath,'');
 }
});

test('briefing images accept only publisher image hosts, never private or executable URLs',()=>{
 const cards=briefingCards('news',{items:[{title:'Fixture headline',url:'https://example.com/one',image:'https://ichef.bbci.co.uk/news/fixture.jpg'},{title:'Blocked local',url:'https://example.com/two',image:'http://127.0.0.1/private'},{title:'Blocked credentials',url:'https://example.com/three',image:'https://user:password@ichef.bbci.co.uk/x'}]});
 assert.match(cards[0].image,/^https:\/\/ichef/);assert.equal(cards[1].image,'');assert.equal(cards[2].image,'');
});
