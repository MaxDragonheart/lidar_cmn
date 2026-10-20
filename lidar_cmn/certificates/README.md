# Certificati

Il file `intermediate_certificates.pem` contiene i certificati intermedi che mancano nella catena inviata dal server `sit.cittametropolitana.na.it`. `lidar_cmn.generic.ssl_context` li aggiunge ai certificati del sistema e alle radici di `certifi`.

| Certificato | Firmato da | Validità | SHA-256 |
|---|---|---|---|
| Sectigo Public Server Authentication CA DV R36 | Sectigo Public Server Authentication Root R46 | 22/03/2021 – 21/03/2036 | `8C:54:C3:34:B6:6B:A4:E4:26:77:2A:F4:A3:F9:13:6C:19:A1:AE:C7:29:FD:B2:8C:53:5C:07:A5:A4:EF:22:E0` |

L'origine del problema, la verifica del certificato e la procedura di aggiornamento sono descritte in [docs/certificato_ssl.md](../../docs/certificato_ssl.md).

## Aggiornamenti
- 20/10/2026: aggiunto Sectigo Public Server Authentication CA DV R36, emittente del certificato del server valido fino al 20/11/2026.
