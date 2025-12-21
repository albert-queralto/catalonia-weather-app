from fastapi import APIRouter, Response, Query
import httpx

router = APIRouter()

@router.get("/aca/pluviometers")
async def get_aca_pluviometers():
    url = "https://aplicacions.aca.gencat.cat/sdim2/apirest/catalog?componentType=pluviometre"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return Response(content=r.content, media_type="application/json")

@router.get("/aca/pluviometer_data")
async def get_pluviometer_data():
    url = "https://aplicacions.aca.gencat.cat/sdim2/apirest/data/PLUVIOMETREACA-EST"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return Response(content=r.content, media_type="application/json")