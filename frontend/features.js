/* Crew Health Companion — add-on: follow-ups on a concern + missed-meal scheduling.
   Load AFTER the main script:  <script src="features.js"></script>  (just before </body>)
   Uses the page's own globals (D, save, norm, renderAll, esc, icon, when, toast, show ...). */
(function(){
"use strict";
const MEALS=[["breakfast","Breakfast","07:30"],["lunch","Lunch","12:30"],["dinner","Dinner","18:30"]];
const FL={better:"Better",same:"Same",worse:"Worse"};
const fuSel={};
const ymd=d=>{d=d||new Date();return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")};
const hm=m=>String(Math.floor(m/60)).padStart(2,"0")+":"+String(m%60).padStart(2,"0");
const mins=s=>{const p=/^(\d{1,2}):(\d{2})$/.exec(s||"");return p?+p[1]*60+ +p[2]:NaN};
const defBlocks=()=>[{id:"b1",n:"Science run",s:"08:30",e:"11:30",d:"",meal:""},{id:"b2",n:"Exercise",s:"13:00",e:"15:00",d:"",meal:""},{id:"b3",n:"Maintenance",s:"15:00",e:"17:30",d:"",meal:""},{id:"b4",n:"Comms window",s:"17:45",e:"18:15",d:"",meal:""}];

/* ---------- data cleaning (so norm() keeps the new fields) ---------- */
function cleanFollow(a){return(Array.isArray(a)?a:[]).filter(f=>f&&FL[f.s]).map(f=>({t:String(f.t||""),s:f.s,note:String(f.note||"")}))}
function cleanMeals(m){m=m||{};const o={blocks:[],log:{},acc:{},dis:{}};
  o.blocks=Array.isArray(m.blocks)?m.blocks.filter(b=>b&&isFinite(mins(b.s))&&isFinite(mins(b.e))).map(b=>({id:String(b.id||Math.random().toString(36).slice(2)),n:String(b.n||"Block"),s:b.s,e:b.e,d:b.d?String(b.d):"",meal:b.meal?String(b.meal):""})):defBlocks();
  Object.keys(m.log||{}).forEach(k=>{const l=m.log[k];if(l&&(l.status==="ate"||l.status==="missed"))o.log[k]={t:String(l.t||""),status:l.status}});
  Object.keys(m.acc||{}).forEach(k=>{if(m.acc[k]&&m.acc[k].bid)o.acc[k]={bid:String(m.acc[k].bid)}});
  Object.keys(m.dis||{}).forEach(k=>{if(m.dis[k])o.dis[k]=true});
  return o}
const _norm=norm;
norm=function(d){const b=_norm(d);if(!b)return b;
  const src=(d&&Array.isArray(d.journal))?d.journal:[];
  b.journal.forEach(e=>{const s=src.find(x=>x&&String(x.id)===e.id);e.follow=cleanFollow(s&&s.follow)});
  b.meals=cleanMeals(d&&d.meals);return b};
function ens(){if(!D.meals)D.meals=cleanMeals();D.journal.forEach(e=>{if(!Array.isArray(e.follow))e.follow=[]})}

/* ---------- 1. Follow-up on the same concern ---------- */
function fuHtml(e){const L=e.follow;
  return`<div class="advice" data-fu="${e.id}"><b>Follow-up on this concern</b>
<ul class="small" style="list-style:none;margin:8px 0;padding:0"><li><span class="mute">${esc(when(e.t))}</span> — Reported</li>${L.map(f=>`<li><span class="mute">${esc(when(f.t))}</span> — <b class="${f.s==="worse"?"hi":f.s==="better"?"ok":""}">${FL[f.s]}</b>${f.note?": "+esc(f.note):""}</li>`).join("")}</ul>
<div class="chips">${Object.keys(FL).map(k=>`<button type="button" class="chip${fuSel[e.id]===k?" on":""}" data-fu-s="${e.id}|${k}">${FL[k]}</button>`).join("")}</div>
<label for="fn_${e.id}">Note (optional)</label><input id="fn_${e.id}" placeholder="e.g. now interrupts a task">
<button type="button" class="ghost" style="margin-top:10px" data-fu-add="${e.id}">Add follow-up</button></div>`}
const _rj=renderJournal;
renderJournal=function(){_rj();ens();
  document.querySelectorAll("#journal [data-card]").forEach(c=>{const e=D.journal.find(x=>x.id===c.dataset.card),a=c.querySelector("button[data-del]");
    if(e&&a)a.insertAdjacentHTML("beforebegin",fuHtml(e))})};

/* ---------- 2. Missed-meal scheduling ---------- */
function todays(){const t=ymd();return D.meals.blocks.filter(b=>!b.d||b.d===t)}
function freeSlot(id,nm){const M=D.meals,t=ymd(),busy=todays().map(b=>[mins(b.s),mins(b.e)]);
  MEALS.forEach(([k,,tm])=>{const mid=t+"-"+k;if(mid===id)return;const l=M.log[mid];if(l&&l.status==="missed")return;const s=mins(tm);busy.push([s,s+30])});
  for(let s=Math.ceil(nm/15)*15;s+30<=21*60+30;s+=15){if(!busy.some(x=>s<x[1]&&s+30>x[0]))return[s,s+30]}
  return null}
function dropAcc(id){const M=D.meals,a=M.acc[id];if(a)M.blocks=M.blocks.filter(b=>b.id!==a.bid);delete M.acc[id];delete M.dis[id]}
function offer(id,name,nm){const M=D.meals,a=M.acc[id];
  if(a){const b=M.blocks.find(x=>x.id===a.bid);return`<div class="note ok">${icon("ok")}<p>${name} added to your schedule${b?" at "+b.s+"–"+b.e:""}.</p></div><button type="button" class="ghost" style="margin-top:10px" data-undo="${id}">Undo</button>`}
  if(M.dis[id])return`<p class="small mute">Suggestion dismissed. Nothing was changed.</p><button type="button" class="ghost" data-undis="${id}">Show it again</button>`;
  const s=freeSlot(id,nm);
  if(!s)return`<div class="note warn">${icon("info")}<p>No free 30-minute slot left today. Your schedule was not changed.</p></div>`;
  return`<div class="advice"><b>Free slot: ${hm(s[0])}–${hm(s[1])}</b><p class="small">Add ${name} here? Nothing changes unless you accept.</p>
<div class="chips"><button type="button" class="chip on" data-acc="${id}|${s[0]}">Add to schedule</button><button type="button" class="chip" data-dis="${id}">Dismiss</button></div>
<details style="border:0;background:none;box-shadow:none"><summary style="padding:6px 0;font-size:.82rem;font-weight:620;color:var(--mute)">Why this suggestion?</summary><p class="small mute" style="margin:4px 0 0">It is the earliest 30-minute gap after now that does not overlap your scheduled blocks or your other meals.</p></details></div>`}
function mealsText(){const M=D.meals,t=ymd();return"Meals today: "+MEALS.map(([k,n])=>{const l=M.log[t+"-"+k];return n+": "+(!l?"not logged":l.status==="ate"?"ate":"missed"+(M.acc[t+"-"+k]?" (rescheduled)":""))}).join("; ")}
function renderMeals(){ens();const el=document.getElementById("meals");if(!el)return;
  const M=D.meals,td=ymd(),n=new Date(),nm=n.getHours()*60+n.getMinutes();
  const cards=MEALS.map(([k,name,t])=>{const id=td+"-"+k,l=M.log[id];let body;
    if(!l)body=`<div class="advice"><b>No entry for ${name} yet.</b> Did you eat it, or miss it?<div class="chips"><button type="button" class="chip" data-ml="${id}|ate">Ate it</button><button type="button" class="chip" data-ml="${id}|missed">Missed it</button></div></div>`;
    else if(l.status==="ate")body=`<p class="small ok">Logged as eaten.</p><button type="button" class="ghost" data-mclr="${id}">Change answer</button>`;
    else body=`<p class="small warn">Logged as missed.</p>`+offer(id,name,nm)+`<div style="margin-top:8px"><button type="button" class="ghost" data-mclr="${id}">Change answer</button></div>`;
    const pill=!l?`<span class="pill mute">Not logged</span>`:l.status==="ate"?`<span class="pill ok">Ate</span>`:`<span class="pill warn">Missed</span>`;
    return`<div class="card fx"><div class="eh"><h3>${name} <small class="mute">· ${t}</small></h3>${pill}</div>${body}</div>`}).join("");
  const blocks=todays().slice().sort((a,b)=>mins(a.s)-mins(b.s));
  el.innerHTML=`<div class="head fx"><span class="eyebrow">Meals</span><h2>Meals &amp; schedule</h2><p class="mute small">An empty log is not treated as a missed meal. Tell us which it was, or say it in your own words.</p></div>
<div class="cols"><div class="col"><div class="card fx"><h3>Say it in your words</h3><label for="mtxt" class="vh">Describe your meal</label><input id="mtxt" placeholder="e.g. I missed lunch"><button type="button" class="cta" id="mtxtadd">Log it</button></div>${cards}</div>
<div class="col"><div class="card fx"><h3>Today’s schedule</h3>${blocks.length?blocks.map(b=>`<div class="row"><span>${esc(b.n)}<br><small class="mute">${b.s}–${b.e}</small></span><button type="button" class="ghost" data-bdel="${b.id}" aria-label="Remove ${esc(b.n)}">${icon("trash")}</button></div>`).join(""):`<p class="mute small">Nothing scheduled.</p>`}
<label for="mbn">Add a block</label><input id="mbn" placeholder="Name"><div class="two" style="margin-top:8px"><input id="mbs" type="time" aria-label="Start"><input id="mbe" type="time" aria-label="End"></div><button type="button" class="cta" id="mbadd">Add to today</button></div>
<div class="card fx"><h3>Last 7 days</h3>${weekCard()}</div>
<div class="card fx"><div class="note">${icon("info")}<p>Saved on this device only. Not synced to anyone yet.</p></div></div></div></div>`}

const worse=e=>e.follow.length&&e.follow[e.follow.length-1].s==="worse";
function weekCard(){const M=D.meals;let logged=0,missed=0,moved=0;
  for(let i=0;i<7;i++){const d=ymd(new Date(Date.now()-i*864e5));MEALS.forEach(([k])=>{const id=d+"-"+k,l=M.log[id];if(l){logged++;if(l.status==="missed"){missed++;if(M.acc[id])moved++}}})}
  const st=(n,l,c)=>`<div class="stat ${c}${n?"":" zero"}"><span class="n">${n}</span><span class="l">${l}</span></div>`;
  return`<div class="stats" style="margin-top:0">${st(logged+"/21","Meals logged","t-ok")}${st(missed,"Missed","t-warn")}${st(moved,"Rescheduled","t-ok")}</div><p class="small mute" style="margin-top:12px">Unlogged meals are shown as unknown, never as missed.</p>`}

/* saved-on-device status (honest: nothing is synced) */
let lastSave=null;const _save=save;save=function(){_save();lastSave=new Date();paintSync()};
function paintSync(){const bar=document.getElementById("bar");if(!bar)return;let e=document.getElementById("syncst");
  if(!e){e=document.createElement("span");e.id="syncst";e.className="pill mute";e.setAttribute("role","status");bar.insertBefore(e,document.getElementById("mode"))}
  e.textContent=lastSave?"Saved on this device "+lastSave.toLocaleTimeString([],{timeStyle:"short"})+" · not synced":"On this device · not synced"}

/* "Why this suggestion?" on the sleep/alertness insight */
function whyInsight(id){const sc=document.getElementById(id),i=sc&&sc.querySelector(".insight");if(!i||i.querySelector("details"))return;
  i.querySelector("p").insertAdjacentHTML("afterend",`<details style="border:0;background:none;box-shadow:none;margin-top:4px"><summary style="padding:4px 0;font-size:.8rem;font-weight:620;color:var(--mute)">Why this suggestion?</summary><p class="small mute" style="margin:2px 0 0;font-weight:500">Your latest check-in is compared with the average of up to six earlier ones. It only calls out a drop when sleep stayed within half an hour of average and alertness fell by a point or more.</p></details>`);}
const _rh=renderHome;renderHome=function(){_rh();ens();whyInsight("home");
  const n=D.journal.filter(worse).length,h=document.getElementById("home");
  const tl=h.querySelector(".tiles");if(tl)tl.insertAdjacentHTML("beforeend",`<button class="tile" data-tab="meals"><span class="ti">${icon("meal")}</span><span><b>Meals &amp; schedule</b><small>Missed a meal? Find a slot</small></span><span class="go">${icon("arrow")}</span></button>`);
  const cta=h.querySelector('.card.s5 button.cta[data-tab="check"]');
  if(n&&cta)cta.insertAdjacentHTML("beforebegin",`<div class="note warn">${icon("alert")}<p>${n} concern${n>1?"s":""} reported as getting worse. See Journal.</p></div>`)};
const _rt=renderTrends;renderTrends=function(){_rt();whyInsight("trends")};

/* wire into render + handoff */
const _ra=renderAll;renderAll=function(){_ra();renderMeals();paintSync()};
const _ho=handoff;
handoff=function(){ens();const L=_ho().split("\n"),g=L.pop();
  D.journal.forEach((e,i)=>{if(e.follow.length){L.push("Follow-ups on concern "+(i+1)+":");e.follow.forEach(f=>L.push("  "+when(f.t)+" - "+FL[f.s]+(f.note?": "+f.note:"")));if(worse(e))L.push("  <-- latest follow-up: WORSE");L.push("")}});
  L.push(mealsText(),"",g);return L.join("\n")};

/* ---------- events ---------- */
document.addEventListener("click",ev=>{const t=ev.target;let b;
  if(b=t.closest("[data-fu-s]")){const[id,k]=b.dataset.fuS.split("|");fuSel[id]=k;b.parentNode.querySelectorAll(".chip").forEach(c=>c.classList.toggle("on",c===b));return}
  if(b=t.closest("[data-fu-add]")){const id=b.dataset.fuAdd,e=D.journal.find(x=>x.id===id);if(!e)return;
    if(!fuSel[id]){toast("Pick Better, Same or Worse","warn");return}
    const inp=document.getElementById("fn_"+id);e.follow.push({t:new Date().toISOString(),s:fuSel[id],note:(inp.value||"").trim()});delete fuSel[id];save();renderAll();toast("Follow-up saved on this device");return}
  if(b=t.closest("[data-ml]")){const[id,s]=b.dataset.ml.split("|");ens();D.meals.log[id]={t:new Date().toISOString(),status:s};save();renderMeals();return}
  if(b=t.closest("[data-mclr]")){const id=b.dataset.mclr;ens();dropAcc(id);delete D.meals.log[id];save();renderMeals();return}
  if(b=t.closest("[data-acc]")){const[id,s]=b.dataset.acc.split("|"),st=+s,name=(MEALS.find(m=>id.endsWith("-"+m[0]))||[0,"Meal"])[1];
    if(freeSlot(id,0)===null){toast("That slot is no longer free","warn");renderMeals();return}
    const bid="m"+Date.now().toString(36);D.meals.blocks.push({id:bid,n:name+" (rescheduled)",s:hm(st),e:hm(st+30),d:ymd(),meal:id});D.meals.acc[id]={bid};delete D.meals.dis[id];save();renderMeals();toast(name+" added at "+hm(st));return}
  if(b=t.closest("[data-dis]")){D.meals.dis[b.dataset.dis]=true;save();renderMeals();return}
  if(b=t.closest("[data-undis]")){delete D.meals.dis[b.dataset.undis];save();renderMeals();return}
  if(b=t.closest("[data-undo]")){dropAcc(b.dataset.undo);save();renderMeals();toast("Undone. Schedule restored.");return}
  if(b=t.closest("[data-bdel]")){const x=D.meals.blocks.find(q=>q.id===b.dataset.bdel);if(x&&x.meal)delete D.meals.acc[x.meal];D.meals.blocks=D.meals.blocks.filter(q=>q.id!==b.dataset.bdel);save();renderMeals();return}
  if(t.closest("#mbadd")){const n=document.getElementById("mbn"),s=document.getElementById("mbs"),e=document.getElementById("mbe");
    if(!n.value.trim()||!isFinite(mins(s.value))||!isFinite(mins(e.value))||mins(e.value)<=mins(s.value)){toast("Enter a name and a start before end time","warn");return}
    D.meals.blocks.push({id:"b"+Date.now().toString(36),n:n.value.trim().slice(0,60),s:s.value,e:e.value,d:ymd(),meal:""});save();renderMeals();toast("Added to today");return}
  if(t.closest("#mtxtadd")){const v=document.getElementById("mtxt").value,m=/breakfast|lunch|dinner|supper/i.exec(v);
    const miss=/miss|skip|forgot|didn.?t (eat|have)|no (breakfast|lunch|dinner)/i.test(v),ate=/\b(ate|had|finished)\b/i.test(v);
    if(!m||(!miss&&!ate)){toast("Say which meal and whether you ate or missed it","warn");return}
    const k=m[0].toLowerCase()==="supper"?"dinner":m[0].toLowerCase(),id=ymd()+"-"+k;
    D.meals.log[id]={t:new Date().toISOString(),status:miss?"missed":"ate"};save();renderMeals();toast("Logged"+(miss?". No question needed.":""))}
});

/* ---------- nav tab + screen ---------- */
IC.meal='<path d="M6 3v7a2 2 0 0 0 4 0V3M8 3v18"/><path d="M17 3c-2 1.5-3 4-3 7h3v11"/>';
const main=document.getElementById("main"),foot=main.querySelector("footer"),sec=document.createElement("section");
sec.className="screen";sec.id="meals";sec.setAttribute("aria-label","Meals");main.insertBefore(sec,foot);
const nav=document.getElementById("nav"),jb=nav.querySelector('[data-tab="journal"]');
jb.insertAdjacentHTML("afterend",`<button type="button" data-tab="meals">${icon("meal")}<span>Meals</span></button>`);
ens();renderAll();moveInd();
})();
