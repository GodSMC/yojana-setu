import fs from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {respond,evaluate,parse} from '../web/engine.mjs';
const read=path=>JSON.parse(fs.readFileSync(new URL(path,import.meta.url),'utf8'));
const data=read('../web/schemes.json'),ui=read('../web/ui.json'),cases=read('./conversations.json');
for(const c of cases)test(c.name,()=>{
  let state=null,out;
  for(const input of c.inputs){out=respond(state,input,data,ui);state=out.state;}
  for(const key of ['status','scheme','kind','field'])if(key in c)assert.equal(out.reply[key],c[key]);
});
test('missing facts never produce a positive assessment',()=>{for(const s of data.schemes)assert.equal(evaluate(s,{}).status,'review');});
test('state input is data, not an object property lookup',()=>{for(const s of ['__proto__','constructor','toString','<img src=x>'])assert.equal(parse(data.fields.state,s,data),null);});
test('numbers use bounded decimal parsing',()=>{for(const s of ['Infinity','NaN','1e3','-5','0x12','120.2'])assert.equal(parse(data.fields.age,s,data),null);assert.equal(parse(data.fields.age,'६०',data),60);});
test('all rules use supported operators and field definitions',()=>{for(const s of data.schemes){for(const f of s.fields)assert.ok(data.fields[f]);for(const r of s.rules){assert.ok(['eq','lte','gte','marks'].includes(r.op));assert.ok(s.fields.includes(r.field));}assert.ok(s.source.startsWith('https://'));}});
