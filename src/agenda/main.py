from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agenda.api.genders import router as genders_router
from agenda.api.addresses import router as addresses_router
from agenda.api.localities import router as localities_router
from agenda.api.users import router as users_router

app = FastAPI(title='Agenda')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(genders_router)
app.include_router(addresses_router)
app.include_router(localities_router)
app.include_router(users_router)

@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'agenda'}

