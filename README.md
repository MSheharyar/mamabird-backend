# mamabird-backend
## Deploying

`node scripts/deploy.mjs release` uploads the last commit of `backend/` to the VPS, test-imports it, restarts the API and checks `/health`. Setup and every command: [docs/DEPLOY.md](docs/DEPLOY.md).
