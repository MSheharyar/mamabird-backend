// Deploys the Mamabird API (backend/) to the Hostinger VPS over SSH, so nobody has to type commands on the
// server. Same pattern as the ODA CRM's scripts/deploy-godaddy.mjs.
//
// Settings come from .env.deploy in the repo folder (never committed; copy .env.deploy.example):
//   SSH_HOST, SSH_USER, SSH_PORT, SSH_KEY, APP_DIR, VENV, SERVICE, RESTART_CMD, LOGS_CMD, API_URL
// One-time setup (SSH key, finding how the API runs) is in docs/DEPLOY.md.
//
//   node scripts/deploy.mjs check            show the server, Python, the app folder and HOW the API is run (changes nothing)
//   node scripts/deploy.mjs release          back up the code, upload the committed backend/, install packages,
//                                            test-import the app, restart it, and check /health
//   node scripts/deploy.mjs health           check /health
//   node scripts/deploy.mjs logs [lines]     show the API's recent log
//   node scripts/deploy.mjs restart          restart the API (no upload)
//   node scripts/deploy.mjs backups          list the code backups
//   node scripts/deploy.mjs rollback         put the previous code back and restart (undo the last release)
//
// The server's .env (API keys) is never uploaded, overwritten or printed. What is uploaded is the last COMMIT
// (git HEAD), not whatever is lying in the folder. Commit first, then deploy.
import { spawnSync } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

const root = join(import.meta.dirname, '..');
const envFile = process.env.DEPLOY_ENV || join(root, '.env.deploy');
if (!existsSync(envFile)) fail(`Missing ${envFile}. Copy .env.deploy.example to .env.deploy and fill it in (see docs/DEPLOY.md).`);
const env = Object.fromEntries(readFileSync(envFile, 'utf8').split(/\r?\n/).filter((l) => /^\w+=/.test(l))
  .map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim()]));
if (!env.SSH_HOST || !env.SSH_USER) fail('Set SSH_HOST and SSH_USER in .env.deploy.');

const APP = env.APP_DIR || '';
const VENV = env.VENV || (APP ? `${APP}/venv` : '');
const API = (env.API_URL || 'https://api.threebabybirdies.com').replace(/\/$/, '');
const SUDO = env.SSH_USER === 'root' ? '' : 'sudo -n ';
const RESTART = env.RESTART_CMD || (env.SERVICE ? `${SUDO}systemctl restart ${env.SERVICE}` : '');
const LOGS = env.LOGS_CMD || (env.SERVICE ? `${SUDO}journalctl -u ${env.SERVICE} --no-pager -n` : '');
// Never replaced, deleted or backed up as code: secrets, the Python environment, runtime files.
const KEEP = ['.env', '.env.*', 'venv', '.venv', '__pycache__', 'logs', '*.log', ...(env.KEEP || '').split(',')].map((s) => s.trim()).filter(Boolean);

const gitSsh = 'C:\\Program Files\\Git\\usr\\bin\\ssh.exe';
const SSH = env.SSH_BIN || (existsSync(gitSsh) ? gitSsh : 'ssh');
const KEY = env.SSH_KEY || join(homedir(), '.ssh', 'threebabybirdies_deploy');
const q = (s) => `'${String(s).replace(/'/g, `'\\''`)}'`;
// A bash case pattern: the * stay wildcards, everything else is literal.
const pat = (k) => k.split('*').map((p) => (p ? q(p) : '')).join('*');

function fail(msg) { console.error(`\n${msg}\n`); process.exit(1); }
function needApp() { if (!APP) fail('Set APP_DIR in .env.deploy (run "check" to find it).'); }

function remote(script, input, { allowFail = false } = {}) {
  const b64 = Buffer.from(`set -e -o pipefail\ncd ~\n${script}`).toString('base64');
  const args = ['-i', KEY, '-p', env.SSH_PORT || '22', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new',
    '-o', 'ConnectTimeout=20', `${env.SSH_USER}@${env.SSH_HOST}`, `bash -c "$(echo ${b64} | base64 -d)"`];
  const r = spawnSync(SSH, args, { input, stdio: [input ? 'pipe' : 'ignore', 'inherit', 'inherit'], maxBuffer: 1 << 30 });
  if (r.error) fail(`Could not start ssh (${r.error.code}). On Windows, install Git for Windows (it brings ssh), or set SSH_BIN in .env.deploy.`);
  if (r.status === 255) fail('Could not sign in over SSH. Check SSH_HOST, SSH_USER, SSH_PORT and SSH_KEY in .env.deploy, and that the key is added on the VPS (docs/DEPLOY.md).');
  if (r.status !== 0 && !allowFail) fail(`Server step failed (exit ${r.status}). Nothing after this step was done.`);
  return r.status;
}

/** Code backup of APP_DIR (no .env, no venv) into ~/backups, newest 15 kept. */
const backupScript = () => `
mkdir -p ~/backups
B="$HOME/backups/api-code-$(date -u +%Y%m%d-%H%M%S)-$$.tar.gz"
tar -czf "$B" -C ${q(APP)} ${KEEP.map((k) => `--exclude=${q(k)}`).join(' ')} .
echo "Backed up the current code: $B"
ls -1t ~/backups/api-code-*.tar.gz | tail -n +16 | xargs -r rm -f
`;

/** Put the newest code backup back. */
const restoreScript = () => `
B="$(ls -1t ~/backups/api-code-*.tar.gz 2>/dev/null | head -1)"
[ -n "$B" ] || { echo "No code backup found."; exit 3; }
cd ${q(APP)}
for f in * .[!.]* ..?*; do
  [ -e "$f" ] || continue
  case "$f" in ${KEEP.map(pat).join('|')}) continue;; esac
  rm -rf -- "$f"
done
tar -xzf "$B"
rm -f ~/backups/api-manifest.txt
echo "Code restored from $(basename "$B")."
`;

// One && chain: bash ignores set -e inside an if condition, which is where release runs this.
const installAndTest = () => `
cd ${q(APP)} &&
{ [ -x ${q(VENV)}/bin/python ] || { echo "No Python environment at ${VENV} (set VENV in .env.deploy)."; false; }; } &&
echo "Installing packages (quick when nothing changed) …" &&
timeout 900 ${q(VENV)}/bin/pip install -q --disable-pip-version-check -r requirements.txt &&
echo "Test-importing the app …" &&
${q(VENV)}/bin/python -c "import app.main" &&
echo "  the app imports cleanly."
`;

// The restart command runs detached from this SSH session's output (and capped at 2 minutes), so a command
// that leaves a process holding the terminal cannot keep the session open forever. Its output is shown after.
const restartScript = () => `
echo "Restarting: ${RESTART.replace(/[`$\\"]/g, '\\$&')}"
mkdir -p ~/backups
if timeout 120 bash -c ${q(RESTART)} </dev/null >~/backups/restart.log 2>&1; then cat ~/backups/restart.log; else
  cat ~/backups/restart.log; echo "The restart command failed or took over 2 minutes."; exit 5; fi
`;

async function health(tries = 1) {
  for (let i = 1; i <= tries; i++) {
    try {
      const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(8000) });
      const body = await r.text();
      if (r.ok && body.includes('ok')) { console.log(`${API}/health: OK`); return true; }
      if (i === tries) console.log(`${API}/health answered ${r.status}: ${body.slice(0, 200)}`);
    } catch (e) {
      if (i === tries) console.log(`${API}/health did not answer: ${e.cause?.code || e.message}`);
    }
    if (i < tries) await new Promise((res) => setTimeout(res, 3000));
  }
  return false;
}

const cmd = process.argv[2];
if (cmd === 'check') {
  remote(`
echo "Signed in as $(whoami) on $(hostname), home $HOME"
echo "Python: $(python3 --version 2>&1)"
echo "Disk: $(df -h / | tail -1 | awk '{print $4" free of "$2}')"
${APP ? `echo "--- ${APP}/:"; ls -A ${q(APP)} 2>/dev/null || echo "(not found)"
[ -f ${q(APP)}/.env ] && echo "    .env present ($(grep -c '=' ${q(APP)}/.env) settings; not shown)" || echo "    NO .env in ${APP}"
[ -x ${q(VENV)}/bin/python ] && echo "    Python environment: ${VENV}" || echo "    NO Python environment at ${VENV}"` : 'echo "(APP_DIR not set yet; the clues below show where the API lives)"'}
echo "--- how the API is running (fill SERVICE / RESTART_CMD / APP_DIR from this):"
# (grep -v 'bash -c' leaves out this very script, whose text mentions uvicorn too)
PROCS="$(ps -eo pid,user,args 2>/dev/null | grep -iE '[u]vicorn|[g]unicorn' | grep -v 'bash -c' || true)"
if [ -z "$PROCS" ]; then echo "  no uvicorn/gunicorn process found"; else
  echo "$PROCS" | cut -c1-200
  for p in $(echo "$PROCS" | awk '{print $1}' | head -3); do echo "  pid $p runs in: $(readlink /proc/$p/cwd 2>/dev/null)"; done
fi
command -v systemctl >/dev/null && systemctl list-units --type=service --all --no-pager --plain 2>/dev/null | grep -iE 'uvicorn|gunicorn|mama|chirpy|api|fastapi|birdie' | awk '{print "  systemd service: "$1" ("$4")"}' || true
command -v pm2 >/dev/null && { echo "  pm2:"; pm2 jlist 2>/dev/null | grep -o '"name":"[^"]*"' | sort -u | sed 's/^/    /'; } || true
command -v docker >/dev/null && docker ps --format '  docker: {{.Names}} ({{.Image}})' 2>/dev/null || true
grep -rlis 'api.threebabybirdies.com' /etc/nginx /etc/apache2 /etc/caddy 2>/dev/null | sed 's/^/  web server config: /' || true
echo "--- code backups:"; ls -1t ~/backups/api-code-*.tar.gz 2>/dev/null | head -5 || echo "  (none yet)"
`);
} else if (cmd === 'release') {
  needApp();
  if (!RESTART) fail('Set SERVICE (or RESTART_CMD) in .env.deploy. Run "check" to see how the API is run.');
  const dirty = spawnSync('git', ['status', '--porcelain', '--', 'backend'], { cwd: root, encoding: 'utf8' }).stdout.trim();
  if (dirty) console.log('Note: backend/ has uncommitted changes. They are NOT uploaded; only the last commit is.\n');
  const exclude = [':(exclude).env', ':(exclude).env.*'];
  const tar = spawnSync('git', ['archive', '--format=tar.gz', 'HEAD:backend', '--', '.', ...exclude], { cwd: root, maxBuffer: 1 << 30 });
  if (tar.status !== 0) fail(`git archive failed: ${tar.stderr}`);
  const files = spawnSync('git', ['ls-tree', '-r', '--name-only', 'HEAD:backend'], { cwd: root, encoding: 'utf8' }).stdout.trim().split('\n')
    .filter((f) => !/^\.env(\.|$)/.test(f));
  if (!files.includes('app/main.py') || !files.includes('requirements.txt')) fail('This commit has no backend/app/main.py or requirements.txt; refusing to upload it.');
  const head = spawnSync('git', ['log', '-1', '--format=%h %s'], { cwd: root, encoding: 'utf8' }).stdout.trim();
  const manifest = Buffer.from(files.join('\n') + '\n').toString('base64');

  console.log(`Releasing ${head} (${files.length} files) to ${APP}/ …`);
  const status = remote(`
[ -f ${q(APP)}/.env ] || { echo "No .env in ${APP}: refusing to deploy to what may be the wrong folder."; exit 3; }
${backupScript()}
cd ${q(APP)}
M=~/backups/api-manifest.txt
echo ${manifest} | base64 -d > "$M.new"
tar -xzf -
# Files the previous release had and this one does not (first release: nothing is deleted).
# (grep finds nothing on most releases and returns 1; that is not a failure, hence the || true)
if [ -f "$M" ]; then
  { grep -vxFf "$M.new" "$M" || true; } | while IFS= read -r f; do if [ -f "$f" ]; then rm -f -- "$f"; echo "  removed $f"; fi; done
fi
mv "$M.new" "$M"
if ! ( ${installAndTest().trim().split('\n').join('\n  ')} ); then
  echo ""
  echo "The new code does not start, so it was NOT restarted; putting the previous code back."
  ${restoreScript().trim().split('\n').join('\n  ')}
  exit 4
fi
${restartScript()}`, tar.stdout, { allowFail: true });
  if (status === 4) fail('Release stopped before the restart. The API kept running the previous code, which is back in place.');
  if (status !== 0) fail(`Release failed on the server (exit ${status}). Check with: node scripts/deploy.mjs health`);
  console.log('Waiting for the API to come back …');
  if (!(await health(10))) fail('The API is not healthy after the restart. See: node scripts/deploy.mjs logs   Undo with: node scripts/deploy.mjs rollback');
  console.log('\nReleased.');
} else if (cmd === 'rollback') {
  needApp();
  if (!RESTART) fail('Set SERVICE (or RESTART_CMD) in .env.deploy.');
  remote(`${restoreScript()}\n${installAndTest()}\n${restartScript()}`);
  console.log('Waiting for the API to come back …');
  process.exit((await health(10)) ? 0 : 1);
} else if (cmd === 'restart') {
  if (!RESTART) fail('Set SERVICE (or RESTART_CMD) in .env.deploy.');
  remote(restartScript());
  process.exit((await health(10)) ? 0 : 1);
} else if (cmd === 'health') {
  process.exit((await health()) ? 0 : 1);
} else if (cmd === 'logs') {
  if (!LOGS) fail('Set SERVICE (or LOGS_CMD) in .env.deploy.');
  const n = /^\d+$/.test(process.argv[3] || '') ? process.argv[3] : '100';
  remote(`${LOGS} ${n}`);
} else if (cmd === 'backups') {
  remote('ls -1t ~/backups/api-code-*.tar.gz 2>/dev/null | xargs -r -n1 basename || echo "(none yet)"');
} else {
  console.log('Usage: node scripts/deploy.mjs check | release | health | logs [lines] | restart | backups | rollback');
}
