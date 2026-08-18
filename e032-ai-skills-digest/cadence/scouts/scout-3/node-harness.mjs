const base = process.env.OPENCODE_GO_BASE_URL;
const key = process.env.OPENCODE_GO_API_KEY;
const model = process.env.OPENCODE_GO_MODEL || 'deepseek-v4-flash';
const res = await fetch(base + 'chat/completions', {
  method: 'POST',
  headers: { 'content-type': 'application/json', authorization: 'Bearer ' + key },
  body: JSON.stringify({ model, messages: [{ role: 'user', content: 'Reply with exactly: ok' }], max_tokens: 200 }),
});
const j = await res.json();
const msg = j && j.choices && j.choices[0] ? j.choices[0].message.content : JSON.stringify(j).slice(0, 80);
console.log('status=' + res.status + ' model=' + (j.model || '?') + ' reply=' + JSON.stringify(msg).slice(0, 60));