const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
for(const stem of ['mock','live']){
 const f=path.join(__dirname,'../recipes/n8n/unifi-inventory-'+stem+'.json');
 const wf=JSON.parse(fs.readFileSync(f,'utf8'));
 assert.equal(wf.active,false);
 assert.ok(wf.nodes.some(n=>n.type==='n8n-nodes-base.manualTrigger'));
 const http=wf.nodes.filter(n=>n.type==='n8n-nodes-base.httpRequest');
 if(stem==='mock') assert.equal(http.length,0);
 else {
   assert.equal(http.length,1);
   assert.equal(http[0].parameters.method,'GET');
   assert.match(http[0].parameters.url,/unifi\.example\.invalid/);
   assert.equal(http[0].parameters.options.timeout,10000);
   assert.equal(http[0].credentials,undefined);
 }
 const summary=wf.nodes.find(n=>n.name==='Redacted Summary');
 const fn=new Function('$input',summary.parameters.jsCode);
 const good=fn({all:()=>[{json:{offset:0,limit:100,totalCount:3,data:[{state:'ONLINE'},{state:'OFFLINE'},{state:'ONLINE'}]}}]});
 assert.equal(good[0].json.onlineThisPage,2);
 assert.equal(good[0].json.nonOnlineThisPage,1);
 assert.equal(good[0].json.hasMoreOrUnknownPages,false);
 const paged=fn({all:()=>[{json:{offset:0,totalCount:9,data:[{state:'ONLINE'}]}}]});
 assert.equal(paged[0].json.hasMoreOrUnknownPages,true);
 assert.throws(()=>fn({all:()=>[{json:{secret:'do-not-echo'}}]}));
 assert.ok(!JSON.stringify(good).includes('secret'));
}
console.log('PASS: n8n flows mock/no network, live disabled GET-only, redaction & paging');
