#!/usr/bin/env python3
"""Web UI for M1-P8 Interactive Storytelling Agent (reuses the engine in story_agent.py).
Run:  GROQ_API_KEY=... python3 story_web.py   then open http://127.0.0.1:8765
Works without a key too (falls back to the built-in rule-based engine)."""
import json, os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import story_agent as sa

PORT = int(os.environ.get("PORT", "8765"))
LOCK = threading.Lock()
STATE = {"mem": None}

def snapshot():
    m = STATE["mem"]
    if not m:
        return {"started": False, "llm": sa.llm_available()}
    return {"started": True, "llm": sa.llm_available(), "theme": m.theme, "turn": m.turn, "tension": m.tension,
            "story": m.story, "choices": [c[1] for c in m.choices], "characters": m.characters,
            "places": m.places, "items": m.items, "events": m.events[-20:]}

def start(theme):
    m = sa.Memory()
    m.theme = theme.strip()[:80] or "forgotten castle"
    STATE["mem"] = m
    sa.begin(m)

def choose(payload):
    m = STATE["mem"]
    if not m: return
    if payload.get("index") is not None and 0 <= int(payload["index"]) < len(m.choices):
        decision = m.choices[int(payload["index"])]
    else:
        text = str(payload.get("text", "")).strip()[:300]
        if not text: return
        decision = ("free", text)
    sa.step(m, decision)

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>The Storyteller</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--paper:#f1e9d6;--page:#fbf7ec;--ink:#2a2420;--mut:#7b6f60;--red:#8b2e2a;--rule:#d8cbb0;--serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--serif);font-size:18px;line-height:1.6}
a{color:var(--red)}
header{max-width:1100px;margin:0 auto;padding:22px 24px 0;display:flex;justify-content:space-between;align-items:baseline;font-size:.82rem;color:var(--mut)}
header h1{margin:0;font-size:.95rem;font-weight:400;letter-spacing:.28em;text-transform:uppercase;color:var(--ink)}
.layout{max-width:1100px;margin:14px auto 60px;padding:0 24px;display:grid;grid-template-columns:minmax(0,1fr) 270px;gap:34px;align-items:start}
.layout.solo{grid-template-columns:minmax(0,1fr);max-width:680px}
.book{background:var(--page);border:1px solid var(--rule);box-shadow:0 1px 0 #fff inset,0 18px 40px -22px rgba(60,40,10,.45);padding:56px 64px 46px}
.title{text-align:center;padding:30px 0 18px}
.title h2{font-weight:400;font-style:italic;font-size:2.1rem;line-height:1.25;margin:0 0 12px}
.title p{color:var(--mut);margin:0 auto 30px;max-width:460px;font-size:1rem}
.field{display:flex;gap:14px;align-items:flex-end;max-width:520px;margin:0 auto}
input[type=text]{font:inherit;font-size:1.05rem;width:100%;background:transparent;border:0;border-bottom:1.5px solid var(--ink);padding:8px 2px;color:var(--ink);outline:none;border-radius:0}
input[type=text]::placeholder{color:#a89c88;font-style:italic}input[type=text]:focus{border-bottom-color:var(--red)}
.btn{font:inherit;font-size:.95rem;letter-spacing:.06em;cursor:pointer;background:var(--ink);color:var(--page);border:0;padding:10px 20px;border-radius:2px;white-space:nowrap}
.btn:hover{background:var(--red)}.btn:disabled{opacity:.5;cursor:wait}
.try{margin-top:26px;font-size:.92rem;color:var(--mut);text-align:center}.try button{font:inherit;background:none;border:0;color:var(--red);cursor:pointer;text-decoration:underline;text-underline-offset:3px;padding:0 3px}
.chapter{margin:0 0 34px;transition:opacity .4s}.chapter.old{opacity:.62}
.chapter h3{margin:0 0 14px;text-align:center;font-weight:400;font-size:.8rem;letter-spacing:.3em;text-transform:uppercase;color:var(--mut)}
.chapter h3::after{content:"";display:block;width:34px;height:1px;background:var(--rule);margin:10px auto 0}
.chapter p{margin:0;text-align:left;hyphens:auto}
.chapter.new p::first-letter{float:left;font-size:3.1rem;line-height:.85;padding:6px 8px 0 0;color:var(--red)}
.chapter.new{animation:turn .6s ease both}@keyframes turn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.ask{border-top:1px solid var(--rule);margin-top:6px;padding-top:22px}
.ask h4{margin:0 0 12px;font-weight:400;font-style:italic;color:var(--mut);font-size:1rem}
.opt{display:flex;gap:14px;width:100%;text-align:left;font:inherit;background:none;border:0;border-left:2px solid transparent;padding:9px 12px;margin:0 0 2px;cursor:pointer;color:var(--ink)}
.opt b{font-weight:400;color:var(--red);min-width:20px}.opt:hover{border-left-color:var(--red);background:rgba(139,46,42,.06)}.opt:disabled{cursor:wait;opacity:.6}
.own{display:flex;gap:14px;align-items:flex-end;margin-top:18px}.own label{font-style:italic;color:var(--mut);font-size:.95rem;white-space:nowrap}
.wait{font-style:italic;color:var(--mut);padding:8px 2px}.wait::after{content:"";animation:dots 1.4s steps(4,end) infinite}
@keyframes dots{0%{content:""}25%{content:"."}50%{content:".."}75%{content:"..."}}
aside{font-size:.88rem;position:sticky;top:18px;background:rgba(251,247,236,.6);border:1px solid var(--rule);padding:20px 22px}
aside h5{margin:0 0 8px;font-weight:400;font-size:.72rem;letter-spacing:.26em;text-transform:uppercase;color:var(--mut);border-bottom:1px solid var(--rule);padding-bottom:6px}
aside section{margin-bottom:20px}aside section:last-of-type{margin-bottom:12px}
aside ul{list-style:none;margin:0;padding:0;max-height:210px;overflow:auto}aside li{margin:0 0 6px;line-height:1.4}
aside li small{color:var(--mut);font-style:italic}.none{color:#a89c88;font-style:italic}
.danger{display:flex;gap:4px;align-items:center}.danger i{width:15px;height:6px;background:var(--rule);display:block}.danger i.on{background:var(--red)}
.link{font:inherit;font-size:.85rem;background:none;border:0;color:var(--mut);cursor:pointer;text-decoration:underline;text-underline-offset:3px;padding:0}.link:hover{color:var(--red)}
@media(max-width:900px){.layout{grid-template-columns:1fr}aside{position:static}.book{padding:34px 24px}}
</style></head><body>
<header><h1>The Storyteller</h1><span id="mode"></span></header>
<div class="layout solo" id="layout">
 <div>
  <div class="book" id="startbox"><div class="title"><h2>What shall the story be about?</h2>
   <p>Name a theme. The storyteller keeps track of everyone you meet and everything that happens, and what you decide changes what comes next.</p></div>
   <div class="field"><input type="text" id="theme" placeholder="a haunted lighthouse, a heist in space..." autofocus><button class="btn" id="go">Begin</button></div>
   <div class="try" id="sugg">Or try: </div></div>
  <div class="book" id="storybox" style="display:none"><div id="story"></div>
   <div class="ask"><h4>What do you do?</h4><div id="choices"></div>
    <div class="own"><label for="free">Or write your own:</label><input type="text" id="free" placeholder="describe what you do"><button class="btn" id="send">Continue</button></div></div></div>
 </div>
 <aside id="side" style="display:none">
  <section><h5>Danger</h5><div class="danger" id="danger"></div></section>
  <section><h5>People</h5><ul id="chars"></ul></section>
  <section><h5>Carrying</h5><ul id="items"></ul></section>
  <section><h5>Places</h5><ul id="places"></ul></section>
  <section><h5>What has happened</h5><ul id="events"></ul></section>
  <button class="link" id="reset">Start a new story</button>
 </aside>
</div>
<script>
const $=id=>document.getElementById(id);let busy=false,shown=0;
const ROMAN=n=>{const r=[[10,'X'],[9,'IX'],[5,'V'],[4,'IV'],[1,'I']];let s='';for(const[v,c]of r)while(n>=v){s+=c;n-=v}return s};
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return r.json()}
function el(t,c,x){const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
function list(id,rows){const u=$(id);u.textContent='';if(!rows.length){u.appendChild(el('li','none','nothing yet'));return}
 rows.forEach(r=>{const li=el('li');if(Array.isArray(r)){li.appendChild(document.createTextNode(r[0]));if(r[1])li.appendChild(el('small','',' ('+r[1]+')'))}else li.textContent=r;u.appendChild(li)})}
function render(s){
 $('mode').textContent=s.llm?'written with Groq':'offline mode';
 $('startbox').style.display=s.started?'none':'block';$('storybox').style.display=s.started?'block':'none';$('side').style.display=s.started?'block':'none';
 $('layout').className='layout'+(s.started?'':' solo');
 if(!s.started){shown=0;return}
 const st=$('story');st.textContent='';
 s.story.forEach((t,i)=>{const last=i===s.story.length-1;const c=el('div','chapter '+(last?'new':'old'));c.appendChild(el('h3','','Chapter '+ROMAN(i+1)));c.appendChild(el('p','',t));st.appendChild(c)});
 const ch=$('choices');ch.textContent='';
 s.choices.forEach((c,i)=>{const b=el('button','opt');b.append(el('b','',String.fromCharCode(97+i)+')'),document.createTextNode(c));b.onclick=()=>act({index:i});ch.appendChild(b)});
 const d=$('danger');d.textContent='';for(let i=1;i<=10;i++)d.appendChild(el('i',i<=s.tension?'on':''));
 list('chars',Object.entries(s.characters).map(([n,c])=>[n,c.role+(c.trust?', trust '+(c.trust>0?'+':'')+c.trust:'')]));
 list('items',s.items);list('places',s.places.slice(-4));list('events',s.events.slice(-8));
 if(s.story.length>shown){const cs=document.querySelectorAll('.chapter');if(cs.length>1)cs[cs.length-1].scrollIntoView({behavior:'smooth',block:'start'})}
 shown=s.story.length;
}
async function act(body){if(busy)return;busy=true;document.querySelectorAll('.opt,#send').forEach(b=>b.disabled=true);
 const ch=$('choices');ch.textContent='';ch.appendChild(el('div','wait','The next page is being written'));
 try{render(await api('/api/choose',body))}finally{busy=false;document.querySelectorAll('#send').forEach(b=>b.disabled=false);$('free').value=''}}
$('go').onclick=async()=>{if(busy)return;busy=true;$('go').disabled=true;$('go').textContent='Writing...';
 try{render(await api('/api/start',{theme:$('theme').value}))}finally{busy=false;$('go').disabled=false;$('go').textContent='Begin'}};
$('theme').onkeydown=e=>{if(e.key==='Enter')$('go').click()};
$('send').onclick=()=>{const t=$('free').value.trim();if(t)act({text:t})};$('free').onkeydown=e=>{if(e.key==='Enter')$('send').click()};
$('reset').onclick=async()=>render(await api('/api/reset',{}));
['haunted lighthouse','space heist','lost city under the ocean','detective noir'].forEach((x,i,a)=>{const b=el('button','',x);b.onclick=()=>{$('theme').value=x;$('go').click()};$('sugg').appendChild(b);if(i<a.length-1)$('sugg').appendChild(document.createTextNode(' / '))});
api('/api/state').then(render);
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path in ("/", "/index.html"): self.send(200, PAGE, "text/html")
        elif self.path == "/api/state":
            with LOCK: self.send(200, json.dumps(snapshot()))
        else: self.send(404, "{}")
    def do_POST(self):
        try: payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
        except Exception: payload = {}
        with LOCK:
            try:
                if self.path == "/api/start": start(str(payload.get("theme", "")))
                elif self.path == "/api/choose": choose(payload)
                elif self.path == "/api/reset": STATE["mem"] = None
                else: return self.send(404, "{}")
                self.send(200, json.dumps(snapshot()))
            except Exception as e:
                self.send(500, json.dumps({"started": False, "error": str(e)}))

if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"Storyteller running at http://127.0.0.1:{PORT}  (Ctrl+C to stop)")
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\nStopped.")
