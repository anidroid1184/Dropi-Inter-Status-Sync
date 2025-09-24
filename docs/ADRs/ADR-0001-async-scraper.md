# ADR-0001: Async Playwright Scraper with Concurrency / Scraper Playwright Asíncrono con Concurrencia

## Status / Estado
Accepted / Aceptada

## Context / Contexto
We must process thousands of tracking numbers reliably while controlling resource usage and avoiding anti-bot throttling. A synchronous scraper limits throughput and complicates resilience to transient blanks.

Necesitamos procesar miles de guías de forma confiable controlando recursos y evitando bloqueos anti-bot. Un scraper sincrónico limita el rendimiento y complica la resiliencia ante vacíos transitorios.

## Decision / Decisión
Adopt an async Playwright scraper (`web/inter_scraper_async.py`) with:
- Bounded concurrency (Semaphore)
- Optional RPS pacing
- Retries with backoff per tracking
- Robust iframe/popup handling and debug artifacts

Adoptar un scraper Playwright asíncrono con:
- Concurrencia acotada (Semaphore)
- RPS opcional
- Reintentos con backoff por guía
- Manejo robusto de iframe/popup y artefactos de debug

## Consequences / Consecuencias
- Higher throughput on the same hardware.
- Better tolerance to intermittent failures.
- Slightly more complex lifecycle management (start/close browser).
- Requires careful tuning of `--max-concurrency`, `--rps` and timeouts.

- Mayor rendimiento con el mismo hardware.
- Mejor tolerancia a fallos intermitentes.
- Gestión de ciclo de vida un poco más compleja (start/close).
- Requiere ajuste fino de `--max-concurrency`, `--rps` y timeouts.
