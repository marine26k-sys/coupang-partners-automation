'use strict';
const $=id=>document.getElementById(id);
let products=[],featured=[],recommendations=[],category='전체',saved=new Set(),compare=new Set();
try{saved=new Set(JSON.parse(localStorage.getItem('sallim:saved')||'[]').filter(x=>typeof x==='string'));}catch{}
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function safeURL(url,kind){try{const u=new URL(url);if(u.protocol!=='https:')return '';return kind==='image'&&(u.hostname.endsWith('.coupangcdn.com')||u.hostname==='ads-partners.coupang.com')?u.href:kind==='link'&&u.hostname==='link.coupang.com'?u.href:'';}catch{return '';}}
const price=p=>typeof p.price==='number'?p.price.toLocaleString('ko-KR'):'가격 확인';

function comparisonMarkup(p){
 if(p.reviewReason)return '<div class="change">가격과 구성을 구매 페이지에서 확인해주세요.</div>';
 if(typeof p.previousPrice!=='number'||typeof p.priceChange!=='number')return '<div class="change history-empty">이전 가격 기록 없음</div>';
 const date=String(p.previousDate||'');
 const shortDate=/^\d{4}-\d{2}-\d{2}$/.test(date)?`${Number(date.slice(5,7))}/${Number(date.slice(8,10))}`:date;
 const direction=p.priceChange===0?'same':p.priceChange<0?'down':'up';
 const status=p.priceChange===0?'가격 유지':`${p.priceChange<0?'↓':'↑'} ${Math.abs(p.priceChange).toLocaleString('ko-KR')}원 ${p.priceChange<0?'내림':'오름'}`;
 return `<div class="change price-history"><div class="history-reference"><span class="history-label">이전 가격</span><strong>${p.previousPrice.toLocaleString('ko-KR')}<small>원</small></strong><time datetime="${escapeHTML(date)}">${escapeHTML(shortDate)} 기준</time></div><span class="price-status ${direction}">${status}</span></div>`;
}

function render(){
 const query=$('search').value.trim().toLocaleLowerCase();
 let list=(category==='Threads 소개'?featured:products).filter(p=>(category==='전체'||(category==='추천'&&recommendations.some(r=>r.id===p.id&&r.category===p.category))||(category==='하락'&&typeof p.priceChange==='number'&&p.priceChange<0&&!p.stale)||(category==='저장'?saved.has(p.id):p.category===category))&&(!query || `${p.name} ${p.category} 살림 #${p.catalogNumber||''}`.toLocaleLowerCase().includes(query) || (p.catalogNumber && p.catalogNumber===query.replace(/^(살림\s*)?#?/, '').padStart(3,'0'))));
 const budget=$('budget').value;
 if(budget!=='all')list=list.filter(p=>typeof p.price==='number'&&p.price>0&&(budget==='10000'?p.price<=10000:budget==='30000'?p.price>10000&&p.price<=30000:p.price>30000));
 if($('sort').value==='low')list.sort((a,b)=>(a.price??Infinity)-(b.price??Infinity));
 if($('sort').value==='high')list.sort((a,b)=>(b.price??-Infinity)-(a.price??-Infinity));
 $('savedCount').textContent=products.filter(p=>saved.has(p.id)).length;
 $('grid').innerHTML=list.map(p=>{const image=safeURL(p.image,'image'),url=safeURL(p.url,'link');return `<article class="card" id="${escapeHTML(p.id)}"><a class="photo" href="${escapeHTML(url)}" target="_blank" rel="sponsored noopener" aria-label="${escapeHTML(p.name)} 상품 정보">${image?`<img src="${escapeHTML(image)}" alt="${escapeHTML(p.name)}" loading="lazy">`:'<span>사진 준비 중</span>'}</a><button class="save" data-id="${escapeHTML(p.id)}" aria-label="${escapeHTML(p.name)} 저장" aria-pressed="${saved.has(p.id)}">${saved.has(p.id)?'♥':'♡'}</button><p class="category">${p.number?`소개 #${p.number} · ${escapeHTML(p.date)}`:escapeHTML(p.category)} ${typeof p.rank==='number'?`<span class="rank-label">${escapeHTML(p.source)} ${p.rank}위</span>`:''} ${p.rocket?'<span class="rocket">로켓배송</span>':''}</p><p class="product-reference">살림 #${escapeHTML(p.catalogNumber||p.id)}</p><h3>${escapeHTML(p.name)}</h3><div class="price">${price(p)}${typeof p.price==='number'?'<small> 원</small>':''}</div>${signalMarkup(p)}${/^https:\/\/www\.threads\.com\//.test(p.relatedPostUrl||'')?`<a class="post-link" href="${escapeHTML(p.relatedPostUrl)}" target="_blank" rel="noopener">이 상품의 Threads 글 ↗</a>`:''}${p.postUrl?`<a class="post-link" href="${escapeHTML(p.postUrl)}" target="_blank" rel="noopener">Threads 원문 ↗</a><small class="price-note">${p.priceDate?escapeHTML(p.priceDate.slice(0,10))+" 게시 당시 가격":"가격은 구매 페이지에서 확인"}</small>`:comparisonMarkup(p)}<button class="compare-toggle" data-compare="${escapeHTML(p.id)}" aria-pressed="${compare.has(p.id)}">${compare.has(p.id)?"비교 선택됨 ✓":"비교 담기 +"}</button><a class="buy" href="${escapeHTML(url)}" target="_blank" rel="sponsored noopener">쿠팡에서 확인 <span>↗</span></a></article>`;}).join('');
 renderComparison();
 $('message').hidden=list.length>0;
 $('message').textContent=category==='저장'?'아직 저장한 상품이 없어요. 상품의 하트를 눌러 모아두세요.':'일치하는 상품이 없어요. 다른 검색어나 카테고리를 선택해주세요.';
}
$('grid').addEventListener('click',event=>{const button=event.target.closest('button.save');if(!button)return;const id=button.dataset.id;if(saved.has(id))saved.delete(id);else saved.add(id);try{localStorage.setItem('sallim:saved',JSON.stringify([...saved]));}catch{}render();});
document.querySelectorAll('[data-category]').forEach(button=>button.addEventListener('click',()=>{category=button.dataset.category;document.querySelectorAll('[data-category]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});render();}));
$('budget').addEventListener('change',render);$('search').addEventListener('input',render);$('sort').addEventListener('change',render);
async function load(){
 let data,cached=false;
 try{const res=await fetch('catalog.json?t='+Date.now(),{signal:AbortSignal.timeout(7000),cache:'no-store'});if(!res.ok)throw new Error('unavailable');data=await res.json();}
 catch{$('grid').textContent='상품 정보를 불러오지 못했어요. 잠시 후 새로고침해주세요.';$('updated').textContent='상품 정보 연결 확인 필요';return;}
 products=Array.isArray(data.products)?data.products.filter(p=>typeof p.name==='string'&&typeof p.id==='string'&&safeURL(p.url,'link')):[];
 recommendations=Array.isArray(data.recommendations)?data.recommendations:[];
 featured=Array.isArray(data.featured)?data.featured.filter(p=>safeURL(p.url,'link')&&typeof p.name==='string'&&typeof p.id==='string'&&/^https:\/\/www\.threads\.com\//.test(p.postUrl||'')):[];
 renderMarketComparison(data.comparisons);
 const date=new Date(data.updatedAt);
 const compared=products.filter(p=>typeof p.priceChange==='number').length;
 const historyStatus=document.getElementById('comparisonStatus');
 if(historyStatus)historyStatus.textContent=`가격 확인 ${products.length}개 · 이전 날짜와 비교 가능 ${compared}개 · 비교 이력 없음 ${products.length-compared}개`;
 $('updated').textContent=(cached?'저장된 자료 · ':'최근 수집 · ')+(Number.isNaN(date.valueOf())?'시각 미확인':date.toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'long',day:'numeric',hour:'2-digit',minute:'2-digit'}))+(data.partial?' · 일부 카테고리 미수집':'');
 const hero=products.find(p=>p.category==='수납'&&safeURL(p.image,'image'));
 if(hero){$('featureImage').src=safeURL(hero.image,'image');$('featureImage').alt=hero.name;$('featureImage').hidden=false;$('featureFallback').hidden=true;}
 render();
 document.querySelectorAll('.card img').forEach(img=>img.addEventListener('error',()=>{img.hidden=true;},{once:true}));
}
load();

// Returning to an open tab refreshes the displayed catalog without waiting for a manual reload.
document.addEventListener("visibilitychange",()=>{if(!document.hidden)load();});

function renderComparison(){
 const panel=$('comparePanel');
 const all=[...products,...featured];
 const chosen=[...compare].map(id=>all.find(p=>p.id===id)).filter(Boolean);
 panel.hidden=chosen.length===0;
 panel.innerHTML='<h3>선택 상품 비교</h3><p class="price-note">상품명이 같은 경우에도 구성·판매 옵션이 다를 수 있습니다. 상세 사양은 구매 페이지에서 확인해주세요.</p><div class="comparison-cards">'+chosen.map(p=>`<article><strong>${escapeHTML(p.name)}</strong><p>${price(p)}${typeof p.price==='number'?'원':''}</p><small>${p.postUrl?'게시 당시 정보 · '+escapeHTML((p.priceDate||p.date||'').slice(0,10)):'현재 목록 수집 시점 기준'}</small><a href="${escapeHTML(safeURL(p.url,'link'))}" target="_blank" rel="sponsored noopener">구성·옵션 확인 ↗</a><button data-remove="${escapeHTML(p.id)}">비교에서 빼기</button></article>`).join('')+'</div>';
}
$('grid').addEventListener('click',e=>{const button=e.target.closest('[data-compare]');if(!button)return;const id=button.dataset.compare;if(compare.has(id))compare.delete(id);else if(compare.size<3)compare.add(id);else{const toast=$('toast');toast.textContent='비교는 최대 3개까지 선택할 수 있어요.';toast.hidden=false;setTimeout(()=>toast.hidden=true,2500);return;}render();});
$('comparePanel').addEventListener('click',e=>{const b=e.target.closest('[data-remove]');if(b){compare.delete(b.dataset.remove);render();}});

function signalMarkup(p){
 let text=p.reviewReason?'<p class="review-note">'+escapeHTML(p.reviewReason)+'</p>':'';
 if(p.stale)text='<p class="signal-note">최근 수집 실패 · '+escapeHTML((p.observedAt||'').slice(0,16).replace('T',' '))+' 자료</p>';
 if(category==='추천'){const pick=recommendations.find(r=>r.id===p.id&&r.category===p.category);if(pick)text+='<p class="signal-note">'+pick.reasons.map(escapeHTML).join('<br>')+'</p>';}
 if(p.rankChange!=null)text+='<p class="signal-note">목록 순위 '+(p.rankChange===0?'유지':Math.abs(p.rankChange)+'계단 '+(p.rankChange>0?'상승':'하락'))+' · '+escapeHTML(p.previousRankDate||'')+' 대비</p>';
 if(p.priceHistory?.length>=2)text+='<details class="price-detail"><summary>가격 기록 '+p.observationDays+'일</summary><p>같은 판매 옵션 · 관측한 날짜 기준</p>'+p.priceHistory.map(x=>'<div>'+escapeHTML(x.date)+' · '+Number(x.price).toLocaleString('ko-KR')+'원</div>').join('')+'</details>';
 return text;
}

function renderMarketComparison(groups){
 const host=document.getElementById('marketCompare');if(!host)return;
 const valid=Array.isArray(groups)?groups.filter(g=>Array.isArray(g.offers)&&g.offers.length>=2&&g.offers.every(o=>{const age=Date.now()-Date.parse(o.checkedAt);return Number.isFinite(age)&&age>=0&&age<=21600000;})):[];
 host.innerHTML=valid.length?valid.map(group=>'<article><h3>'+escapeHTML(group.name)+'</h3><p>'+escapeHTML(group.configuration)+'</p>'+group.offers.map(offer=>{
  let url='';try{const u=new URL(offer.url);if(u.protocol==='https:'&&['link.coupang.com','toss.shopping','toss.im'].includes(u.hostname))url=u.href;}catch{}
  return url?'<p><a href="'+escapeHTML(url)+'" target="_blank" rel="sponsored noopener">'+(offer.service==='toss'?'토스쇼핑':'쿠팡')+' ↗</a> · 상품 '+Number(offer.price).toLocaleString('ko-KR')+'원 · '+(offer.shipping==null?'배송비 미확인':'배송비 '+Number(offer.shipping).toLocaleString('ko-KR')+'원')+'</p><small>확인 '+escapeHTML(new Date(offer.checkedAt).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}))+'</small>':'';
 }).join('')+'<p class="price-note">'+escapeHTML(group.note)+'</p></article>').join(''):'<p>동일한 모델·색상·규격·수량이 확인된 상품만 비교해요. 현재 확인된 비교 상품은 없습니다.</p>';
}
