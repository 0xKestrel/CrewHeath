#!/usr/bin/env python3
"""Adds Anatomy Explorer (search + systems + 2D heart) to Crew Health Companion.
Usage:  python3 apply_anatomy_patch.py path/to/index.html
Makes index.html.bak first. Aborts without writing if any anchor is missing."""
import shutil, sys
p = sys.argv[1] if len(sys.argv) > 1 else "index.html"
s = open(p, encoding="utf-8").read()
if "ANAT=[" in s: sys.exit("Already patched.")

CSS = r"""
/* ---------- Anatomy explorer ---------- */
.asr{display:flex;gap:8px;margin-top:6px}.asr input{flex:1}.asr button{padding:0 16px;border-radius:14px;font-weight:700;color:var(--on);background:linear-gradient(135deg,var(--acc),var(--acc2))}
.ares{margin-top:14px;padding:14px 16px;border-radius:18px;background:var(--chip);border:1px solid var(--line)}
.ares h3{margin:0 0 4px;font-size:1.15rem}.ares .tag{margin-right:6px}
.gold{color:#f5c542}:root[data-theme=light] .gold{color:#8a6500}
.amk circle{fill:#f5c542;stroke:#fff3c4;stroke-width:1.5}.amk .rg{fill:none;stroke:#f5c542;stroke-width:2;transform-box:fill-box;transform-origin:center;animation:amk 1.7s ease-out infinite}
@keyframes amk{from{transform:scale(.5);opacity:1}to{transform:scale(2.6);opacity:0}}
.heartbox{margin-top:14px;border-radius:20px;padding:10px 8px 12px;border:1px solid rgba(255,90,110,.28);background:radial-gradient(120% 90% at 50% 40%,#2a0b14,#0c0409 70%);box-shadow:0 0 40px -18px #ff3b52,inset 0 1px 0 rgba(255,255,255,.05);color:#f3d4d8}
.heartbox svg{display:block;width:100%;height:auto;overflow:visible}
.hbeat{transform-box:fill-box;transform-origin:50% 62%;animation:hbeat .83s ease-in-out infinite}
.hglow{transform-box:fill-box;transform-origin:center;animation:hglow .83s ease-out infinite}
.hfl{fill:none;stroke-dasharray:.1 18;stroke-width:5;animation:hflow .83s linear infinite}
.ecg{animation:ecg .83s linear infinite}
.hlab{font:500 10.5px var(--font);fill:#e9b9bf}.hln{stroke:#e9b9bf;stroke-opacity:.4;stroke-width:.8}
.hbar{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between;padding:6px 10px 0;font-size:.78rem}
.hph{position:relative;display:inline-block;height:1.2em;vertical-align:bottom;min-width:5.5em;font-weight:700;letter-spacing:.06em;text-transform:uppercase}.hph i{font-style:normal;position:absolute}
.hph .s{animation:hsys .83s infinite}.hph .d{animation:hdia .83s infinite}
.hpause{padding:5px 12px;border:1px solid rgba(255,130,145,.4);color:#f3d4d8;font-size:.78rem}
.paused *{animation-play-state:paused!important}
@keyframes hbeat{0%{transform:scale(1)}10%{transform:scale(1.05)}22%{transform:scale(1.012)}34%{transform:scale(1.03)}50%,100%{transform:scale(1)}}
@keyframes hglow{0%{opacity:.3;transform:scale(.94)}10%{opacity:.85;transform:scale(1.08)}50%,100%{opacity:.3;transform:scale(.94)}}
@keyframes hflow{to{stroke-dashoffset:-18}}
@keyframes ecg{to{transform:translateX(-100px)}}
@keyframes hsys{0%,34%{opacity:1}35%,100%{opacity:0}}
@keyframes hdia{0%,34%{opacity:0}35%,100%{opacity:1}}
"""

JS = r"""
/* ---------- Anatomy explorer: search, systems, 2D heart ---------- */
const SYS={skeletal:"Skeletal system",muscular:"Muscular system",nervous:"Nervous system",circulatory:"Circulatory system",respiratory:"Respiratory system"};
const SYSD={skeletal:"The bones and joints that support the body and protect organs.",muscular:"Skeletal muscles that move the body. Loaded by gravity on Earth, so they weaken faster in orbit without exercise.",nervous:"The brain, spinal cord and nerves that sense, decide and signal.",circulatory:"The heart and blood vessels that move blood around the body.",respiratory:"The airways and lungs that bring oxygen in and carry carbon dioxide out."};
const SYSAL={skeletal:"skeletal system|skeleton|skeletal",muscular:"muscular system|musculature|muscular",nervous:"nervous system|neural",circulatory:"circulatory system|blood vessels|vessels|vascular|cardiovascular|blood",respiratory:"respiratory system|respiratory|breathing"};
const WB=" Bone density here is monitored on long missions (see Bone density in the Guide).";
const ANT=(id,n,s,al,x,y,d)=>({id,n,s,al:al.split("|"),x,y,d});
const ANAT=[
ANT("skull","Skull","skeletal","cranium|head bone",100,38,"Bony case of the head. Protects the brain and forms the face."),
ANT("spine","Spine","skeletal","vertebral column|backbone|vertebrae|spinal column",100,125,"Stack of 33 vertebrae that supports the trunk and encloses the spinal cord."+WB),
ANT("ribcage","Rib cage","skeletal","ribs|thoracic cage|chest bones|rib",100,108,"Twelve pairs of ribs with the sternum. Protects the heart and lungs and moves with breathing."),
ANT("sternum","Sternum","skeletal","breastbone|breast bone",100,98,"Flat bone at the front of the chest where the ribs attach."),
ANT("clavicle","Clavicle","skeletal","collarbone|collar bone",80,84,"Collarbone linking the shoulder blade to the sternum."),
ANT("humerus","Humerus","skeletal","upper arm bone",54,118,"Long bone of the upper arm, from shoulder to elbow."),
ANT("forearm","Radius and ulna","skeletal","radius|ulna|forearm bones|forearm",52,160,"The two long bones of the forearm."),
ANT("pelvis","Pelvis","skeletal","hip bone|hips|pelvic girdle",100,185,"Ring of bones that carries the body's weight to the legs."+WB),
ANT("femur","Femur","skeletal","thigh bone|thighbone",88,232,"Thigh bone. The longest and strongest bone in the body."+WB),
ANT("tibia","Tibia","skeletal","shin|shin bone|shinbone",87,297,"Shin bone. The main weight-bearing bone of the lower leg."+WB),
ANT("shoulderj","Shoulder joint","skeletal","glenohumeral joint|shoulder socket",66,90,"Ball-and-socket joint between the humerus and shoulder blade. The most mobile joint."),
ANT("hipj","Hip joint","skeletal","hip socket",88,194,"Ball-and-socket joint between the femur and pelvis."),
ANT("kneej","Knee joint","skeletal","knee|knee cap|kneecap|patella",87,262,"Hinge joint between the femur and tibia, with the kneecap at the front."),
ANT("deltoid","Deltoid","muscular","shoulder muscle|shoulder muscles|delts",60,92,"Rounded muscle that lifts the arm at the shoulder."),
ANT("pec","Pectorals","muscular","chest muscle|chest muscles|pecs",88,100,"Chest muscles that push and draw the arms across the body."),
ANT("biceps","Biceps","muscular","bicep|biceps brachii|upper arm muscle",54,112,"Front upper-arm muscle that bends the elbow."),
ANT("triceps","Triceps","muscular","tricep|triceps brachii",54,134,"Back upper-arm muscle that straightens the elbow."),
ANT("abs","Abdominals","muscular","abs|core|abdominal muscles|stomach muscles",100,152,"Trunk muscles that stabilise the spine and pelvis."),
ANT("glutes","Gluteals","muscular","glutes|buttocks|gluteus",100,196,"Hip and buttock muscles used to stand and climb. Weakens without gravity."),
ANT("quads","Quadriceps","muscular","quad|quads|front thigh|thigh muscle",87,225,"Four muscles on the front of the thigh that straighten the knee. Weakens without gravity."),
ANT("hams","Hamstrings","muscular","hamstring|back thigh",113,232,"Muscles on the back of the thigh that bend the knee."),
ANT("calf","Calf muscles","muscular","calf|gastrocnemius|soleus|calves",113,296,"Lower-leg muscles used to stand and walk. Weakens without gravity."),
ANT("brain","Brain","nervous","cerebrum|cerebellum|encephalon",100,36,"Control centre of the nervous system."),
ANT("cord","Spinal cord","nervous","spinal nerve|spine cord",100,125,"Nerve bundle running inside the spine, linking brain and body."),
ANT("sciatic","Sciatic nerve","nervous","sciatica nerve",88,212,"The longest nerve in the body, from the lower back down the leg."),
ANT("optic","Optic nerve","nervous","eye nerve|vision nerve",100,48,"Carries signals from the eye to the brain. Tracked on long missions for eyesight changes."),
ANT("vest","Vestibular system","nervous","inner ear|balance organ|ear balance",71,52,"Inner-ear organs that sense motion and head position. Adapts in microgravity."),
ANT("aorta","Aorta","circulatory","main artery|aortic arch",104,118,"The body's largest artery, carrying oxygen-rich blood from the left ventricle."),
ANT("vcava","Vena cava","circulatory","great vein|superior vena cava|inferior vena cava",96,126,"Two large veins returning oxygen-poor blood to the heart."),
ANT("carotid","Carotid artery","circulatory","neck artery|carotid",92,70,"Neck arteries supplying the brain and face."),
ANT("lungs","Lungs","respiratory","lung|pulmonary",100,108,"Paired organs where oxygen enters the blood and carbon dioxide leaves."),
ANT("trachea","Trachea","respiratory","windpipe|airway|airways",100,78,"Windpipe carrying air to the lungs."),
ANT("diaph","Diaphragm","respiratory","breathing muscle",100,146,"Dome-shaped muscle under the lungs that drives breathing.")];
const AMB={bone:["skeletal",["skull","spine","ribcage","pelvis","femur","tibia","humerus"]],muscle:["muscular",["deltoid","biceps","quads","calf","glutes","pec"]],nerve:["nervous",["brain","cord","sciatic","optic","vest"]],vein:["circulatory",["vcava","aorta","carotid"]],artery:["circulatory",["aorta","carotid"]],joint:["skeletal",["shoulderj","hipj","kneej"]],shoulder:["skeletal",["shoulderj","deltoid","clavicle"]],leg:["skeletal",["femur","tibia","quads","calf"]],arm:["skeletal",["humerus","forearm","biceps","triceps"]]};
const nz=s=>String(s).toLowerCase().replace(/[^a-z ]/g," ").split(/\s+/).filter(Boolean).map(w=>w.length>3&&!/ss$/.test(w)?w.replace(/s$/,""):w).join(" ");
function lev(a,b){const m=[];for(let i=0;i<=a.length;i++){m[i]=[i];for(let j=1;j<=b.length;j++)m[i][j]=i?0:j}
for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)m[i][j]=Math.min(m[i-1][j]+1,m[i][j-1]+1,m[i-1][j-1]+(a[i-1]===b[j-1]?0:1));return m[a.length][b.length]}
function ascore(n,a){if(n===a)return 100;if((" "+n+" ").includes(" "+a+" "))return 80+a.length;if(n.length>=3&&(" "+a+" ").includes(" "+n+" "))return 60;const d=lev(n,a);return a.length>=4&&d<=(a.length>6?2:1)?50-d*10:0}
function anatFind(q){const n=nz(q);if(!n)return null;
if(/heart|cardiac/.test(n))return{k:"heart"};
if(AMB[n])return{k:"amb",t:q.trim(),sys:AMB[n][0],ids:AMB[n][1]};
let best=null,bs=0;const tryit=(als,r)=>als.forEach(a=>{const sc=ascore(n,nz(a));if(sc>bs){bs=sc;best=r}});
ANAT.forEach(it=>tryit([it.n].concat(it.al),{k:"item",it}));
Object.keys(SYSAL).forEach(k=>tryit(SYSAL[k].split("|"),{k:"sys",sys:k}));
return bs>=50?best:{k:"none",q:q.trim()}}
let aq="",anat=null;
const aget=id=>ANAT.find(x=>x.id===id);
const achips=ids=>`<div class="chips">${ids.map(i=>`<button class="chip" data-aq="${esc(aget(i).n)}">${esc(aget(i).n)}</button>`).join("")}</div>`;
function anatMarker(){if(!anat||anat.k!=="item")return"";const i=anat.it;return`<g class="amk" pointer-events="none"><circle class="rg" cx="${i.x}" cy="${i.y}" r="7"/><circle cx="${i.x}" cy="${i.y}" r="4"/></g>`}
function ecgPath(){let d="M0 24";for(let k=0;k<6;k++){const o=k*100;d+=`H${o+20}q4 -6 8 0H${o+38}L${o+42} 28L${o+48} 3L${o+54} 34L${o+58} 24H${o+72}q6 -8 12 0H${o+100}`}return d}
function heartSvg(){const vs=(id,w,o,f,fl)=>`<use href="#${id}" stroke="${o}" stroke-width="${w+5}"/><use href="#${id}" stroke="${f}" stroke-width="${w}"/><use href="#${id}" stroke="#fff" stroke-opacity=".16" stroke-width="${Math.max(2,w/4)}" transform="translate(-${w/5},0)"/>${fl?`<use href="#${id}" class="hfl" stroke="${fl}"/>`:""}`;
const OX=["#3a0610","#b3202f","#ffb3b0"],DX=["#2c0818","#6b1d4a","#e093b4"];
const P={ao:"M222 205C222 140 222 100 244 84C274 66 306 82 312 122C316 170 318 240 322 335",b1:"M232 80L228 40",b2:"M252 72L254 36",b3:"M276 72L284 40",pt:"M192 198C192 160 200 140 214 128",lpa:"M214 128C240 120 270 118 300 128",rpa:"M206 132C180 122 160 116 140 120",svc:"M154 56L158 172",ivc:"M128 352C126 300 130 260 142 228",pv1:"M352 176C335 184 320 190 304 196",pv2:"M352 222C335 218 322 212 304 210",pv3:"M72 150C95 152 115 160 130 172",pv4:"M72 180C92 182 110 184 124 188"};
const lab=(t,x,y,tx,ty,end)=>`<line class="hln" x1="${x+(end?4:-4)}" y1="${y-3}" x2="${tx}" y2="${ty}"/><text class="hlab" x="${x}" y="${y}" text-anchor="${end?"end":"start"}">${t}</text>`;
return`<svg viewBox="-80 0 560 440" role="img" aria-label="Anatomical illustration of the human heart with its major vessels, beating continuously"><defs>
<radialGradient id="hgl" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ff3b52" stop-opacity=".55"/><stop offset="1" stop-color="#ff3b52" stop-opacity="0"/></radialGradient>
<radialGradient id="hlv" cx=".35" cy=".3" r=".85"><stop offset="0" stop-color="#e0485a"/><stop offset=".55" stop-color="#a81c2f"/><stop offset="1" stop-color="#5a0a17"/></radialGradient>
<radialGradient id="hrv" cx=".3" cy=".3" r=".9"><stop offset="0" stop-color="#c23a52"/><stop offset=".55" stop-color="#8e1a2e"/><stop offset="1" stop-color="#4a0813"/></radialGradient>
<radialGradient id="hat" cx=".4" cy=".35" r=".8"><stop offset="0" stop-color="#9b2a46"/><stop offset="1" stop-color="#3d0a1c"/></radialGradient>
<filter id="hbl"><feGaussianBlur stdDeviation="7"/></filter>
${Object.keys(P).map(k=>`<path id="p${k}" d="${P[k]}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`).join("")}</defs>
<circle class="hglow" cx="205" cy="270" r="170" fill="url(#hgl)"/>
${vs("ppv3",11,...OX.slice(0,2),OX[2])}${vs("ppv4",11,...OX.slice(0,2),OX[2])}${vs("ppv1",11,...OX.slice(0,2),OX[2])}${vs("ppv2",11,...OX.slice(0,2),OX[2])}
${vs("pprpa",14,DX[0],DX[1],DX[2])}${vs("psvc",18,DX[0],DX[1],DX[2])}${vs("pivc",20,DX[0],DX[1],DX[2])}
${vs("pao",26,OX[0],OX[1],OX[2])}${["b1","b2","b3"].map(k=>vs("p"+k,9,OX[0],OX[1])).join("")}
${vs("plpa",16,DX[0],DX[1],DX[2])}${vs("ppt",24,DX[0],DX[1],DX[2])}
<g class="hbeat">
<path d="M262 175C285 160 310 175 305 205C298 222 285 225 280 222C270 205 262 190 262 175Z" fill="url(#hat)" stroke="#2a0612" stroke-width="2"/>
<path d="M120 205C110 165 150 140 185 160C200 175 195 200 175 210C150 222 125 225 120 205Z" fill="url(#hat)" stroke="#2a0612" stroke-width="2"/>
<path d="M140 230C120 285 160 355 240 394C215 340 205 270 200 198C175 190 150 205 140 230Z" fill="url(#hrv)" stroke="#2a0612" stroke-width="2"/>
<path d="M200 198C205 270 215 340 240 394C300 362 318 290 292 226C275 195 230 185 200 198Z" fill="url(#hlv)" stroke="#2a0612" stroke-width="2"/>
<path d="M200 198C205 270 215 340 240 394" fill="none" stroke="#c98a5a" stroke-opacity=".55" stroke-width="6" stroke-linecap="round"/>
<ellipse cx="255" cy="262" rx="26" ry="50" fill="#fff" opacity=".1" filter="url(#hbl)" transform="rotate(12 255 262)"/>
<ellipse cx="165" cy="262" rx="18" ry="38" fill="#fff" opacity=".07" filter="url(#hbl)" transform="rotate(-10 165 262)"/>
<path d="M218 190C220 250 225 320 238 382" fill="none" stroke="#ff5a63" stroke-width="3.5" stroke-linecap="round"/>
<path d="M190 180C160 185 135 215 140 250C142 275 160 320 185 350" fill="none" stroke="#ff5a63" stroke-width="3.2" stroke-linecap="round"/>
<path d="M262 190C290 200 300 230 296 262" fill="none" stroke="#ff5a63" stroke-width="3" stroke-linecap="round"/>
</g>
${lab("Superior vena cava",66,50,152,62,1)}${lab("Pulmonary veins",60,150,76,152,1)}${lab("Right atrium",90,222,128,208,1)}${lab("Right ventricle",90,306,158,300,1)}${lab("Inferior vena cava",90,350,127,336,1)}
${lab("Aortic arch",362,44,300,76)}${lab("Pulmonary artery",362,108,292,124)}${lab("Pulmonary veins",362,204,352,200)}${lab("Left atrium",362,244,298,214)}${lab("Left ventricle",362,304,272,292)}${lab("Descending aorta",362,352,322,332)}
</svg>`}
function heartPanel(){return`<div class="heartbox" id="heart"><div class="hbar"><span><b>Heart</b> · anterior view, 2D illustration</span><span>Cycle: <span class="hph" aria-hidden="true"><i class="s">Systole</i><i class="d">Diastole</i></span></span></div>
${heartSvg()}
<svg viewBox="0 0 300 40" style="display:block;width:100%;height:42px;overflow:hidden" role="img" aria-label="Schematic ECG trace"><g class="ecg"><path d="${ecgPath()}" fill="none" stroke="#ff6b78" stroke-width="1.6" stroke-linejoin="round"/></g></svg>
<div class="hbar"><span><i style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#ffb3b0;margin-right:5px"></i>Oxygen-rich <i style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#e093b4;margin:0 5px 0 12px"></i>Oxygen-poor</span><button class="hpause" data-hp="1" aria-pressed="false">Pause animation</button></div>
<p class="small" style="margin:8px 10px 0;opacity:.7">Illustrative cardiac cycle at a fixed 72 beats per minute. It is not your data and not linked to your readings.</p></div>`}
function anatCard(){const a=anat;let r="";
if(a&&a.k==="heart")r=`<div class="ares"><h3 class="gold">Heart</h3><span class="tag">${SYS.circulatory}</span><p class="small mute" style="margin-top:8px">Four-chambered muscular pump. The right side sends blood to the lungs, the left side to the body.</p></div>${heartPanel()}`;
else if(a&&a.k==="item")r=`<div class="ares"><h3 class="gold">${esc(a.it.n)}</h3><span class="tag">${SYS[a.it.s]}</span><p style="margin:8px 0 0">${esc(a.it.d)}</p><p class="small mute" style="margin-top:8px">The gold marker on the body map below shows a schematic position only. The 3D isolated view is not installed (it needs an anatomical GLB model).</p></div>`;
else if(a&&a.k==="sys")r=`<div class="ares"><h3 class="gold">${SYS[a.sys]}</h3><p style="margin:6px 0 0">${SYSD[a.sys]}</p><p class="small mute" style="margin-top:8px">Pick a structure:</p><div class="chips">${ANAT.filter(x=>x.s===a.sys).map(x=>`<button class="chip" data-aq="${esc(x.n)}">${esc(x.n)}</button>`).join("")}${a.sys==="circulatory"?`<button class="chip" data-aq="heart">Heart</button>`:""}</div></div>`;
else if(a&&a.k==="amb")r=`<div class="ares"><h3>“${esc(a.t)}” could mean several things</h3><p class="small mute">Which one do you want to examine?</p>${achips(a.ids)}<div class="chips"><button class="chip" data-sys="${a.sys}">Whole ${SYS[a.sys].toLowerCase()}</button></div></div>`;
else if(a&&a.k==="none")r=`<div class="ares"><h3>No match for “${esc(a.q)}”</h3><p class="small mute">Try a bone, muscle, nerve, organ or system name, for example:</p>${achips(["femur","skull","biceps","brain","lungs"])}</div>`;
return`<div class="card fx"><h3>Anatomy explorer</h3><label for="aq" class="vh">Search anatomy</label><div class="asr"><input id="aq" type="search" autocomplete="off" placeholder="Search anatomy: bone, muscle, nerve, heart…" value="${esc(aq)}"><button type="button" id="aGo">Search</button></div>
<div class="chips">${Object.keys(SYS).map(k=>`<button class="chip${a&&a.k==="sys"&&a.sys===k?" on":""}" data-sys="${k}">${SYS[k].replace(" system","")}</button>`).join("")}<button class="chip${a&&a.k==="heart"?" on":""}" data-aq="heart">Heart</button></div>${r}${a?`<button class="ghost" id="aRst" style="margin-top:12px">Reset</button>`:""}<p class="small mute" style="margin:12px 0 0">Educational reference only, not a diagnosis.</p></div>`}
function runSearch(q){aq=q;anat=anatFind(q);renderCheck();const i=$("#aq");if(i&&!anat)i.focus()}
document.addEventListener("click",ev=>{const b=ev.target.closest&&ev.target.closest("[data-aq],[data-sys],#aGo,#aRst,[data-hp]");if(!b)return;
if(b.dataset.hp){const h=$("#heart"),p=h.classList.toggle("paused");b.setAttribute("aria-pressed",p);b.textContent=p?"Resume animation":"Pause animation";return}
if(b.dataset.aq!=null)runSearch(b.dataset.aq);else if(b.dataset.sys){anat={k:"sys",sys:b.dataset.sys};aq="";renderCheck()}
else if(b.id==="aGo")runSearch($("#aq").value);else if(b.id==="aRst"){anat=null;aq="";renderCheck()}});
document.addEventListener("keydown",ev=>{if(ev.key==="Enter"&&ev.target.id==="aq"){ev.preventDefault();runSearch(ev.target.value)}});
document.addEventListener("input",ev=>{if(ev.target.id==="aq")aq=ev.target.value});
"""

def rep(old, new):
    global s
    assert s.count(old) == 1, "Anchor not found exactly once: " + old[:70]
    s = s.replace(old, new)

rep("/* ---------- Charts ---------- */", CSS + "\n/* ---------- Charts ---------- */")
rep("/* ---------- boot ---------- */", JS + "\n/* ---------- boot ---------- */")
rep('<rect class="scan"', '${anatMarker()}<rect class="scan"')
rep('<div class="col"><div class="card fx"><h3>Body map</h3>', '<div class="col">${anatCard()}<div class="card fx"><h3>Body map</h3>')
shutil.copy(p, p + ".bak")
open(p, "w", encoding="utf-8").write(s)
print("Patched. Backup at", p + ".bak")