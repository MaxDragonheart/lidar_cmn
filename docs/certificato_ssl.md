# Certificato SSL del server

Questa pagina descrive un problema del server di Città Metropolitana di Napoli da cui il package scarica i dati, `sit.cittametropolitana.na.it`, e come lo risolve il package dalla versione 2.0.0.

## In breve

- **Sintomo**: i download falliscono con l'errore

    ```
    <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>
    ```

    anche se gli stessi URL si aprono senza problemi nel browser.

- **Origine**: il server è configurato in modo incompleto. Invia solo il proprio certificato, senza il certificato intermedio che lo ha firmato. Il problema non dipende dal package, da Python o dalla rete da cui ci si collega.
- **Effetto**: su Linux e macOS Python non riesce mai a verificare il certificato. Su Windows ci riesce solo se il certificato intermedio è già nella cache di Windows, una condizione che il package non controlla.
- **Soluzione**: il package include il certificato intermedio mancante e le radici di [certifi](https://pypi.org/project/certifi/), e li usa in tutte le connessioni HTTPS tramite `lidar_cmn.generic.ssl_context`. Il download funziona allo stesso modo su Windows, Linux e macOS, senza configurazioni da parte dell'utente e senza disattivare la verifica dei certificati.

## Come si verifica un certificato

Quando un client apre una connessione HTTPS, il server presenta il proprio certificato. Il client lo accetta solo se riesce a costruire una *catena di fiducia* che parte da quel certificato e arriva a un certificato radice di cui si fida:

```
certificato del server (foglia)   *.cittametropolitana.na.it
        │ firmato da
        ▼
certificato intermedio            Sectigo Public Server Authentication CA DV R36
        │ firmato da
        ▼
certificato radice                Sectigo Public Server Authentication Root R46
```

I certificati radice sono pochi (`certifi` ne contiene circa 120). Sono preinstallati nell'archivio del sistema operativo e, per Python, nel package `certifi`. I certificati intermedi sono molti di più e cambiano più spesso, quindi il client non li conosce in anticipo. Per questo il protocollo TLS stabilisce che sia il server a inviarli: il server invia il proprio certificato seguito, nell'ordine, da quelli che lo hanno firmato. Può omettere solo la radice, che il client deve già possedere ([RFC 5246, §7.4.2](https://www.rfc-editor.org/rfc/rfc5246#section-7.4.2); [RFC 8446, §4.4.2](https://www.rfc-editor.org/rfc/rfc8446#section-4.4.2) per TLS 1.3).

## Dove si origina il problema

La catena del certificato di `sit.cittametropolitana.na.it`, verificata il 20/10/2026, è questa:

| Livello | Certificato | Firmato da | Validità | Inviato dal server | Presente nel client |
|---|---|---|---|---|---|
| Foglia | `*.cittametropolitana.na.it` | Sectigo Public Server Authentication CA DV R36 | 06/05/2026 – 20/11/2026 | sì | non serve |
| Intermedio | Sectigo Public Server Authentication CA DV R36 | Sectigo Public Server Authentication Root R46 | 22/03/2021 – 21/03/2036 | **no** | **no** |
| Radice | Sectigo Public Server Authentication Root R46 | sé stesso | 22/03/2021 – 21/03/2046 | non serve | sì (sistema operativo, `certifi` ≥ 2023.7.22) |

Il client ha la radice ma non l'intermedio, e il server non glielo invia: la catena si interrompe al primo anello. È quello che OpenSSL indica con `unable to get local issuer certificate`, cioè «non trovo chi ha firmato questo certificato».

Lo si vede con `openssl`, disponibile su Linux e su macOS e, su Windows, in Git Bash:

```bash
openssl s_client -connect sit.cittametropolitana.na.it:443 -servername sit.cittametropolitana.na.it </dev/null
```

```
Certificate chain
 0 s:CN=*.cittametropolitana.na.it
   i:C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV R36
---
...
Verify return code: 21 (unable to verify the first certificate)
```

La catena contiene solo il certificato `0`, cioè la foglia. Con il server configurato correttamente comparirebbe anche il certificato `1`, l'intermedio:

```
Certificate chain
 0 s:CN=*.cittametropolitana.na.it
   i:C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV R36
 1 s:C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV R36
   i:C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication Root R46
```

e `Verify return code: 0 (ok)`.

Il server dichiara `Server: Apache/2.2.15 (CentOS)`. In Apache 2.2 la catena si configura con la direttiva `SSLCertificateChainFile`, che deve puntare al file del certificato intermedio. A quanto risulta dal comportamento del server, la direttiva manca oppure non punta al file giusto.

## Perché in alcuni casi funziona

Il certificato del server contiene l'estensione *Authority Information Access* (AIA), con l'indirizzo da cui scaricare il certificato che lo ha firmato:

```
Authority Information Access:
    CA Issuers - URI:http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt
```

Alcuni client usano questo indirizzo per scaricare da soli l'intermedio mancante e completare la catena, altri no. Per questo lo stesso URL funziona in un programma e non in un altro:

| Client | Completa da solo la catena? | Esito |
|---|---|---|
| Browser (Chrome, Edge, Firefox, Safari) | di norma sì: scaricano l'intermedio tramite AIA oppure lo hanno già in un elenco precaricato | funziona |
| Programmi che usano la verifica di Windows: curl di Windows, PowerShell, .NET | sì: Windows scarica l'intermedio tramite AIA e lo conserva nell'archivio *Autorità di certificazione intermedie* dell'utente (`Cert:\CurrentUser\CA`) | funziona |
| Python su Windows | no, perché usa OpenSSL. Legge però gli archivi di Windows, compreso `Cert:\CurrentUser\CA` | funziona **solo se** un altro programma ha già messo l'intermedio nella cache di Windows |
| Python su Linux | no: OpenSSL non scarica i certificati tramite AIA e il sistema fornisce solo le radici | fallisce |
| Python su macOS (python.org, Homebrew, conda) | no: usa OpenSSL, non la verifica di macOS | fallisce |
| curl e wget su Linux | no (OpenSSL o GnuTLS) | fallisce |

Python non scarica i certificati tramite AIA su nessun sistema operativo, perché OpenSSL non lo fa. Su Windows il risultato dipende quindi da uno stato nascosto della macchina, cioè da cosa contiene la cache dei certificati intermedi.

### Che cosa è successo il 20/10/2026

Su un PC Windows il download dell'intero dataset con la versione 2.0.0 senza questa correzione:

1. alle 08:55 è fallito con `CERTIFICATE_VERIFY_FAILED` sui primi cinque tasselli e si è fermato, come previsto da `max_consecutive_failures`;
2. per la diagnosi è stata fatta una richiesta allo stesso server con `curl`, che su Windows ha usato la verifica del sistema operativo. Windows ha scaricato l'intermedio tramite AIA e lo ha salvato in `Cert:\CurrentUser\CA`;
3. alle 08:57 lo stesso download, rilanciato senza modifiche, funzionava.

Lo stesso PC e lo stesso codice hanno dato risultati opposti a due minuti di distanza. Su Linux e macOS il passo 2 non sarebbe servito a nulla.

## La soluzione adottata nel package

### 1. Il certificato intermedio incluso nel package

Il file `lidar_cmn/certificates/intermediate_certificates.pem` contiene il certificato *Sectigo Public Server Authentication CA DV R36*, preceduto da un'intestazione leggibile con soggetto, emittente, validità, SHA-256 e provenienza. Il certificato:

- è stato scaricato dall'indirizzo AIA del certificato del server, `http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt`;
- è stato verificato con `openssl verify`: è firmato dalla radice *Sectigo Public Server Authentication Root R46* di `certifi`, e con esso la catena del server si verifica;
- ha SHA-256 `8C:54:C3:34:B6:6B:A4:E4:26:77:2A:F4:A3:F9:13:6C:19:A1:AE:C7:29:FD:B2:8C:53:5C:07:A5:A4:EF:22:E0`, uguale a quello della copia scaricata da Windows.

La configurazione `lidar_cmn.config.intermediate_certificates_path` contiene il percorso del file.

### 2. Le radici di `certifi`

`certifi` è ora una dipendenza esplicita del package, dalla versione 2023.7.22: è la prima che contiene la radice *Sectigo Public Server Authentication Root R46*. Le radici di `certifi` sono le stesse su ogni sistema operativo. Così il package funziona anche dove l'archivio del sistema non è disponibile a Python, per esempio con il Python di python.org su macOS se non è stato eseguito `Install Certificates.command`, o in container Linux minimali.

### 3. Il contesto SSL del package

`lidar_cmn.generic.ssl_context` crea il contesto SSL usato da tutte le connessioni HTTPS del package:

```python
@cache
def ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    context.load_verify_locations(cafile=intermediate_certificates_path)

    return context
```

Il contesto si fida, nell'ordine:

1. dei certificati del sistema operativo, come `ssl.create_default_context`, compresi quelli indicati con le variabili d'ambiente `SSL_CERT_FILE` e `SSL_CERT_DIR`;
2. delle radici di `certifi`;
3. dei certificati intermedi inclusi nel package.

Viene creato una sola volta (`functools.cache`) e condiviso da tutti i download, così da non rileggere i certificati per ciascuno dei 10902 tasselli. Lo usano:

- `lidar_cmn.generic.download_from_url`, e quindi `lidar_cmn.download.download_data`;
- `lidar_cmn.vector.read_lidar_index` con `source="wfs"`, perché anche il servizio WFS è su `sit.cittametropolitana.na.it`.

La verifica resta completa: il contesto richiede un certificato valido (`ssl.CERT_REQUIRED`) e controlla che corrisponda al nome del server (`check_hostname`).

### 4. Altre modifiche collegate

- `download_from_url` ha il parametro `context`, per usare un contesto SSL diverso da quello del package.
- `download_data` non ritenta i file il cui certificato non si può verificare. L'errore non cambia ritentando: il file fallisce subito, senza le attese tra un tentativo e l'altro.

### Esito su ciascun sistema operativo

| Sistema operativo | Prima della correzione | Con la correzione |
|---|---|---|
| Windows, intermedio già nella cache | funziona | funziona |
| Windows, intermedio non nella cache | fallisce | funziona |
| Linux | fallisce | funziona |
| macOS | fallisce | funziona |

Il comportamento su Linux e macOS è verificato dal test `test_intermediate_certificates_sit`, che esclude i certificati del sistema operativo (vedi [Test](#test)).

## Alternative scartate

- **Disattivare la verifica dei certificati** (`ssl._create_unverified_context()` o equivalenti): il package accetterebbe qualunque server che si spacci per quello di Città Metropolitana, e i tasselli scaricati potrebbero essere alterati senza che nessuno se ne accorga. È esclusa.
- **[truststore](https://pypi.org/project/truststore/)**, che affida la verifica al sistema operativo: su Windows e macOS completerebbe la catena tramite AIA, ma su Linux usa OpenSSL e continuerebbe a fallire. Non risolve il problema su tutti i sistemi operativi.
- **Scaricare l'intermedio tramite AIA all'interno del package**: si adatterebbe da sola a un cambio di intermedio, ma l'indirizzo AIA è in HTTP semplice e il certificato scaricato andrebbe verificato prima di fidarsene. Da Python 3.13, inoltre, `ssl.create_default_context` imposta `VERIFY_X509_PARTIAL_CHAIN`: ogni certificato aggiunto al contesto diventa un punto di fiducia. Un errore in questa verifica permetterebbe a un attaccante di far accettare al package un certificato a sua scelta. La complessità e il rischio non valgono il vantaggio.
- **Chiedere agli utenti di installare il certificato intermedio**: un'operazione manuale diversa per ogni sistema operativo, da ripetere su ogni macchina.
- **Correggere il server**: è la soluzione definitiva, ma non dipende da chi sviluppa il package. Va segnalata al gestore, vedi [Segnalazione al gestore del server](#segnalazione-al-gestore-del-server).

## Sicurezza

- La verifica del certificato e del nome del server resta attiva su tutte le connessioni.
- Il certificato incluso è pubblico, autentico (vedi sopra) ed è un'autorità intermedia con `pathlen:0`: può firmare solo certificati finali, non altre autorità.
- Fidarsi di questo certificato non estende la fiducia: tutto ciò che firma è già accettato da chi si fida della radice R46, cioè da tutti i sistemi operativi e da `certifi`. L'unica differenza riguarda il futuro: se R46 o R36 venissero revocati o rimossi dagli archivi, il package continuerebbe a fidarsi di R36 finché il file non viene aggiornato. Python, del resto, non controlla la revoca dei certificati (CRL e OCSP). Vedi [Manutenzione](#manutenzione).

## Test

Test offline (`pytest -m "not network"`), uguali su ogni sistema operativo:

- `tests/conftest.py`, fixture `https_server`: un server HTTPS locale che, come `sit.cittametropolitana.na.it`, invia solo il proprio certificato. Usa una piccola infrastruttura di certificati di prova (radice, intermedio, server) in `tests/data/tls`, creata da `tests/data/tls/make_certificates.sh`;
- `test_download_from_url_incomplete_chain`: con la sola radice il download fallisce con `unable to get local issuer certificate`. Riproduce il problema;
- `test_download_from_url_intermediate`: aggiungendo l'intermedio il download riesce. È il meccanismo della soluzione;
- `test_intermediate_certificates`: il file incluso contiene esattamente il certificato atteso (SHA-256) e non è scaduto;
- `test_ssl_context`: il contesto del package verifica certificato e nome del server e si fida dell'intermedio incluso e delle radici di `certifi`;
- `test_download_data_certificate`: un certificato che non si può verificare non viene ritentato.

Test `network` (`pytest -m network`), sul server reale:

- `test_ssl_context_sit`: la connessione con il contesto del package riesce;
- `test_intermediate_certificates_sit`: la connessione riesce con le sole radici di `certifi` e l'intermedio incluso, **senza i certificati del sistema operativo**, quindi nelle stesse condizioni su Windows, Linux e macOS. Il test è ripetuto con i flag di verifica che `ssl.create_default_context` imposta da Python 3.13 (`VERIFY_X509_STRICT` e `VERIFY_X509_PARTIAL_CHAIN`).

Controprova, sullo stesso server: con le sole radici di `certifi`, senza l'intermedio, la connessione fallisce con `unable to get local issuer certificate`.

## Manutenzione

Le scadenze da tenere d'occhio:

- **20/11/2026**: scade il certificato del server. Al rinnovo Sectigo potrebbe firmarlo con un intermedio diverso da R36;
- **21/03/2036**: scade l'intermedio R36.

Dopo un rinnovo del certificato del server, eseguire i test `network`. Se falliscono con `CERTIFICATE_VERIFY_FAILED`:

1. leggere l'emittente del nuovo certificato e l'indirizzo AIA del suo intermedio:

    ```bash
    openssl s_client -connect sit.cittametropolitana.na.it:443 -servername sit.cittametropolitana.na.it </dev/null 2>/dev/null \
        | openssl x509 -noout -issuer -ext authorityInfoAccess
    ```

2. scaricare l'intermedio (in formato DER) e convertirlo in PEM:

    ```bash
    curl -o intermedio.crt <URI di CA Issuers>
    openssl x509 -inform DER -in intermedio.crt -out intermedio.pem
    ```

3. verificare che sia firmato da una radice di `certifi` e che completi la catena del server:

    ```bash
    CERTIFI=$(python -c "import certifi; print(certifi.where())")
    openssl s_client -connect sit.cittametropolitana.na.it:443 -servername sit.cittametropolitana.na.it </dev/null 2>/dev/null \
        | openssl x509 > server.pem
    openssl verify -CAfile "$CERTIFI" intermedio.pem
    openssl verify -CAfile "$CERTIFI" -untrusted intermedio.pem server.pem
    ```

    Entrambi i comandi devono rispondere `OK`.

4. aggiungere il certificato a `lidar_cmn/certificates/intermediate_certificates.pem`, con la stessa intestazione degli altri (`openssl x509 -in intermedio.pem -noout -subject -issuer -dates -fingerprint -sha256`). Non rimuovere R36 finché il server lo usa;
5. aggiornare gli SHA-256 attesi in `tests/test_generic.py` e la tabella di questa pagina.

Se invece `openssl s_client` mostra anche il certificato `1`, il server è stato corretto. L'intermedio incluso non serve più, ma non fa danni: lo si può rimuovere in una versione successiva.

## Reti aziendali con ispezione TLS

Alcune reti aziendali intercettano il traffico HTTPS e lo firmano di nuovo con un certificato radice proprio. In quel caso:

- su Windows la radice aziendale è di norma già nell'archivio di sistema, che `ssl_context` legge;
- su Linux e macOS basta indicare il file PEM della radice aziendale con la variabile d'ambiente `SSL_CERT_FILE` (o una cartella con `SSL_CERT_DIR`), che `ssl_context` legge. Le radici di `certifi` e l'intermedio incluso restano comunque attivi;
- in alternativa si può passare un contesto SSL proprio a `download_from_url` con il parametro `context`.

## Segnalazione al gestore del server

La soluzione definitiva è configurare la catena completa sul server. Un testo da inviare al SIT di Città Metropolitana di Napoli:

> Il server `sit.cittametropolitana.na.it` (Apache/2.2.15) invia nella connessione HTTPS solo il certificato `*.cittametropolitana.na.it`, senza il certificato intermedio *Sectigo Public Server Authentication CA DV R36* che lo ha emesso. I browser completano la catena da soli, ma i client che non lo fanno, come Python, curl su Linux e altri strumenti basati su OpenSSL, rifiutano la connessione con l'errore «unable to get local issuer certificate». Per correggere il problema basta configurare il certificato intermedio con la direttiva `SSLCertificateChainFile`. Il certificato si scarica da `http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt`. Il risultato si può verificare con `openssl s_client -connect sit.cittametropolitana.na.it:443 -servername sit.cittametropolitana.na.it`, che dopo la correzione deve mostrare due certificati e `Verify return code: 0 (ok)`.
