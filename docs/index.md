# lidar_cmn
Python package che consente il download dei dati LiDAR di Città Metropolitana di Napoli

## Installazione

`pip install lidar-cmn`

!!! NOTE

    ## LIDAR Città Metropolitana di Napoli
    Quadro unione delle riprese LIDAR (Light Detection and Ranging) effettuate dalla Nuova Avioriprese nel 2009 integrate dal volo 2012. Prodotto nell'ambito del progetto Cecosca (Centro Satellitare Cave).

    Ciascuno dei due modelli, DTM e DSM, è diviso in 5451 tasselli da 500 × 500 m, con risoluzione di 1 m, in formato ESRI ASCII grid (`.asc`), pubblicati dal [SIT di Città Metropolitana di Napoli](https://sit.cittametropolitana.na.it/downloads.php).

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

### Indice dei tasselli

`read_lidar_index` legge l'indice dei tasselli, con l'URL di ciascun file nella colonna `url`. Con `source="local"` (predefinito) legge quello incluso nel package; con `source="wfs"` legge quello ufficiale dal servizio WFS di Città Metropolitana di Napoli, utile se gli indirizzi dei file dovessero cambiare di nuovo.

### Messaggi di log

Il package non configura il logging. Per vederne i messaggi:

```python
import logging

from lidar_cmn.config import log_format

logging.basicConfig(level=logging.INFO, format=log_format)
```

!!! NOTE

    ## Sistema di riferimento
    L'indice dei tasselli e i limiti amministrativi sono in EPSG:32633 (WGS 84 / UTM zona 33N). Le coordinate dei file `.asc` sono nello stesso sistema, ma i file non lo dichiarano: non sono accompagnati da un `.prj`.

!!! INFO

    Questo progetto non è collegato né supportato da Città Metropolitana di Napoli.

Le novità di ogni versione sono nel [CHANGELOG](https://github.com/MaxDragonheart/lidar_cmn/blob/main/CHANGELOG.md).

Questo repository è stato creato grazie a [MkDocs](https://www.mkdocs.org/), [Material for MkDocs](https://squidfunk.github.io/mkdocs-material) e [mkdocstring](https://mkdocstrings.github.io/).
