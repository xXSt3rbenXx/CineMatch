// Messaggio temporaneo in basso ("toast"): compare, resta 2.5 secondi e sparisce
function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => toast.classList.remove("visible"), 2500);
}

// Toast lasciato dalla pagina prima di ricaricarsi: lo mostriamo ora
document.addEventListener("DOMContentLoaded", () => {
  const message = sessionStorage.getItem("toast");
  if (message) {
    sessionStorage.removeItem("toast");
    showToast(message);
  }
});

// Fa sparire una scheda con una breve dissolvenza, poi la toglie dalla pagina
function removeCard(card, list) {
  card.classList.add("removing");  // avvia la dissolvenza definita nel CSS
  setTimeout(() => {
    card.remove();
    // Se c'è una lista e non resta nessun film, ricarichiamo per mostrare il messaggio giusto
    if (list && !list.querySelector(".movie-card")) {
      // Se c'è un toast visibile, lo "portiamo" oltre il ricaricamento
      const toast = document.getElementById("toast");
      if (toast && toast.classList.contains("visible")) sessionStorage.setItem("toast", toast.textContent);
      window.location.reload();
    }
  }, 500);  // 500 ms: la durata della dissolvenza
}

// Aggiorna un numero del contatore in cima alla watchlist (nelle altre pagine non c'è e non fa nulla)
function bumpCount(id, delta) {
  const counter = document.getElementById(id);
  if (counter) counter.textContent = Number(counter.textContent) + delta;
}

// Cuore della watchlist senza ricaricare la pagina.
// Se questo script non parte, i form funzionano comunque nel modo classico (con ricaricamento).
document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (!form.classList.contains("heart-form")) return;  // ci interessano solo i cuori
  event.preventDefault();  // blocca l'invio classico del form

  const removing = form.action.endsWith("/watchlist/remove");
  // Per togliere un film chiediamo conferma, per aggiungerlo basta un clic
  if (removing && !confirm("Remove this movie from your watchlist?")) return;

  const response = await fetch(form.action, {
    method: "POST",
    body: new FormData(form),
    headers: { "X-Requested-With": "fetch" },  // così il server risponde con un JSON
  });

  if (response.status === 401) {  // la sessione è scaduta: serve rifare il login
    window.location.href = "/login";
    return;
  }

  if (!response.ok) return;

    const { saved } = await response.json();
  const card = form.closest(".movie-card");
  const title = card.querySelector(".card-title").textContent;
  const message = saved ? `"${title}" added to your watchlist` : `"${title}" removed from your watchlist`;

// Cuore della scheda scelta con la ricerca della watchlist: la scheda sfuma e la pagina.
  if (form.closest(".selected-movie[data-reload-on-save]")) {
    sessionStorage.setItem("toast", message);
    removeCard(card);
    const url = new URL(window.location.href);
    url.searchParams.delete("movie");
    setTimeout(() => window.location.replace(url.pathname + url.search), 500);
    return;
  }

  showToast(message);

  // Nella lista della watchlist la scheda tolta sparisce
  const list = form.closest(".watchlist-list");
  if (!saved && list) {
    bumpCount("count-total", -1);
    // Se il film tolto era segnato come visto, scende anche quel numero
    if (card.querySelector(".check.watched")) bumpCount("count-watched", -1);
    removeCard(card, list);
    return;
  }

  // Altrove (es. home) la scheda resta: aggiorniamo solo il cuore
  const button = form.querySelector(".heart");
  form.action = saved ? "/watchlist/remove" : "/watchlist/add";
  button.classList.toggle("saved", saved);  // il CSS riempie il cuore se il film è salvato
  button.title = saved ? "Remove from watchlist" : "Add to watchlist";
  button.setAttribute("aria-label", button.title);
});

// Segno "visto" nella watchlist: si accende e si spegne senza ricaricare la pagina e senza conferma
document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (!form.classList.contains("check-form")) return;  // ci interessano solo i ✓
  event.preventDefault();

  const response = await fetch(form.action, {
    method: "POST",
    body: new FormData(form),
    headers: { "X-Requested-With": "fetch" },
  });
  if (response.status === 401) {  // la sessione è scaduta: serve rifare il login
    window.location.href = "/login";
    return;
  }
  if (!response.ok) return;

  // Aggiorna il ✓: verde se visto, grigio se da vedere
  const { watched } = await response.json();
  const button = form.querySelector(".check");
  form.elements.watched.value = watched ? "0" : "1";  // il prossimo clic farà il contrario
  button.classList.toggle("watched", watched);
  button.title = watched ? "Mark as not watched" : "Mark as watched";
  button.setAttribute("aria-label", button.title);
  bumpCount("count-watched", watched ? 1 : -1);

  // Con il filtro "Watched" o "To watch" attivo, la scheda che non corrisponde più sparisce
  const list = form.closest(".watchlist-list");
  const status = list ? list.dataset.status : "";
  if ((status === "watched" && !watched) || (status === "to_watch" && watched)) {
    removeCard(form.closest(".movie-card"), list);
  }
});

// Pulsante "Close" in fondo alla scheda aperta: chiude la scheda
document.addEventListener("click", (event) => {
  const button = event.target.closest(".card-close");
  if (!button) return;
  const card = button.closest(".movie-card");
  card.open = false;
  // Se la parte alta della scheda è uscita dallo schermo, la riportiamo in vista
  if (card.getBoundingClientRect().top < 0) card.scrollIntoView({ behavior: "smooth", block: "start" });
});

// Locandina a schermo intero: cliccandola si apre sopra la pagina, un clic ovunque la chiude
document.addEventListener("click", (event) => {
  const viewer = document.getElementById("poster-viewer");
  if (!viewer) return;

  // Clic sul visore aperto (immagine o sfondo): si chiude
  if (event.target.closest("#poster-viewer")) {
    viewer.close();
    return;
  }

  const poster = event.target.closest(".poster");
  if (!poster || poster.src.endsWith("poster-placeholder.svg")) return;  // il placeholder non si ingrandisce

  const image = viewer.querySelector("img");
  image.src = poster.src;  // subito la versione già caricata, sfocata...
  image.alt = poster.alt;
  image.classList.add("loading");
  viewer.showModal();

  // Appena arriva quella in alta qualità la mettiamo a fuoco
  const hd = new Image();
  hd.onload = () => {
    if (!viewer.open) return;
    image.src = hd.src;
    image.classList.remove("loading");
  };
  hd.onerror = () => image.classList.remove("loading");  // se la HD non arriva, togliamo almeno la sfocatura
  hd.src = `/api/poster/${poster.dataset.movieId}?size=original`;
});