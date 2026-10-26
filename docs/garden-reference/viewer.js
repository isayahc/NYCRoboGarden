/** Display the existing adapter's portable OI mesh with separate GIS annotations. */
import * as THREE from 'three';
import {OrbitControls} from '../../simulation/vendor/OrbitControls.js';

const $ = id => document.getElementById(id);
const packageRoot = '../../data/scenes/st-nicholas-boundary/';

/** Fetch a retained JSON artifact and report HTTP failures explicitly. */
async function getJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

/** Make a readable annotation; labels do not represent physical objects. */
function label(text, position, color = '#cbe8d3') {
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 80;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = color; ctx.font = 'bold 42px system-ui';
  ctx.textAlign = 'center'; ctx.fillText(text, 128, 56);
  const material = new THREE.SpriteMaterial({map: new THREE.CanvasTexture(canvas), depthTest: false});
  const sprite = new THREE.Sprite(material);
  sprite.position.fromArray(position); sprite.scale.set(4, 1.25, 1);
  return sprite;
}

/** Load actual native scene buffers; never author garden interiors in the viewer. */
async function start() {
  const [portable, metadata, overlays, validation] = await Promise.all([
    getJSON(packageRoot + 'garden.oi.json'), getJSON(packageRoot + 'garden-georeference.json'),
    getJSON(packageRoot + 'reference-overlays.json'), getJSON('../garden-layout-validation.json'),
  ]);
  if (portable.format !== 'astra.scene' || portable.units !== 'm' || portable.upAxis !== 'Y' ||
      portable.instances.length !== 1 || metadata.source.record_id !== 'nyc-greenthumb:M394-GT001') {
    throw new Error('Unexpected reference scene; refusing to display an unreviewed layout.');
  }
  $('area').textContent = validation.geodesic_area_m2.toFixed(2) + ' m²';
  $('separation').textContent = validation.parcel_comparisons[0].hausdorff_distance_m.toFixed(2);
  const renderer = new THREE.WebGLRenderer({antialias: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  $('viewport').append(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#14251f');
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 300);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.minDistance = 8; controls.maxDistance = 100;
  controls.maxPolarAngle = Math.PI * .49;
  const grid = new THREE.GridHelper(70, 14, '#355b43', '#284332');
  grid.position.y = -.02; scene.add(grid);
  const item = portable.instances[0];
  const asset = portable.bundledAssets.find(a => a.id === item.assetId);
  const part = asset.parts[0];
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(part.vertices, 3));
  geometry.setIndex(part.indices); geometry.computeVertexNormals();
  const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({color: '#51845c', side: THREE.DoubleSide}));
  mesh.position.fromArray(item.position);
  mesh.rotation.set(...item.rotation.map(THREE.MathUtils.degToRad));
  scene.add(mesh);
  const outline = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({color: '#b5e4a5'}));
  outline.position.copy(mesh.position); outline.position.y += .03; scene.add(outline);
  for (let i = 0; i < part.vertices.length; i += 3) {
    const point = [part.vertices[i] + item.position[0], .15, part.vertices[i + 2] + item.position[2]];
    scene.add(label(String.fromCharCode(65 + i / 3), [point[0] - .7, .3, point[2] - .7]));
  }
  const parcel = new THREE.Group();
  for (const ring of overlays.parcel_rings_local_m) {
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(ring.map(p => new THREE.Vector3(p[0], .08, p[2]))),
      new THREE.LineDashedMaterial({color: '#efb86e', dashSize: .65, gapSize: .35}));
    line.computeLineDistances(); parcel.add(line);
  }
  scene.add(parcel);
  const pinGroup = new THREE.Group();
  const p = overlays.website_pin_local_m;
  const pin = new THREE.Mesh(new THREE.SphereGeometry(.4, 12, 8), new THREE.MeshBasicMaterial({color: '#f2a4a0'}));
  pin.position.set(p[0], .4, p[2]); pinGroup.add(pin);
  pinGroup.add(label('Website pin', [p[0], 1.2, p[2] - 1.4], '#f2a4a0'));
  pinGroup.visible = false; scene.add(pinGroup);
  scene.add(new THREE.ArrowHelper(new THREE.Vector3(0, 0, -1), new THREE.Vector3(12, .1, -5), 5, 0xcbe8d3, 1, .6));
  scene.add(label('N', [12, .2, -12]));
  scene.add(label('5 m grid', [11, .2, 10], '#90ad97'));
  const setView = mode => {
    camera.up.set(0, 1, 0);
    controls.target.set(0, 0, 0);
    const distance = Math.max(49, 45 / camera.aspect);
    camera.position.set(...(mode === 'plan' ? [0, distance, .01] : [24, 28, 30]));
    controls.update();
    $('plan').setAttribute('aria-pressed', String(mode === 'plan'));
    $('orbit').setAttribute('aria-pressed', String(mode === 'orbit'));
    renderer.render(scene, camera);
  };
  $('plan').onclick = () => setView('plan'); $('orbit').onclick = () => setView('orbit');
  $('reset').onclick = () => { $('parcel').checked = true; $('website').checked = false; parcel.visible = true; pinGroup.visible = false; setView('plan'); };
  $('parcel').onchange = () => { parcel.visible = $('parcel').checked; renderer.render(scene, camera); };
  $('website').onchange = () => {
    pinGroup.visible = $('website').checked;
    if (pinGroup.visible) { camera.position.set(-8, 76, .01); controls.target.set(-8, 0, -4); controls.update(); }
    renderer.render(scene, camera);
  };
  controls.addEventListener('change', () => renderer.render(scene, camera));
  new ResizeObserver(() => {
    const {clientWidth: width, clientHeight: height} = $('viewport');
    renderer.setSize(width, height); camera.aspect = width / height; camera.updateProjectionMatrix();
    setView($('orbit').getAttribute('aria-pressed') === 'true' ? 'orbit' : 'plan');
  }).observe($('viewport'));
  const raycaster = new THREE.Raycaster();
  renderer.domElement.addEventListener('pointerup', event => {
    const rect = renderer.domElement.getBoundingClientRect();
    raycaster.setFromCamera(new THREE.Vector2(2 * (event.clientX - rect.left) / rect.width - 1,
      1 - 2 * (event.clientY - rect.top) / rect.height), camera);
    if (raycaster.intersectObject(mesh).length) {
      $('selection').textContent = 'NYC Parks source-backed outline · inferred flat LOD0 surface · observation date unknown.';
    }
  });
  $('selection').textContent = 'Four municipal corners preserved. Interior measurements and operator review are pending.';
  $('viewport').dataset.loaded = 'true';
  setView('plan');
}

start().catch(error => { $('selection').textContent = 'Reference unavailable: ' + error.message; $('selection').classList.add('error'); });
