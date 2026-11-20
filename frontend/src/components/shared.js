import {esc,week} from '../utils/format.js';
import {STATES} from '../constants.js';
export const badge=x=>`<span class="status ${esc(x.status)}">${esc(STATES[x.status]||x.status)}</span>`;
export const capacity=(n,seats)=>`<div class="capacity"><div class="label"><span>预计上座 / 座位</span><b class="mono">${n??'—'} / ${seats}</b></div><div class="bar"><span style="width:${n==null?0:Math.min(100,100*n/seats)}%"></span></div></div>`;
export const dayTile=(x,seats)=>`<article class="day"><div class="week">${week(x.date)} / ${x.date.slice(5,7)}月</div><div class="date">${x.date.slice(8)}</div><div class="arrivals">${x.forecast??'—'} <small style="display:inline">人 / ${x.curtain}</small></div>${badge(x)}${x.forecast!=null?`<small>引导员 ≥ ${Math.max(1,Math.ceil(x.forecast/40))} 名</small>`:'<small>先完成验票日历和上座预测</small>'}</article>`;
export const empty=text=>`<div class="empty">${esc(text)}</div>`;
export function notify(message){const n=document.querySelector('#toast');n.textContent=message;n.classList.add('show');clearTimeout(window.notifyTimer);window.notifyTimer=setTimeout(()=>n.classList.remove('show'),4500)}
