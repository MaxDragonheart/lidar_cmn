# Mosaico VRT

`lidar_cmn.raster.build_vrt` riunisce i tasselli scaricati in un unico raster virtuale (VRT). Il VRT è un file XML che GDAL, e i programmi basati su GDAL come QGIS, leggono come un solo raster. Il file rimanda ai tasselli `.asc` senza copiarne i dati: per il DTM completo occupa circa 2,4 MB.

```python
from pathlib import Path

from lidar_cmn.raster import build_vrt, write_prj_files

summary = build_vrt(folder=Path("lidar/dtm"), lidar_type="dtm")
print(summary.path)          # lidar/dtm.vrt
print(len(summary.tiles))    # tasselli nel VRT
print(summary.excluded)      # tasselli esclusi, con il motivo

write_prj_files(folder=Path("lidar/dtm"))   # facoltativo: un .prj per ogni tassello
```

Il package scrive il VRT da solo, senza GDAL. GDAL serve solo per leggerlo.

## Caratteristiche del VRT

- **Celle**: celle di 1 m, sulla griglia più diffusa fra i tasselli.
- **Sistema di riferimento**: EPSG:32633 (WGS 84 / UTM zona 33N). I file `.asc` non dichiarano il proprio sistema di riferimento, quindi lo dichiara il VRT.
- **NoData**: -9999, come nei tasselli. Le celle NoData di un tassello sono trasparenti: dove due tasselli si sovrappongono, si vede quello sotto.
- **Percorsi**: i percorsi dei tasselli sono relativi al VRT. Spostando insieme `dtm.vrt` e la cartella `dtm`, il VRT continua a funzionare.

## Come sono fatti i tasselli

I tasselli non formano una griglia uniforme. Questi sono i 5449 tasselli DTM e i 5449 tasselli DSM scaricati il 20/10/2026:

| Caso | DTM | DSM | Trattamento nel VRT |
|---|---|---|---|
| Celle di 1 m, angoli su metri interi (quasi tutti del rilievo 2009) | 3386 | 3472 | griglia del VRT, nessuna modifica |
| Celle di 1 m, griglia spostata di 0,17 m in X e 0,46 m in Y (rilievo 2012 e una parte del 2009) | 1968 | 1969 | spostati sulla griglia del VRT |
| Celle di 1 m, griglia spostata di 0,5/0,5 m | 73 | — | spostati sulla griglia del VRT |
| Celle di 1 m, griglia spostata di 0,67/0,96 m | 5 | 8 | spostati sulla griglia del VRT |
| Celle di 1 m ma non 500 × 500 (tasselli ritagliati lungo la costa e i bordi) | 328 | 277 | nessuna modifica: restano nel loro poligono dell'indice |
| Celle diverse da 1 m (da 0,02 a 0,93 m), quasi sempre con un lato di 128 celle | 17 | — | 2 ricampionati, 15 esclusi (vedi sotto) |
| Coppie di tasselli sovrapposte (circa 160 m² ciascuna), quasi sempre tra griglie diverse | 46 | 55 | vince il rilievo più recente |

Le anomalie dei due modelli non coincidono. I 17 tasselli DTM con celle diverse da 1 m sono regolari nel DSM. In tutto, 182 tasselli hanno un'estensione o una cella diversa tra DTM e DSM.

Inoltre due tasselli dell'indice, `002196` e `002197`, non sono pubblicati dal server: rispondono 404 sia per il DTM sia per il DSM. Si trovano fuori dai confini comunali, a 0,6 e 1,1 km da Giugliano in Campania.

## Le scelte

**Griglia.** Il VRT usa la griglia più diffusa fra i tasselli con celle di 1 m: per il DTM e per il DSM è quella con gli angoli su metri interi. I due VRT hanno la stessa origine e le stesse dimensioni, quindi si possono combinare cella per cella, per esempio DSM − DTM per l'altezza di edifici e vegetazione. I tasselli su una griglia spostata vengono spostati sulla cella del VRT più vicina, cioè con il vicino più prossimo. Lo spostamento è inferiore a mezza cella: 0,17 m in X e 0,46 m in Y per la griglia del 2012. Le quote non cambiano: ogni cella del tassello diventa una cella del VRT.

**Sovrapposizioni.** I tasselli sono disegnati per anno del rilievo: prima il 2009, poi il 2012. Dove si sovrappongono si vede il rilievo 2012, il più recente. Dove il 2012 ha celle NoData si vede il 2009.

**Tasselli con celle diverse da 1 m.** Sembrano esportazioni difettose: hanno celle da 0,02 a 0,93 m e quasi sempre un lato di 128 celle. Sono trattati così:

- quelli che si sovrappongono ai comuni della Città Metropolitana (lo stesso criterio di `target_area`) restano nel VRT, ricampionati a 1 m con il vicino più prossimo. Per il DTM sono `000336` e `000880`: strisce costiere con quote tra −0,4 e 2,5 m;
- gli altri sono esclusi e compaiono in `summary.excluded` con il motivo. Per il DTM sono 15, tutti "Extra Prov Na". Il DSM non ne ha.

**Altri esclusi.** Restano fuori anche i file `.asc` che non sono nell'indice dei tasselli e quelli con un'intestazione illeggibile.

**Tecnica.** Ogni tassello è agganciato con i suoi bordi alle linee più vicine della griglia del VRT. Con bordi frazionari, GDAL ripeterebbe l'ultima riga o colonna di un tassello spostato nella cella successiva, sporcando i tasselli vicini e allargando il mosaico lungo la costa.

## Uso del VRT

- **QGIS**: *Layer* → *Aggiungi layer* → *Aggiungi layer raster*, scegliendo `dtm.vrt`.
- **GDAL, rasterio**: si apre come qualunque raster, per esempio `rasterio.open("lidar/dtm.vrt")`.
- **ArcGIS Pro**: legge i VRT di GDAL. Con questi dati la lettura va ancora verificata.

**Prestazioni.** Il VRT legge i `.asc`, che sono file di testo. Leggere una zona è rapido: 2 × 2 km richiedono circa 0,1 s. Visualizzare l'intera area da lontano richiede invece di leggere tutti i 5434 tasselli. Per un uso intenso, con GDAL:

```bash
# Piramidi per la visualizzazione: crea dtm.vrt.ovr accanto al VRT
gdaladdo -r average lidar/dtm.vrt

# Oppure: un unico GeoTIFF compresso e ottimizzato (Cloud Optimized GeoTIFF)
gdal_translate -of COG -co COMPRESS=DEFLATE -co PREDICTOR=FLOATING_POINT lidar/dtm.vrt lidar/dtm.tif
```

## Verifiche

Sui dati reali, con VRT di 70 396 × 53 849 celle e origine in (402431, 4541244):

| | DTM | DSM |
|---|---|---|
| Tasselli nel VRT | 5434 | 5449 |
| Spostati sulla griglia del VRT | 2046 | 1977 |
| Ricampionati | 2 | 0 |
| Esclusi | 15 | 0 |
| Celle valide confrontate con i tasselli originali (200 tasselli scelti a caso) | 48,7 milioni | 48,5 milioni |
| Celle diverse dal tassello originale | 0 | 0 |

Restano fuori dal confronto le celle dove si vede un tassello disegnato dopo. Nei 2 tasselli DTM ricampionati, tutti i valori del VRT provengono dal tassello originale.

Test offline in `tests/test_raster.py`, su tasselli sintetici che riproducono i casi reali:

- griglia spostata;
- sovrapposizione tra il 2009 e il 2012;
- NoData trasparente;
- tasselli a 0,5 m dentro e fuori dai confini;
- file non presente nell'indice;
- tassello con soli valori interi.
