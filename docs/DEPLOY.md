# Deploying the API (api.threebabybirdies.com)

One command from your PC updates the API on the Hostinger VPS, checks that it is healthy, and can undo
it. Nobody needs to type commands on the server. (Same setup as the ODA CRM.)

```
node scripts/deploy.mjs release
```

You need **Node.js** (18 or newer) and **Git for Windows** (which brings `ssh`) on the PC.
The website has its own script and guide: `mamabird-website/docs/DEPLOY.md`. The same SSH key works for both.

## One-time setup

**1. SSH key.** If you made `threebabybirdies_deploy` for the website, reuse it. If not, in PowerShell:

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\threebabybirdies_deploy -C "threebabybirdies deploy" -N '""'
Get-Content $env:USERPROFILE\.ssh\threebabybirdies_deploy.pub | Set-Clipboard
```

**2. Let the key in on the VPS.** hPanel → your VPS → **Settings → SSH keys** → add the key you copied.

**3. Settings.** Copy `.env.deploy.example` to `.env.deploy` (never committed). Fill in `SSH_HOST` (the
VPS IP), `SSH_USER`, `SSH_PORT` and `SSH_KEY`.

**4. Find out how the API runs** (this changes nothing):

```
node scripts/deploy.mjs check
```

It lists the running uvicorn process and the folder it runs in, any systemd, pm2 or docker service, and the
web-server config for `api.threebabybirdies.com`. Copy what it shows into `.env.deploy`:
- `APP_DIR`: the folder the uvicorn process runs in (it holds `app/`, `requirements.txt` and `.env`).
- `SERVICE`: the systemd service name. If it runs under pm2, set `RESTART_CMD` and `LOGS_CMD` instead.
- `VENV`: only if the Python environment is not `APP_DIR/venv`.

Run `check` again. It should now say that `.env` and the Python environment are present.

**If the API runs some other way** (for example in a `screen` session started by hand), it won't survive a
reboot. Set it up as a systemd service first. Ask Claude, and it will write the unit file.

## Releasing

1. Commit your change in `backend/`. **Only the last commit is uploaded.**
2. `node scripts/deploy.mjs release`

`release` does all of the following:
1. Refuses to run if `APP_DIR` has no `.env`, in case it's the wrong folder.
2. Backs up the current code to `~/backups` on the VPS (no `.env`, no venv; the newest 15 are kept).
3. Uploads the commit's `backend/` folder, and removes files that the previous release had but this one
   doesn't.
4. Installs the packages from `requirements.txt` and **test-imports the app before restarting**. If the
   new code doesn't start, it puts the old code back without restarting, so the API never goes down
   because of a bad release.
5. Restarts the API and waits for `/health` to answer.

The server's `.env` (API keys) is never uploaded, overwritten or printed.

## Every command

| Command | What it does |
|---|---|
| `check` | Shows the server, Python, the app folder and how the API is run. Changes nothing. |
| `release` | Backup, upload, install, test-import, restart, health check. |
| `health` | Checks `/health`. |
| `logs [lines]` | Shows the API's recent log (100 lines by default). |
| `restart` | Restarts the API without uploading anything. |
| `backups` | Lists the code backups. |
| `rollback` | Puts the code from before the last release back, then restarts. |

## Database changes

The database is Supabase. The SQL files in `backend/migrations/` are run by hand in the Supabase SQL
editor; this script does not run them. Run a new migration **before** releasing code that needs it.
