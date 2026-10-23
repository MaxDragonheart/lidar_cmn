# Dati di base

## LIDAR Città Metropolitana di Napoli
Quadro unione delle riprese LIDAR (Light Detection and Ranging) effettuate dalla Nuova Avioriprese nel 2009 integrate dal volo 2012. Prodotto nell'ambito del progetto Cecosca (Centro Satellitare Cave).

Il file `quadro_unione_lidar.gpkg` contiene i layer `dtm` e `dsm`, con un poligono per tassello e l'URL del file nella colonna `url`. Corrispondono ai layer WFS `sit:quadro_unione_lidar_dtm` e `sit:quadro_unione_lidar_dsm` del [SIT di Città Metropolitana di Napoli](https://sit.cittametropolitana.na.it/geoserver/ows?service=wfs&version=2.0.0&request=GetCapabilities).

## Limiti Amministrativi
I limiti ammininistrativi sono prelevati dallo storico dei limiti amministrativi di [ISTAT](https://www.istat.it/it/archivio/222527). I comuni sono nel layer `prov_na_2023` di `limiti_amministrativi.gpkg`.

## Aggiornamenti
- 15/10/2026: aggiornati gli URL dei tasselli nei layer `dtm` e `dsm`. I vecchi indirizzi (`http://sit.cittametropolitana.na.it/cecosca/RILIEVO/<foglio>/DTM|DSM/asc/<refname>.asc`) non sono più raggiungibili; i nuovi sono quelli dei layer WFS, `https://sit.cittametropolitana.na.it/documenti/territorio/lidar_asc_dtm/<refname>.asc` per il DTM e `https://sit.cittametropolitana.na.it/documenti/territorio/lidar_asc/<refname>.asc` per il DSM. Geometrie e altri attributi sono invariati.

## Note
Il file `lidar_cmn.qgz` è il file progetto di [QGIS](https://www.qgis.org/) che raccorda i dati di base.
