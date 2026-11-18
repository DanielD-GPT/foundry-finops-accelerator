# Deployment guide

## New Foundry

Leave `EXISTING_FOUNDRY_NAME` empty. Set `DEPLOY_SAMPLE_MODEL=true` only after checking model quota and accepting model charges. The default is `false`.

## Existing Foundry

Set both `EXISTING_FOUNDRY_NAME` and `EXISTING_FOUNDRY_RESOURCE_GROUP`. The resource must be in the selected subscription. The accelerator adds diagnostic settings but does not change existing model deployments.

## Environments

`development` uses 30-day Log Analytics retention, LRS storage, and up to ten 512 MB Function instances. `production` uses 90-day retention, ZRS, Grafana zone redundancy, and up to twenty Function instances.

Run `scripts/validate.ps1` before provisioning. `scripts/deploy.ps1` performs validation, `azd provision`, `azd deploy`, and post-provision dashboard setup. Azure operations use the signed-in identity and do not store credentials.

Cost Management export creation is subscription scoped. The Function processes gzip or plain CSV files and records completed blob names in `state/processed.json`.
