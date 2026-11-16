// Pezzi generici dell'interfaccia: toast e finestre (<dialog>), usati da cards.js

// Toast: resta 2.5 secondi; type "success" lo colora di verde
function showToast(message, type = "") {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.toggle("success", type === "success");
  toast.classList.add("visible");
  clearTimeout(toast.timer);  // un nuovo toast riparte da capo invece di sparire prima
  toast.timer = setTimeout(() => toast.classList.remove("visible"), 2500);
}

// Toast salvato in sessionStorage da una pagina che si è ricaricata: lo mostriamo ora
document.addEventListener("DOMContentLoaded", () => {
  const message = sessionStorage.getItem("toast");
  if (message) {
    const type = sessionStorage.getItem("toastType") || "";
    sessionStorage.removeItem("toast");
    sessionStorage.removeItem("toastType");
    showToast(message, type);
  }
});

// Chiude un <dialog> dopo la dissolvenza; i 300 ms devono coincidere con l'animazione in dialogs.css
function closeDialog(dialog, value = "") {
  dialog.classList.add("closing");
  setTimeout(() => {
    dialog.classList.remove("closing");
    dialog.close(value);
  }, 300);
}

// Esc (e "indietro" su Android) chiuderebbero subito: passiamo anche loro dalla dissolvenza
document.querySelectorAll("dialog").forEach((dialog) => {
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeDialog(dialog);
  });
});

// Sostituisce confirm(): la promessa vale true solo se si sceglie "Remove"
function askConfirm(message) {
  const dialog = document.getElementById("confirm-dialog");
  if (!dialog) return Promise.resolve(confirm(message));
  dialog.querySelector("#confirm-message").textContent = message;
  dialog.returnValue = "";  // altrimenti resterebbe la risposta della volta prima
  dialog.showModal();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), { once: true });
  });
}

// Il clic sul dialog stesso (non sul riquadro interno) è un clic sullo sfondo: annulla
document.getElementById("confirm-dialog")?.addEventListener("click", (event) => {
  const dialog = event.currentTarget;
  const button = event.target.closest("button[data-value]");
  if (button) closeDialog(dialog, button.dataset.value);
  else if (event.target === dialog) closeDialog(dialog, "cancel");
});
