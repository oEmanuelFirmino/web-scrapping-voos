# flight_checker_hybrid.py
import requests
import os
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime

# Carregar credenciais Amadeus
load_dotenv()
CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

CSV_FILE = "flights_hybrid_results.csv"


# ========= AMADEUS ==========
def obter_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    r = requests.post(url, data=data)
    r.raise_for_status()
    return r.json()["access_token"]


def buscar_voos_amadeus(token, origem, destino, data_ida, data_volta):
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "originLocationCode": origem,
        "destinationLocationCode": destino,
        "departureDate": data_ida,
        "returnDate": data_volta,
        "adults": 1,
        "currencyCode": "BRL",
        "max": 5,
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


# ========= SCRAPING ==========
def buscar_preco_gol(origem, destino, data_ida, data_volta):
    """Scraping simplificado do buscador da GOL"""
    url = f"https://b2c.voegol.com.br/compra/busca-flights?from={origem}&to={destino}&departure={data_ida}&return={data_volta}&adt=1&chd=0&inf=0"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    preco = soup.find("span", {"class": "amount"})
    if preco:
        return preco.get_text().strip()
    return None


def buscar_preco_latam(origem, destino, data_ida, data_volta):
    """Scraping simplificado LATAM"""
    url = f"https://www.latamairlines.com/br/pt/oferta/voos?origin={origem}&destination={destino}&departure={data_ida}&return={data_volta}&adults=1&children=0&infants=0"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    preco = soup.find("span", {"class": "price"})
    if preco:
        return preco.get_text().strip()
    return None


def buscar_preco_azul(origem, destino, data_ida, data_volta):
    """Scraping simplificado Azul"""
    url = f"https://www.voeazul.com.br/br/pt/home/selecao-de-voo?from={origem}&to={destino}&departure={data_ida}&return={data_volta}&adults=1&children=0&infants=0"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    preco = soup.find("span", {"class": "valor"})
    if preco:
        return preco.get_text().strip()
    return None


# ========= PIPELINE ==========
def comparar_precos():
    token = obter_token()
    origem, destino = "GRU", "NAT"
    data_ida, data_volta = "2025-10-12", "2025-10-18"

    voos_amadeus = buscar_voos_amadeus(token, origem, destino, data_ida, data_volta)

    registros = []
    for voo in voos_amadeus.get("data", []):
        preco_amadeus = voo["price"]["total"]
        cia = ",".join(voo.get("validatingAirlineCodes", []))

        # Scraping paralelo
        preco_gol = buscar_preco_gol(origem, destino, data_ida, data_volta)
        preco_latam = buscar_preco_latam(origem, destino, data_ida, data_volta)
        preco_azul = buscar_preco_azul(origem, destino, data_ida, data_volta)

        registros.append(
            {
                "origin": origem,
                "destination": destino,
                "departure": data_ida,
                "return": data_volta,
                "airline": cia,
                "amadeus_price_brl": preco_amadeus,
                "gol_price": preco_gol,
                "latam_price": preco_latam,
                "azul_price": preco_azul,
                "query_time": datetime.now().isoformat(),
            }
        )

    df = pd.DataFrame(registros)

    if not os.path.exists(CSV_FILE):
        df.to_csv(CSV_FILE, index=False, mode="w", encoding="utf-8")
    else:
        df.to_csv(CSV_FILE, index=False, mode="a", header=False, encoding="utf-8")

    print(df)


if __name__ == "__main__":
    comparar_precos()
