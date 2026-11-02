import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { Window } from 'happy-dom';
const window = new Window({url:'http://localhost:5173'});
for (const key of ['window','document','navigator','HTMLElement','HTMLMediaElement','HTMLInputElement','HTMLFormElement','Element','Node','Text','Comment','Event','CustomEvent','MutationObserver','getComputedStyle']) Object.defineProperty(globalThis,key,{value:key==='getComputedStyle'?window.getComputedStyle.bind(window):window[key],configurable:true});
const compiler = await import('svelte/compiler');
const {compile} = compiler.default || compiler;
const {mount,unmount,flushSync} = await import('svelte');
const temp = await fs.mkdtemp(join(tmpdir(),'onboarding-credits-'));
const tick = async () => { await new Promise(r=>setTimeout(r,0));flushSync(); };
const mock = { get: async()=>balance, post: async()=>balance };
globalThis.mockApi = mock;
const components = {};
for (const name of ['Onboarding','Credits']) {
 let js = compile(await fs.readFile(new URL(`../src/components/${name}.svelte`,import.meta.url),'utf8'),{generate:'client',filename:`${name}.svelte`}).js.code;
 js = js.replace(/(['"])svelte(\/[^'"]*)?\1/g,(_m,_q,suffix)=>JSON.stringify(import.meta.resolve('svelte'+(suffix||'')))).replace(/import \{ api \} from [^;]+;/,'const api = globalThis.mockApi;');
 const file = join(temp,`${name}.mjs`);await fs.writeFile(file,js);components[name]=(await import(pathToFileURL(file))).default;
}
let component;let balance;
function start(name,props={}) { document.body.innerHTML='<div id="root"></div>';flushSync(()=>{component=mount(components[name],{target:document.querySelector('#root'),props});}); }
function input(id,value) { const el=document.getElementById(id);el.value=value;el.dispatchEvent(new window.Event('input',{bubbles:true}));flushSync(); }
async function submit() { document.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick(); }
function button(text) { return [...document.querySelectorAll('button')].find(el=>el.textContent===text); }
let payload;let completed=0;
mock.post = async(path,body)=>{payload={path,body};};
start('Onboarding',{onComplete:async()=>{completed++;}});input('date-of-birth','2000-01-01');input('discovery-source','  A friend  ');await submit();
assert.deepEqual(payload,{path:'/me/onboarding',body:{date_of_birth:'2000-01-01',discovery_source:'A friend'}});assert.equal(completed,1);await unmount(component);console.log('PASS onboarding data and completion');
mock.post=async()=>{throw new Error('You must be at least 14 to use this service.');};
start('Onboarding',{onComplete:async()=>{completed++;}});input('date-of-birth','2020-01-01');input('discovery-source','Search');await submit();assert.match(document.querySelector('[role=alert]').textContent,/at least 14/);assert.equal(completed,1);await unmount(component);console.log('PASS rejected age stays in onboarding');
balance={day:'2026-11-02',tier:'free',limit:5,used:0,remaining:5,resets_at:'2099-01-01T00:00:00Z'};
mock.get=async()=>balance;mock.post=async()=>({...balance,used:1,remaining:4});
start('Credits');await tick();assert.match(document.body.textContent,/5 of 5/);button('Use 1 credit').click();await tick();assert.match(document.body.textContent,/4 of 5/);await unmount(component);console.log('PASS credit spend displays server response');
balance={...balance,used:4,remaining:1};mock.post=async()=>{balance={...balance,used:5,remaining:0};throw new Error('Daily credit limit reached.');};
start('Credits');await tick();button('Use 1 credit').click();await tick();assert.equal(button('Use 1 credit').disabled,true);assert.match(document.querySelector('[role=alert]').textContent,/Daily credit limit/);await unmount(component);console.log('PASS exhausted credits and cross-client refresh');
balance={...balance,resets_at:'2000-01-01T00:00:00Z'};start('Credits');await tick();assert.equal(button('Use 1 credit').disabled,false);await unmount(component);console.log('PASS yesterday exhaustion does not block next-day spend');
await window.happyDOM.close();await fs.rm(temp,{recursive:true,force:true});
