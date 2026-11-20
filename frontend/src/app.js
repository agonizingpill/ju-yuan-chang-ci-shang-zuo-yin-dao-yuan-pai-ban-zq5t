import {api,send} from './api.js';
import {store,refresh,production} from './store.js';
import {ROLES} from './constants.js';
import {esc} from './utils/format.js';
import {notify} from './components/shared.js';
import * as calendar from './pages/calendar.js';
import * as history from './pages/history.js';
import * as forecast from './pages/forecast.js';
import * as crew from './pages/crew.js';
import * as staff from './pages/staff.js';
import * as debrief from './pages/debrief.js';
import * as zones from './pages/zones.js';
import * as incidents from './pages/incidents.js';
import * as lost from './pages/lost.js';
const pages={calendar,history,forecast,crew,staff,debrief,zones,incidents,lost},labels={calendar:'演出日历',history:'验票历史',forecast:'上座预测',crew:'场务点名',staff:'实名到岗',debrief:'散场交接',zones:'入口岗位',incidents:'现场事件',lost:'失物交接'};
let timer,drawVersion=0;
function login(){document.querySelector('#app').innerHTML=`<div class="login"><section class="loginposter"><div class="mono">NANAN / LITTLE THEATRE<br>南岸小剧场 · 场务值班室</div><div><span class="mono">NOVEMBER REPERTOIRE / 2026</span><h1>潮汐独白</h1><p>观众入座之前，剧场已经开始运转。<br>以每一场的真实验票，准备下一场的相遇。</p></div><div class="ticket"><span>160 席 / 95 分钟</span><span>19:30 开场</span></div></section><section class="loginform"><div class="eyebrow">FRONT OF HOUSE ACCESS</div><h2>今晚，谁来值班？</h2><p class="muted">登录查看演出日历、上座预测与场务点名。</p><form id="login"><label>岗位邮箱</label><input type="email" name="email" value="steward@nanan.demo" required><label>口令</label><input type="password" name="password" value="Curtain2026!" required><button class="primary">进入值班室</button><div class="error" id="login-error"></div></form><p class="muted">演示账号：admin / steward / viewer @nanan.demo<br>统一口令 Curtain2026!<br>经理确认点名，领班编班，观察员只读。</p></section></div>`;document.querySelector('#login').onsubmit=async e=>{e.preventDefault();try{const r=await send('/auth/login',Object.fromEntries(new FormData(e.target)));localStorage.setItem('theatre-token',r.token);store.user=r.user;if(location.hash==='#calendar')await draw();else location.hash='#calendar'}catch(x){document.querySelector('#login-error').textContent=x.message}}}
async function draw(){const version=++drawVersion;clearTimeout(timer);if(!localStorage.getItem('theatre-token'))return login();try{if(!store.user)store.user=await api('/me');await refresh();if(version!==drawVersion)return;const key=location.hash.slice(1) in pages?location.hash.slice(1):'calendar';document.querySelector('#app').innerHTML=`<header class="masthead"><div class="mastrow"><div class="wordmark">南岸剧场<small>NANAN / LITTLE THEATRE</small></div><div class="account"><span>${esc(ROLES[store.user.role])} · <span class="mono">${esc(store.user.email)}</span></span><button id="logout">离开值班室</button></div></div><nav class="nav">${Object.entries(labels).map(([k,label],i)=>`<a href="#${k}" class="${key===k?'active':''}"><span class="mono">0${i+1}</span> ${label}</a>`).join('')}</nav></header><main class="main"><div class="topnote"><span>演出与场务 · NOVEMBER 2026</span><select class="production-select" id="production-picker">${store.productions.map(x=>`<option value="${x.id}" ${x.id===Number(store.productionId)?'selected':''}>${esc(x.title+' / '+x.code)}</option>`).join('')}</select></div>${pages[key].render(store)}<footer class="footer">NANAN FRONT OF HOUSE / 连续验票 · 有据排班 · 开场就绪</footer></main>`;document.querySelector('#logout').onclick=()=>{localStorage.removeItem('theatre-token');store.user=null;login()};document.querySelector('#production-picker').onchange=async e=>{store.productionId=Number(e.target.value);await draw()};pages[key].bind(store,draw);if(production(store).forecast_state==='calculating')timer=setTimeout(draw,1200)}catch(e){notify(e.message)}}
window.addEventListener('hashchange',draw);draw();
