import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import {join, dirname} from 'node:path';
import {Window} from 'happy-dom';
const window = new Window({url:'http://localhost:5173'});
for(const key of ['window','document','navigator','HTMLElement','HTMLMediaElement','HTMLInputElement','HTMLFormElement','Element','Node','Text','Comment','Event','CustomEvent','MutationObserver','getComputedStyle']) {
 Object.defineProperty(globalThis,key,{value: key==='getComputedStyle'?window.getComputedStyle.bind(window):window[key],configurable:true});
}
const root=fileURLToPath(new URL('..', import.meta.url));
const sveltePath=dirname(fileURLToPath(import.meta.resolve('svelte/package.json')));
const compiler=await import(pathToFileURL(sveltePath+'/compiler/index.js'));
const {compile}=compiler.default || compiler;
let src=await fs.readFile(root+'/src/components/AuthForm.svelte','utf8');
let js=compile(src,{generate:'client',filename:'AuthForm.svelte'}).js.code;
js=js.replace(/(['"])svelte(\/[^'"]*)?\1/g, (_m,_quote,suffix)=>JSON.stringify(import.meta.resolve('svelte'+(suffix || ''))))
.replace(/import \{ supabase \} from [^;]+;/,'const supabase = globalThis.mockSupabase;');
let calls=[];let response={data:{session:null},error:null};let pending;
globalThis.mockSupabase={auth:Object.fromEntries(['signInWithPassword','signUp','resetPasswordForEmail','updateUser'].map(method=>[method,async (...args)=>{calls.push({method,args});return pending?await pending:response}]))};
const temp=await fs.mkdtemp(join(tmpdir(),'starter-auth-'));
const compiled=join(temp,'AuthForm.mjs');
await fs.writeFile(compiled,js);
const {mount,unmount,flushSync}=await import(pathToFileURL(sveltePath+'/src/index-client.js'));
const {default:AuthForm}=await import(pathToFileURL(compiled));
let component;
function start(props={}) { calls=[];response={data:{session:null},error:null};pending=null;document.body.innerHTML='<div id="root"></div>';flushSync(()=>{component=mount(AuthForm,{target:document.querySelector('#root'),props})}); }
async function stop(){await unmount(component);}
function fill(id,value){const el=document.getElementById(id);el.value=value;el.dispatchEvent(new window.Event('input',{bubbles:true}));flushSync();}
function click(text){const el=[...document.querySelectorAll('button')].find(x=>x.textContent===text);assert.ok(el,text);el.click();flushSync();}
async function submit(){document.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,0));flushSync();}
start();fill('auth-email','demo@example.com');fill('auth-password','secret value');await submit();assert.deepEqual(calls,[{method:'signInWithPassword',args:[{email:'demo@example.com',password:'secret value'}]}]);assert.equal(document.getElementById('auth-password').value,'');await stop();console.log('PASS password login');
start();response={error:new Error('Invalid login credentials')};fill('auth-email','demo@example.com');fill('auth-password','bad');await submit();assert.equal(document.querySelector('[role=alert]').textContent,'Invalid login credentials');assert.equal(document.querySelector('fieldset').disabled,false);await stop();console.log('PASS error and retry state');
start({settings:true});click('Create account');fill('auth-email','demo@example.com');fill('auth-password','password123');fill('auth-confirmation','different');await submit();assert.equal(calls.length,0);assert.match(document.querySelector('[role=alert]').textContent,/do not match/);fill('auth-confirmation','password123');await submit();assert.equal(calls[0].method,'signUp');assert.equal(calls[0].args[0].options.emailRedirectTo,'http://localhost:5173/settings');assert.match(document.querySelector('[role=status]').textContent,/confirm your account/);assert.equal(document.getElementById('auth-password').value,'');await stop();console.log('PASS signup matching, confirmation-required response and redirect');
start();click('Create account');response={data:{session:{access_token:'fake'}},error:null};fill('auth-email','demo@example.com');fill('auth-password','password123');fill('auth-confirmation','password123');await submit();assert.equal(document.querySelector('[role=status]').textContent,'Account created.');await stop();console.log('PASS signup with immediate session');
start();click('Forgot password?');fill('auth-email','demo@example.com');await submit();assert.deepEqual(calls[0],{method:'resetPasswordForEmail',args:['demo@example.com',{redirectTo:'http://localhost:5173/reset-password'}]});assert.match(document.querySelector('[role=status]').textContent,/If an account exists/);await stop();console.log('PASS recovery email');
start({resetPassword:true,signedIn:true});fill('auth-password','password123');fill('auth-confirmation','password123');await submit();assert.deepEqual(calls[0],{method:'updateUser',args:[{password:'password123'}]});assert.match(document.querySelector('[role=status]').textContent,/Password updated/);assert.equal(document.querySelector('a').getAttribute('href'),'/');assert.equal(document.querySelector('form'),null);await stop();console.log('PASS recovery password update');
start({resetPassword:true,signedIn:false});assert.match(document.querySelector('h2').textContent,/Reset password/);assert.equal(document.getElementById('auth-password'),null);await stop();console.log('PASS expired recovery session');
start();let finish;pending=new Promise(r=>finish=r);fill('auth-email','demo@example.com');fill('auth-password','password123');await submit();assert.equal(document.querySelector('fieldset').disabled,true);await submit();assert.equal(calls.length,1);finish({error:null});await new Promise(r=>setTimeout(r,0));flushSync();assert.equal(document.querySelector('fieldset').disabled,false);await stop();console.log('PASS pending and duplicate submission guard');
await window.happyDOM.close();

await fs.rm(temp,{recursive:true,force:true});
