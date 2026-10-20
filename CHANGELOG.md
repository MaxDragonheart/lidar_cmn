# Changelog

Le modifiche rilevanti di ogni versione. Il formato segue [Keep a Changelog](https://keepachangelog.com/it-IT/1.1.0/) e la numerazione delle versioni segue [Semantic Versioning](https://semver.org/lang/it/).

## [2.1.0] - 2026-10-20

### Aggiunto
- Modulo `lidar_cmn.raster`, per riunire i tasselli scaricati in un raster virtuale GDAL (VRT) senza copiarne i dati:
  - `build_vrt(folder, lidar_type)`: crea il VRT dei tasselli di una cartella e restituisce un `VrtSummary` con i tasselli inclusi, spostati, ricampionati ed esclusi. Il VRT ha celle di 1 m sulla griglia più diffusa e dichiara EPSG:32633. I tasselli su griglie spostate vengono spostati sulla cella più vicina, di meno di mezza cella. Dove due tasselli si sovrappongono si vede il rilievo 2012. I tasselli con celle diverse da 1 m vengono ricampionati se si sovrappongono ai comuni della Città Metropolitana, altrimenti vengono esclusi;
  - `write_vrt`, `read_header`, `grid_offset` e `AsciiGridHeader`, per usare i grid ESRI ASCII anche fuori dal caso dei LiDAR;
  - `write_prj_files(folder)`: scrive il `.prj` di ogni tassello, che i file `.asc` non hanno.
- Impostazione `raster_cellsize` in `lidar_cmn.config`.
- Dipendenza esplicita `pyproj` (già richiesta da `geopandas`) e, per i test, `rasterio`.
- Pagine Mosaico VRT e Raster della documentazione.

### Corretto
- `test_intermediate_certificates_sit` falliva dietro un proxy che ispeziona il traffico HTTPS, per esempio Zscaler: il proxy sostituisce il certificato del server con uno della propria autorità, di cui `certifi` non si fida. Ora il test viene saltato quando il certificato del server non è emesso da Sectigo.

## [2.0.0] - 2026-10-20

### Corretto
- I download da `https://sit.cittametropolitana.na.it` fallivano con `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`, sempre su Linux e macOS e su Windows quando il certificato intermedio non era già nella cache di sistema. Il server invia una catena di certificati incompleta, senza l'intermedio *Sectigo Public Server Authentication CA DV R36*, e Python non lo scarica da solo. Il package ora include l'intermedio e lo usa in tutte le connessioni HTTPS, insieme ai certificati del sistema e alle radici di `certifi`, con la verifica dei certificati sempre attiva. Dettagli nella pagina [Certificato SSL](docs/certificato_ssl.md) della documentazione.
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
- Le annotazioni di tipo di `read_vector` dichiaravano `str` per `bbox`, `mask` e `rows`.

### Aggiunto
- `read_lidar_index(lidar_type, source)`: indice dei tasselli incluso nel package o, con `source="wfs"`, quello ufficiale del servizio WFS di Città Metropolitana di Napoli.
- `read_boundaries()`: limiti dei comuni della Città Metropolitana inclusi nel package.
- `download_data`: parametri `overwrite`, `retries`, `timeout` e `max_consecutive_failures`; eccezione `DownloadError`; funzione `is_valid_file`.
- `download_from_url`: parametri `timeout` e `context` (contesto SSL).
- `lidar_cmn.generic.ssl_context()`: contesto SSL del package, usato da `download_from_url`, `download_data` e `read_lidar_index(source="wfs")`.
- `lidar_cmn/certificates/intermediate_certificates.pem`, con il certificato intermedio mancante nella catena del server, e le impostazioni `certificates_path` e `intermediate_certificates_path` in `lidar_cmn.config`.
- Dipendenza `certifi` (≥ 2023.7.22, la prima versione con la radice *Sectigo Public Server Authentication Root R46*), per avere le stesse radici su ogni sistema operativo.
- `download_data` non ritenta i file il cui certificato non si può verificare.
- Pagina Certificato SSL della documentazione.
- GitHub Action `.github/workflows/test.yml`. Esegue i test offline su Linux, Windows e macOS con Python dalla 3.10 alla 3.14, e i test `network` sugli stessi sistemi con Python 3.10 e 3.14. Gira a ogni push e pull request, e ogni settimana per notare i cambiamenti del server.
- GitHub Action `.github/workflows/release.yml`: pubblica il package su PyPI quando viene pubblicata una release su GitHub con il tag uguale alla versione. Usa il Trusted Publishing, senza token. Prima di pubblicare verifica il tag, esegue i test offline e controlla che il wheel contenga i dati e il certificato del package.
- `target_area`: parametro `use_bbox`, per selezionare i tasselli sul rettangolo d'ingombro come nelle versioni precedenti.
- `lidar_cmn.__version__`.
- Docstring in stile Google per tutti i moduli, le classi e le funzioni, con descrizione di argomenti, valori restituiti, eccezioni ed esempi; nella documentazione, pagina Config con le impostazioni del package.
- Test offline con un server HTTP locale e con un server HTTPS locale che invia una catena di certificati incompleta (certificati di prova in `tests/data/tls`), e test `network` sui server di Città Metropolitana di Napoli.

### Modificato (non retrocompatibile)
- `target_area` seleziona i tasselli che si sovrappongono al confine dell'area: per la stessa area restituisce meno tasselli (ad esempio 566 invece di 870 per Napoli), con le geometrie intere dei tasselli invece di quelle ritagliate sul rettangolo d'ingombro. `use_bbox=True` ripristina la selezione precedente.
- La cartella `geodata` è passata dalla radice del repository a `lidar_cmn/geodata`.
- `download_data` solleva `DownloadError` se qualche file non viene scaricato.
- Il package non configura più il logging: i suoi messaggi si vedono solo se l'applicazione lo configura, ad esempio con `logging.basicConfig(level=logging.INFO)`. È stato rimosso `lidar_cmn.config.console_handler`.
