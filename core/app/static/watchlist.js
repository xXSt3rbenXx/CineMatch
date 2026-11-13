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
  const button = form.querySelector(".heart");
  form.action = saved ? "/watchlist/remove" : "/watchlist/add";
  button.textContent = saved ? "♥" : "♡";
  button.title = saved ? "Remove from watchlist" : "Add to watchlist";
  button.setAttribute("aria-label", button.title);
});