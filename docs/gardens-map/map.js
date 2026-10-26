'use strict';
const $=id=>document.getElementById(id), NS='http://www.w3.org/2000/svg';
const svg=$('map');
const R=6378137, radians=Math.PI/180, originY=Math.log(Math.tan(Math.PI/4+40.7*radians/2));
const project=([lon,lat])=>[(lon+74)*radians*R,-R*(Math.log(Math.tan(Math.PI/4+lat*radians/2))-originY)];
let data, rows=[], filtered=[], boundaries=[], selected=null, cityBounds, view, drag=null;
const labelPositions={'Brooklyn':[-73.955,40.63],'Queens':[-73.81,40.735],'Manhattan':[-73.977,40.785],'Bronx':[-73.86,40.855],'Staten Island':[-74.15,40.585]};
const elements=new Map();

function element(tag,attributes){const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attributes))e.setAttribute(k,v);return e;}
function polygons(geometry){return geometry?geometry.type==='MultiPolygon'?geometry.coordinates:[geometry.coordinates]:[];}
function path(geometry){return polygons(geometry).map(p=>p.map(r=>r.map((c,i)=>`${i?'L':'M'}${project(c).map(n=>n.toFixed(1)).join(',')}`).join('')+'Z').join('')).join('');}
function bounds(points){return [Math.min(...points.map(p=>p[0])),Math.min(...points.map(p=>p[1])),Math.max(...points.map(p=>p[0])),Math.max(...points.map(p=>p[1]))];}
function geometryBounds(g){return bounds(polygons(g).flat(2).map(project));}
function screenScale(){return Math.max(view.w/svg.clientWidth,view.h/svg.clientHeight);}
function updateView(){
  svg.setAttribute('viewBox',`${view.x} ${view.y} ${view.w} ${view.h}`);
  const scale=screenScale();
  for(const marker of elements.values())marker.setAttribute('r',(marker.classList.contains('selected')?7:4)*scale);
  document.querySelectorAll('.borough-label').forEach(e=>e.setAttribute('font-size',12*scale));
}
function fit(b=cityBounds,minSpan=800){
  const aspect=Math.max(.2,svg.clientWidth/svg.clientHeight);
  let w=Math.max(minSpan,b[2]-b[0])*1.12,h=Math.max(minSpan,b[3]-b[1])*1.12;
  if(w/h<aspect)w=h*aspect;else h=w/aspect;
  view={x:(b[0]+b[2]-w)/2,y:(b[1]+b[3]-h)/2,w,h};updateView();
}
function mapPoint(clientX,clientY){return new DOMPoint(clientX,clientY).matrixTransform(svg.getScreenCTM().inverse());}
function zoom(factor,anchor){
  if(!view)return;
  const center=anchor||{x:view.x+view.w/2,y:view.y+view.h/2};
  const newW=Math.max(80,Math.min((cityBounds[2]-cityBounds[0])*3,view.w*factor));
  factor=newW/view.w;
  view={x:center.x+(view.x-center.x)*factor,y:center.y+(view.y-center.y)*factor,w:newW,h:view.h*factor};updateView();
}
function select(site,zoomIn=false){
  selected=site;
  window.showGardenResearch?.(site);
  $('details').hidden=false;
  $('site-name').textContent=site.name;
  $('site-address').textContent=site.address||'Address not provided';
  $('site-status').textContent=`${site.borough} · ${site.status} · ${site.id}`;
  $('site-coordinates').textContent=site.location?`${site.location[1].toFixed(6)}, ${site.location[0].toFixed(6)}`:'No valid coordinate in source';
  $('site-footprint').textContent=site.footprint?'Official garden footprint available; zoom in to view it. Interior beds and paths are not supplied by this dataset.':'No garden footprint supplied. This marker is a location, not a surveyed layout.';
  $('zoom-site').disabled=!site.location&&!site.footprint;
  $('footprint').replaceChildren();
  if(site.footprint)$('footprint').append(element('path',{d:path(site.footprint)}));
  for(const [key,node] of elements)node.classList.toggle('selected',key===site.key);
  document.querySelectorAll('.result').forEach(node=>node.classList.toggle('selected',node.dataset.key===site.key));
  updateView();
  if(zoomIn&&site.location){
    const [x,y]=project(site.location);
    // A gentle zoom on selection; never zoom back out when already close.
    const factor=view.w>1200?.65:1;
    view={x:x-view.w*factor/2,y:y-view.h*factor/2,w:view.w*factor,h:view.h*factor};
    updateView();
  }
}
function draw(refit=true){
  const query=$('search').value.trim().toLowerCase(),boro=$('borough').value,active=$('statusFilter').value;
  filtered=rows.filter(s=>(!boro||s.borough===boro)&&(!active||s.status.toLowerCase()===active.toLowerCase())&&(!query||`${s.name} ${s.address} ${s.id}`.toLowerCase().includes(query)));
  $('markers').replaceChildren();elements.clear();
  let mapped=0;
  for(const site of filtered){
    if(!site.location)continue;
    const [x,y]=project(site.location);
    const marker=element('circle',{cx:x,cy:y,r:1,class:`marker${site.status.toLowerCase()==='active'?'':' inactive'}`,tabindex:0,role:'button','aria-label':site.name});
    marker.addEventListener('click',()=>select(site,true));
    marker.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(site,true);}});
    marker.addEventListener('pointerenter',e=>{const tip=$('tooltip');tip.textContent=site.name;tip.hidden=false;const rect=$('map-wrap').getBoundingClientRect();tip.style.left=Math.min(e.clientX-rect.left+12,rect.width-240)+'px';tip.style.top=Math.max(0,e.clientY-rect.top-36)+'px';});
    marker.addEventListener('pointerleave',()=>{$('tooltip').hidden=true;});
    $('markers').append(marker);elements.set(site.key,marker);mapped++;
  }
  const missing=filtered.length-mapped;
  $('count').textContent=`${mapped} mapped / ${filtered.length} matching records${missing?` · ${missing} without coordinates`:''}`;
  $('map-status').textContent=`${boro||'All five boroughs'} · Drag to pan · Scroll to zoom`;
  $('results').replaceChildren(...filtered.slice(0,75).map(site=>{
    const button=document.createElement('button');button.className='result';button.dataset.key=site.key;
    const name=document.createElement('strong'),info=document.createElement('span');name.textContent=site.name;info.textContent=`${site.borough} · ${site.status}${site.location?'':' · no coordinate'}`;
    button.append(name,info);button.onclick=()=>select(site,true);return button;
  }));
  $('list-note').textContent=filtered.length>75?`Showing the first 75 results. Narrow your search to find a specific garden.`:filtered.length?'Select a garden or a map marker for details.':'No matching gardens. Try a different filter.';
  boundaries.forEach(b=>b.node.classList.toggle('dim',!!boro&&b.name!==boro));
  if(selected&&!filtered.includes(selected)){selected=null;$('details').hidden=true;$('footprint').replaceChildren();window.clearGardenResearch?.();}
  if(refit){
    if(query&&mapped){fit(bounds(filtered.filter(s=>s.location).map(s=>project(s.location))));}
    else if(boro){fit(boundaries.find(b=>b.name===boro).bounds);}
    else fit();
  }
  if(selected)select(selected);else updateView();
}

svg.addEventListener('wheel',e=>{if(!view)return;e.preventDefault();zoom(Math.exp(Math.max(-1,Math.min(1,e.deltaY/300))),mapPoint(e.clientX,e.clientY));},{passive:false});
svg.addEventListener('pointerdown',e=>{if(!view||e.target.classList.contains('marker'))return;drag={x:e.clientX,y:e.clientY,view:{...view}};svg.setPointerCapture(e.pointerId);svg.classList.add('dragging');});
svg.addEventListener('pointermove',e=>{if(!drag)return;const scale=screenScale();view.x=drag.view.x-(e.clientX-drag.x)*scale;view.y=drag.view.y-(e.clientY-drag.y)*scale;updateView();});
function endDrag(){drag=null;svg.classList.remove('dragging');}
svg.addEventListener('pointerup',endDrag);svg.addEventListener('pointercancel',endDrag);
$('zoom-in').onclick=()=>zoom(.7);$('zoom-out').onclick=()=>zoom(1/.7);$('fit-city').onclick=()=>{if(cityBounds)fit();};
$('zoom-site').onclick=()=>{if(!selected)return;if(selected.footprint)fit(geometryBounds(selected.footprint),120);else{const [x,y]=project(selected.location);fit([x-400,y-400,x+400,y+400]);}};
['borough','statusFilter'].forEach(id=>$(id).onchange=()=>{if(data)draw();});$('search').oninput=()=>{if(data)draw();};
$('reset').onclick=()=>{if(!data)return;$('borough').value='';$('statusFilter').value='';$('search').value='';selected=null;$('details').hidden=true;$('footprint').replaceChildren();window.clearGardenResearch?.();draw();};
new ResizeObserver(()=>{if(view)updateView();}).observe(svg);

async function start(){
  const response=await fetch('./map-data.json');if(!response.ok)throw Error(`Map data HTTP ${response.status}`);data=await response.json();
  rows=data.gardens.map((row,i)=>({...row,key:`${row.id}-${i}`}));
  $('total').textContent=data.record_count.toLocaleString();
  $('source-date').textContent=`Local data snapshot: ${new Date(data.retrieved_at).toLocaleDateString()}. Works without map tiles or third-party scripts.`;
  for(const borough of data.boroughs){const node=element('path',{d:path(borough.geometry),class:'borough'});$('boundaries').append(node);boundaries.push({name:borough.name,node,bounds:geometryBounds(borough.geometry)});const [x,y]=project(labelPositions[borough.name]);const label=element('text',{x,y,class:'borough-label'});label.textContent=borough.name.toUpperCase();$('labels').append(label);}
  cityBounds=bounds(boundaries.flatMap(b=>[[b.bounds[0],b.bounds[1]],[b.bounds[2],b.bounds[3]]]));
  if(['localhost','127.0.0.1','[::1]'].includes(location.hostname)){const url=new URL(location.href);url.port='8080';url.pathname='/';url.search='';url.hash='';$('demo-link').href=url.href;}else{$('demo-link').hidden=true;}
  draw();
  const requested=new URLSearchParams(location.search).get('garden');
  if(requested){const site=rows.find(row=>row.id===requested);if(site)select(site,true);}
}
start().catch(error=>{$('map-status').textContent=`Unable to load map: ${error.message}`;$('map-status').classList.add('error');$('total').textContent='Unavailable';});
