import {respond} from './engine.mjs';
const $ = s => document.querySelector(s);
let data, ui, state = null, lastReply, history = [];
const storageKey = 'yojana-setu-v1';
const input = $('#message'), messages = $('#messages');

function save() {
  try {sessionStorage.setItem(storageKey, JSON.stringify({state, history: history.slice(-35), lastReply}));} catch { /* Storage can be disabled by the browser. */ }
}
function localise() {
  const lang = state?.lang || 'en';
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-en]').forEach(el => {
    const text = el.dataset[lang];
    if (el.tagName === 'H1') {
      const lines = text.split('<br>');
      el.replaceChildren(document.createTextNode(lines[0]), document.createElement('br'));
      const em = document.createElement('em'); em.textContent = lines[1]; el.append(em);
    } else if (text.includes('<br>')) {
      el.replaceChildren(...text.split('<br>').flatMap((x,i) => i ? [document.createElement('br'),document.createTextNode(x)] : [document.createTextNode(x)]));
    } else el.textContent = text;
  });
  input.placeholder = lang === 'hi' ? 'यहाँ लिखें, या बोलें दबाएँ…' : 'Type here, or tap Speak…';
  $('#restart').setAttribute('aria-label', lang === 'hi' ? 'उत्तर मिटाएँ और फिर शुरू करें' : 'Delete answers and restart');
  $('#scheme-list').replaceChildren();
  for (const scheme of data.schemes) {
    const btn = document.createElement('button'); btn.type = 'button'; btn.className = 'scheme-card' + (state?.scheme === scheme.id ? ' active' : '');
    const icon = document.createElement('span'); icon.className = 'scheme-icon'; icon.textContent = scheme.icon; icon.setAttribute('aria-hidden','true');
    const body = document.createElement('span'), name = document.createElement('strong'), sub = document.createElement('small');
    name.textContent = scheme.name[lang]; sub.textContent = scheme.category[lang]; body.append(name,sub);
    const arrow = document.createElement('span'); arrow.className = 'scheme-arrow'; arrow.textContent = '↗';
    btn.append(icon,body,arrow); btn.onclick = () => {send(scheme.id, scheme.name[lang]); if(innerWidth < 641) $('.chat').scrollIntoView({block:'start',behavior:'smooth'});};
    $('#scheme-list').append(btn);
  }
  const p = lastReply?.progress;
  $('#progress').hidden = !p;
  if (p) $('#progress').textContent = lang === 'hi' ? `सवाल ${p.done+1} / ${p.total} · उत्तर बदलने के लिए पिछला उत्तर दबाएँ` : `Question ${p.done+1} of ${p.total} · You can go back to change an answer`;
  input.setAttribute('list', lastReply?.field === 'state' ? 'states' : '');
  input.inputMode = data.fields[lastReply?.field]?.type === 'number' ? 'decimal' : 'text';
}
function addMessage(entry, active = false) {
  const wrap = document.createElement('div'); wrap.className = 'message ' + entry.role + (entry.reply?.kind === 'assessment' ? ' assessment ' + entry.reply.status : '');
  const sender = document.createElement('p'); sender.className = 'sender'; sender.textContent = entry.role === 'user' ? (state?.lang === 'hi' ? 'आप' : 'YOU') : 'SETU';
  const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = entry.text;
  wrap.append(sender,bubble);
  if (active && entry.reply?.options?.length) {
    const options = document.createElement('div'); options.className = 'options';
    entry.reply.options.forEach(o => {const b = document.createElement('button');b.type='button';b.className='option';b.textContent=o.label;b.onclick=()=>send(o.value,o.label);options.append(b);});
    wrap.append(options);
  }
  if (entry.reply?.links?.length) {
    const links = document.createElement('div'); links.className='links';
    entry.reply.links.forEach(l => {const a=document.createElement('a');a.textContent=l.label+' ↗';a.href=l.url;a.target='_blank';a.rel='noopener noreferrer';links.append(a);});wrap.append(links);
  }
  messages.append(wrap);
}
function render() {
  messages.replaceChildren();
  history.forEach((entry,i) => addMessage(entry,i===history.length-1));
  localise();
  messages.scrollTop=messages.scrollHeight;
}
function send(text, label) {
  if (!data || !text.trim()) return;
  if (text === '/delete') {history=[];try{sessionStorage.removeItem(storageKey);}catch{}}
  else history.push({role:'user',text:label || text});
  const answer=respond(state,text,data,ui);state=answer.state;lastReply=answer.reply;
  history.push({role:'bot',text:lastReply.text,reply:lastReply});
  if(history.length>35) history=history.slice(-35);
  input.value='';save();render();
}
$('#composer').onsubmit=e=>{e.preventDefault();send(input.value);};
$('#language').onclick=()=>send('/language',state?.lang==='hi'?'English':'हिंदी');
$('#menu').onclick=()=>send('/menu');
$('#help').onclick=()=>send('/help');
$('#back').onclick=()=>send('/back');
$('#privacy').onclick=()=>send('/privacy');
$('#restart').onclick=()=>send('/delete');

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let listening=false, recognition;
$('#speak').onclick=()=>{
  const status=$('#voice-status'), hindi=state?.lang==='hi';
  if (!SpeechRecognition) {status.textContent=hindi?'इस ब्राउज़र में वाणी सुविधा उपलब्ध नहीं है। फ़ोन के कीबोर्ड का माइक इस्तेमाल करें।':'Speech input is unavailable in this browser. Use your phone keyboard’s microphone instead.';return;}
  if (listening) {recognition.stop();return;}
  recognition=new SpeechRecognition();recognition.lang=hindi?'hi-IN':'en-IN';recognition.interimResults=false;recognition.maxAlternatives=1;
  recognition.onstart=()=>{listening=true;status.textContent=hindi?'सुन रहे हैं… ब्राउज़र की वाणी सेवा ऑडियो प्रोसेस कर सकती है।':'Listening… Your browser’s speech service may process this audio.';};
  recognition.onresult=e=>{input.value=e.results[0][0].transcript;status.textContent=hindi?'टेक्स्ट जाँचें, फिर भेजें दबाएँ।':'Check the text, then press Send.';input.focus();};
  recognition.onerror=()=>{status.textContent=hindi?'माइक उपलब्ध नहीं है। अनुमति जाँचें या लिखकर भेजें।':'Microphone unavailable. Check permission or type your message.';};
  recognition.onend=()=>{listening=false;};
  try{recognition.start();}catch{listening=false;status.textContent=hindi?'वाणी सुविधा शुरू नहीं हुई। कृपया लिखें।':'Speech input could not start. Please type instead.';}
};
async function start(){
  try{
    [data,ui]=await Promise.all(['schemes.json','ui.json'].map(async url=>{const r=await fetch(url);if(!r.ok)throw Error('load');return r.json();}));
    const dl=document.createElement('datalist');dl.id='states';data.states.forEach(s=>{const o=document.createElement('option');o.value=s;dl.append(o);});document.body.append(dl);
    try{const saved=JSON.parse(sessionStorage.getItem(storageKey));if(saved?.state && ['en','hi'].includes(saved.state.lang) && saved.state.profile && Array.isArray(saved.history)){state=saved.state;history=saved.history;lastReply=saved.lastReply;}}catch{}
    if(!lastReply){const answer=respond(null,'/start',data,ui);state=answer.state;lastReply=answer.reply;history=[{role:'bot',text:lastReply.text,reply:lastReply}];}
    render();
  }catch{
    messages.textContent='The guide could not load. Please refresh, or visit myscheme.gov.in for official scheme information.';
    $('#send').disabled=true;$('#speak').disabled=true;
  }
}
start();
