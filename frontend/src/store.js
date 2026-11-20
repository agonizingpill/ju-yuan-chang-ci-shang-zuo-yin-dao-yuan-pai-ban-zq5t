import {api} from './api.js';
export const store={user:null,productions:[],performances:[],calls:[],staff:[],assignments:[],debriefs:[],zones:[],posts:[],incidents:[],items:[],itemClaims:[],productionId:null};
export async function refresh(){[store.productions,store.performances,store.calls,store.staff,store.assignments,store.debriefs,store.zones,store.posts,store.incidents,store.items,store.itemClaims]=await Promise.all([api('/productions'),api('/performances'),api('/crew-calls'),api('/staff'),api('/crew-assignments'),api('/show-debriefs'),api('/entrance-zones'),api('/zone-posts'),api('/house-incidents'),api('/lost-items'),api('/item-claims')]);if(!store.productionId&&store.productions.length)store.productionId=store.productions[0].id;return store}
export const production=s=>s.productions.find(x=>x.id===Number(s.productionId));
export const performances=s=>s.performances.filter(x=>x.production_id===Number(s.productionId));
