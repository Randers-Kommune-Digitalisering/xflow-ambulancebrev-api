# API – X-Flow Ambulancebrev
[**Formål**](#formål) | [**Beskrivelse**](#beskrivelse) | [**Afhængigheder**](#afhængigheder) | [**Udvikling**](#udvikling)

## Formål

Applikationen udstiller et lille HTTP endpoint til at journalisere et *Ambulancebrev* (PDF) på personalesager i SBSYS. Den modtager en base64-kodet PDF fra X-Flow, finder medarbejderen ud fra et DQ-nummer via Delta, slår medarbejderens personalesager op i SBSYS og journaliserer dokumentet på alle aktive personalesager.

## Beskrivelse

Den primære forretningsflow ligger i endpointet `POST /api/journaliser` i [src/api_endpoints.py](src/api_endpoints.py).

### Overordnet flow

1. Klienten (fx X-Flow) kalder `POST /api/journaliser` med JSON payload:
   - `user`: streng i formatet `"<fulde navn> - <dq-nummer>"`
   - `data`: base64-enkodet PDF (string)
2. API validerer at payload er til stede, at `data` er base64, og at det dekodede indhold starter med `%PDF`.
3. Hvis `TESTING=True`, bruges `TEST_CPR_NUMBER` direkte. Ellers:
   - DQ-nummer udtrækkes fra `user`
   - Delta forespørges (OIDC client credentials) for at finde medarbejderens CPR
4. SBSYS forespørges på personalesager for CPR-nummeret.
5. Kun aktive sager journaliseres (status-id `6`).
6. Dokumentet uploades/journaliseres på hver aktiv personalesag med fast metadata (beskrivelse + dokumentnavn).


## Afhængigheder

Nedenfor er de væsentlige afhængigheder for applikationen.

### :gear: Frameworks og biblioteker

- Python 3.10+
- [Flask](https://palletsprojects.com/p/flask/) (HTTP API)
- [py-healthcheck](https://pypi.org/project/py-healthcheck/) (health endpoint)
- [prometheus-client](https://pypi.org/project/prometheus-client/) (metrics)
- [requests](https://pypi.org/project/requests/) (HTTP kald til Delta/SBSYS)
- [python-dotenv](https://pypi.org/project/python-dotenv/) (indlæsning af `.env` lokalt)


### :cloud: Eksterne services/API’er

- **Delta**
  - API: `DELTA_URL` (`POST api/object/graph-query`)
  - Auth: `DELTA_AUTH_URL` + `DELTA_REALM` (OIDC token endpoint)
- **SBSYS/SBSIP**
  - SBSYS API: `SBSYS_URL(_TEST)`
  - Auth (password grant): `SBSIP_URL(_TEST)`

### :heavy_dollar_sign: Miljøvariabler

Applikationen læser miljøvariabler i [src/utils/config.py](src/utils/config.py) og indlæser evt. også en lokal `.env` fil (overskriver **ikke** eksisterende env vars).

#### **Generelle variabler**

| Navn | Default | Beskrivelse |
|---|---:|---|
| `PORT` | `8080` | Port som Flask kører på |
| `DEBUG` | `False` | Flask debug + mere logning |
| `POD_NAME` | `pod_name_not_set` | Bruges som label i readiness-metrics |
| `TESTING` | `True` | Slår test-mode til (se nedenfor) |

#### **SBSYS/SBSIP (production)** *(bruges når `TESTING=False`)*

| Navn | Beskrivelse |
|---|---|
| `SBSYS_URL` | Base URL til SBSYS API |
| `SBSIP_URL` | Base URL til SBSIP auth server |
| `SBSYS_USERNAME` | Brugernavn til password grant |
| `SBSYS_PASSWORD` | Password til password grant |
| `SBSIP_CLIENT_ID` | OIDC client id |
| `SBSIP_CLIENT_SECRET` | OIDC client secret |

#### **SBSYS/SBSIP (test)** *(bruges når `TESTING=True`)*

| Navn | Beskrivelse |
|---|---|
| `SBSYS_URL_TEST` | Base URL til SBSYS API (test) |
| `SBSIP_URL_TEST` | Base URL til SBSIP auth server (test) |
| `SBSYS_USERNAME_TEST` | Brugernavn (test) |
| `SBSYS_PASSWORD_TEST` | Password (test) |
| `SBSIP_CLIENT_ID_TEST` | OIDC client id (test) |
| `SBSIP_CLIENT_SECRET_TEST` | OIDC client secret (test) |

#### **Delta**

| Navn | Beskrivelse |
|---|---|
| `DELTA_URL` | Base URL til Delta API |
| `DELTA_AUTH_URL` | Base URL til Delta auth server |
| `DELTA_REALM` | Realm for token endpoint |
| `DELTA_CLIENT_ID` | OIDC client id |
| `DELTA_CLIENT_SECRET` | OIDC client secret |

#### **Test**

| Navn | Beskrivelse |
|---|---|
| `TEST_CPR_NUMBER` | CPR som bruges når `TESTING=True` |

## Udvikling

### Lokal udvikling (Windows)

1. Opret venv og installer dependencies:
   ```bat
   setup-dev-windows.cmd
   ```
2. Start applikationen:
   ```bat
   python src\main.py
   ```
3. Kør tests:
   ```bat
   pytest
   ```

### Lokal udvikling (Linux/CodeSpace)

1. Opret venv og installer dependencies:
   ```bash
   source ./setup-dev-linux.sh
   ```
2. Start applikationen:
   ```bash
   python src/main.py
   ```
3. Kør tests:
   ```bash
   pytest
   ```

### Kørsel med Docker

- Byg og kør:
  ```bash
  docker compose up --build
  ```

Applikationen eksponeres som standard på `http://localhost:8080`.

### API endpoints

- `GET /healthz` – healthcheck
- `GET /metrics` – Prometheus metrics
- `POST /api/journaliser` – journaliser ambulancebrev

#### Eksempel: kald til `POST /api/journaliser`

**Payload**

```json
{
  "user": "Fornavn Efternavn - dq12345",
  "data": "<base64-enkodet PDF>"
}
```

### Hard-coded værdier (og hvor de ændres)

- **Aktiv sagsstatus**: `SBSYS_SAG_STATUS_ACTIVE = 6` i [src/api_endpoints.py](src/api_endpoints.py).
- **Metadata ved journalisering** (beskrivelse, dokumentnavn, aktindsigt): fastlagt i `SbsysClient.journalize()` i [src/sbsys_client.py](src/sbsys_client.py).
- **Brugerformat**: DQ-nummer udtrækkes ved at splitte på `" - "` i [src/api_endpoints.py](src/api_endpoints.py). Hvis inputformat ændrer sig (X-Flow standard), skal parsing opdateres samme sted.
