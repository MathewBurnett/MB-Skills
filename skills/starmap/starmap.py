#!/usr/bin/env python3
"""Render a wayfinder map as a pannable star-map.

Reads the map from the **GitHub issue tracker** adapter: a map issue, its
sub-issues as tickets, and GitHub's native issue dependencies as blocking
edges. Nothing is written down — every status, edge and count is derived from
the tracker at generation time and stamped with the moment it was read.

    starmap.py <map-issue> [--repo owner/name] [--out path.html]

Visual language follows the star-map design record: status is the whole star
(colour, size, glow, pulse), ticket type rides in the label, satisfied edges
flow while unsatisfied ones stay dashed and dark, fog drifts at the rim.
"""

import argparse
import datetime
import json
import re
import subprocess
import sys

STATUS_ORDER = ["resolved", "claimed", "frontier", "blocked", "out_of_scope"]


def gh(*args, parse=True):
    """Run gh, returning parsed JSON (or raw text)."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed:\n{r.stderr.strip()}")
    out = r.stdout.strip()
    if not parse:
        return out
    return json.loads(out) if out else None


def detect_repo():
    return gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner", parse=False)


def section(body, *names):
    """Pull a markdown section's body by any of its heading names."""
    for n in names:
        m = re.search(rf"^#{{1,3}}\s*{re.escape(n)}\s*$(.*?)(?=^#{{1,3}}\s|\Z)",
                      body or "", re.S | re.M | re.I)
        if m:
            return m.group(1).strip()
    return ""


def gist(body):
    for head in ("Goal", "Question", "Answer"):
        s = section(body, head)
        if s:
            first = next((l for l in s.split("\n") if l.strip() and not l.startswith(">")), "")
            return " ".join(first.split())
    text = re.sub(r"^>.*$", "", body or "", flags=re.M)
    return " ".join(text.split())[:180]


def build(map_num, repo):
    mp = gh("issue", "view", str(map_num), "-R", repo,
            "--json", "number,title,body,url,state")
    body = mp["body"] or ""

    kids = gh("api", f"repos/{repo}/issues/{map_num}/sub_issues",
              "--jq", "[.[]|{number,state,title}]") or []
    if not kids:
        raise SystemExit(
            f"#{map_num} has no sub-issues. This renders the GitHub-issues adapter "
            "(map issue + sub-issues + native dependencies); a .plan/ markdown map "
            "is a different shape and is not supported.")

    nodes, edges = [], {}
    for k in kids:
        n = k["number"]
        # REST rather than `gh issue view`: state_reason is not a --json field on
        # every gh version, and out-of-scope hangs off it.
        d = gh("api", f"repos/{repo}/issues/{n}")
        blockers = gh("api", f"repos/{repo}/issues/{n}/dependencies/blocked_by",
                      "--jq", "[.[]|{number,state}]") or []
        edges[n] = blockers

        labels = [l["name"] for l in d["labels"]]
        ttype = next((l.split(":", 1)[1] for l in labels if l.startswith("wayfinder:")), "task")
        assignees = [a["login"] for a in d["assignees"]]
        closed = d["state"] == "closed"
        open_blockers = [b["number"] for b in blockers if b["state"] != "closed"]

        if closed and (d.get("state_reason") == "not_planned" or ttype == "out-of-scope"):
            status = "out_of_scope"
        elif closed:
            status = "resolved"
        elif assignees:
            status = "claimed"
        elif open_blockers:
            status = "blocked"
        else:
            status = "frontier"

        nodes.append({
            "num": n, "title": d["title"], "type": ttype, "status": status,
            "claimedBy": assignees[0] if assignees else None,
            "gist": gist(d["body"] or ""), "body": d["body"] or "",
            "url": d["html_url"],
            "undermined": bool(re.search(r"undermined", d["body"] or "", re.I)),
            "blockers": [{"num": b["number"], "satisfied": b["state"] == "closed"}
                         for b in blockers],
        })

    rank = {}

    def rank_of(n, seen=()):
        if n in rank:
            return rank[n]
        if n in seen:                       # cycle guard
            return 0
        bs = [b["number"] for b in edges.get(n, []) if b["number"] in edges]
        rank[n] = 0 if not bs else 1 + max(rank_of(b, seen + (n,)) for b in bs)
        return rank[n]

    for n in nodes:
        n["rank"] = rank_of(n["num"])

    # fog: bullets under "Not yet specified" (current shape) or "Fog" (older maps)
    fog = []
    for line in section(body, "Not yet specified", "Fog", "Fog of war").split("\n"):
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if not m:
            continue
        t = " ".join(m.group(1).split())
        anchor = re.search(r"#(\d+)", t)
        fog.append({"title": re.sub(r"\s*\(?#\d+\)?", "", t).strip(),
                    "anchor": int(anchor.group(1)) if anchor else None})

    undermined = ""
    um = re.findall(r"^.*undermined.*$", body, re.I | re.M)
    if um:
        undermined = " ".join(re.sub(r"[>*_`]", "", um[0]).split())[:400]

    return {
        "destination": section(body, "Destination") or mp["title"],
        "destinationNote": ("" if section(body, "Destination")
                            else "This map predates the Destination section — its title is the anchor."),
        "mapTitle": mp["title"], "mapUrl": mp["url"],
        "nodes": nodes, "fog": fog, "undermined": undermined,
        "generated": datetime.datetime.now().strftime("%d %b %Y, %H:%M"),
    }


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Star-map — __TITLE__</title>
<style>
  * { box-sizing:border-box; }
  html, body { margin:0; padding:0; height:100%; overflow:hidden;
    background:#05070f; color:#dbe4f0;
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
  /* canvas is a replaced element: inset:0 alone leaves it at its intrinsic
     300x150, so the size has to be stated outright. */
  #sky { position:fixed; top:0; left:0; width:100%; height:100%;
         display:block; cursor:grab; touch-action:none; }
  #sky.dragging { cursor:grabbing; }

  #hud { position:fixed; top:0; left:0; right:0; padding:18px 22px;
    pointer-events:none; z-index:10; background:linear-gradient(#05070fdd,#05070f00); }
  #hud .dest { font-size:11px; letter-spacing:.22em; text-transform:uppercase;
    color:#7d8ba3; margin-bottom:4px; }
  #hud h1 { margin:0; font-size:20px; font-weight:600; letter-spacing:-.01em; }
  #hud h1 a { color:#f0f5ff; text-decoration:none; pointer-events:auto; }
  #hud h1 a:hover { text-decoration:underline; }
  #hud .note { font-size:11px; color:#5f6c82; margin-top:5px; max-width:520px; line-height:1.5; }
  #bar { margin-top:12px; display:flex; height:6px; width:min(420px,52vw);
    border:1px solid #1c2436; border-radius:2px; overflow:hidden; background:#0b1020; }
  #bar div { height:100%; }
  #tally { margin-top:7px; display:flex; gap:14px; flex-wrap:wrap;
    font-size:11px; color:#8d9bb2; font-variant-numeric:tabular-nums; }
  #tally span { display:flex; align-items:center; gap:5px; }
  #tally i { width:7px; height:7px; border-radius:50%; display:inline-block; }

  #warn { position:fixed; bottom:14px; left:22px; right:22px; max-width:640px;
    font-size:11px; line-height:1.55; color:#e0a89a; pointer-events:none; z-index:10;
    border-left:2px solid #7f3f34; padding:6px 0 6px 10px; }
  #warn:empty { display:none; }
  #stamp { position:fixed; bottom:14px; right:22px; font-size:10px; color:#4a5570;
    text-align:right; line-height:1.5; pointer-events:none; z-index:10; }
  #legend { position:fixed; top:50%; right:18px; transform:translateY(-50%);
    font-size:10px; color:#6b7890; z-index:9; pointer-events:none;
    display:flex; flex-direction:column; gap:7px; }
  #legend span { display:flex; align-items:center; gap:6px; justify-content:flex-end; }
  #legend i { width:8px; height:8px; border-radius:50%; }

  #panel { position:fixed; top:0; right:0; height:100%; width:min(560px,92vw);
    background:#080c18f2; backdrop-filter:blur(8px); border-left:1px solid #1e2740;
    z-index:20; transform:translateX(100%);
    transition:transform .28s cubic-bezier(.22,.61,.36,1);
    display:flex; flex-direction:column; }
  #panel.open { transform:translateX(0); }
  #panel header { padding:20px 22px 14px; border-bottom:1px solid #17203a; }
  #panel .kicker { font-size:10px; letter-spacing:.2em; text-transform:uppercase;
    display:flex; gap:10px; align-items:center; margin-bottom:8px; flex-wrap:wrap; }
  #panel h2 { margin:0 0 8px; font-size:19px; line-height:1.3; }
  #panel h2 a { color:#f0f5ff; text-decoration:none; }
  #panel h2 a:hover { text-decoration:underline; }
  #panel .blockers { font-size:11px; color:#8d9bb2; line-height:1.7; }
  #panel .blockers b { color:#dbe4f0; font-weight:500; }
  #panel .body { padding:16px 22px 40px; overflow-y:auto; flex:1;
    font-size:13px; line-height:1.65; color:#b9c5d8; }
  #panel .body h3 { color:#eaf1ff; font-size:13px; letter-spacing:.04em;
    text-transform:uppercase; margin:22px 0 8px; }
  #panel .body code { background:#131c30; padding:1px 5px; border-radius:3px;
    font-size:12px; color:#a8c6f0; }
  #panel .body pre { background:#0b1120; border:1px solid #18213a; padding:10px;
    border-radius:4px; overflow-x:auto; font-size:11.5px; }
  #panel .body a { color:#7fb0ef; }
  #panel .body table { border-collapse:collapse; width:100%; margin:10px 0; font-size:12px; }
  #panel .body td { border:1px solid #1c2540; padding:5px 8px; text-align:left; }
  #panel .close { position:absolute; top:16px; right:18px; cursor:pointer;
    background:none; border:none; color:#5f6c82; font-size:20px; line-height:1; }
  #panel .close:hover { color:#dbe4f0; }
  .pill { padding:2px 7px; border-radius:2px; font-size:9px; letter-spacing:.14em; }
</style>
</head>
<body>
<canvas id="sky"></canvas>
<div id="hud">
  <div class="dest">destination</div>
  <h1><a id="destLink" href="#" target="_blank" rel="noopener"></a></h1>
  <div class="note" id="destNote"></div>
  <div id="bar"></div><div id="tally"></div>
</div>
<div id="legend"></div><div id="warn"></div><div id="stamp"></div>
<div id="panel">
  <button class="close" aria-label="Close">&times;</button>
  <header>
    <div class="kicker" id="pKicker"></div>
    <h2><a id="pTitle" href="#" target="_blank" rel="noopener"></a></h2>
    <div class="blockers" id="pBlockers"></div>
  </header>
  <div class="body" id="pBody"></div>
</div>
<script>
const GRAPH = __GRAPH__;
const COLOR = {
  resolved:    { core:'#c6d8ef', glow:'#5d7fa8',   r:7,  label:'resolved' },
  frontier:    { core:'#ffd166', glow:'#c8901f',   r:12, label:'frontier' },
  claimed:     { core:'#ff9d3d', glow:'#b3612088', r:10, label:'claimed' },
  blocked:     { core:'#b4595b', glow:'#5e2a2c',   r:6,  label:'blocked' },
  out_of_scope:{ core:'#6b7280', glow:'#33373f',   r:6,  label:'out of scope' },
};
function seeded(n){ const x = Math.sin(n*127.1)*43758.5453; return x - Math.floor(x); }

const maxRank = Math.max(0, ...GRAPH.nodes.map(n=>n.rank));
const RING = 165;
const N = GRAPH.nodes.map(n => {
  const a = seeded(n.num)*Math.PI*2, rad = 90 + n.rank*RING;
  return Object.assign({}, n, { x:Math.cos(a)*rad, y:Math.sin(a)*rad, vx:0, vy:0,
                                targetR:rad, phase:seeded(n.num*7)*Math.PI*2 });
});
const byNum = Object.fromEntries(N.map(n=>[n.num,n]));

for (let s=0; s<500; s++) {                     // fixed relaxation: same every load
  for (const a of N) {
    let fx=0, fy=0;
    for (const b of N) {
      if (a===b) continue;
      const dx=a.x-b.x, dy=a.y-b.y, d2=Math.max(dx*dx+dy*dy,400), f=90000/d2;
      fx += dx/Math.sqrt(d2)*f; fy += dy/Math.sqrt(d2)*f;
    }
    const r = Math.hypot(a.x,a.y)||1, pull=(a.targetR-r)*0.06;
    fx += a.x/r*pull; fy += a.y/r*pull;
    a.vx=(a.vx+fx*0.012)*0.82; a.vy=(a.vy+fy*0.012)*0.82;
  }
  for (const a of N) { a.x+=a.vx; a.y+=a.vy; }
}

const FOG = GRAPH.fog.map((f,i) => {
  const a = seeded(900+i*37)*Math.PI*2;
  const rad = 130 + maxRank*RING + 210 + seeded(950+i)*90;
  return Object.assign({}, f, { x:Math.cos(a)*rad, y:Math.sin(a)*rad, phase:seeded(970+i)*6.28 });
});

const LAYERS=[{n:260,s:.25,r:.7,a:.35},{n:150,s:.5,r:1,a:.5},{n:70,s:.85,r:1.5,a:.7}];
const FIELD = LAYERS.map((L,li)=>{
  const stars=[];
  for(let i=0;i<L.n;i++) stars.push({
    x:(seeded(li*1000+i*3+1)-.5)*7000, y:(seeded(li*1000+i*3+2)-.5)*7000,
    r:L.r*(.5+seeded(li*1000+i*3+3)), a:L.a*(.4+seeded(li*1000+i*3+4)*.6) });
  return { stars, s:L.s };
});

const cv=document.getElementById('sky'), ctx=cv.getContext('2d');
let cam={x:0,y:0,z:.85,tx:0,ty:0,tz:.85}, dpr=1, W=0, H=0;
function resize(){
  dpr = Math.min(window.devicePixelRatio||1, 2);
  W = cv.clientWidth  || window.innerWidth;
  H = cv.clientHeight || window.innerHeight;
  cv.width=Math.round(W*dpr); cv.height=Math.round(H*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);
}
window.addEventListener('resize',resize); window.addEventListener('load',resize); resize();

let drag=null;
cv.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,moved:false};cv.classList.add('dragging');});
cv.addEventListener('pointermove',e=>{
  if(!drag) return;
  const dx=e.clientX-drag.x, dy=e.clientY-drag.y;
  if(Math.abs(dx)+Math.abs(dy)>3) drag.moved=true;
  cam.tx-=dx/cam.z; cam.ty-=dy/cam.z; cam.x=cam.tx; cam.y=cam.ty;
  drag.x=e.clientX; drag.y=e.clientY;
});
cv.addEventListener('pointerup',e=>{
  cv.classList.remove('dragging');
  if(drag&&!drag.moved) pick(e.clientX,e.clientY);
  drag=null;
});
cv.addEventListener('wheel',e=>{
  e.preventDefault();
  cam.tz=Math.min(2.4,Math.max(.3,cam.tz*(e.deltaY<0?1.12:.893)));
},{passive:false});
function toScreen(p){ return {x:(p.x-cam.x)*cam.z+W/2, y:(p.y-cam.y)*cam.z+H/2}; }

let selected=null;
function pick(sx,sy){
  let hit=null;
  for(const n of N){
    const s=toScreen(n), rr=(COLOR[n.status].r+10)*cam.z;
    if((sx-s.x)**2+(sy-s.y)**2 < rr*rr) hit=n;
  }
  if(hit){ selected=hit; openPanel(hit); cam.tx=hit.x; cam.ty=hit.y; return; }
  for(const f of FOG){
    const s=toScreen(f);
    if((sx-s.x)**2+(sy-s.y)**2 < (46*cam.z)**2){ openFog(f); return; }
  }
  closePanel();
}

const panel=document.getElementById('panel');
function md(src){
  const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const lines=esc(src).split('\n');
  let out='', inCode=false, inTable=false;
  for(const raw of lines){
    if(/^```/.test(raw)){ out+=inCode?'</pre>':'<pre>'; inCode=!inCode; continue; }
    if(inCode){ out+=raw+'\n'; continue; }
    const l=raw.replace(/`([^`]+)`/g,'<code>$1</code>')
               .replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>')
               .replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
    const cells=l.trim().match(/^\|(.+)\|$/);
    if(cells){
      if(/^[\s|:-]+$/.test(l)) continue;
      if(!inTable){ out+='<table>'; inTable=true; }
      out+='<tr>'+cells[1].split('|').map(c=>'<td>'+c.trim()+'</td>').join('')+'</tr>';
      continue;
    }
    if(inTable){ out+='</table>'; inTable=false; }
    const h=l.match(/^(#{1,4})\s+(.*)$/);
    if(h){ out+='<h3>'+h[2]+'</h3>'; continue; }
    if(/^\s*[-*]\s+/.test(l)){ out+='<div style="padding-left:14px">• '+l.replace(/^\s*[-*]\s+/,'')+'</div>'; continue; }
    if(!l.trim()){ out+='<div style="height:8px"></div>'; continue; }
    out+='<p style="margin:0 0 8px">'+l+'</p>';
  }
  if(inTable) out+='</table>';
  if(inCode) out+='</pre>';
  return out;
}
function openPanel(n){
  const c=COLOR[n.status];
  document.getElementById('pKicker').innerHTML =
    `<span class="pill" style="background:${c.core}22;color:${c.core}">${c.label}</span>`+
    `<span style="color:#5f6c82">#${n.num}</span>`+
    `<span style="color:#5f6c82">${n.type}</span>`+
    (n.claimedBy?`<span style="color:#ff9d3d">claimed by ${n.claimedBy}</span>`:'')+
    (n.undermined?`<span style="color:#e0a89a">undermined</span>`:'');
  const t=document.getElementById('pTitle'); t.textContent=n.title; t.href=n.url;
  document.getElementById('pBlockers').innerHTML = n.blockers.length
    ? 'Blocked by '+n.blockers.map(b=>
        `<b>${byNum[b.num]?byNum[b.num].title:('#'+b.num)}</b> ${b.satisfied?'✓ resolved':'— still open'}`
      ).join(' · ')
    : 'No blockers.';
  const pb=document.getElementById('pBody'); pb.innerHTML=md(n.body); pb.scrollTop=0;
  panel.classList.add('open');
}
function openFog(f){
  document.getElementById('pKicker').innerHTML =
    '<span class="pill" style="background:#6b46c122;color:#a78bfa">fog</span>'+
    '<span style="color:#5f6c82">not yet specified</span>';
  const t=document.getElementById('pTitle'); t.textContent=f.title; t.href=GRAPH.mapUrl;
  document.getElementById('pBlockers').innerHTML = f.anchor && byNum[f.anchor]
    ? `Anchored to <b>${byNum[f.anchor].title}</b>`
    : 'Unanchored — no live ticket holds this question yet.';
  document.getElementById('pBody').innerHTML =
    '<p style="margin:0;color:#8d9bb2">In scope, but not yet sharp enough to ticket. '+
    'It graduates into one or more tickets once the frontier reaches it — or into nothing.</p>';
  panel.classList.add('open');
}
function closePanel(){ selected=null; panel.classList.remove('open'); }
panel.querySelector('.close').addEventListener('click',closePanel);
window.addEventListener('keydown',e=>{ if(e.key==='Escape') closePanel(); });

function drawEdges(t){
  for(const n of N) for(const b of n.blockers){
    const from=byNum[b.num]; if(!from) continue;
    const a=toScreen(from), c=toScreen(n);
    const mx=(a.x+c.x)/2, my=(a.y+c.y)/2;
    const nx=-(c.y-a.y), ny=(c.x-a.x), len=Math.hypot(nx,ny)||1;
    const bow=.14*Math.hypot(c.x-a.x,c.y-a.y);
    const qx=mx+nx/len*bow, qy=my+ny/len*bow;
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.quadraticCurveTo(qx,qy,c.x,c.y);
    if(b.satisfied){
      ctx.strokeStyle='rgba(150,190,240,0.30)'; ctx.lineWidth=1.3*cam.z;
      ctx.setLineDash([]); ctx.stroke();
      for(let k=0;k<3;k++){                       // flow: blocker -> dependent
        const u=((t*0.00013+k/3+b.num*0.11)%1), iu=1-u;
        const px=iu*iu*a.x+2*iu*u*qx+u*u*c.x, py=iu*iu*a.y+2*iu*u*qy+u*u*c.y;
        ctx.beginPath(); ctx.arc(px,py,1.7*cam.z,0,6.2832);
        ctx.fillStyle='rgba(198,216,239,'+(0.75*Math.sin(Math.PI*u))+')'; ctx.fill();
      }
    } else {
      ctx.strokeStyle='rgba(120,135,160,0.16)'; ctx.lineWidth=cam.z;
      ctx.setLineDash([5*cam.z,6*cam.z]); ctx.stroke(); ctx.setLineDash([]);
    }
  }
}
function drawNodes(t){
  for(const n of N){
    const c=COLOR[n.status], s=toScreen(n);
    const y=s.y+Math.sin(t*.0009+n.phase)*2.2*cam.z;
    let r=c.r*cam.z;
    if(n.status==='frontier') r*=1+.10*Math.sin(t*.0028);
    const sel=selected===n;
    const g=ctx.createRadialGradient(s.x,y,0,s.x,y,r*5.5);
    g.addColorStop(0,c.glow); g.addColorStop(1,'rgba(0,0,0,0)');
    ctx.globalAlpha = n.status==='frontier'?.55:.34;
    ctx.beginPath(); ctx.arc(s.x,y,r*5.5,0,6.2832); ctx.fillStyle=g; ctx.fill();
    ctx.globalAlpha=1;
    ctx.beginPath(); ctx.arc(s.x,y,r,0,6.2832); ctx.fillStyle=c.core; ctx.fill();
    if(n.undermined){                             // cracked halo
      ctx.beginPath(); ctx.arc(s.x,y,r+4*cam.z,0,6.2832);
      ctx.setLineDash([3*cam.z,4*cam.z]);
      ctx.strokeStyle='rgba(224,120,100,.85)'; ctx.lineWidth=1.6*cam.z; ctx.stroke();
      ctx.setLineDash([]);
    }
    if(sel){
      ctx.beginPath(); ctx.arc(s.x,y,r+7*cam.z,0,6.2832);
      ctx.strokeStyle='#ffffffcc'; ctx.lineWidth=1.4*cam.z; ctx.stroke();
    }
    if(cam.z>.5){
      const label='#'+n.num+' '+n.title;
      ctx.font=`${Math.max(10,11*cam.z)}px ui-sans-serif, system-ui, sans-serif`;
      ctx.textAlign='center'; ctx.fillStyle=sel?'#fff':'#c3cfe2';
      ctx.fillText(label.length>34?label.slice(0,33)+'…':label, s.x, y+r+16*cam.z);
      ctx.fillStyle='#63708a';
      ctx.font=`${Math.max(8,9*cam.z)}px ui-monospace, monospace`;
      ctx.fillText(n.type, s.x, y+r+29*cam.z);
    }
  }
  ctx.textAlign='left';
}
function drawFog(t){
  for(const f of FOG){
    const s=toScreen(f), rr=(40+6*Math.sin(t*.0006+f.phase))*cam.z;
    const g=ctx.createRadialGradient(s.x,s.y,0,s.x,s.y,rr*2.2);
    g.addColorStop(0,'rgba(139,120,220,0.20)'); g.addColorStop(1,'rgba(0,0,0,0)');
    ctx.beginPath(); ctx.arc(s.x,s.y,rr*2.2,0,6.2832); ctx.fillStyle=g; ctx.fill();
    if(f.anchor&&byNum[f.anchor]){
      const a=toScreen(byNum[f.anchor]);
      ctx.beginPath(); ctx.moveTo(s.x,s.y); ctx.lineTo(a.x,a.y);
      ctx.setLineDash([3*cam.z,7*cam.z]);
      ctx.strokeStyle='rgba(139,120,220,0.22)'; ctx.lineWidth=1; ctx.stroke();
      ctx.setLineDash([]);
    }
    if(cam.z>.45){
      ctx.font=`italic ${Math.max(9,10*cam.z)}px ui-sans-serif, system-ui, sans-serif`;
      ctx.textAlign='center'; ctx.fillStyle='rgba(167,139,250,0.75)';
      ctx.fillText(f.title.length>30?f.title.slice(0,29)+'…':f.title, s.x, s.y+rr+6*cam.z);
      ctx.textAlign='left';
    }
  }
}
function frame(t){
  cam.z+=(cam.tz-cam.z)*.12; cam.x+=(cam.tx-cam.x)*.12; cam.y+=(cam.ty-cam.y)*.12;
  ctx.fillStyle='#05070f'; ctx.fillRect(0,0,W,H);
  for(const L of FIELD) for(const st of L.stars){
    const x=(st.x-cam.x*L.s)*cam.z+W/2, y=(st.y-cam.y*L.s)*cam.z+H/2;
    if(x<-20||x>W+20||y<-20||y>H+20) continue;
    ctx.globalAlpha=st.a; ctx.fillStyle='#aebedb';
    ctx.beginPath(); ctx.arc(x,y,st.r*cam.z,0,6.2832); ctx.fill();
  }
  ctx.globalAlpha=1;
  const o=toScreen({x:0,y:0});
  const cg=ctx.createRadialGradient(o.x,o.y,0,o.x,o.y,190*cam.z);
  cg.addColorStop(0,'rgba(120,160,220,0.16)'); cg.addColorStop(1,'rgba(0,0,0,0)');
  ctx.beginPath(); ctx.arc(o.x,o.y,190*cam.z,0,6.2832); ctx.fillStyle=cg; ctx.fill();
  drawFog(t); drawEdges(t); drawNodes(t);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

const dl=document.getElementById('destLink');
dl.textContent=GRAPH.destination; dl.href=GRAPH.mapUrl;
document.getElementById('destNote').textContent=GRAPH.destinationNote;
const order=['resolved','claimed','frontier','blocked','out_of_scope'];
const counts={}; for(const k of order) counts[k]=N.filter(n=>n.status===k).length;
document.getElementById('bar').innerHTML=order.filter(k=>counts[k])
  .map(k=>`<div style="width:${counts[k]/N.length*100}%;background:${COLOR[k].core}"></div>`).join('');
document.getElementById('tally').innerHTML=order
  .map(k=>`<span><i style="background:${COLOR[k].core}"></i>${counts[k]} ${COLOR[k].label}</span>`).join('')
  +(FOG.length?`<span style="color:#a78bfa"><i style="background:#a78bfa"></i>${FOG.length} fog</span>`:'');
document.getElementById('legend').innerHTML=order
  .map(k=>`<span>${COLOR[k].label}<i style="background:${COLOR[k].core}"></i></span>`).join('')
  +(FOG.length?'<span style="color:#a78bfa">fog<i style="background:#a78bfa"></i></span>':'');
document.getElementById('warn').textContent=GRAPH.undermined;
document.getElementById('stamp').innerHTML =
  'drag to pan · scroll to zoom · click a star<br>read from the GitHub adapter, '+GRAPH.generated;
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Render a wayfinder map as a star-map.")
    ap.add_argument("map", type=int, help="the map issue number")
    ap.add_argument("--repo", help="owner/name (default: this clone's remote)")
    ap.add_argument("--out", help="output path (default: /tmp/starmap-<map>.html)")
    a = ap.parse_args()

    repo = a.repo or detect_repo()
    out = a.out or f"/tmp/starmap-{a.map}.html"

    g = build(a.map, repo)
    html = (TEMPLATE
            .replace("__TITLE__", g["mapTitle"].replace("&", "&amp;").replace("<", "&lt;"))
            .replace("__GRAPH__", json.dumps(g)))
    with open(out, "w") as f:
        f.write(html)

    counts = {k: sum(1 for n in g["nodes"] if n["status"] == k) for k in STATUS_ORDER}
    print(f"{g['mapTitle']}  ({repo}#{a.map})")
    print("  " + " · ".join(f"{v} {k.replace('_',' ')}" for k, v in counts.items() if v)
          + (f" · {len(g['fog'])} fog" if g["fog"] else ""))
    for n in sorted(g["nodes"], key=lambda n: (n["rank"], n["num"])):
        print(f"  {n['num']:>5}  rank={n['rank']}  {n['status']:<12} {n['type']:<10} {n['title']}")
    print(f"\nwrote {out}")
    return out


if __name__ == "__main__":
    main()
