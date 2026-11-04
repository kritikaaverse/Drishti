// In development, empty base uses Vite's same-origin /api proxy.
// On a phone, localhost is the phone: configure a reachable HTTPS host or laptop LAN IP.
export let API_BASE=(sessionStorage.getItem('drishti-api-base')??import.meta.env.VITE_API_BASE_URL??'').replace(/\/$/,'');
export const DEMO_MODE=import.meta.env.VITE_DEMO_MODE==='true';
let language='en';
export const setApiLanguage=value=>{language={English:'en',Hindi:'hi',Marathi:'mr'}[value]||value||'en'};
export const getApiKey=()=>sessionStorage.getItem('drishti-api-key')||'';
export function saveApiKey(value){sessionStorage.setItem('drishti-api-key',value);window.dispatchEvent(new Event('drishti-key-changed'))}
export function saveApiConnection(base,key){const trimmed=base.trim().replace(/\/$/,'');if(trimmed){const parsed=new URL(trimmed);if(!['http:','https:'].includes(parsed.protocol)||parsed.username||parsed.password||parsed.search||parsed.hash||parsed.pathname!=='/')throw new Error('Use only the backend origin, e.g. https://your-laptop.example, without paths or credentials.');if(location.protocol==='https:'&&parsed.protocol==='http:')throw new Error('This HTTPS page needs an HTTPS backend. Leave URL empty for the same-origin proxy.')}API_BASE=trimmed;sessionStorage.setItem('drishti-api-base',trimmed);saveApiKey(key.trim())}
export const senderUrl=()=>`${API_BASE}/camera-sender`;
async function request(path,options={}){
 const headers=new Headers(options.headers);if(getApiKey())headers.set('X-API-Key',getApiKey());
 const response=await fetch(`${API_BASE}${path}`,{...options,headers,signal:options.signal||AbortSignal.timeout(45000)});
 if(!response.ok){let error;try{error=await response.json()}catch{}const failure=new Error(error?.error||`Backend request failed (${response.status}). Check your connection.`);failure.status=response.status;throw failure}
 if(options.blob){const blob=await response.blob();blob.eventId=response.headers.get('X-Drishti-Event-Id');return blob}return response.json();
}
const title=value=>value.replace(/\b\w/g,c=>c.toUpperCase());
export function uiDetections(data){return(data.detections||[]).map((d,i)=>({...d,id:`${data.event_id||data.timestamp||'frame'}-${i}`,name:title(d.name),rawName:d.name,confidence:Math.round(d.confidence*100),direction:{left:'On your left',center:'Directly ahead',right:'On your right'}[d.position]||d.position,distance:d.distance==null?'Not available':`${d.distance} m`,time:new Date(data.timestamp).toLocaleTimeString(),timestamp:data.timestamp,icon:d.name==='person'?'person':['car','bus','truck'].includes(d.name)?'car':['bicycle','motorcycle'].includes(d.name)?'bike':d.name==='traffic light'?'traffic':'object',category:d.category||'Objects'}))}
export const normalizeResult=data=>({...data,raw:data,detections:uiDetections(data),text:data.ocr?.text||'',description:data.scene_description||'',objects:[...new Set((data.detections||[]).map(d=>d.name))]});
async function upload(path,file){const body=new FormData();body.append('image',file);return normalizeResult(await request(`${path}?language=${language}&device_id=web-dashboard`,{method:'POST',body}))}
export const api={
 health:()=>request('/api/health'),cameraStatus:()=>request('/api/camera/status'),snapshot:()=>request('/api/camera/snapshot',{blob:true}),
 analyze:file=>upload('/api/detection/analyze',file),analyzeAll:file=>upload('/api/detection/analyze-all',file),readText:file=>upload('/api/ocr/read',file),describe:file=>upload('/api/scene/describe',file),obstacles:file=>upload('/api/obstacle/detect',file),guidance:file=>upload('/api/navigation/guidance',file),
 history:async()=>{const data=await request('/api/detection/history?limit=100');return{...data,detections:data.records.flatMap(r=>uiDetections(r.response))}},
 deleteHistory:()=>request('/api/detection/history',{method:'DELETE'}),deviceStatus:()=>request('/api/device/status'),
 voiceCommand:command=>request('/api/voice/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command,language})}),
 voiceMessage:message=>request('/api/voice/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,language,device_id:'web-dashboard'})})
};
// Latest-only server queue + reconnecting observer. This never opens a laptop webcam.
export function connectRealtime(onMessage,onError){let socket,timer,stopped=false,delay=1000,reported=false;function open(){if(stopped)return;const base=API_BASE||location.origin;socket=new WebSocket(`${base.replace(/^http/,'ws')}/api/ws/vision`);socket.onopen=()=>{socket.send(JSON.stringify({role:'watch',device_id:'web-dashboard',language,api_key:getApiKey()}))};socket.onmessage=event=>{try{const data=JSON.parse(event.data);if(data.type==='ready'){delay=1000;reported=false;return}if(data.type==='detections')onMessage({...normalizeResult(data),type:'detections'});else if(data.success===false)onError?.(data.error);else onMessage(data)}catch{onError?.('Could not read a real-time server message.')}};socket.onerror=()=>{if(!reported){reported=true;onError?.('Live backend connection unavailable. Retrying…')}};socket.onclose=event=>{if(stopped)return;onMessage({type:'camera_status',connected:false});if(event.code===1008){onError?.('Live connection rejected. Check API key and CORS origin in Device Management.');return}timer=setTimeout(open,delay);delay=Math.min(delay*2,15000)}}open();return{close(){stopped=true;clearTimeout(timer);socket?.close()}}}
