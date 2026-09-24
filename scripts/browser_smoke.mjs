// Requires Node >=22 and a separate Chrome --remote-debugging-port=9223.
import fs from 'node:fs/promises';
const tabs=await (await fetch('http://127.0.0.1:9223/json')).json();
const targetUrl=process.env.METRO_DASHBOARD_URL || 'http://127.0.0.1:8080';
const tab=tabs.find(t=>t.type==='page'&&t.url.startsWith(targetUrl));
if(!tab)throw Error('Dashboard tab not found');
const socket=new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
let serial=0;const pending=new Map(),errors=[];
socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Runtime.exceptionThrown')errors.push(m.params);if(m.id){const p=pending.get(m.id);pending.delete(m.id);if(m.error)p.reject(m.error);else p.resolve(m.result);}};
function call(method,params={}){return new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
await call('Runtime.enable');
await call('Page.enable');
await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1080,deviceScaleFactor:1,mobile:false});
await call('Page.reload',{ignoreCache:true});
for(let i=0;i<40;i++){await new Promise(r=>setTimeout(r,250));if(await evaluate('typeof frames!=="undefined" && frames.length>0'))break;}
const loaded=await evaluate('({frames:frames.length,bag:document.getElementById("bag").textContent,error:document.getElementById("error").textContent})');
if(!loaded.frames||loaded.error)throw Error(JSON.stringify(loaded));
await evaluate('idx=Math.min(10,frames.length-1);update();document.querySelector("[data-view=top]").click();');
if(await evaluate('view')!=='top')throw Error('View toggle broken');
await evaluate(`document.querySelector('[data-view="3d"]').click();`);
await evaluate(`(()=>{
 const prior=JSON.stringify(reviewLabels),stored=localStorage.getItem(reviewKey);
 try {
  document.getElementById('hide-detections').click();
  if(!hideDetections||!document.getElementById('objects').textContent.includes('скрыты'))throw Error('Review overlay not hidden');
  document.getElementById('label-distance').value='25.5';
  document.getElementById('label-note').value='AUTOMATED TEST - RESTORED';
  saveLabel(true);
  const row=reviewLabels[frames[idx].frame_index];
  if(row.obstacle_present!==true||row.nearest_distance_m!==25.5||row.bag_timestamp!==frames[idx].bag_timestamp)throw Error('Label mismatch');
 } finally {
  reviewLabels=JSON.parse(prior);
  if(stored===null)localStorage.removeItem(reviewKey);else localStorage.setItem(reviewKey,stored);
  hideDetections=false;document.getElementById('hide-detections').checked=false;update();
 }
})()`);
await fs.mkdir('analysis',{recursive:true});
let shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
await fs.writeFile('analysis/dashboard.png',Buffer.from(shot.data,'base64'));
await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await new Promise(r=>setTimeout(r,300));
if(await evaluate('document.documentElement.scrollWidth>innerWidth+2'))throw Error('Mobile horizontal overflow');
shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
await fs.writeFile('analysis/dashboard-mobile.png',Buffer.from(shot.data,'base64'));
await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1080,deviceScaleFactor:1,mobile:false});
if(process.argv.includes('--video')){
 const encoded=await evaluate(`(async()=>{
  playing=false;idx=0;view='top';zoom=1;update();
  const output=document.createElement('canvas');output.width=1280;output.height=800;
  const dc=output.getContext('2d'),stream=output.captureStream(12);
  const mime=MediaRecorder.isTypeSupported('video/webm;codecs=vp9')?'video/webm;codecs=vp9':'video/webm';
  const recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:2500000}),chunks=[];
  recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
  const finished=new Promise(resolve=>recorder.onstop=resolve);recorder.start();
  for(let i=0;i<frames.length;i++){
   idx=i;update();dc.fillStyle='#080e16';dc.fillRect(0,0,1280,800);
   dc.fillStyle='#48dbbd';dc.font='bold 28px sans-serif';dc.fillText('METRO GUARD / '+summary.bag.split('/').pop(),35,45);
   dc.drawImage(canvas,0,75,1280,610);
   dc.fillStyle='#ffb75b';dc.font='20px sans-serif';dc.fillText('Frame '+frames[i].frame_index+' | '+frames[i].status+' | '+frames[i].processing_ms.toFixed(1)+' ms',35,720);
   dc.fillStyle='#8da2b8';dc.font='17px sans-serif';dc.fillText('Research baseline. Uncalibrated corridor. Detection accuracy not validated.',35,760);
   const duration=i+1<frames.length?Math.max(.05,frames[i+1].bag_timestamp-frames[i].bag_timestamp):.5;
   await new Promise(r=>setTimeout(r,duration*1000));
  }
  recorder.stop();await finished;stream.getTracks().forEach(t=>t.stop());
  const bytes=new Uint8Array(await new Blob(chunks,{type:mime}).arrayBuffer());
  let str='';for(let start=0;start<bytes.length;start+=32768)str+=String.fromCharCode(...bytes.subarray(start,start+32768));
  return btoa(str);
 })()`);
 await fs.writeFile('analysis/demo.webm',Buffer.from(encoded,'base64'));
}
if(errors.length)throw Error(JSON.stringify(errors));
await fs.writeFile('analysis/browser_check.json',JSON.stringify({passed:true,...loaded,console_exceptions:errors.length,mobile_overflow:false,manual_review_tested:true,test_labels_removed:true,video:process.argv.includes('--video')},null,2));
console.log(JSON.stringify({passed:true,...loaded}));socket.close();
