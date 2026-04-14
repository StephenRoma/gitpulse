## GitHub Copilot Chat

- Extension: 0.41.2 (prod)
- VS Code: 1.113.0 (cfbea10c5ffb233ea9177d34726e6056e89913dc)
- OS: win32 10.0.26200 x64
- GitHub Account: StephenRoma

## Network

User Settings:
```json
  "http.systemCertificatesNode": true,
  "github.copilot.advanced.debug.useElectronFetcher": true,
  "github.copilot.advanced.debug.useNodeFetcher": false,
  "github.copilot.advanced.debug.useNodeFetchFetcher": true
```

Connecting to https://api.github.com:
- DNS ipv4 Lookup: 140.82.112.6 (6 ms)
- DNS ipv6 Lookup: Error (33 ms): getaddrinfo ENOTFOUND api.github.com
- Proxy URL: None (1 ms)
- Electron fetch (configured): HTTP 200 (66 ms)
- Node.js https: HTTP 200 (112 ms)
- Node.js fetch: HTTP 200 (34 ms)

Connecting to https://api.githubcopilot.com/_ping:
- DNS ipv4 Lookup: 140.82.114.21 (33 ms)
- DNS ipv6 Lookup: Error (30 ms): getaddrinfo ENOTFOUND api.githubcopilot.com
- Proxy URL: None (1 ms)
- Electron fetch (configured): HTTP 200 (123 ms)
- Node.js https: HTTP 200 (124 ms)
- Node.js fetch: HTTP 200 (135 ms)

Connecting to https://copilot-proxy.githubusercontent.com/_ping:
- DNS ipv4 Lookup: 4.249.131.160 (40 ms)
- DNS ipv6 Lookup: Error (31 ms): getaddrinfo ENOTFOUND copilot-proxy.githubusercontent.com
- Proxy URL: None (1 ms)
- Electron fetch (configured): HTTP 200 (219 ms)
- Node.js https: HTTP 200 (242 ms)
- Node.js fetch: HTTP 200 (202 ms)

Connecting to https://mobile.events.data.microsoft.com: HTTP 404 (54 ms)
Connecting to https://dc.services.visualstudio.com: HTTP 404 (502 ms)
Connecting to https://copilot-telemetry.githubusercontent.com/_ping: HTTP 200 (150 ms)
Connecting to https://copilot-telemetry.githubusercontent.com/_ping: HTTP 200 (147 ms)
Connecting to https://default.exp-tas.com: HTTP 400 (136 ms)

Number of system certificates: 80

## Documentation

In corporate networks: [Troubleshooting firewall settings for GitHub Copilot](https://docs.github.com/en/copilot/troubleshooting-github-copilot/troubleshooting-firewall-settings-for-github-copilot).