import time

# Circuit Breaker riutilizzabile: dopo troppi errori di fila smette di chiamare
# un servizio esterno per un po', poi fa un tentativo di prova (half-open)
class CircuitBreaker:
    def __init__(self, failure_limit: int = 3, cooldown_seconds: float = 30, clock=time.monotonic):
        self.failure_limit = failure_limit        # errori di fila prima di aprire il circuito
        self.cooldown_seconds = cooldown_seconds  # attesa prima del tentativo di prova
        self.clock = clock                        # orologio: nei test lo sostituiamo con uno finto
        self.failures = 0                         # errori di fila finora
        self.opened_at = None                     # momento in cui si è aperto (None = chiuso)

    # "closed" = tutto normale, "open" = non si chiama, "half_open" = attesa finita, si fa una prova
    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        if self.clock() - self.opened_at >= self.cooldown_seconds:
            return "half_open"
        return "open"

    # Vero se possiamo chiamare il servizio
    def allow_request(self) -> bool:
        return self.state != "open"

    # Chiamata riuscita: si torna alla normalità
    def record_success(self):
        self.failures = 0
        self.opened_at = None

    # Chiamata fallita: al limite il circuito si apre; in half-open basta un errore per riaprirlo
    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_limit:
            self.opened_at = self.clock()