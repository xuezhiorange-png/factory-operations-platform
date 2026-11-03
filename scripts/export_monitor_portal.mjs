import { mkdir, readdir, readFile, writeFile, stat } from 'node:fs/promises';
import { resolve, relative, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const root = fileURLToPath(new URL('../', import.meta.url));
const destination = resolve(process.argv[2] || '');
if (!process.argv[2] || destination.startsWith(root)) throw new Error('Choose an empty external export directory');
try { await stat(destination); throw new Error('Export destination must not exist'); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const paths = [
  'src/integrations/monitor', 'src/modules/assets', 'src/modules/settings/people',
  'src/modules/identity/account.ts', 'src/shared/components', 'src/shared/composables',
  'src/shared/icons.ts', 'src/shared/types.ts', 'src/shared/contracts.ts',
  'src/shared/api-path.ts', 'src/app/features.ts',
];
const files = [];
async function copy(path) {
  const source = join(root, 'frontend', path);
  if ((await stat(source)).isDirectory()) {
    for (const name of (await readdir(source)).sort()) await copy(join(path, name));
  } else {
    const bytes = await readFile(source), output = join(destination, path);
    await mkdir(resolve(output, '..'), { recursive: true });
    await writeFile(output, bytes, { flag: 'wx' });
    files.push({ path, sha256: createHash('sha256').update(bytes).digest('hex') });
  }
}
for (const path of paths) await copy(path);
await writeFile(join(destination, 'package.json'), JSON.stringify({
  name: '@factory-operations/monitor-portal', version: '0.1.0', private: true, type: 'module',
  exports: { '.': './src/integrations/monitor/index.ts' },
  peerDependencies: { vue: '^3.5.0', 'vue-router': '^4.3.0', '@lucide/vue': '^1.49.0' },
}, null, 2) + '\n');
await writeFile(join(destination, 'SOURCE.json'), JSON.stringify({
  repository: 'https://github.com/xuezhiorange-png/factory-operations-platform',
  head: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  dirty: Boolean(execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' }).trim()),
  exportPath: relative(root, fileURLToPath(import.meta.url)), files,
}, null, 2) + '\n');
console.log(JSON.stringify({ destination, files: files.length }));
