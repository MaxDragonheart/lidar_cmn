# lidar_cmn
[![Test](https://github.com/MaxDragonheart/lidar_cmn/actions/workflows/test.yml/badge.svg)](https://github.com/MaxDragonheart/lidar_cmn/actions/workflows/test.yml)

Python package che consente il download dei dati LiDAR di Città Metropolitana di Napoli

I dati sono il DTM e il DSM delle riprese LiDAR effettuate dalla Nuova Avioriprese nel 2009, integrate dal volo 2012, prodotti nell'ambito del progetto Cecosca (Centro Satellitare Cave) e pubblicati dal [SIT di Città Metropolitana di Napoli](https://sit.cittametropolitana.na.it/downloads.php). Ciascuno dei due modelli è diviso in 5451 tasselli da 500 × 500 m, con risoluzione di 1 m, in formato ESRI ASCII grid (`.asc`).

Documentazione: [maxdragonheart.github.io/lidar_cmn](https://maxdragonheart.github.io/lidar_cmn/)

## Installazione

`pip install lidar-cmn`

## Uso

### Download dei tasselli di un comune

```python
from pathlib import Path

from lidar_cmn.download import download_data
from lidar_cmn.vector import read_boundaries, read_lidar_index, target_area

selection = target_area(
    boundaries=read_boundaries(),
    link_source=read_lidar_index(lidar_type="dtm"),
    target="Procida"
)
download_data(selection=selection, output_folder=Path("lidar"), output_folder_name="dtm")
```

`target_area` seleziona i tasselli che si sovrappongono al confine del comune indicato in `target`, con il nome della colonna `COMUNE` dei limiti amministrativi, o dell'intera Città Metropolitana con `target=None`. Con `use_bbox=True` seleziona invece i tasselli che si sovrappongono al rettangolo d'ingombro dell'area, come nelle versioni precedenti alla 2.0.0.

### Download dell'intero dataset

```python
for lidar_type in ["dtm", "dsm"]:
    download_data(
        selection=read_lidar_index(lidar_type=lidar_type),
        output_folder=Path("lidar"),
        output_folder_name=lidar_type
    )
```

Con `target=None`, invece, `target_area` seleziona 5158 tasselli su 5451: esclude quelli che non si sovrappongono ai confini comunali, cioè 284 dei 304 tasselli con `appartenen = "Extra Prov Na"` e 9 tasselli con `appartenen = "Prov Na"`.

### Interruzioni ed errori

- `download_data` salta i file già presenti nella cartella di destinazione: se il download si interrompe, basta rilanciarlo per riprenderlo. Con `overwrite=True` scarica di nuovo tutti i file.
- Ogni file viene scritto in un file temporaneo `.part` e rinominato solo quando il download è completo e il file è un ESRI ASCII grid valido.
- Ogni file viene tentato fino a `retries` volte (3), tranne in caso di errori definitivi come 404 Not Found; `timeout` (30 s) è l'attesa massima della risposta del server.
- Un file non scaricato non ferma gli altri: alla fine `download_data` solleva `DownloadError`, con gli URL dei file mancanti in `DownloadError.urls`. Il download si ferma dopo `max_consecutive_failures` (5) file falliti di seguito, ad esempio quando il server non è raggiungibile.

### Mosaico dei tasselli (VRT)

```python
from lidar_cmn.raster import build_vrt

summary = build_vrt(folder=Path("lidar/dtm"), lidar_type="dtm")   # crea lidar/dtm.vrt
```

`build_vrt` riunisce i tasselli scaricati in un raster virtuale GDAL (VRT), che QGIS e GDAL leggono come un unico raster senza copiare i dati. Il VRT ha celle di 1 m e dichiara EPSG:32633, che i file `.asc` non dichiarano.

I tasselli non sono tutti sulla stessa griglia:
- quelli su una griglia spostata vengono spostati sulla cella più vicina del VRT, di meno di mezza cella;
- dove due tasselli si sovrappongono si vede il rilievo 2012;
- i tasselli con celle diverse da 1 m vengono ricampionati se si sovrappongono ai comuni della Città Metropolitana, altrimenti vengono esclusi.

`summary.excluded` elenca i tasselli esclusi, con il motivo. `write_prj_files` scrive un `.prj` per ogni tassello. Dettagli nella pagina [docs/mosaico_vrt.md](docs/mosaico_vrt.md).

### Indice dei tasselli

`read_lidar_index` legge l'indice dei tasselli, con l'URL di ciascun file nella colonna `url`. Con `source="local"` (predefinito) legge quello incluso nel package; con `source="wfs"` legge quello ufficiale dal servizio WFS di Città Metropolitana di Napoli, utile se gli indirizzi dei file dovessero cambiare di nuovo.

### Certificato SSL del server

Il server di Città Metropolitana di Napoli, `sit.cittametropolitana.na.it`, invia una catena di certificati incompleta: manca il certificato intermedio *Sectigo Public Server Authentication CA DV R36*. Senza correzioni Python non riesce a verificarlo e i download falliscono con `CERTIFICATE_VERIFY_FAILED`, sempre su Linux e macOS, a volte su Windows. Il package include il certificato intermedio mancante e le radici di `certifi` e li usa in tutte le connessioni HTTPS, con la verifica dei certificati sempre attiva: non serve nessuna configurazione. Origine del problema, soluzione e manutenzione sono descritte in [docs/certificato_ssl.md](docs/certificato_ssl.md).

### Messaggi di log

Il package non configura il logging. Per vederne i messaggi:

```python
import logging

from lidar_cmn.config import log_format

logging.basicConfig(level=logging.INFO, format=log_format)
```

## Sistema di riferimento

L'indice dei tasselli e i limiti amministrativi sono in EPSG:32633 (WGS 84 / UTM zona 33N). Le coordinate dei file `.asc` sono nello stesso sistema, ma i file non lo dichiarano: non sono accompagnati da un `.prj`.

## Test

```
pytest                    # tutti i test
pytest -m "not network"   # esclude i test che usano i server di Città Metropolitana di Napoli
```

La GitHub Action [`.github/workflows/test.yml`](.github/workflows/test.yml) esegue i test a ogni push e pull request, e ogni lunedì alle 06:00 UTC:

- i test offline su Linux, Windows e macOS, con Python 3.10, 3.11, 3.12, 3.13 e 3.14;
- i test `network` sugli stessi sistemi operativi, con Python 3.10 e 3.14. Tra questi c'è la verifica del certificato di `sit.cittametropolitana.na.it`: l'esecuzione settimanale segnala se il server cambia certificato.

## Pubblicazione su PyPI

La GitHub Action [`.github/workflows/release.yml`](.github/workflows/release.yml) pubblica il package su PyPI ogni volta che viene pubblicata una release su GitHub. Creare e pushare solo un tag, senza release, non avvia la pubblicazione.

Per pubblicare una nuova versione:

1. aggiornare `version` in `pyproject.toml` e il [CHANGELOG](CHANGELOG.md), poi unire le modifiche in `main`;
2. su GitHub, da *Releases* → *Draft a new release*, creare un tag uguale alla versione, per esempio `2.0.0` (va bene anche `v2.0.0`), e pubblicare la release.

La Action:

1. verifica che il tag corrisponda alla versione di `pyproject.toml` e che il package sia `lidar-cmn`, altrimenti si ferma senza pubblicare;
2. esegue i test offline;
3. prepara il wheel e il sorgente (`python -m build`), li controlla con `twine check` e verifica che il wheel contenga i dati di `geodata` e il certificato di `certificates`;
4. li pubblica su PyPI con il *Trusted Publishing* dell'ambiente GitHub `pypi`, senza token salvati nei secret.

Configurazione da fare una sola volta, prima della prima release:

- su PyPI, nel progetto [`lidar-cmn`](https://pypi.org/manage/project/lidar-cmn/settings/publishing/), da *Manage* → *Publishing*, aggiungere un *trusted publisher* GitHub con questi dati: owner `MaxDragonheart`, repository `lidar_cmn`, workflow `release.yml`, ambiente `pypi`;
- su GitHub, nel repository, da *Settings* → *Environments*, creare l'ambiente `pypi`. È facoltativo: se manca, GitHub lo crea al primo avvio. Lì si possono aggiungere regole di protezione, per esempio l'approvazione manuale prima della pubblicazione.

## Novità

Vedi il [CHANGELOG](CHANGELOG.md).

Questo progetto non è collegato né supportato da Città Metropolitana di Napoli.
