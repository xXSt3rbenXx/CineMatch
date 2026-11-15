// Casella di ricerca con suggerimenti: funziona su ogni .search presente nella pagina
document.querySelectorAll(".search").forEach((box) => {
  const input = box.querySelector("input");
  const list = box.querySelector(".suggestions");
  let timer;

  const clear = box.querySelector(".clear");  // la X, presente solo se c'è un film scelto

  // Toglie il film scelto: via la X e la scheda (con la dissolvenza della watchlist)
  // e via ?movie=id dall'indirizzo, così ricaricando la pagina la scheda non torna
  function deselect() {
    if (!clear || !clear.isConnected) return;  // già fatto (o nessun film scelto)
    clear.remove();
    const selected = document.querySelector(".selected-movie .movie-card");
    if (selected) removeCard(selected);
    const url = new URL(window.location.href);
    url.searchParams.delete("movie");
    history.replaceState(null, "", url.pathname + url.search);
  }

  // La X: svuota la casella e toglie il film scelto senza ricaricare la pagina
  if (clear) {
    clear.addEventListener("click", (event) => {
      event.preventDefault();
      input.value = "";
      deselect();
      input.focus();  // pronta per una nuova ricerca
    });
  }

  // Modificare il titolo del film scelto vuol dire cercarne un altro
  input.addEventListener("input", () => {
    deselect();
    // Aspetta che l'utente smetta di scrivere per 250 ms, poi chiede i suggerimenti
    clearTimeout(timer);
    timer = setTimeout(showSuggestions, 250);
  });

  async function showSuggestions() {
    const query = input.value.trim();
    const response = await fetch("/api/search?q=" + encodeURIComponent(query));
    const movies = await response.json();

    // Se nel frattempo l'utente ha cambiato testo, questa risposta è vecchia: la ignoriamo
    if (input.value.trim() !== query) return;

    list.innerHTML = "";  // svuota i suggerimenti precedenti
    for (const movie of movies) {
      // Stessa pagina con ?movie=id; gli altri parametri (es. i filtri della watchlist) restano
      const url = new URL(window.location.href);
      url.searchParams.set("movie", movie.id);

      const link = document.createElement("a");
      link.href = url.pathname + url.search;
      // textContent mostra il titolo come semplice testo, mai come HTML
      link.textContent = movie.title + " (" + movie.year + ")";
      const item = document.createElement("li");
      item.appendChild(link);
      list.appendChild(item);
    }
  }
});