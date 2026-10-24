import * as THREE from 'three';
import {OrbitControls} from '/vendor/OrbitControls.js';
import {mergeGeometries} from '/vendor/BufferGeometryUtils.js';

const $ = id => document.getElementById(id);
const viewport = $('viewport');
const nodes = new Map();
const frames = [];
let latest = null, clockOffset = null, follow = true, lastReceived = 0;
let received = 0, rendered = 0, meterStart = performance.now();

async function getJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.json();
}

async function meshGeometry(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Mesh download failed: ${response.status}`);
  const buffer = await response.arrayBuffer();
  const header = new DataView(buffer);
  const vertices = header.getUint32(0, true), faces = header.getUint32(4, true);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(buffer, 8, vertices * 3), 3));
  geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer, 8 + vertices * 12, faces * 3), 1));
  geometry.computeVertexNormals();
  geometry.computeBoundingSphere();
  return geometry;
}

function primitive(kind, size) {
  const [x, y, z] = size;
  switch (kind) {
    case 'box': return new THREE.BoxGeometry(2*x, 2*y, 2*z);
    case 'plane': return new THREE.PlaneGeometry(2*(x||8), 2*(y||8));
    case 'sphere': return new THREE.SphereGeometry(x, 16, 12);
    case 'ellipsoid': return new THREE.SphereGeometry(1, 16, 12).scale(x, y, z);
    case 'capsule': return new THREE.CapsuleGeometry(x, 2*y, 4, 12).rotateX(Math.PI/2);
    case 'cylinder': return new THREE.CylinderGeometry(x, x, 2*y, 16).rotateX(Math.PI/2);
    default: throw new Error(`Unsupported geometry: ${kind}`);
  }
}

function status(state) {
  $('phase').textContent = state.active_crop ? `${state.phase} · ${state.active_crop}` : state.phase;
  $('box').textContent = `Collection box: ${state.box_count||0} / 3`;
  $('cycle').textContent = `Cycle ${state.cycle||1} · continuous harvest`;
  $('progress').max = state.duration||72;
  $('progress').value = state.elapsed||0;
  const signature = JSON.stringify(state.tasks);
  if ($('tasks').dataset.signature !== signature) {
    $('tasks').dataset.signature = signature;
    $('tasks').replaceChildren(...(state.tasks||[]).map(task => {
      const li = document.createElement('li');
      li.textContent = `Bed ${task.bed+1} · ${task.crop} · ${task.status==='complete'?'harvested':task.status}`;
      return li;
    }));
  }
}

function receive(state) {
  if (!Number.isFinite(state.total_elapsed) || !state.transforms) return;
  const now = performance.now()/1000;
  if (clockOffset === null || (latest && state.total_elapsed < latest.total_elapsed)) {
    frames.length = 0;
    clockOffset = now-state.total_elapsed;
  }
  // Correct accumulated network delay without advancing beyond the server clock.
  clockOffset = Math.min(clockOffset, now-state.total_elapsed);
  frames.push(state);
  if (frames.length > 12) frames.shift();
  latest = state;
  lastReceived = now;
  received++;
  status(state);
}

async function start() {
  const renderer = new THREE.WebGLRenderer({antialias:true, powerPreference:'high-performance'});
  let renderScale = Math.min(devicePixelRatio, 1.25), slowWindows = 0;
  renderer.setPixelRatio(renderScale);
  const gl=renderer.getContext(), debug=gl.getExtension('WEBGL_debug_renderer_info');
  $('performance').dataset.renderer=debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  viewport.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#182820');
  scene.add(new THREE.HemisphereLight(0xe8f6ff, 0x586b3a, 1.4));
  const sunlight = new THREE.DirectionalLight(0xfff2d9, 2);
  sunlight.position.set(3, 1, 7);
  scene.add(sunlight);
  const camera = new THREE.PerspectiveCamera(45, 1, .01, 100);
  camera.up.set(0, 0, 1);
  camera.position.set(4, 5, 4);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.minDistance = .35;
  controls.maxDistance = 15;
  controls.maxPolarAngle = Math.PI*.49;
  controls.target.set(0, 0, .2);
  const setFollow = value => {
    follow = value;
    $('follow').setAttribute('aria-pressed', String(value));
    $('overview').setAttribute('aria-pressed', String(!value));
  };
  controls.addEventListener('start', () => setFollow(false));
  $('follow').onclick = () => setFollow(true);
  $('overview').onclick = () => {
    setFollow(false);
    camera.position.set(4, 5, 4);
    controls.target.set(0, 0, .2);
    controls.update();
  };
  new ResizeObserver(() => {
    const width = viewport.clientWidth, height = viewport.clientHeight;
    renderer.setSize(width, height);
    camera.aspect = width/height;
    camera.updateProjectionMatrix();
  }).observe(viewport);
  const description = await getJSON('/api/scene');
  const meshes = new Map();
  const entries = Object.entries(description.meshes);
  let cursor = 0;
  await Promise.all(Array.from({length:Math.min(6, entries.length)}, async () => {
    while (cursor < entries.length) {
      const [id, url] = entries[cursor++];
      meshes.set(Number(id), await meshGeometry(url));
      $('loading').textContent = `Loading robot meshes… ${meshes.size}/${entries.length}`;
    }
  }));
  const materials = new Map();
  const staticGroups = new Map();
  for (const item of description.geometries) {
    const key = item.rgba.join(',');
    if (!materials.has(key)) materials.set(key, new THREE.MeshLambertMaterial({
      color:new THREE.Color().setRGB(...item.rgba.slice(0,3),THREE.SRGBColorSpace), opacity:item.rgba[3],
      transparent:item.rgba[3]<1, side:THREE.DoubleSide,
    }));
    const geometry = item.kind==='mesh' ? meshes.get(item.mesh) : primitive(item.kind, item.size);
    const object = new THREE.Mesh(geometry, materials.get(key));
    object.position.fromArray(item.position);
    object.quaternion.fromArray(item.quaternion);
    object.name = `geom-${item.id}`;
    if (item.dynamic) {
      scene.add(object);
      nodes.set(item.id, object);
    } else {
      object.updateMatrix();
      const baked = (geometry.index ? geometry.toNonIndexed() : geometry.clone()).applyMatrix4(object.matrix);
      baked.deleteAttribute('uv');
      if (!staticGroups.has(key)) staticGroups.set(key, []);
      staticGroups.get(key).push(baked);
    }
  }
  // Batch the stationary plants/soil/bed walls instead of issuing a draw per leaf.
  for (const [key, geometries] of staticGroups) {
    scene.add(new THREE.Mesh(mergeGeometries(geometries), materials.get(key)));
    geometries.forEach(geometry => geometry.dispose());
  }
  receive(await getJSON('/api/state'));
  $('loading').style.display = 'none';
  const events = new EventSource('/api/events');
  events.onmessage = event => {
    try { receive(JSON.parse(event.data)); }
    catch (error) { console.error('Invalid mission state', error); }
  };
  events.onerror = () => { $('connection').textContent = 'Reconnecting to mission…'; };
  window.addEventListener('pagehide', () => events.close(), {once:true});
  const p0 = new THREE.Vector3(), p1 = new THREE.Vector3();
  const q0 = new THREE.Quaternion(), q1 = new THREE.Quaternion();
  const focus = new THREE.Vector3(), destination = new THREE.Vector3();
  let previousTime = performance.now();
  function animate(now) {
    requestAnimationFrame(animate);
    const dt = Math.min((now-previousTime)/1000, .1);
    previousTime = now;
    if (frames.length) {
      // 100 ms interpolation buffer smooths 30 Hz state updates at display refresh rate.
      const targetTime = now/1000-clockOffset-.1;
      while (frames.length>2 && frames[1].total_elapsed<=targetTime) frames.shift();
      const a = frames[0], b = frames[1]||a;
      const span = b.total_elapsed-a.total_elapsed;
      const blend = span>0 ? THREE.MathUtils.clamp((targetTime-a.total_elapsed)/span,0,1) : 1;
      const reset = a.cycle!==b.cycle;
      for (let i=0; i<a.transforms.length; i++) {
        const x=a.transforms[i], y=b.transforms[i];
        if (!y || x[0]!==y[0]) continue;
        const object=nodes.get(x[0]);
        p0.fromArray(x,1); p1.fromArray(y,1);
        q0.fromArray(x,4); q1.fromArray(y,4);
        // Produce resets at cycle boundaries rather than flying backward into beds.
        const t=reset ? (blend<1?0:1) : blend;
        object.position.copy(p0).lerp(p1,t);
        object.quaternion.copy(q0).slerp(q1,t);
      }
      if (follow) {
        if (b.active_bed!==null) {
          focus.fromArray(a.focus).lerp(p1.fromArray(b.focus),blend);
          destination.copy(focus).add(p0.set(1.05,1.2,.9));
        } else {
          focus.set(0,0,.2);
          destination.set(4,5,4);
        }
        const ease=1-Math.exp(-3*dt);
        controls.target.lerp(focus,ease);
        camera.position.lerp(destination,ease);
      }
    }
    controls.update();
    renderer.render(scene,camera);
    rendered++;
    if (now-meterStart>=1000) {
      const seconds=(now-meterStart)/1000;
      const fps=rendered/seconds;
      slowWindows=fps<25?slowWindows+1:0;
      if (slowWindows>=3 && renderScale>.5) {
        renderScale=Math.max(.5,renderScale*.75);
        renderer.setPixelRatio(renderScale);
        slowWindows=0;
      }
      $('performance').textContent=`${Math.round(fps)} FPS · ${Math.round(received/seconds)} pose updates/s · ${Math.round(renderScale*100)}% render scale`;
      $('connection').textContent=now/1000-lastReceived<2?'Live · browser rendering':'Waiting for fresh poses…';
      meterStart=now; rendered=0; received=0;
    }
  }
  requestAnimationFrame(animate);
}

start().catch(error => {
  console.error(error);
  $('loading').textContent=`Unable to start 3D viewer: ${error.message}. Check WebGL support and reload.`;
});
