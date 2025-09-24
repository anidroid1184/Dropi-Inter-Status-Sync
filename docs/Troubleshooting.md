# Troubleshooting / Resolución de problemas

## Playwright fails to launch / Playwright no inicia
- Ensure Chromium is installed via `python -m playwright install chromium`.
- On Linux, avoid `playwright install-deps` on unsupported distros; use `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1` if needed.

## Many blank results / Muchos resultados vacíos
- Increase `--timeout-ms`.
- Reduce `--max-concurrency` and add `--rps 0.6`.
- Set `HEADLESS=false` and `BLOCK_RESOURCES=false` to observe UI and iframes.
- Check logs and HTML/PNG under `logs/` for the failing guide.

## Google Sheets 429/quota
- Writes are chunked and retried with backoff. If persistent, reduce batch sizes and rerun later.

## Credentials errors / Errores de credenciales
- Ensure `credentials.json` is at project root or `GOOGLE_APPLICATION_CREDENTIALS` points to it.

## Mappings not applied / Mapeos no aplicados
- Verify paths for `DROPI_MAP_PATH` and `INTER_MAP_PATH` and that JSON is valid.
- Use `TrackerService.explain_normalization` to see which rule matched.
