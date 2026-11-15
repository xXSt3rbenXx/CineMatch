from app.circuit_breaker import CircuitBreaker

# Orologio finto: il tempo avanza solo quando lo diciamo noi
class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

def make_breaker():
    clock = FakeClock()
    return CircuitBreaker(failure_limit=3, cooldown_seconds=30, clock=clock), clock

# All'inizio il circuito è chiuso e le chiamate passano
def test_starts_closed():
    breaker, _ = make_breaker()
    assert breaker.state == "closed"
    assert breaker.allow_request()

# Sotto il limite di errori il circuito resta chiuso
def test_stays_closed_below_limit():
    breaker, _ = make_breaker()
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == "closed"

# Al terzo errore di fila si apre e blocca le chiamate
def test_opens_after_limit():
    breaker, _ = make_breaker()
    for _ in range(3):
        breaker.record_failure()
    assert breaker.state == "open"
    assert not breaker.allow_request()

# Un successo azzera il conteggio: gli errori devono essere "di fila"
def test_success_resets_count():
    breaker, _ = make_breaker()
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert breaker.state == "closed"

# Passata l'attesa si passa a half-open e si può fare una prova
def test_half_open_after_cooldown():
    breaker, clock = make_breaker()
    for _ in range(3):
        breaker.record_failure()
    clock.now = 29
    assert breaker.state == "open"
    clock.now = 30
    assert breaker.state == "half_open"
    assert breaker.allow_request()

# In half-open: se la prova riesce si torna chiusi
def test_half_open_success_closes():
    breaker, clock = make_breaker()
    for _ in range(3):
        breaker.record_failure()
    clock.now = 30
    breaker.record_success()
    assert breaker.state == "closed"

# In half-open: se la prova fallisce si riapre subito, per altri 30 secondi
def test_half_open_failure_reopens():
    breaker, clock = make_breaker()
    for _ in range(3):
        breaker.record_failure()
    clock.now = 30
    breaker.record_failure()
    assert breaker.state == "open"
    clock.now = 59
    assert breaker.state == "open"
    clock.now = 60
    assert breaker.state == "half_open"