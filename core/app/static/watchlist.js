// Fa sparire una scheda con una breve dissolvenza, poi la toglie dalla pagina
function removeCard(card, list) {
  card.classList.add("removing");  // avvia la dissolvenza definita nel CSS
  setTimeout(() => {
    card.remove();
    // Se non resta nessun film, ricarichiamo per mostrare il messaggio giusto
    if (!list.querySelector(".movie-card")) window.location.reload();
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

  // Aggiorna il cuore: pieno se salvato, vuoto se tolto
  const { saved } = await response.json();

  // Nella pagina della watchlist la scheda tolta sparisce subito
  const list = form.closest(".watchlist-list");
  if (!saved && list) {
    const card = form.closest(".movie-card");
    bumpCount("count-total", -1);
    
    // Se il film tolto era segnato come visto, scende anche quel numero
    if (card.querySelector(".check.watched")) bumpCount("count-watched", -1);
    removeCard(form.closest(".movie-card"), list);
    return;
  }

  const button = form.querySelector(".heart");
  form.action = saved ? "/watchlist/remove" : "/watchlist/add";
  button.textContent = saved ? "♥" : "♡";
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