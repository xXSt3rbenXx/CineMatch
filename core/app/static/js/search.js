// Casella di ricerca con suggerimenti: funziona su ogni .search presente nella pagina
document.querySelectorAll(".search").forEach((box) => {
  const input = box.querySelector("input");
  const list = box.querySelector(".suggestions");
  let timer;

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
    // Aspetta 250 ms di pausa nella scrittura, per non fare una richiesta a ogni tasto
    clearTimeout(timer);
    timer = setTimeout(showSuggestions, 250);
  });

  async function showSuggestions() {
    const query = input.value.trim();
    const response = await fetch("/api/search?q=" + encodeURIComponent(query));
    const movies = await response.json();

    // Nel frattempo l'utente ha cambiato testo: questa risposta è vecchia
    if (input.value.trim() !== query) return;

    list.innerHTML = "";
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
});
