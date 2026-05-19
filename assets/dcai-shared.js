/* DirectCare AI — shared scripts for marketing pages */
(function(){
  var t=document.getElementById('mobile-toggle'),d=document.getElementById('mobile-drawer');
  if(!t||!d)return;
  var o=t.querySelector('.icon-open'),c=t.querySelector('.icon-close');
  function s(p){
    d.classList.toggle('open',p);
    t.setAttribute('aria-expanded',p?'true':'false');
    d.setAttribute('aria-hidden',p?'false':'true');
    if(o)o.style.display=p?'none':'';
    if(c)c.style.display=p?'':'none';
    document.body.style.overflow=p?'hidden':'';
  }
  t.addEventListener('click',function(){s(!d.classList.contains('open'));});
  d.addEventListener('click',function(e){if(e.target.tagName==='A')s(false);});
  window.addEventListener('resize',function(){if(window.innerWidth>980&&d.classList.contains('open'))s(false);});
})();

/* Affiliate click-ID propagation */
(function(){
  var K='dcai_clickId',T='dcai_clickId_ts',TTL=7*24*60*60*1000;
  var IN=['utm_clickId','utm_clickid','clickid','clickId','cid','aff_id','flex_id'];
  var H=['directcare.ai','www.directcare.ai','women.directcare.ai','mens.directcare.ai','directcare-home.vercel.app','mens-hair-loss.vercel.app','womens-hair-loss.vercel.app','sexual-health-mocha.vercel.app','directcare-weight-loss.vercel.app','business.tellescope.com','directcareai.portal.tellescope.com'];
  function U(h){try{return new URL(h,window.location.href);}catch(e){return null;}}
  function fq(){var u=U(window.location.href);if(!u)return null;for(var i=0;i<IN.length;i++){var v=u.searchParams.get(IN[i]);if(v)return v;}return null;}
  function sv(id){try{sessionStorage.setItem(K,id);localStorage.setItem(K,id);localStorage.setItem(T,String(Date.now()));}catch(e){}}
  function ld(){try{var s=sessionStorage.getItem(K);if(s)return s;var l=localStorage.getItem(K);var ts=parseInt(localStorage.getItem(T)||'0',10);if(l&&Date.now()-ts<TTL){sessionStorage.setItem(K,l);return l;}if(l){localStorage.removeItem(K);localStorage.removeItem(T);}}catch(e){}return null;}
  var cid=fq();if(cid)sv(cid);else cid=ld();if(!cid)return;
  function rw(){document.querySelectorAll('a[href]').forEach(function(a){var r=a.getAttribute('href');if(!r||r.charAt(0)==='#'||r.indexOf('mailto:')===0||r.indexOf('tel:')===0||r.indexOf('javascript:')===0)return;var u=U(a.href);if(!u||H.indexOf(u.hostname)===-1)return;if(!u.searchParams.has('utm_clickId')){u.searchParams.set('utm_clickId',cid);a.href=u.toString();}});}
  rw();
  if('MutationObserver' in window){var mo=new MutationObserver(rw);mo.observe(document.body,{childList:true,subtree:true});setTimeout(function(){mo.disconnect();},4000);}
  try{window.__dcaiClickId=cid;}catch(e){}
})();
