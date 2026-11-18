# CineMatch: accordi tra Core e AI Service

Riferimento unico per le parti in comune. Chi cambia qualcosa qui avvisa gli altri prima di farlo.

## 1. Infrastruttura

- Servizio `ai` nel docker-compose, porta **8001**.
- Il Core lo raggiunge con la variabile `AI_SERVICE_URL`:
  - `http://ai:8001` dentro Docker;
  - `http://localhost:8001` in locale.
- L'AI monta `dataset/catalog` **in sola lettura** e legge `catalog.csv`, `embeddings.npy` e `meta.json`. Gli ID sono quelli di `catalog.csv`.
- Modello: `all-MiniLM-L6-v2`.
- PyTorch **solo CPU**: nel requirements usare `--extra-index-url https://download.pytorch.org/whl/cpu`.
- Il modello si scarica **durante la build dell'immagine**, non al primo avvio.
- L'AI è **stateless**: tutto quello che serve arriva nella richiesta.
- Il Core si avvia anche se l'AI è spenta (niente `depends_on` bloccante). In quel caso mostra "Recommendations are unavailable right now" e il resto del sito funziona.
- Il Core usa un timeout di **1 s per la connessione e 2 s per la lettura** verso l'AI. Per l'AI non c'è Circuit Breaker: c'è solo sulle locandine TMDB.
- Obiettivo di prestazioni: risposta entro **300 ms**, da misurare sul prototipo.

## 2. `GET /health`

```json
{ "status": "ok", "catalog_version": "1cbe923bdda3" }
```

- `catalog_version` è il campo `version` di `dataset/catalog/meta.json`.
- L'endpoint serve all'healthcheck del compose.
- Il Core confronta la versione con la sua: se è diversa registra un avviso, ma non si blocca.

## 3. `POST /recommend`

Un solo endpoint. Il campo `mode` sceglie la strategia (Strategy Registry).

### Richiesta

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| `mode` | string | sempre | `"similar"` oppure `"quiz"` |
| `movie_id` | int | solo in `similar` | il film scelto dall'utente |
| `genres` | list[string] | no (default `[]`) | da 0 a 2, nomi **esatti** del catalogo (vedi §6) |
| `year_min` | int o null | no | compreso nell'intervallo; null = nessun limite |
| `year_max` | int o null | no | compreso nell'intervallo; null = nessun limite |
| `max_runtime` | int o null | no | minuti, compreso; null = nessun limite |
| `tone` | string | solo in `quiz` | una delle chiavi del §5 |
| `exclude_ids` | list[int] | no (default `[]`) | film da non restituire: la watchlist dell'utente, se non spunta "Include movies in my watchlist" (vedi sotto) |
| `limit` | int | no (default `20`) | da 1 a 100; il Core chiede 100 per il "Load more" |

In `similar` i campi del quiz vengono ignorati.

**Film già in watchlist.** In tutte e due le pagine l'utente trova la casella "Include movies in my watchlist", **spenta di default**: normalmente vede solo film che non ha ancora salvato.
- Casella spenta e utente con il login fatto: il Core manda in `exclude_ids` gli id della sua watchlist.
- Casella spuntata, oppure utente senza login: il Core manda una lista vuota.

L'AI non sa niente della casella né della watchlist: toglie semplicemente gli id che riceve.

```json
{ "mode": "similar", "movie_id": 155, "exclude_ids": [13, 680], "limit": 100 }
```

```json
{
  "mode": "quiz",
  "genres": ["Thriller", "Crime"],
  "year_min": 1990,
  "year_max": 2010,
  "max_runtime": 120,
  "tone": "tense",
  "exclude_ids": [],
  "limit": 100
}
```

### Risposta (200)

```json
{
  "results": [
    { "movie_id": 238, "score": 0.734 },
    { "movie_id": 680, "score": 0.712 }
  ],
  "relaxed_filters": ["runtime", "years"],
  "applied": {
    "genres": ["Thriller", "Crime"],
    "year_min": 1980,
    "year_max": 2020,
    "max_runtime": null
  }
}
```

- `results`: al massimo `limit` film, già in ordine (§4).
- `score`: cosine similarity, arrotondata a 3 decimali e portata a 0 se negativa. Il Core decide come mostrarla (es. "73% match").
  - In `similar` è la somiglianza col film scelto.
  - In `quiz` è la somiglianza con il tono.
- `relaxed_filters`: i filtri allentati, nell'ordine in cui è successo. Valori possibili: `"runtime"`, `"years"`, `"genres"`. In `similar` è sempre `[]`.
- `applied`: i filtri **realmente usati** dopo l'allentamento, con null = tolto. Il Core li usa per il messaggio all'utente, es. "We widened the years to 1980–2020". In `similar` vale `null`.

### Errori

- **404**: `movie_id` non presente nel catalogo.
- **422**: input non valido, con il formato automatico di FastAPI. Casi:
  - campo obbligatorio mancante;
  - tono sconosciuto;
  - genere che non esiste;
  - più di 2 generi;
  - `year_min > year_max`;
  - `limit` fuori da 1–100.

## 4. Strategie

### Regole comuni
- **Deterministico**: stessa richiesta, stessa risposta. Niente casualità (niente shuffle o sample).
- **Ordinamento stabile**: a parità di punteggio vince il film con **più voti** (`vote_count`). Se anche i voti sono uguali, vince l'**id più basso**.
- I film in `exclude_ids` vengono tolti **prima** di ordinare e di allentare i filtri. Quando contiene la watchlist (casella "Include movies in my watchlist" non spuntata), i risultati sono tutti film nuovi per l'utente.

### `similar` ("What do you like?")
- Cosine similarity tra l'embedding del film scelto e tutti gli altri film.
- Si escludono il film stesso e gli `exclude_ids`.
- Ordine: `score` decrescente, poi voti, poi id.

### `quiz` ("Feeling lucky")

**Filtri** (un film passa se li rispetta tutti):
- **Generi**: ha **almeno uno** dei generi scelti (OR). Con la lista vuota passano tutti.
- **Anni**: `year_min ≤ year ≤ year_max`. Un limite a null non conta.
- **Durata**: `runtime ≤ max_runtime`. Con il filtro durata attivo, i film senza durata (vuota o 0) vengono esclusi.

**Come funziona**, passo per passo:
1. Si applicano al catalogo i filtri e `exclude_ids`: restano i candidati.
2. Se i candidati sono **meno di 20**, si allenta un filtro (vedi **Allentamento**) e si rifiltra. Si continua finché non si arriva a 20, o finché non resta niente da allentare.
3. Si ordinano i candidati (vedi **Ordine**) e si restituiscono i primi `limit`.

**Tono**:
- Non è un filtro: ordina i candidati.
- Ogni tono è l'embedding della sua frase (o la media, se le frasi sono due), calcolato all'avvio.
- Anche gli embedding dei film sono fissi, quindi lo `score` di ogni film per ogni tono si può calcolare **una volta all'avvio**. A ogni richiesta restano solo filtri e ordinamento, e allentare non obbliga a ricalcolare niente.

**Ordine**: si confronta la prima chiave, e solo a parità si passa alla successiva.
1. `score` col tono, decrescente;
2. `vote_count`, decrescente;
3. `id`, crescente.

I generi servono **solo a filtrare** (almeno uno di quelli scelti) e non spostano l'ordine. Un film con entrambi i generi ma lontano dal tono non passa davanti a un film con un genere solo ma vicino al tono. Così l'ordine dei risultati coincide sempre con la percentuale mostrata all'utente.

L'ordinamento usa lo `score` completo. L'arrotondamento a 3 decimali si fa solo nella risposta.

**Allentamento** (passo 2): un filtro alla volta, in quest'ordine:
  1. **Durata**: +30 minuti a ogni passo. Quando supera il film più lungo del catalogo, il filtro è tolto.
  2. **Anni**: −10 a `year_min` e +10 a `year_max` a ogni passo (es. 1990–2010 → 1980–2020 → 1970–2030 → …). Ogni limite si ferma al primo o all'ultimo anno del catalogo, e si continua ad allargare l'altro. Così l'intervallo resta il più vicino possibile a quello scelto.
  3. **Generi**: si tolgono tutti insieme. L'ordine resta lo stesso: solo per tono.

- Il risultato non è mai vuoto: senza filtri resta tutto il catalogo ordinato per tono.
- La soglia di 20 è fissa, **non dipende da `limit`**: la prima pagina resta il più fedele possibile alle risposte dell'utente.

## 5. Toni

Le **chiavi** sono fisse: il Core le usa nel form con le sue etichette. Le **frasi** le scegliete voi e restano dentro l'AI: l'utente vede solo l'etichetta.

| Chiave | Etichetta nel form |
|---|---|
| `light` | Light & fun |
| `tense` | Tense |
| `emotional` | Emotional |
| `romantic` | Romantic |
| `epic` | Epic adventure |
| `mind_bending` | Mind-bending |
| `scary` | Scary |

### Come scrivere frasi efficaci
L'embedding di un film non contiene solo la sinossi: contiene titolo, `Genres: …`, `Keywords: …` (i temi di TMDB, fino a 15), `Director: …` e sinossi (vedi `movie_text` in `scripts/build_catalog.py`). Le frasi dei toni funzionano meglio se **imitano lo stesso formato**: una frase in stile sinossi, seguita da una riga di keywords tipiche del tono.
- **In inglese**, come i testi dei film e il modello.
- **Descrivere situazioni e temi**, non l'effetto su chi guarda. "A detective races against time to stop a killer" funziona meglio di "a movie that keeps you on the edge of your seat".
- **Keywords reali**: prenderle tra quelle che compaiono davvero nel catalogo (es. le più frequenti nei film del genere più vicino al tono), non inventarle.
- **Niente negazioni** ("not scary", "without violence"): gli embedding le ignorano, e "not scary" finisce vicino a "scary".
- **Una frase per tono** per iniziare. Se il tono dipende troppo da poche parole, se ne aggiunge una seconda e si usa la media dei due vettori: equivale alla media delle due similarità.

### Come verificarle
- Per ogni tono, stampare i primi 15 film del catalogo e controllare a occhio che siano giusti.
- Controllare la similarità tra i vettori dei toni: se due toni superano circa 0.8, sono troppo vicini e una delle frasi va riscritta.

### Proposta iniziale da provare
Le keywords sono state verificate sul catalogo: ognuna compare in almeno 10 film.

- **light**: "A group of friends get into hilarious misadventures on a road trip. Keywords: friendship, best friend, group of friends, road trip, party, holiday."
- **tense**: "A detective races against time to stop a ruthless killer before he strikes again. Keywords: murder, serial killer, suspense, kidnapping, hostage, race against time."
- **emotional**: "After a tragedy, a man struggles to rebuild his life and find hope again. Keywords: dying and death, loss of father, loss of mother, loss of family, cancer, father son relationship."
- **romantic**: "Two strangers fall in love despite everything standing in their way. Keywords: love, new love, love of one's life, romance, romantic comedy."
- **epic**: "A hero embarks on an epic quest across vast lands to defeat a powerful enemy. Keywords: battle, army, war, hero, kingdom, sword and sorcery."
- **mind_bending**: "Reality starts to fall apart as a man uncovers a mystery about time and memory. Keywords: time travel, dream, virtual reality, memory, parallel world, identity."
- **scary**: "A family moves into a house haunted by a terrifying evil presence. Keywords: ghost, supernatural, demon, haunted house, demonic possession, curse, exorcism."

## 6. Dati del catalogo utili

- 4743 film, anni dal 1916 al 2017, durata massima 338 minuti. Oggi tutti hanno la durata.
- Nel CSV i generi sono separati da `|`.
- Generi validi: Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Family, Fantasy, Foreign, History, Horror, Music, Mystery, Romance, Science Fiction, TV Movie, Thriller, War, Western.
- Il primo e l'ultimo anno, la durata massima e i generi validi vanno **calcolati dal catalogo all'avvio**, non scritti nel codice: il catalogo può cambiare.

## 7. Chi fa cosa

**AI Service**:
- `GET /health` e `POST /recommend` come sopra;
- le due strategie nel Registry;
- le frasi dei toni, scelte e provate;
- il Dockerfile.

**Core**:
- il client verso l'AI, con i timeout;
- un finto AI con lo stesso formato, per lavorare in parallelo;
- le pagine "What do you like?" e "Feeling lucky", con:
  - la casella "Include movies in my watchlist", spenta di default: se non è spuntata, il Core manda in `exclude_ids` i film della watchlist;
  - il "Load more" (20 film per volta, fino a 100);
  - la percentuale di somiglianza;
  - il messaggio sui filtri allentati;
  - il messaggio "AI non disponibile".

## 8. Miglioramenti possibili

### Catalogo più pulito
Tra le keywords più frequenti ci sono parole che non dicono niente del film (`duringcreditsstinger`, `aftercreditsstinger`, `woman director`, `independent film`, `based on novel`). Finiscono negli embedding di tutti i film. Toglierle in `scripts/build_catalog.py` migliora sia `similar` sia il tono del quiz.
- Vanno tolte dalla **colonna `keywords` del CSV**, non solo dal testo per gli embedding. La versione del catalogo è un hash di `catalog.csv` e del modello: solo così cambia, e Core e AI si accorgono se uno dei due ha il catalogo vecchio.
- Gli ID restano gli stessi, quindi le watchlist salvate non cambiano. Non vanno tolti film: quelli salvati sparirebbero dalle watchlist.
- `dataset/catalog/` non è nel repository: dopo il pull **ognuno rilancia** `python scripts/build_catalog.py` (completo, non `--catalog-only`).
