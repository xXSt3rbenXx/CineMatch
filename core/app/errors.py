from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.templating import templates

# Titolo e frase per ogni errore; gli altri codici usano GENERIC
MESSAGES = {
    404: ("This page doesn't exist", "The link may be broken, or the page may have been moved."),
    500: ("Something went wrong", "It's a problem on our side. Please try again in a moment."),
}
GENERIC = ("Something went wrong", "This request couldn't be completed.")


# Il JavaScript e le API leggono JSON: a loro una pagina HTML romperebbe il codice
def wants_page(request: Request) -> bool:
    return not request.url.path.startswith("/api/") and request.headers.get("X-Requested-With") != "fetch"


def error_page(request: Request, status_code: int):
    heading, text = MESSAGES.get(status_code, GENERIC)
    return templates.TemplateResponse(
        request,
        "error.html",
        {"title": f"{heading} - CineMatch", "code": status_code, "heading": heading, "text": text},
        status_code=status_code,
    )


# Errori "previsti": pagina inesistente (404), metodo sbagliato (405)...
async def http_error(request: Request, exc: HTTPException):
    if wants_page(request):
        return error_page(request, exc.status_code)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)


# Parametri non validi nell'indirizzo (es. /similar?movie=abc)
async def validation_error(request: Request, exc: RequestValidationError):
    if wants_page(request):
        return error_page(request, 422)
    return JSONResponse({"detail": exc.errors()}, status_code=422)


# Errori imprevisti: all'utente nessun dettaglio tecnico (il dettaglio resta nel terminale del server)
async def server_error(request: Request, exc: Exception):
    if wants_page(request):
        return error_page(request, 500)
    return JSONResponse({"detail": "Internal Server Error"}, status_code=500)