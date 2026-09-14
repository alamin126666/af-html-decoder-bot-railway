#!/usr/bin/env node
'use strict';
/**
 * RDX DECODER v6.0 — Multi-Block + Iframe Protection Cleaner
 * - Extends v5.0: also strips iframe-based protection IIFE wrapper
 * - After decode, detects & removes (function(){ var _x = createElement('iframe')... })();
 * - Leaves only real app code in each script block
 * - Full check: warns if any obfuscation patterns remain after decode
 *
 * Usage: node RDX_DECODER_v6.js <obf.html> [out.html]
 */

const fs   = require('fs');
const vm   = require('vm');
const path = require('path');

/* ── ANSI ─────────────────────────────────────────────────────────── */
const C = {
  r:'\x1b[0m', b:'\x1b[1m', d:'\x1b[2m',
  bG:'\x1b[92m', bR:'\x1b[91m', bY:'\x1b[93m',
  bC:'\x1b[96m', bM:'\x1b[95m', bW:'\x1b[97m',
};
const cl  = (...p) => p.join('') + C.r;
const raw = s => s.replace(/\x1b\[[0-9;]*m/g,'');
const L = {
  ok  (l,v=''){console.log(`  ${cl(C.bG,'✔')}  ${cl(C.b,C.bW,l)}${v?'  '+cl(C.d,C.bW,v):''}`)},
  err (l,v=''){console.log(`  ${cl(C.bR,'✘')}  ${cl(C.b,C.bW,l)}${v?'  '+cl(C.d,C.bW,v):''}`)},
  warn(l,v=''){console.log(`  ${cl(C.bY,'⚠')}  ${cl(C.b,C.bW,l)}${v?'  '+cl(C.d,C.bW,v):''}`)},
  info(l,v=''){console.log(`  ${cl(C.bC,'◆')}  ${cl(C.b,C.bW,l)}${v?'  '+cl(C.d,C.bW,v):''}`)},
  nl  (){console.log('')},
  sec (t){console.log('');console.log(`  ${cl(C.bM,C.b,'▶')}  ${cl(C.b,C.bW,t)}`);
          console.log(`  ${cl(C.d,C.bC,'━'.repeat(56))}`);},
};

/* ── BANNER ───────────────────────────────────────────────────────── */
function banner(){
  const box = (s,col=C.bC) => `  ${cl(col,C.b,'║')}  ${s}`;
  console.log(`\n  ${cl(C.bC,C.b,'╔'+'═'.repeat(56)+'╗')}`);
  console.log(box(cl(C.bM,C.b,'RDX DECODER  v7.0  ·  Pattern-Aware Cleaner')));
  console.log(box(cl(C.d,C.bW,'Decodes ALL blocks · Strips iframe protection IIFE')));
  console.log(box(cl(C.d,C.bW,'v5 methods + Post-decode iframe wrapper removal')));
  console.log(`  ${cl(C.bC,C.b,'╚'+'═'.repeat(56)+'╝')}\n`);
}

/* ── PURE-PROTECTION SIGNATURES ─────────────────────────────────── */
const PROT_ONLY = ['_iPoison','_sBlock','_hBlock','_chkC','_chkBot','_chkDev'];

/* ── IFRAME PROTECTION IIFE DETECTION ───────────────────────────── */
/**
 * Detects iframe-based protection IIFE at the start of a decoded block.
 * Pattern: (function(){ var _xxx = document.createElement('iframe'); ... })();
 * After this IIFE, the real app code follows.
 */
function stripIframeProtectionIIFE(code) {
  const trimmed = code.trimStart();

  // Must start with (function(){
  if (!trimmed.startsWith('(function(){') && !trimmed.startsWith('(function() {')) {
    return { stripped: false, code };
  }

  // Signs this is an iframe protection IIFE
  const hasIframeCreate = /document\.createElement\s*\(\s*['"]iframe['"]\s*\)/.test(trimmed.slice(0, 3000));
  const hasContentWindowEval = /contentWindow\.eval/.test(trimmed.slice(0, 3000));
  if (!hasIframeCreate || !hasContentWindowEval) {
    return { stripped: false, code };
  }

  // Find the end of the IIFE: })(); — scan for it
  // We need to find the matching })(); for the outer (function(){
  let depth = 0;
  let i = 0;
  // Skip opening (function(){
  // Find end by brace matching
  let start = trimmed.indexOf('{');
  if (start === -1) return { stripped: false, code };

  depth = 0;
  let iifeEnd = -1;
  for (let j = start; j < trimmed.length; j++) {
    if (trimmed[j] === '{') depth++;
    else if (trimmed[j] === '}') {
      depth--;
      if (depth === 0) {
        // Check for })(); after this }
        const tail = trimmed.slice(j, j + 10);
        if (/^\}\s*\)\s*\(\s*\)\s*;/.test(tail)) {
          // Find actual end including )();
          const endMatch = trimmed.slice(j).match(/^\}\s*\)\s*\(\s*\)\s*;/);
          if (endMatch) {
            iifeEnd = j + endMatch[0].length;
            break;
          }
        }
        // If just } and depth=0 but no )(); — not an IIFE end
      }
    }
  }

  if (iifeEnd === -1) return { stripped: false, code };

  const afterIIFE = trimmed.slice(iifeEnd).trimStart();
  if (afterIIFE.length < 50) {
    // No real code after — this might be the only block, keep as-is
    return { stripped: false, code };
  }

  return { stripped: true, code: afterIIFE };
}

/* ─────────────────────────────────────────────────────────────────────
   SANDBOX
───────────────────────────────────────────────────────────────────── */
function makeSandbox(captureDocWrite=false){
  let _out='';
  const fakeEl=(tag='div')=>{
    const el={style:{},className:'',id:'',innerHTML:'',textContent:'',
      tagName:tag.toUpperCase(),children:[],childNodes:[],
      appendChild:()=>{},removeChild:()=>{},addEventListener:()=>{},
      setAttribute:()=>{},getAttribute:()=>null,
      getBoundingClientRect:()=>({width:0,height:0,top:0,left:0})};
    if(tag==='canvas'){
      el.getContext=()=>({fillRect:()=>{},strokeRect:()=>{},clearRect:()=>{},
        fillText:()=>{},strokeText:()=>{},getImageData:()=>({data:new Array(4).fill(0)}),
        putImageData:()=>{},drawImage:()=>{},measureText:()=>({width:10}),
        beginPath:()=>{},moveTo:()=>{},lineTo:()=>{},stroke:()=>{},fill:()=>{},
        save:()=>{},restore:()=>{},createLinearGradient:()=>({addColorStop:()=>{}})});
      el.toDataURL=()=>'';
    }
    return el;
  };
  const fakeDoc={
    open:()=>{_out='';},close:()=>{},
    write:(s)=>{if(captureDocWrite)_out+=s;},
    writeln:(s)=>{if(captureDocWrite)_out+=s+'\n';},
    cookie:'',title:'',readyState:'complete',
    createElement:fakeEl,createTextNode:(t)=>({nodeValue:t}),
    head:fakeEl('head'),body:fakeEl('body'),documentElement:fakeEl('html'),
    addEventListener:()=>{},removeEventListener:()=>{},dispatchEvent:()=>{},
    getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[],
    createDocumentFragment:()=>fakeEl('fragment'),
  };
  const nav={userAgent:'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36',
    webdriver:false,language:'en-US',languages:['en-US','en'],
    platform:'Linux armv8l',hardwareConcurrency:4,maxTouchPoints:5,
    plugins:{length:3},onLine:true,cookieEnabled:true};
  const sb={
    document:fakeDoc,navigator:nav,
    location:{href:'https://example.com/',hostname:'example.com',pathname:'/',
      protocol:'https:',port:'',replace:()=>{},assign:()=>{},reload:()=>{}},
    history:{pushState:()=>{},replaceState:()=>{},back:()=>{}},
    screen:{width:1080,height:2340,colorDepth:24},
    console:{log:()=>{},warn:()=>{},error:()=>{},info:()=>{}},
    setTimeout:()=>0,setInterval:()=>0,clearTimeout:()=>{},clearInterval:()=>{},
    requestAnimationFrame:()=>0,cancelAnimationFrame:()=>{},
    localStorage:{getItem:()=>null,setItem:()=>{},removeItem:()=>{},clear:()=>{}},
    sessionStorage:{getItem:()=>null,setItem:()=>{},removeItem:()=>{},clear:()=>{}},
    Image:function(){return{src:''};},
    Audio:function(){return{play:()=>Promise.resolve(),pause:()=>{},load:()=>{}};},
    Event:class Event{constructor(t){this.type=t;}},
    CustomEvent:class CustomEvent{constructor(t,d){this.type=t;this.detail=d?.detail;}},
    MutationObserver:class{observe(){}disconnect(){}},
    ResizeObserver:class{observe(){}disconnect(){}},
    IntersectionObserver:class{observe(){}disconnect(){}},
    WebSocket:class{send(){}close(){}},
    fetch:()=>Promise.resolve({json:()=>Promise.resolve({}),text:()=>Promise.resolve(''),ok:true,status:200}),
    XMLHttpRequest:class{open(){}send(){}setRequestHeader(){}addEventListener(){}},
    crypto:{getRandomValues:(a)=>{for(let i=0;i<a.length;i++)a[i]=Math.random()*256|0;return a;},subtle:{}},
    performance:{now:()=>Date.now(),timing:{}},
    stop:()=>{},
    URL:typeof URL!=='undefined'?URL:class URL{constructor(u){this.href=u;}},
    Blob:class Blob{constructor(){this.size=0;}},
    atob:s=>Buffer.from(s,'base64').toString('binary'),
    btoa:s=>Buffer.from(s,'binary').toString('base64'),
    devicePixelRatio:3,
    Math,JSON,Date,Promise,Symbol,Error,
    parseInt,parseFloat,isNaN,isFinite,
    decodeURIComponent,encodeURIComponent,decodeURI,encodeURI,escape,unescape,
    Object,Array,String,Number,Boolean,Function,RegExp,
    Map,Set,WeakMap,WeakSet,Proxy,Reflect,
    ArrayBuffer,Uint8Array,Int32Array,Float64Array,
    clearTimeout,clearInterval,
    eval:()=>{},window:null,self:null,top:null,globalThis:null,
  };
  sb.window=sb;sb.self=sb;sb.top=sb;sb.globalThis=sb;
  return {sandbox:sb,getOutput:()=>_out};
}

/* ── PATTERN DETECTOR ────────────────────────────────────────────── */
function detectPattern(block){
  if(/try\s*\{\s*\(0,eval\)\(\w+\)\s*\}\s*catch/.test(block)) return 3;
  if(/while\s*\(/.test(block)&&/document\s*\.\s*(write|open)\s*\(/.test(block)) return 2;
  if(/\(0,eval\)\(\w+\)\s*;/.test(block)) return 1;
  return 0;
}

/* ── PATTERN 1 ───────────────────────────────────────────────────── */
function decodePattern1(scriptBlock){
  const m=scriptBlock.match(/\(0,eval\)\((\w+)\)\s*;/);
  if(!m) throw new Error('P1 › eval var not found');
  const varName=m[1];
  const HOOK=`__RDX_P1_${Date.now()}__`;
  const patched=scriptBlock.replace(
    new RegExp(`\\(0,eval\\)\\(${varName}\\)\\s*;`,'g'),
    `${HOOK}(${varName});`
  );
  let captured=null;
  const {sandbox}=makeSandbox(false);
  sandbox[HOOK]=code=>{captured=code;};
  vm.createContext(sandbox);
  vm.runInContext(patched,sandbox,{timeout:60000});
  if(!captured) throw new Error('P1 › nothing captured');
  return captured;
}

/* ── PATTERN 2 ───────────────────────────────────────────────────── */
function decodePattern2(scriptBlock){
  const {sandbox,getOutput}=makeSandbox(true);
  vm.createContext(sandbox);
  try{vm.runInContext(scriptBlock,sandbox,{timeout:30000});}catch(_){}
  const out=getOutput();
  if(out.length<100) throw new Error(`P2 › output too small (${out.length})`);
  return out;
}

/* ── PATTERN 3 ───────────────────────────────────────────────────── */
function decodePattern3(scriptBlock){
  const m=scriptBlock.match(/try\s*\{\s*\(0,eval\)\((\w+)\)\s*\}\s*catch\s*(\{\s*\})?/);
  if(!m) throw new Error('P3 › try-eval var not found');
  const varName=m[1];
  const HOOK=`__RDX_P3_${Date.now()}__`;
  const tryPat=new RegExp(`try\\s*\\{\\s*\\(0,eval\\)\\(${varName}\\)\\s*\\}\\s*catch\\s*(\\{[^}]*\\})?`,'g');
  const patched=scriptBlock.replace(tryPat,`try{${HOOK}(${varName})}catch{}`);
  let layer2=null;
  const {sandbox:s1}=makeSandbox(false);
  s1[HOOK]=code=>{layer2=code;};
  vm.createContext(s1);
  try{vm.runInContext(patched,s1,{timeout:20000});}catch(_){}
  if(!layer2) throw new Error('P3 › L1 capture failed');
  const TAIL='document.open();document.write(';
  const ti=layer2.indexOf(TAIL);
  if(ti!==-1){
    const {sandbox:s2,getOutput}=makeSandbox(true);
    vm.createContext(s2);
    try{vm.runInContext(layer2.slice(ti),s2,{timeout:10000});}catch(_){}
    const out=getOutput();
    if(out.length>=100) return out;
  }
  const {sandbox:s2b,getOutput:getB}=makeSandbox(true);
  const lp=layer2.replace(/if\s*\(\s*!\s*_\$\s*\)/g,'if(false)')
                  .replace(/if\s*\(\s*_\$\s*===?\s*false\s*\)/g,'if(false)');
  vm.createContext(s2b);
  try{vm.runInContext(lp,s2b,{timeout:30000});}catch(_){}
  const outB=getB();
  if(outB.length>=100) return outB;
  throw new Error('P3 › L2 capture failed');
}

/* ── PATTERN 4 — Hybrid ─────────────────────────────────────────── */
function decodePatternHybrid(scriptBlock){
  const m=scriptBlock.match(/\(0,eval\)\((\w+)\)/);
  if(!m) throw new Error('Hybrid › no (0,eval)() found');
  const varName=m[1];
  const HOOK=`__RDX_H_${Date.now()}__`;
  let patched=scriptBlock
    .replace(new RegExp(`\\(0,eval\\)\\(${varName}\\)`,'g'),`${HOOK}(${varName})`)
    .replace(/window\s*\[\s*['"]\S+['"]\s*\]/g,'null');
  let captured=null;
  const {sandbox}=makeSandbox(false);
  sandbox[HOOK]=code=>{captured=code;};
  vm.createContext(sandbox);
  try{vm.runInContext(patched,sandbox,{timeout:60000});}catch(_){}
  if(!captured) throw new Error('Hybrid › nothing captured');
  return captured;
}

/* ── DECODE ONE BLOCK ────────────────────────────────────────────── */
function decodeBlock(body,pat){
  const strategies={1:decodePattern1,2:decodePattern2,3:decodePattern3};
  if(strategies[pat]){
    try{return strategies[pat](body);}catch(_){}
  }
  return decodePatternHybrid(body);
}

/* ── INNER LAYER CHECK ───────────────────────────────────────────── */
function resolveInner(decoded){
  const ip=detectPattern(decoded);
  if(ip===0) return decoded;
  L.warn('Inner obfuscation detected',`P${ip} — secondary decode`);
  const sm=decoded.match(/<script([^>]*)>([\s\S]*?)<\/script>/i);
  if(sm&&!sm[1].includes('src')&&sm[2].length>500){
    try{
      const r=decodeBlock(sm[2],detectPattern(sm[2])||ip);
      L.ok('Inner layer resolved',`${(r.length/1024).toFixed(1)} KB`);
      return r;
    }catch(_){}
  }
  try{
    const r=decodeBlock(decoded,ip);
    L.ok('Inner layer resolved',`${(r.length/1024).toFixed(1)} KB`);
    return r;
  }catch(_){}
  return decoded;
}

/* ── POST-DECODE FULL CHECK ──────────────────────────────────────── */
function fullDecodeCheck(html){
  const scriptRx=/<script([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  const issues=[];
  while((m=scriptRx.exec(html))!==null){
    const attrs=m[1], body=m[2];
    if(attrs.toLowerCase().includes('src')||body.length<100) continue;
    const pat=detectPattern(body);
    if(pat>0) issues.push({pat,size:(body.length/1024).toFixed(1)+'KB'});
  }
  return issues;
}

/* ── MAIN ────────────────────────────────────────────────────────── */
async function main(){
  banner();

  const inputFile=process.argv[2];
  if(!inputFile||!fs.existsSync(inputFile)){
    L.err('File not found',inputFile||'(none)');
    process.exit(1);
  }
  const base=path.basename(inputFile,path.extname(inputFile));
  const outputFile=process.argv[3]||path.join(path.dirname(inputFile),`${base}_decoded.html`);

  /* Step 1 — Read */
  L.sec('INPUT');
  const rawHTML=fs.readFileSync(inputFile,'utf-8');
  L.ok('Loaded',`${inputFile}  (${(rawHTML.length/1024).toFixed(1)} KB)`);

  /* Step 2 — Find all obfuscated blocks */
  L.sec('BLOCK DETECTION');
  const blockRx=/<script([^>]*)>([\s\S]*?)<\/script>/gi;
  const blocks=[];
  let bm;
  while((bm=blockRx.exec(rawHTML))!==null){
    const attrs=bm[1],body=bm[2];
    if(attrs.toLowerCase().includes('src')||body.length<500) continue;
    const pat=detectPattern(body);
    if(pat>0) blocks.push({
      fullMatch:bm[0],start:bm.index,end:bm.index+bm[0].length,body,pat
    });
  }
  if(!blocks.length){L.err('No obfuscated blocks found');process.exit(1);}
  L.ok(`Found ${blocks.length} block(s)`,
    blocks.map((b,i)=>`#${i+1}:P${b.pat}:${(b.body.length/1024).toFixed(0)}KB`).join('  '));

  /* Step 3 — Decode all blocks */
  L.sec('MULTI-BLOCK DECODE');
  let result=rawHTML, offset=0, ok=0, fail=0, protWarn=0, iframeStripped=0;

  for(let i=0;i<blocks.length;i++){
    const blk=blocks[i];
    const kb=(blk.body.length/1024).toFixed(1);
    process.stdout.write(
      `  ${cl(C.d,C.bW,`[${i+1}/${blocks.length}]`)}  `+
      `${cl(C.bC,'P'+blk.pat)}  ${cl(C.bW,kb+' KB')}  ... `
    );

    try{
      let decoded=decodeBlock(blk.body,blk.pat);
      decoded=resolveInner(decoded);

      const decodedKB=(decoded.length/1024).toFixed(1);
      const isPureProtection=PROT_ONLY.some(s=>decoded.includes(s))&&decoded.length<7000;

      let replacement;
      if(isPureProtection){
        replacement=`<!-- [RDX v6] protection-only block #${i+1} stripped (${decodedKB} KB) -->`;
        protWarn++;
        process.stdout.write(`${cl(C.bY,'⚠')} ${cl(C.bY,'prot-only stripped')} (${decodedKB} KB)\n`);
      } else {
        // NEW v6: Strip iframe protection IIFE if present at top of decoded block
        const iframeResult = stripIframeProtectionIIFE(decoded);
        if(iframeResult.stripped){
          decoded = iframeResult.code;
          iframeStripped++;
          process.stdout.write(`${cl(C.bG,'✓')} ${cl(C.bG,(decoded.length/1024).toFixed(1)+' KB')} ${cl(C.bY,'[iframe-prot removed]')}\n`);
        } else {
          process.stdout.write(`${cl(C.bG,'✓')} ${cl(C.bG,decodedKB+' KB')}\n`);
        }
        replacement=`<script>\n${decoded}\n</script>`;
      }

      const adjStart=blk.start+offset;
      const adjEnd  =blk.end+offset;
      result=result.slice(0,adjStart)+replacement+result.slice(adjEnd);
      offset+=replacement.length-blk.fullMatch.length;
      ok++;
    }catch(e){
      process.stdout.write(`${cl(C.bR,'✘')} ${cl(C.bR,e.message)}\n`);
      fail++;
    }
  }

  /* Step 4 — Cleanup */
  L.sec('CLEANUP');
  result=result.replace(/<!--[\s\S]{0,2000}?(?:PROTECTED|HTMLObfuscateBot|RDXPROTECT|Obfuscated By)[\s\S]{0,2000}?-->\r?\n*/i,'');
  result=result.replace(/<script[^>]*>\s*<\/script>/gi,'');
  result=result.replace(/\r\n/g,'\n').replace(/\n{3,}/g,'\n\n').replace(/[ \t]+$/gm,'').trimStart();
  L.ok('Done',`${protWarn} prot-only + ${iframeStripped} iframe-prot stripped, ${fail} failed`);

  /* Step 5 — Full decode check (NEW v6) */
  L.sec('POST-DECODE CHECK');
  const issues = fullDecodeCheck(result);
  if(issues.length === 0){
    L.ok('✅ FULL DECODE VERIFIED','No obfuscation patterns remain');
  } else {
    L.warn(`${issues.length} block(s) still have obfuscation — attempting re-decode...`);
    // Re-run decode pass on the result
    const blockRx2=/<script([^>]*)>([\s\S]*?)<\/script>/gi;
    const blocks2=[];
    let bm2;
    while((bm2=blockRx2.exec(result))!==null){
      const attrs=bm2[1],body=bm2[2];
      if(attrs.toLowerCase().includes('src')||body.length<500) continue;
      const pat=detectPattern(body);
      if(pat>0) blocks2.push({fullMatch:bm2[0],start:bm2.index,end:bm2.index+bm2[0].length,body,pat});
    }
    let offset2=0, reOk=0;
    for(const blk2 of blocks2){
      try{
        let dec2=decodeBlock(blk2.body,blk2.pat);
        dec2=resolveInner(dec2);
        const ir=stripIframeProtectionIIFE(dec2);
        if(ir.stripped) dec2=ir.code;
        const rep2=`<script>\n${dec2}\n</script>`;
        const as=blk2.start+offset2, ae=blk2.end+offset2;
        result=result.slice(0,as)+rep2+result.slice(ae);
        offset2+=rep2.length-blk2.fullMatch.length;
        reOk++;
        L.ok(`Re-decode pass: block decoded`,`${(dec2.length/1024).toFixed(1)} KB`);
      }catch(e){
        L.err(`Re-decode failed`,e.message);
      }
    }
    // Final check
    const issues2=fullDecodeCheck(result);
    if(issues2.length===0){
      L.ok('✅ FULL DECODE VERIFIED after re-pass');
    } else {
      L.warn(`⚠ ${issues2.length} block(s) could not be fully decoded`,'Manual inspection needed');
    }
  }

  /* Step 5.5 — Auto Cleaner (v7: Pattern-Aware) */
  L.sec('AUTO CLEANER');
  let wrapperTop=false, wrapperBottom=false, rdxRemoved=0;

  // ── Detect wrapper pattern ─────────────────────────────────────────────────
  // Pattern A │ <!doctype html><html><head><meta charset=UTF-8></head><body>
  //           │ Real HTML is encoded INSIDE a single outer shell + <script>.
  //           │ Needs: top shell removed + trailing </script></body></html> removed.
  //
  // Pattern B │ <!--...protection comment...-->
  //           │ <!DOCTYPE html>...  ← real DOCTYPE follows comment
  //           │ Step 4 already removed the comment; head/CSS intact. No shell to strip.
  //
  // FIX (v7): v6.1 used a broad /^<!doctype html>[^]*?-->/ which accidentally
  //           matched Pattern B files and ate the entire head + CSS section.
  // ──────────────────────────────────────────────────────────────────────────
  const patA=/^<!doctype html><html><head><meta charset=UTF-8><\/head><body>/i.test(result);

  if(patA){
    // 1. Top: remove exact shell + optional comment still present inside it
    const topRx=/^<!doctype html><html><head><meta charset=UTF-8><\/head><body><script>\s*(?:<!--[\s\S]*?-->\s*)?\n?/i;
    if(topRx.test(result)){ result=result.replace(topRx,''); wrapperTop=true; }

    // 2. Bottom: trailing </script></body></html> only exists in Pattern A files
    const botRx=/\s*<\/script><\/body><\/html>\s*$/i;
    if(botRx.test(result)){ result=result.replace(botRx,''); wrapperBottom=true; }
  }

  // 3. RDX own protection-only comments — always clean regardless of pattern
  const rdxRx=/<!--\s*\[RDX v\d+\][^\n]*-->\s*\n?/g;
  const rdxM=result.match(rdxRx);
  if(rdxM){ rdxRemoved=rdxM.length; result=result.replace(rdxRx,''); }

  result=result.trim()+'\n';

  L.ok('Pattern',        patA ? 'A  (outer shell wrapper)' : 'B  (comment-before-DOCTYPE)');
  if(patA){
    L.ok('Top wrapper',    wrapperTop    ? 'removed' : 'not found');
    L.ok('Bottom wrapper', wrapperBottom ? 'removed' : 'not found');
  } else {
    L.ok('Head/CSS',       'preserved  (no shell present)');
  }
  L.ok('RDX comments',   rdxRemoved>0  ? `${rdxRemoved} removed` : 'none found');

  /* Step 6 — Save */
  L.sec('OUTPUT');
  fs.writeFileSync(outputFile,result,'utf-8');
  const titleM=result.match(/<title[^>]*>([^<]*)<\/title>/i);
  if(titleM) L.ok('Title',titleM[1].trim());
  const finalKB=(result.length/1024).toFixed(1);
  const lines=result.split('\n').length;

  /* Result box */
  console.log('');
  const BW=54;
  const hl=cl(C.bG,C.b,'═'.repeat(BW-2));
  const vl=cl(C.bG,C.b,'║');
  console.log(`  ${cl(C.bG,C.b,'╔')}${hl}${cl(C.bG,C.b,'╗')}`);
  console.log(`  ${vl}  ${cl(C.bG,C.b,'✨  DECODE COMPLETE!')}${' '.repeat(BW-22)}${vl}`);
  console.log(`  ${cl(C.bG,C.b,'╠')}${hl}${cl(C.bG,C.b,'╣')}`);
  const row=(k,v)=>{
    const c=`  ${cl(C.bC,k+':')}  ${cl(C.bW,v)}`;
    const pad=' '.repeat(Math.max(0,BW-2-raw(c).length));
    console.log(`  ${vl}${c}${pad}${vl}`);
  };
  row('Input',  `${path.basename(inputFile)} (${(rawHTML.length/1024).toFixed(1)} KB)`);
  row('Output', path.basename(outputFile));
  row('Blocks', `${ok}/${blocks.length} decoded  ·  ${fail} failed`);
  row('Prot',    `${protWarn} prot-only stripped`);
  row('Iframe',  `${iframeStripped} iframe-protection IIFE removed`);
  row('Cleaner', `Pat-${patA?'A':'B'}  top:${wrapperTop?'✔':'–'}  btm:${wrapperBottom?'✔':'–'}  rdx:${rdxRemoved}`);
  row('Size',   `${finalKB} KB  ·  ${lines.toLocaleString()} lines`);
  console.log(`  ${cl(C.bG,C.b,'╚')}${hl}${cl(C.bG,C.b,'╝')}`);
  console.log('');
}

main().catch(err=>{
  process.stdout.write('\x1b[?25h');
  console.error(`\n  ✘  Fatal: ${err.message}\n`);
  process.exit(1);
});
