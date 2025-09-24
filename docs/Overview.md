# Overview / Resumen

This project automates Interrapidísimo tracking status updates into a Google Sheet using a Playwright-based scraper and business rules for normalization.

Este proyecto automatiza la actualización de estados de seguimiento de Interrapidísimo en una Google Sheet usando un scraper basado en Playwright y reglas de negocio para normalización.

## Scope / Alcance
- Read source or existing rows from Google Sheets.
- Scrape tracking status from Interrapidísimo.
- Normalize raw statuses to a controlled catalog and compute alerts.
- Batch-write only changed cells back to Sheets.
- Produce daily logs and audit CSVs.

Lee filas fuente o existentes de Google Sheets, extrae estados desde Interrapidísimo, los normaliza a un catálogo controlado, calcula alertas y escribe en lotes solo las celdas cambiadas. Genera logs diarios y CSVs de auditoría.

## High-level flow / Flujo de alto nivel
1. SheetsClient reads headers and records.
2. Async scraper queries Interrapidísimo with concurrency and throttling.
3. TrackerService normalizes and computes alert decisions.
4. Batched updates to Sheets (column-wise, consecutive ranges).
5. Logs and audit CSVs persist evidence for review.

1) SheetsClient lee cabeceras y filas. 2) El scraper async consulta Interrapidísimo con concurrencia y rate limit. 3) TrackerService normaliza y calcula alertas. 4) Escrituras a Sheets en lotes (por columna y tramos consecutivos). 5) Logs y CSVs de auditoría registran evidencia.

## Directory map / Mapa de directorios
- `app.py`: Orquestador CLI (modo sincrónico y async)
- `scripts/`: Runners utilitarios (`inter_process.py`, `compare_statuses.py`)
- `services/`: Integraciones (Google Sheets, Drive), reglas de negocio
- `web/`: Scrapers (Playwright)
- `docs/`: Documentación técnica
- `recreacion_linux/`: Runner enfocado a Linux (headless + logs)
- `logs/`: Salida operacional (rotación diaria) y auditoría
