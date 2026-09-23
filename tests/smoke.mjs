import create from '../public/ngpcraft.mjs';
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const m=await create();
const rom=readFileSync(process.argv[2]);
function withBytes(bytes,fn){const p=m._malloc(bytes.length);try{m.HEAPU8.set(bytes,p);return fn(p,bytes.length);}finally{m._free(p);}}
assert.equal(withBytes(new Uint8Array(10),(p,n)=>m._web_load(p,n)),0);
assert.equal(withBytes(rom,(p,n)=>m._web_load(p,n)),1);
let audio=0,nonzero=0;const images=new Set();let lastHash;
const start=performance.now();
for(let i=0;i<600;i++){
  assert.ok([0,1,41].includes(m._web_run(i>200&&i<230?64:0)));
  audio+=m._web_audio_frames();
  const ap=m._web_audio()>>1;for(let j=0;j<m._web_audio_frames()*2;j++)if(m.HEAP16[ap+j])nonzero++;
  if(i%30===0){const p=m._web_video();lastHash=createHash('sha256').update(m.HEAPU8.subarray(p,p+160*152*4)).digest('hex');images.add(lastHash);}
}
assert.ok(audio>400000,'audio clock');assert.ok(images.size>1,'changing video');
const p=m._web_save(),save=m.HEAPU8.slice(p,p+m._web_save_size());
assert.equal(withBytes(save,(p,n)=>m._web_save_restore(p,n)),1,'own save accepted');
// Alter a flash byte with a valid checksum to prove data is actually restored.
const flashMutation=new DataView(save.buffer).getUint32(12,true)>0;
if(flashMutation)save[100]^=0x5a;
let checksum=2166136261;
for(const byte of save.subarray(0,save.length-4))checksum=Math.imul(checksum^byte,16777619)>>>0;
new DataView(save.buffer).setUint32(save.length-4,checksum,true);
assert.equal(withBytes(save,(p,n)=>m._web_save_restore(p,n)),1,'edited flash accepted');
let saved=m._web_save();assert.deepEqual(m.HEAPU8.slice(saved,saved+save.length),save,'flash bytes restored');
const bad=save.slice();bad[40]^=1;
assert.equal(withBytes(bad,(p,n)=>m._web_save_restore(p,n)),0,'corruption rejected');
assert.equal(withBytes(save.subarray(1),(p,n)=>m._web_save_restore(p,n)),0,'truncation rejected');
saved=m._web_save();assert.deepEqual(m.HEAPU8.slice(saved,saved+save.length),save,'rejected file leaves data intact');
m._web_reset();
const s=m._web_save();assert.deepEqual(m.HEAPU8.slice(s,s+save.length),save,'reset preserves flash and RTC');
m._web_close();assert.equal(withBytes(rom,(p,n)=>m._web_load(p,n)),1);
assert.equal(withBytes(save,(p,n)=>m._web_save_restore(p,n)),1,'save survives recreation');
const other=rom.slice();other[0x24]^=1;withBytes(other,(p,n)=>m._web_load(p,n));
assert.equal(withBytes(save,(p,n)=>m._web_save_restore(p,n)),0,'other ROM rejected');
m._web_close();
console.log(JSON.stringify({frames:600,elapsed_ms:Math.round(performance.now()-start),audio_frames:audio,nonzero_audio_samples:nonzero,distinct_images:images.size,lastHash,save_bytes:save.length,flash_mutation_test:flashMutation}));
