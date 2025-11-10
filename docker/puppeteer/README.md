# Development

## Debugging using Visual Studio Code

In file `.vscode/launch.json`, add the following debug configuration:

```json
{
            "name": "Debug Puppeteer Server (with nodemon)",
            "type": "node",
            "request": "launch",
            "program": "${workspaceFolder}/docker/puppeteer/node_modules/.bin/nodemon",
            "args": ["server.js"],
            "cwd": "${workspaceFolder}/docker/puppeteer",
            "env": {
                "NODE_ENV": "development",
                "PORT": "3000",
                "BASE_URL": "http://localhost:8080"
            },
            "console": "integratedTerminal",
            "restart": true,
            "runtimeArgs": ["--inspect"],
            "skipFiles": [
                "<node_internals>/**"
            ]
        },
```

Then you can run server using VS Code on port 3000.

Now you need to instruct service `thinkhazard` to use new debug server.
In file `docker-compose.override.yaml` add:

```yaml
services:
  thinkhazard:
    environment:
      PUPPETEER_URL: 'http://localhost:3000'
```

Restart service `thinkhazard`:

```bash
docker compose up -d thinkhazard
```

Now you are ready for debugging the puppeteer server.
