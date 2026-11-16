// Schede dei film: cuore, ✓, pulsante "Close" e visore della locandina (usa ui.js)

// Toglie una scheda dopo la dissolvenza; i 500 ms devono coincidere con .removing in card.css
function removeCard(card, list) {
  card.classList.add("removing");
  setTimeout(() => {
    card.remove();
    // Lista rimasta vuota: ricarichiamo per mostrare il messaggio giusto
    if (list && !list.querySelector(".movie-card")) {
      // Il toast visibile sopravvive al ricaricamento passando da sessionStorage
      const toast = document.getElementById("toast");
      if (toast && toast.classList.contains("visible")) {
        sessionStorage.setItem("toast", toast.textContent);
        sessionStorage.setItem("toastType", toast.classList.contains("success") ? "success" : "");
      }
      window.location.reload();
    }
  }, 500);
}

// Aggiorna il contatore della watchlist (nelle altre pagine non c'è e non fa nulla)
function bumpCount(id, delta) {
  const counter = document.getElementById(id);
  if (counter) counter.textContent = Number(counter.textContent) + delta;
}

// Cuore senza ricaricare la pagina; senza JavaScript i form funzionano comunque nel modo classico
document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (!form.classList.contains("heart-form")) return;
  event.preventDefault();

  const card = form.closest(".movie-card");
  const title = card.querySelector(".card-title").textContent;

  // Per togliere un film chiediamo conferma, per aggiungerlo basta un clic
  const removing = form.action.endsWith("/watchlist/remove");
  if (removing && !(await askConfirm(`Remove "${title}" from your watchlist?`))) return;

  const response = await fetch(form.action, {
    method: "POST",
    body: new FormData(form),
    headers: { "X-Requested-With": "fetch" },  // così il server risponde con JSON invece di un redirect
  });

  if (response.status === 401) {  // sessione scaduta
    window.location.href = "/login";
    return;
  }

  if (!response.ok) return;

  const { saved } = await response.json();
  const message = saved ? `"${title}" added to your watchlist` : `"${title}" removed from your watchlist`;
  const type = saved ? "success" : "";

  // Scheda scelta con la ricerca della watchlist: sfuma e la pagina si ricarica (stessi filtri)
  // per aggiornare la lista; il toast passa da sessionStorage e compare dopo
  if (form.closest(".selected-movie[data-reload-on-save]")) {
    sessionStorage.setItem("toast", message);
    sessionStorage.setItem("toastType", type);
    removeCard(card);
    const url = new URL(window.location.href);
    url.searchParams.delete("movie");
    setTimeout(() => window.location.replace(url.pathname + url.search), 500);
    return;
  }

  showToast(message, type);

  // Nella lista della watchlist la scheda tolta sparisce
  const list = form.closest(".watchlist-list");
  if (!saved && list) {
    bumpCount("count-total", -1);
    if (card.querySelector(".check.watched")) bumpCount("count-watched", -1);
    removeCard(card, list);
    return;
  }

  // Altrove (es. home) la scheda resta: aggiorniamo solo il cuore
  const button = form.querySelector(".heart");
  form.action = saved ? "/watchlist/remove" : "/watchlist/add";
  button.classList.toggle("saved", saved);
  button.title = saved ? "Remove from watchlist" : "Add to watchlist";
  button.setAttribute("aria-label", button.title);
});

// ✓ "visto": senza ricaricare la pagina e senza conferma
document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (!form.classList.contains("check-form")) return;
  event.preventDefault();

  const response = await fetch(form.action, {
    method: "POST",
    body: new FormData(form),
    headers: { "X-Requested-With": "fetch" },
  });
  if (response.status === 401) {  // sessione scaduta
    window.location.href = "/login";
    return;
  }
  if (!response.ok) return;

  const { watched } = await response.json();
  const button = form.querySelector(".check");
  form.elements.watched.value = watched ? "0" : "1";  // il prossimo clic farà il contrario
  button.classList.toggle("watched", watched);
  button.title = watched ? "Mark as not watched" : "Mark as watched";
  button.setAttribute("aria-label", button.title);
  bumpCount("count-watched", watched ? 1 : -1);

  const title = form.closest(".movie-card").querySelector(".card-title").textContent;
  if (watched) showToast(`"${title}" marked as watched`, "success");
  else showToast(`"${title}" marked as not watched`);

  // Con il filtro "Watched" o "To watch" attivo, la scheda che non corrisponde più sparisce
  const list = form.closest(".watchlist-list");
  const status = list ? list.dataset.status : "";
  if ((status === "watched" && !watched) || (status === "to_watch" && watched)) {
    removeCard(form.closest(".movie-card"), list);
  }
});

// "Close" in fondo alla scheda aperta
document.addEventListener("click", (event) => {
  const button = event.target.closest(".card-close");
  if (!button) return;
  const card = button.closest(".movie-card");
  card.open = false;
  // Con una sinossi lunga la parte alta può essere uscita dallo schermo: la riportiamo in vista
  if (card.getBoundingClientRect().top < 0) card.scrollIntoView({ behavior: "smooth", block: "start" });
});

// Locandina a schermo intero; un clic ovunque sul visore lo chiude
document.addEventListener("click", (event) => {
  const viewer = document.getElementById("poster-viewer");
  if (!viewer) return;

  if (event.target.closest("#poster-viewer")) {
    closeDialog(viewer);
    return;
  }

  const poster = event.target.closest(".poster");
  if (!poster || poster.src.endsWith("poster-placeholder.svg")) return;

  // Subito la versione già caricata (sfocata), poi quella HD appena arriva
  const image = viewer.querySelector("img");
  image.src = poster.src;
  image.alt = poster.alt;
  image.classList.add("loading");
  viewer.showModal();

  const hd = new Image();
  hd.onload = () => {
    if (!viewer.open) return;  // il visore è stato chiuso nel frattempo
    image.src = hd.src;
    image.classList.remove("loading");
  };
  hd.onerror = () => image.classList.remove("loading");
  hd.src = `/api/poster/${poster.dataset.movieId}?size=original`;
});
