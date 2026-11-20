import {production,performances,recommendationFor} from '../store.js';
import {esc,week,pretty} from '../utils/format.js';
import {notify,empty} from '../components/shared.js';
import {send,api} from '../api.js';

const SLOT_LABELS=['开场前 60–51 分钟','开场前 50–41 分钟','开场前 40–31 分钟','开场前 30–21 分钟','开场前 20–11 分钟','开场前 10–1 分钟','其余（更早 / 迟到）'];

function observedPerfs(s){return performances(s).filter(x=>x.arrivals!==null)}
function futurePerfs(s){return performances(s).filter(x=>x.arrivals===null)}

async function loadSegments(id){return api('/entry-segments?performance_id='+id)}

function segmentPanel(data,perf,canWrite){
  const rows=data.segments||[];const rec=data.reconcile;const finalized=rec.is_final;
  const bySlot=Object.fromEntries(rows.map(x=>[x.slot_index,x]));
  return `<div class="sectionhead"><h2>${perf.date} 分段验票</h2><small>${week(perf.date)} · 开场 ${perf.curtain} · 整场 ${perf.arrivals} 人</small></div>
  ${finalized?'<p class="panelnote">本场分段已核齐冻结，共 '+rec.segment_total+' 人，与整场验票一致，可作为进门高峰样本。</p>':''}
  <div class="tablewrap"><table><thead><tr><th>时段</th><th>段号</th><th>人数</th><th>实际验票时刻</th><th>状态</th></tr></thead><tbody>
  ${Array.from({length:7},(_,i)=>{const x=bySlot[i];return `<tr><td>${SLOT_LABELS[i]}</td><td class="mono">S${i}</td><td class="mono">${x?x.headcount:'—'}</td><td class="mono">${x?pretty(x.observed_at):'—'}</td><td>${x?(x.is_final?'<span class="status confirmed">已核齐</span>':'<span class="status proposed">草稿</span>'):'<span class="status invalidated">未录</span>'}</td></tr>`}).join('')}
  </tbody></table></div>
  <div class="strip"><div>分段合计<b>${rec.segment_total} 人</b></div><div>整场验票<b>${rec.arrivals} 人</b></div><div>核齐校验<b>${rec.matches?'相符 ✓':'不符'}</b></div></div>
  ${!finalized?`<form id="segment-form">
    <label>按段补录（迟到记录也按实际验票时刻归段）</label>
    <div class="formgrid">
      <div><label>时段</label><select name="slot_index">${SLOT_LABELS.map((l,i)=>`<option value="${i}">${l}</option>`).join('')}</select></div>
      <div><label>该段人数</label><input name="headcount" type="number" min="0" value="0" required></div>
    </div>
    <label>实际验票时刻（本地时间）</label><input name="observed_at" type="datetime-local" value="${perf.date}T18:40" required>
    <div class="actions"><button class="primary" ${canWrite?'':'disabled'}>补录该段</button>
    <button type="button" id="finalize-btn" ${canWrite?'':'disabled'} ${rec.matches?'':'disabled'}>核齐分段</button></div>
    ${rec.matches?'':'<p class="muted">分段合计与整场验票相符后才能核齐；旧场次只有总数则永远不进入样本。</p>'}
  </form>`:''}`;
}

function recommendationCard(s,perf){
  const rec=recommendationFor(s,perf.id);
  if(!rec)return `<article class="rec-card"><h3>${perf.date} · ${week(perf.date)}</h3>${empty('尚未生成进门高峰建议')}<div class="actions"><button data-generate="${perf.id}" ${s.user.role==='viewer'?'disabled':''}>生成建议</button></div></article>`;
  const d=rec.detail||{};
  const head=`<article class="rec-card ${rec.status==='ready'?'ready':'insufficient'}"><div class="sectionhead"><h3>${perf.date} · ${week(perf.date)}</h3><span class="status ${rec.status==='ready'?'confirmed':'invalidated'}">${rec.status==='ready'?'建议就绪 v'+rec.version:'样本不足 v'+rec.version}</span></div>`;
  if(rec.status!=='ready'){
    return head+`<p class="panelnote">${esc(rec.reason||'样本不足')}</p>
    <p class="muted">当前样本 ${rec.sample_size} 场 / 至少 ${d.min_sample_size??5} 场核齐分段。</p>
    <div class="actions"><button data-generate="${perf.id}" ${s.user.role==='viewer'?'disabled':''}>重新试算</button></div></article>`;
  }
  const maxShare=Math.max(...d.avg_shares);
  return head+
  `<p class="muted">基于 ${d.sample_size} 场在本场开演前已核齐的分段样本（后来补录不计入）。</p>
  <div class="peak-bars">${d.slots.map((sl,i)=>`<div class="peak-row"><small>${sl.window}</small><div class="bar"><span style="width:${(d.avg_shares[i]/maxShare*100).toFixed(1)}%" class="${i===d.peak_slot_index?'peak':''}"></span></div><b class="mono">${d.expected_per_slot[i]??'—'}人</b></div>`).join('')}</div>
  <div class="strip"><div>进门高峰<b>${esc(d.peak_window)}</b></div><div>基础班底<b>${d.base_ushers} 名</b></div><div>高峰加岗<b>+${d.extra_ushers} 名 → ${d.peak_ushers} 名</b></div></div>
  <p class="panelnote">加岗时段：${d.surge_slots.map(x=>x.window).join('、')}。建议整体算齐后原子换版，失败保留旧版。</p>
  <div class="actions"><button data-generate="${perf.id}" ${s.user.role==='viewer'?'disabled':''}>重新算齐换版</button></div></article>`;
}

export function render(s){
  const p=production(s),canWrite=s.user.role!=='viewer';
  const past=observedPerfs(s),future=futurePerfs(s);
  return `<div class="pagehead"><div><div class="eyebrow">ENTRY SURGE / 04</div><h1>满场进门，提前加人。</h1><p class="subtitle">开场前一小时按十分钟分段验票，分段合计与整场相符才核齐；只拿开演前已核齐的样本估算下一场高峰。</p></div><span class="mono">7 SEGMENTS / 6 × 10 MIN + OTHER</span></div>
  <div class="columns"><section class="section">
    <div class="sectionhead"><h2>下一场进门高峰与加岗建议</h2><small>排班页同步展示</small></div>
    ${future.length?future.slice(0,7).map(f=>recommendationCard(s,f)).join(''):empty('暂无未来场次')}
  </section>
  <aside class="section">
    <h2>场务补录分段验票</h2>
    <label>选择已开演场次</label>
    <select id="segment-perf">${past.slice().reverse().map(x=>`<option value="${x.id}">${x.date} · 总数 ${x.arrivals} 人</option>`).join('')}</select>
    <div id="segment-panel" style="margin-top:18px"></div>
    <p class="muted" style="margin-top:20px">只有整场总数的旧场次不参与估算；回测只使用被测场开演前已核齐的分段版本，事后补录不改写当时样本。</p>
  </aside></div>`;
}

export function bind(s,reload){
  const canWrite=s.user.role!=='viewer';
  async function drawPanel(){
    const id=Number(document.querySelector('#segment-perf').value);
    const perf=s.performances.find(x=>x.id===id);
    const data=await loadSegments(id);
    document.querySelector('#segment-panel').innerHTML=segmentPanel(data,perf,canWrite);
    const form=document.querySelector('#segment-form');
    if(form)form.onsubmit=async e=>{e.preventDefault();const f=Object.fromEntries(new FormData(e.target));
      try{await send('/entry-segments/batch',{performance_id:id,observed_at:f.observed_at,segments:[{slot_index:Number(f.slot_index),headcount:Number(f.headcount)}]});notify('分段验票已补录');await reload();await drawPanel()}catch(x){notify(x.message)}};
    const fb=document.querySelector('#finalize-btn');
    if(fb)fb.onclick=async()=>{try{await send('/entry-segments/finalize',{performance_id:id});notify('分段已核齐，进入可用样本');await reload();await drawPanel()}catch(x){notify(x.message)}};
  }
  const sel=document.querySelector('#segment-perf');
  if(sel&&sel.options.length){sel.onchange=drawPanel;drawPanel().catch(e=>notify(e.message))}
  document.querySelectorAll('[data-generate]').forEach(b=>b.onclick=async()=>{
    try{await send('/entry-recommendations/generate',{performance_id:Number(b.dataset.generate)});notify('新建议已算齐并换版');await reload()}catch(e){notify(e.message)}});
}
