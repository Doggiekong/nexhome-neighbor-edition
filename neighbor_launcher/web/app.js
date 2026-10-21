"use strict";
const $ = id => document.getElementById(id);
let state, confirmation, posting = false, lost = 0, guideStep = 0;
const guide = [
  "打开 HACS，找到官方 NexHome。",
  "打开右上角菜单，选择 Remove（移除）。如果提示已经配置，选择 IGNORE（保留现有配置并继续）。不要去删除 Home Assistant 中的 NexHome 设置。",
  "确认 REMOVE（移除）后返回这里，点击“我已经完成，重新检查”。我们会先核对，再继续安装。"
];
const actions = {welcome:"check",fresh:"prepare",official:"prepare",update:"prepare",latest:"check",hacs:"check",confirm:"confirm",handoff:"handoff",installed:"native",interrupted:"recover",restored:"check",failed:"check",unhealthy:"check",connection_wait:"check"};
function drawGuide(){
  $("guide-step").textContent = guide[guideStep];
  $("guide-step-count").textContent = `第 ${guideStep + 1} 步，共 ${guide.length} 步`;
  $("guide-back").disabled = guideStep === 0; $("guide-next").disabled = guideStep === guide.length - 1;
}
function render(s){
  state=s; confirmation=s.confirmation;
  $("title").textContent=s.title; $("description").textContent=s.description;
  $("primary").textContent=s.button; $("primary").hidden=!s.button;
  $("primary").disabled=s.busy||posting;
  $("cancel").hidden=s.screen!=="confirm";
  $("recheck").hidden=!["unknown","conflict"].includes(s.screen);
  $("connect").hidden=!s.can_connect; $("connect").disabled=s.busy||posting;
  $("product-identity").textContent=s.upstream_base_version?`友邻加强版 ${s.product_version} · 基于官方组件 ${s.upstream_base_version}`:"";
  $("versions").hidden=s.screen!=="update";
  $("current-version").textContent=s.current_version||"—"; $("new-version").textContent=s.new_version||"—";
  $("notice").textContent=s.handoff_note||(s.screen==="hacs"?"HACS 是 Home Assistant 常用的扩展安装工具。":"");
  $("hacs-guide").hidden=s.screen!=="handoff"; drawGuide();
  $("recovery-help").hidden=s.screen!=="recovery";
  $("known-source").hidden=s.screen!=="unknown";
  $("done-link").hidden=!["installed","latest"].includes(s.screen);
  $("native-help").hidden=!["installed","latest"].includes(s.screen);
  $("progress").replaceChildren(...s.steps.map(text=>{const li=document.createElement("li");li.textContent=text;return li;}));
  $("progress").hidden=!s.steps.length;
  $("diagnostic").textContent=JSON.stringify(s.technical,null,2);
}
async function request(path,options={}){
  const abort=new AbortController(), timer=setTimeout(()=>abort.abort(),8000);
  try {return await fetch(path,{...options,signal:abort.signal,cache:"no-store",credentials:"same-origin"});}
  finally {clearTimeout(timer);}
}
async function poll(){
  try {
    const response=await request("api/state"); if(!response.ok)throw Error("unavailable");
    render(await response.json()); lost=0;
  }catch(_){
    $("notice").textContent="Home Assistant 正在重新连接。已开始的操作会继续，请稍候。";
    if(++lost>60){$("notice").textContent="暂时还连不上 Home Assistant。请稍后重新打开这个页面，不要重复开始安装。";return;}
  }
  setTimeout(poll,state?.busy||lost?2000:5000);
}
$("primary").addEventListener("click",async()=>{
  if(posting||!state||state.busy)return;
  if(state.screen==="installed"){$("done-link").click();return;}
  const action=actions[state.screen];
  if(!action){if(state.screen==="recovery")$("recovery-help").hidden=false;$("technical").open=true;return;}
  posting=true;$("primary").disabled=true;
  try{
    const payload={action};
    if(action==="confirm"){payload.plan=state.plan;payload.confirmed=true;}
    const response=await request("api/action",{method:"POST",headers:{"Content-Type":"application/json","X-Nexhome-Confirm":confirmation},body:JSON.stringify(payload)});
    if(![202,409].includes(response.status))throw Error("action unavailable");
    const current=await request("api/state"); if(current.ok)render(await current.json());
  }catch(_){$("notice").textContent="正在确认已保存的进度，请稍候，不要重复点击。";}
  finally{posting=false;$("primary").disabled=state?.busy||false;}
});
$("cancel").addEventListener("click",async()=>{await request("api/action",{method:"POST",headers:{"Content-Type":"application/json","X-Nexhome-Confirm":confirmation},body:JSON.stringify({action:"cancel"})});const response=await request("api/state");if(response.ok)render(await response.json());});
$("recheck").addEventListener("click",async()=>{if(posting||state.busy)return;posting=true;try{await request("api/action",{method:"POST",headers:{"Content-Type":"application/json","X-Nexhome-Confirm":confirmation},body:JSON.stringify({action:"check"})});}finally{posting=false;}});
$("connect").addEventListener("click",()=>$("done-link").click());
$("guide-back").addEventListener("click",()=>{if(guideStep>0)guideStep--;drawGuide();});
$("guide-next").addEventListener("click",()=>{if(guideStep<guide.length-1)guideStep++;drawGuide();});
$("known-source").addEventListener("click",()=>{$("known-source-help").hidden=false;$("technical").open=true;});
$("copy").addEventListener("click",async()=>{
  const response=await request("api/diagnostics");if(!response.ok)return;
  const text=JSON.stringify(await response.json(),null,2);
  if(navigator.clipboard){try{await navigator.clipboard.writeText(text);$("copy-status").textContent="已复制脱敏诊断信息。";return;}catch(_){}}
  const link=document.createElement("a"),url=URL.createObjectURL(new Blob([text],{type:"application/json"}));
  link.href=url;link.download="nexhome-diagnostics.json";link.click();URL.revokeObjectURL(url);
  $("copy-status").textContent="当前浏览器不支持直接复制，已改为导出脱敏文件。";
});
poll();
