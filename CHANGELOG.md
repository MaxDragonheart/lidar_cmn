# Changelog

Le modifiche rilevanti di ogni versione. Il formato segue [Keep a Changelog](https://keepachangelog.com/it-IT/1.1.0/) e la numerazione delle versioni segue [Semantic Versioning](https://semver.org/lang/it/).

## [2.0.0] - 2026-10-15

### Corretto
- Il download falliva al primo file: gli URL dei tasselli nell'indice incluso nel package puntavano a `http://sit.cittametropolitana.na.it/cecosca/RILIEVO/...`, non più raggiungibile. Sono stati aggiornati ai nuovi indirizzi pubblicati da Città Metropolitana di Napoli, `https://sit.cittametropolitana.na.it/documenti/territorio/lidar_asc_dtm/` per il DTM e `https://sit.cittametropolitana.na.it/documenti/territorio/lidar_asc/` per il DSM. Geometrie e altri attributi dell'indice sono invariati.
- I dati di base (indice dei tasselli e limiti amministrativi) non erano inclusi nel package installato con `pip`: ora sono in `lidar_cmn/geodata` e si leggono con `read_lidar_index` e `read_boundaries`.
- `download_data` si fermava al primo errore e, rilanciato, scaricava di nuovo tutti i file. Ora salta i file già scaricati, ritenta quelli falliti e alla fine segnala quelli non scaricati con `DownloadError`.
- `download_from_url` non aveva un timeout, poteva lasciare file troncati e salvava come `.asc` le pagine HTML restituite da un proxy.
- `target_area` selezionava i tasselli sul rettangolo d'ingombro dell'area invece che sul suo confine.
- `target_area` con un comune inesistente sollevava un `IndexError` poco chiaro: ora solleva `ValueError`.
- Il package configurava il logger radice di Python all'importazione, modificando il logging dell'applicazione che lo usava.
- pytest non raccoglieva i test, per il nome dei file, e i test dipendevano da percorsi assoluti della macchina dell'autore.
- `mkdocs.yml`: la lingua del tema era impostata con `locale`, un'opzione che Material for MkDocs non riconosce, per cui il sito era in inglese (ora `language: it`); il percorso del package per mkdocstrings puntava a una cartella inesistente (`.lidar_cmn`, ora `.`).
- Le dipendenze `pyogrio` (< 0.10) e `fsspec` (< 2025) erano bloccate su versioni vecchie.

### Aggiunto
- `read_lidar_index(lidar_type, source)`: indice dei tasselli incluso nel package o, con `source="wfs"`, quello ufficiale del servizio WFS di Città Metropolitana di Napoli.
- `read_boundaries()`: limiti dei comuni della Città Metropolitana inclusi nel package.
- `download_data`: parametri `overwrite`, `retries`, `timeout` e `max_consecutive_failures`; eccezione `DownloadError`; funzione `is_valid_file`.
- `download_from_url`: parametro `timeout`.
- `target_area`: parametro `use_bbox`, per selezionare i tasselli sul rettangolo d'ingombro come nelle versioni precedenti.
- `lidar_cmn.__version__`.
- Test offline con un server HTTP locale e test `network` sui server di Città Metropolitana di Napoli.

### Modificato (non retrocompatibile)
- `target_area` seleziona i tasselli che si sovrappongono al confine dell'area: per la stessa area restituisce meno tasselli (ad esempio 566 invece di 870 per Napoli), con le geometrie intere dei tasselli invece di quelle ritagliate sul rettangolo d'ingombro. `use_bbox=True` ripristina la selezione precedente.
- La cartella `geodata` è passata dalla radice del repository a `lidar_cmn/geodata`.
- `download_data` solleva `DownloadError` se qualche file non viene scaricato.
- Il package non configura più il logging: i suoi messaggi si vedono solo se l'applicazione lo configura, ad esempio con `logging.basicConfig(level=logging.INFO)`. È stato rimosso `lidar_cmn.config.console_handler`.
