// The browser and Python adapters read the same versioned rules and translations.
export const normalise = v => String(v).trim().toLowerCase().replace(/[०-९]/g, c => String(c.charCodeAt(0) - 2406));
export const initial = (lang = 'en') => ({lang, profile: {}, scheme: null, pending: null, options: []});

export function evaluate(scheme, profile) {
  const missing = scheme.fields.filter(f => !(f in profile) || profile[f] === 'unknown');
  const reasons = [];
  for (const r of scheme.rules) {
    const v = profile[r.field];
    if (v === undefined || v === 'unknown') continue;
    let passed;
    if (r.op === 'marks') {
      if (!profile.sc_st || profile.sc_st === 'unknown') continue;
      passed = v >= (profile.sc_st === 'yes' ? 50 : r.value);
    } else if (r.op === 'eq') passed = v === r.value;
    else if (r.op === 'lte') passed = v <= r.value;
    else if (r.op === 'gte') passed = v >= r.value;
    else throw new Error('Unsupported rule operator');
    if (!passed) reasons.push(r.reason);
  }
  return {status: reasons.length ? 'unlikely' : missing.length ? 'review' : 'possible', reasons};
}

export function parse(field, raw, data) {
  let value = normalise(raw);
  if (['unknown', 'not sure', "don't know", 'पता नहीं', 'नहीं पता'].includes(value)) return 'unknown';
  if (field.type === 'choice') {
    for (const [i, o] of field.options.entries()) {
      const aliases = [...o.map(normalise), String(i + 1)];
      if (o[0] === 'yes') aliases.push('haan', 'han', 'ha', 'हां');
      if (o[0] === 'no') aliases.push('nahi', 'nahin');
      if (aliases.includes(value)) return o[0];
    }
  } else if (field.type === 'number') {
    value = value.replaceAll(',', '').replaceAll('₹', '').trim().replace(/%$/, '').trim();
    if (!/^\d+(?:\.\d+)?$/.test(value)) return null;
    const n = Number(value);
    if (Number.isFinite(n) && n >= field.min && n <= field.max && (!field.integer || Number.isInteger(n))) return n;
  } else if (field.type === 'state') {
    return (Object.hasOwn(data.state_aliases, value) ? data.state_aliases[value] : null) || data.states.find(s => s.toLowerCase() === value) || null;
  }
  return null;
}

export function respond(saved, text, data, ui) {
  let s = structuredClone(saved || initial(/[\u0900-\u097f]/.test(text) ? 'hi' : 'en'));
  const raw = normalise(text), oldLang = s.lang;
  const schemes = Object.fromEntries(data.schemes.map(x => [x.id, x]));
  const t = key => ui[key][s.lang];
  const link = (label, url) => ({label, url});
  const schemeOptions = () => data.schemes.map(x => ({label: x.icon + ' ' + x.name[s.lang], value: x.id}));
  const result = (kind, text, options = [], links = [], extra = {}) => {
    s.options = options;
    return {state: s, reply: {kind, text, options, links, lang: s.lang, ...extra}};
  };
  const menu = (prefix = '') => {
    s.scheme = s.pending = null;
    return result('menu', (prefix ? prefix + '\n\n' : '') + t('welcome') + '\n\n' + t('saved'), schemeOptions());
  };
  const assessment = () => {
    const scheme = schemes[s.scheme], {status, reasons} = evaluate(scheme, s.profile);
    s.pending = null;
    const lines = [scheme.name[s.lang], t(status), ...reasons.map(r => r[s.lang])];
    if (status === 'review') lines.push(t('unknown'));
    lines.push(scheme.benefit[s.lang], scheme.scope[s.lang], scheme.documents[s.lang], t('disclaimer'));
    return result('assessment', lines.join('\n\n'), [{label: t('menu'), value: '/menu'}, {label: t('edit'), value: '/edit'}],
      [link(t('official'), scheme.apply), link(t('source'), scheme.source), link(t('csc'), data.csc_url)], {status, scheme: scheme.id});
  };
  const advance = () => {
    const scheme = schemes[s.scheme];
    for (const key of scheme.fields) {
      if (!(key in s.profile)) {
        s.pending = key;
        const field = data.fields[key];
        return result('question', field.question[s.lang], (field.options || []).map(o => ({value:o[0], label:o[s.lang === 'en' ? 1 : 2]})), [],
          {field:key, scheme:scheme.id, progress:{done:scheme.fields.filter(f => f in s.profile).length, total:scheme.fields.length}});
      }
    }
    return assessment();
  };
  if (['/delete','/reset','delete'].includes(raw)) { s = initial(oldLang); return menu(t('deleted')); }
  if (['/privacy','privacy','/voice'].includes(raw)) return result('info', t(raw === '/voice' ? 'voice' : 'privacy'), [{label:t('menu'),value:'/menu'}]);
  if (['/help','help','/csc','csc','मदद','सहायता'].includes(raw)) return result('help', t('help'), [{label:t('menu'),value:'/menu'}], [link(t('csc'),data.csc_url),link('myScheme','https://www.myscheme.gov.in/')]);
  if (['/language','/hi','/en','hindi','हिंदी','english'].includes(raw)) {
    s.lang = raw === '/language' ? (s.lang === 'en' ? 'hi' : 'en') : (['/hi','hindi','हिंदी'].includes(raw) ? 'hi' : 'en');
    return s.scheme && s.pending ? advance() : menu();
  }
  if (['/edit','edit'].includes(raw)) {s.profile = {}; return s.scheme ? advance() : menu();}
  if (['/back','back'].includes(raw) && s.scheme) {
    const fields = schemes[s.scheme].fields, i = s.pending ? fields.indexOf(s.pending) : fields.length;
    if (i) delete s.profile[fields[i-1]];
    return advance();
  }
  if (['/start','/menu','menu','hi','hello','namaste','नमस्ते',''].includes(raw)) return menu();
  let selected = Object.hasOwn(schemes, raw) ? raw : null;
  if (!selected && !s.pending) {
    if (['1','2','3'].includes(raw) && JSON.stringify(s.options) === JSON.stringify(schemeOptions())) selected = data.schemes[Number(raw)-1].id;
    else {
      const matches = data.schemes.filter(x => x.keywords.some(k => raw.includes(k)));
      if (matches.length === 1) selected = matches[0].id;
    }
  }
  if (selected) {s.scheme = selected; return advance();}
  if (s.pending) {
    const value = parse(data.fields[s.pending], text, data);
    if (value === null) {const answer = advance(); answer.reply.text = t('invalid') + '\n\n' + answer.reply.text; return answer;}
    s.profile[s.pending] = value;
    return value === 'unknown' ? assessment() : advance();
  }
  return result('fallback', t('fallback'), schemeOptions(), [link(t('csc'),data.csc_url),link('myScheme','https://www.myscheme.gov.in/')]);
}
