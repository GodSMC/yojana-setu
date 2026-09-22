import fs from 'node:fs';
import {respond} from '../web/engine.mjs';
const read=path=>JSON.parse(fs.readFileSync(new URL(path,import.meta.url),'utf8'));
const data=read('../web/schemes.json'),ui=read('../web/ui.json'),cases=read('./conversations.json');
const results=cases.map(c=>{let state=null;return c.inputs.map(text=>{const out=respond(state,text,data,ui);state=out.state;return out;});});
process.stdout.write(JSON.stringify(results));
