#!/usr/bin/env python3

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path

from gbre_common import find_source_line, load_manifest


STATUS_CODES = {
    'unknown': 'u',
    'analyzing': 'a',
    'documented': 'd',
    'implementing': 'i',
    'ported': 'p',
    'verified': 'v',
    'excluded': 'x',
    'not_runtime': 'n',
}


def read_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(newline='') as source:
        for item in csv.DictReader(source):
            rows.append(
                {
                    's': int(item['start'], 16),
                    'e': int(item['end_exclusive'], 16),
                    'section': item['section'],
                    'symbol': item['symbol'],
                    'file': item['source_file'],
                    'line': int(item['source_line']) if item['source_line'] else 0,
                    'text': item['source_text'],
                    'unit': item['unit_id'],
                    'relationship': item['relationship'],
                    'mappingConfidence': item['mapping_confidence'],
                    'claim': item['claim'],
                    'status': item['status'],
                    'native': item['native_location'],
                    'notes': item['notes'],
                }
            )
    return rows


def coverage_string(rows: list[dict], rom_size: int) -> str:
    coverage = ['u'] * rom_size
    for row in rows:
        code = STATUS_CODES.get(row['status'], 'u')
        coverage[row['s']:row['e']] = [code] * (row['e'] - row['s'])
    return ''.join(coverage)


def native_targets(manifest, repo_root: Path) -> dict[str, list[dict]]:
    result = {}
    for unit in manifest.units:
        targets = []
        for target in unit.native:
            path = (repo_root / target.path).resolve()
            targets.append(
                {
                    'path': path.as_posix(),
                    'line': find_source_line(path, target.anchor) if path.exists() else 0,
                    'anchor': target.anchor,
                }
            )
        result[unit.id] = targets
    return result


def verified_rom(path: Path, expected_sha1: str, expected_size: int) -> bytes:
    data = path.read_bytes()
    digest = hashlib.sha1(data).hexdigest()
    if len(data) != expected_size or digest != expected_sha1:
        raise ValueError(
            f'ROM mismatch: size={len(data)}, sha1={digest}; '
            f'expected size={expected_size}, sha1={expected_sha1}'
        )
    return data


def script_json(value) -> str:
    return json.dumps(value, separators=(',', ':')).replace('<', '\\u003c')


def build_html(manifest, rows, reference_root: Path, repo_root: Path, rom_path: Path, rom: bytes) -> str:
    totals = {code: 0 for code in STATUS_CODES.values()}
    relationship_totals = {}
    for row in rows:
        code = STATUS_CODES.get(row['status'], 'u')
        totals[code] += row['e'] - row['s']
        relationship = row['relationship'] or (
            'not_runtime' if row['status'] == 'not_runtime' else 'unmapped'
        )
        relationship_totals[relationship] = (
            relationship_totals.get(relationship, 0) + row['e'] - row['s']
        )
    units = [
        {
            'id': unit.id,
            'name': unit.name,
            'status': unit.native_status,
            'understanding': unit.understanding,
            'verification': unit.verification,
            'notes': unit.notes,
            'ranges': [
                {
                    'start': item.start,
                    'end': item.end,
                    'relationship': item.relationship,
                    'confidence': item.confidence,
                    'claim': item.claim,
                    'disposition': item.disposition,
                }
                for item in unit.rom_ranges
            ],
        }
        for unit in manifest.units
    ]
    data = {
        'title': manifest.title,
        'romSize': manifest.rom_size,
        'sha1': manifest.sha1,
        'rows': rows,
        'coverage': coverage_string(rows, manifest.rom_size),
        'hex': rom.hex().upper(),
        'units': units,
        'native': native_targets(manifest, repo_root),
        'referenceRoot': reference_root.resolve().as_posix(),
        'romPath': rom_path.resolve().as_posix(),
        'totals': totals,
        'relationshipTotals': relationship_totals,
    }
    payload = script_json(data)
    title = html.escape(manifest.title)
    return rf'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — GBRE map</title>
<style>
:root {{ color-scheme: dark; font-family: ui-monospace, monospace; background:#111318; color:#e8e8e8; }}
body {{ margin:0; padding:24px; max-width:1180px; }}
h1 {{ margin:0 0 4px; font-size:24px; }}
.muted {{ color:#959ba8; }}
.layout {{ display:grid; grid-template-columns:minmax(520px, 2fr) minmax(320px, 1fr); gap:20px; margin-top:20px; }}
.panel {{ background:#191c23; border:1px solid #303541; border-radius:8px; padding:16px; }}
canvas {{ width:768px; max-width:100%; aspect-ratio:2/1; image-rendering:pixelated; cursor:crosshair; background:#000; }}
.legend {{ display:flex; flex-wrap:wrap; gap:12px; margin:12px 0; font-size:12px; }}
.relationship-summary {{ margin:8px 0 14px; font-size:12px; }}
.swatch {{ display:inline-block; width:10px; height:10px; margin-right:5px; }}
input {{ box-sizing:border-box; width:100%; background:#101217; color:#fff; border:1px solid #3b4250; padding:9px; }}
pre {{ white-space:pre-wrap; overflow-wrap:anywhere; min-height:210px; font-size:12px; }}
a {{ color:#7cc7ff; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; margin-top:12px; }}
td,th {{ border-bottom:1px solid #303541; text-align:left; padding:7px 5px; vertical-align:top; }}
tr:hover {{ background:#222731; }}
button {{ background:none; color:#7cc7ff; border:0; padding:0; font:inherit; cursor:pointer; text-align:left; }}
@media(max-width:900px) {{ .layout {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="muted">32 KiB audit map · SHA-1 {manifest.sha1}</div>
<div class="layout">
  <section class="panel">
    <canvas id="map" width="256" height="128"></canvas>
    <div class="legend" id="legend"></div>
    <div class="muted relationship-summary" id="relationships"></div>
    <input id="query" placeholder="Jump to 0x2007, NextPiece, or tetris.next_piece">
    <table><thead><tr><th>Unit</th><th>ROM</th><th>Native</th><th>Verification</th></tr></thead><tbody id="units"></tbody></table>
  </section>
  <aside class="panel"><pre id="details">Click a byte in the map.</pre></aside>
</div>
<script>
const d={payload};
const colors={{u:'#343945',a:'#365b78',d:'#3c6e91',i:'#d18b35',p:'#62a86b',v:'#44d17a',x:'#76536d',n:'#111318'}};
const names={{u:'unknown',a:'analyzing',d:'documented',i:'implementing',p:'ported',v:'verified',x:'excluded',n:'not runtime'}};
const canvas=document.getElementById('map'),ctx=canvas.getContext('2d');
const image=ctx.createImageData(256,128);
let selectedRanges=[];
for(let i=0;i<d.coverage.length;i++){{
  const c=colors[d.coverage[i]], n=parseInt(c.slice(1),16), p=i*4;
  image.data[p]=(n>>16)&255; image.data[p+1]=(n>>8)&255; image.data[p+2]=n&255; image.data[p+3]=255;
}}
document.getElementById('legend').innerHTML=Object.entries(names).map(([k,v])=>
  `<span><i class="swatch" style="background:${{colors[k]}}"></i>${{v}} (${{d.totals[k]||0}})</span>`).join('')+
  `<span><i class="swatch" style="background:#00E5FF"></i>selected</span>`;
document.getElementById('relationships').textContent='relationships: '+
  Object.entries(d.relationshipTotals).map(([name,count])=>`${{name}}=${{count}}`).join(' · ');
function rowAt(address){{
  let lo=0,hi=d.rows.length-1;
  while(lo<=hi){{const m=(lo+hi)>>1,r=d.rows[m];if(address<r.s)hi=m-1;else if(address>=r.e)lo=m+1;else return r;}}
}}
function hex(n,w=4){{return '0x'+n.toString(16).toUpperCase().padStart(w,'0')}}
function vscode(path,line=0){{return encodeURI('vscode://file'+path+(line?':'+line:''));}}
function esc(value){{return String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}}
function drawMap(){{
  ctx.putImageData(image,0,0);
  ctx.fillStyle='#00E5FF';
  for(const [start,end] of selectedRanges){{
    for(let address=start;address<end;address++)
      ctx.fillRect(address%256,Math.floor(address/256),1,1);
  }}
}}
function show(address,ranges){{
  address=Math.max(0,Math.min(d.romSize-1,address)); const r=rowAt(address); if(!r)return;
  selectedRanges=ranges||[[r.s,r.e]];
  drawMap();
  const highlighted=selectedRanges.map(([start,end])=>`${{hex(start)}}–${{hex(end)}}`).join(', ');
  const from=Math.max(0,address-8),to=Math.min(d.romSize,address+16),bytes=[];
  for(let i=from;i<to;i++)bytes.push(d.hex.slice(i*2,i*2+2));
  const asm=r.file?`<a href="${{vscode(d.referenceRoot+'/'+r.file,r.line)}}">${{r.file}}:${{r.line}}</a>`:'none';
  const native=(d.native[r.unit]||[]).map(n=>`<a href="${{vscode(n.path,n.line)}}">${{esc(n.anchor)}}</a>`).join(', ')||'none';
  const rom=`<a href="${{vscode(d.romPath)}}">open ROM</a>`;
  document.getElementById('details').innerHTML=
`address: ${{hex(address)}}
span:    ${{hex(r.s)}}–${{hex(r.e)}} (${{r.e-r.s}} bytes)
highlight: ${{highlighted}}
section: ${{esc(r.section)}}
symbol:  ${{esc(r.symbol||'none')}}
unit:    ${{esc(r.unit||'none')}}
status:  ${{esc(r.status)}}
link:    ${{esc(r.relationship||'none')}} (${{esc(r.mappingConfidence||'none')}})
claim:   ${{esc(r.claim||'none')}}

assembly: ${{asm}}
native:   ${{native}}
binary:   ${{rom}}

${{esc(r.text||'')}}

${{hex(from)}}: ${{bytes.join(' ')}}

${{esc(r.notes||'')}}`;
}}
canvas.addEventListener('click',e=>{{const q=canvas.getBoundingClientRect();show(Math.floor((e.clientX-q.left)*256/q.width)+Math.floor((e.clientY-q.top)*128/q.height)*256);}});
function selectQuery(query){{
  query=String(query||'').trim();
  const number=query.match(/^(?:0x|\$)?([0-9a-f]+)$/i);
  if(number)return show(parseInt(number[1],16));
  const unit=d.units.find(u=>u.id.toLowerCase()===query.toLowerCase());
  if(unit)return show(unit.ranges[0].start,unit.ranges.map(r=>[r.start,r.end]));
  const row=d.rows.find(r=>r.symbol.toLowerCase()===query.toLowerCase()||r.symbol.toLowerCase().includes(query.toLowerCase()));
  if(row){{
    const unitRanges=d.units.find(u=>u.id===row.unit)?.ranges.map(r=>[r.start,r.end]);
    show(row.s,unitRanges);
  }}
}}
document.getElementById('query').addEventListener('change',e=>{{
  selectQuery(e.target.value);
}});
document.getElementById('units').innerHTML=d.units.map(u=>{{
  const ranges=u.ranges.map(r=>`${{hex(r.start)}}–${{hex(r.end)}} ${{r.relationship}}`).join('<br>');
  return `<tr><td><button onclick="selectQuery('${{u.id}}')">${{esc(u.id)}}</button><br><span class="muted">${{esc(u.notes)}}</span></td><td>${{ranges}}</td><td>${{esc(u.status)}}</td><td>${{esc(u.verification)}}</td></tr>`;
}}).join('');
show(0);
</script>
</body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description='Build a navigable GBRE coverage report')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--rom-map', type=Path, required=True)
    parser.add_argument('--reference-root', type=Path, required=True)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    rom = verified_rom(args.rom, manifest.sha1, manifest.rom_size)
    repo_root = manifest.path.parent.parent
    output = build_html(
        manifest, read_rows(args.rom_map), args.reference_root, repo_root, args.rom, rom
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output)
    print(f'Wrote navigable report to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
