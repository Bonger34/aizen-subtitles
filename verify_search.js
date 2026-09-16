// verify_search.js — 用 node 模拟前端搜索, 验证数据可用性与帧文件存在
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const BASE = 'D:/Bonger/Desktop/2026-08-21-18-21-50/VV_Rob/docs';
// 1. 加载 frames_map
global.window = {};
require(path.join(BASE, 'frames_map.js'));
const FMAP = window.FRAMES_MAP;
console.log('frames_map 键数', Object.keys(FMAP).length);

// 2. 加载 subtitle_db(gzip JSON)
const raw = zlib.gunzipSync(fs.readFileSync(path.join(BASE, 'subtitle_db')));
const db = JSON.parse(raw.toString('utf8'));
console.log('subtitle_db 条数', db.length);
console.log('示例', JSON.stringify(db[0]));

// 3. 模拟搜索
const queries = ['爱染', '罗布水晶', '波源', '寿喜锅', '朝阳'];
let missFrame = 0, hit = 0;
for (const q of queries) {
  const res = db.filter(r => r.x && r.x.includes(q));
  const withFrame = res.filter(r => {
    const key = `${r.f}|${r.t}`;
    const fn = FMAP[key];
    if (!fn) return false;
    return fs.existsSync(path.join(BASE, 'frames', fn));
  });
  hit += withFrame.length;
  const missing = res.length - withFrame.length;
  missFrame += missing;
  console.log(`搜索"${q}": ${res.length} 条, 有帧 ${withFrame.length}${missing ? ` (缺帧 ${missing})` : ''}`);
  if (withFrame.length) {
    const s = withFrame[0];
    console.log(`   例: ${s.f} ${s.t} [${s.x}] -> ${FMAP[s.f + '|' + s.t]}`);
  }
}
console.log(`\n合计命中 ${hit} 条, 缺帧 ${missFrame} 条`);
