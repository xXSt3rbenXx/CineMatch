// Casella di ricerca con suggerimenti: funziona su ogni .search presente nella pagina
document.querySelectorAll(".search").forEach((box) => {
  const input = box.querySelector("input");
  const list = box.querySelector(".suggestions");
  let timer;
  let active = -1;  // posizione del suggerimento evidenziato con le frecce; -1 = nessuno
  let closeTimer;

  const clear = box.querySelector(".clear");  // c'è solo se un film è già stato scelto

  // Toglie il film scelto senza ricaricare; replaceState lo toglie anche dall'indirizzo,
  // così ricaricando la pagina la scheda non torna
  function deselect() {
    if (!clear || !clear.isConnected) return;  // già fatto
    clear.remove();
    const selected = document.querySelector(".selected-movie .movie-card");
    if (selected) removeCard(selected);
    const url = new URL(window.location.href);
    url.searchParams.delete("movie");
    history.replaceState(null, "", url.pathname + url.search);
  }

  // Senza JavaScript la X resta un link che ricarica la pagina
  if (clear) {
    clear.addEventListener("click", (event) => {
      event.preventDefault();
      input.value = "";
      deselect();
      input.focus();
    });
  }

  // Modificare il titolo del film scelto vuol dire cercarne un altro
  input.addEventListener("input", () => {
    deselect();
    clearTimeout(timer);
    // Casella vuota: niente da cercare, l'elenco sfuma via subito senza aspettare
        if (!input.value.trim()) {
      timer = setTimeout(closeSuggestions, 100);
      return;
    }
    // Aspetta 250 ms di pausa nella scrittura, per non fare una richiesta a ogni tasto
    timer = setTimeout(showSuggestions, 250);
  });

  async function showSuggestions() {
    const query = input.value.trim();
    const response = await fetch("/api/search?q=" + encodeURIComponent(query));
    const movies = await response.json();

    // Nel frattempo l'utente ha cambiato testo: questa risposta è vecchia
    if (input.value.trim() !== query) return;

    // Nessun risultato (o testo troppo corto): l'elenco sfuma via invece di sparire di colpo
    if (!movies.length) {
      closeSuggestions();
      return;
    }

    // Una chiusura ancora in corso non deve cancellare i suggerimenti nuovi
    clearTimeout(closeTimer);
    list.classList.remove("closing");

    list.innerHTML = "";
    active = -1;

    for (const movie of movies) {
      // Stessa pagina con ?movie=id: gli altri parametri (es. i filtri della watchlist) restano
      const url = new URL(window.location.href);
      url.searchParams.set("movie", movie.id);

      const link = document.createElement("a");
      link.href = url.pathname + url.search;
      // textContent e non innerHTML: un titolo non viene mai interpretato come HTML
      link.textContent = movie.title + " (" + movie.year + ")";
      const item = document.createElement("li");
      item.appendChild(link);
      list.appendChild(item);
    }
  }
  
  // Evidenzia un suggerimento; dopo l'ultimo si torna al primo, prima del primo si va all'ultimo
  function highlight(index) {
    const links = list.querySelectorAll("a");
    if (!links.length) return;
    if (index < 0) index = links.length - 1;
    if (index >= links.length) index = 0;
    active = index;
    links.forEach((link, i) => link.classList.toggle("active", i === active));
  }

  // Prima la dissolvenza, poi lo svuotamento; i 150 ms coincidono con .suggestions in forms.css
  function closeSuggestions() {
    clearTimeout(closeTimer);  // una sola chiusura alla volta
    active = -1;
    if (!list.children.length) return;
    list.classList.add("closing");
    closeTimer = setTimeout(() => {
      list.innerHTML = "";
      list.classList.remove("closing");
    }, 150);
  }

  // Frecce, Invio ed Esc, come nella ricerca di Google
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();  // altrimenti il cursore del testo salterebbe alla fine
      highlight(active + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      highlight(active === -1 ? -1 : active - 1);
    } else if (event.key === "Enter") {
      const link = list.querySelectorAll("a")[active];
      if (link) window.location.href = link.href;
    } else if (event.key === "Escape") {
      closeSuggestions();
    }
  });

  // L'elenco si chiude cliccando fuori dalla casella
  document.addEventListener("click", (event) => {
    if (!box.contains(event.target)) closeSuggestions();
  });

  // e si riapre tornando nella casella, se c'è del testo e non c'è già un film scelto
  input.addEventListener("focus", () => {
    const movieChosen = clear && clear.isConnected;
    if (input.value.trim() && !list.children.length && !movieChosen) showSuggestions();
  });

});
