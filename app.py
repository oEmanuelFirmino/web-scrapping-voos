# flight_checker_csv_airlines.py
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import schedule
import time
import pandas as pd

# Carregar credenciais
load_dotenv()
CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

CSV_FILE = "flights_results.csv"


# Função para obter token de acesso
def obter_token():
    auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    auth_data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(auth_url, data=auth_data)
    response.raise_for_status()
    return response.json()["access_token"]


# Função para buscar voos
def buscar_voos(token, origem, destino, data_ida, data_volta):
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "originLocationCode": origem,
        "destinationLocationCode": destino,
        "departureDate": data_ida,
        "returnDate": data_volta,
        "adults": 1,
        "currencyCode": "BRL",  # força retorno em reais
        "max": 20,
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


# Função para ajustar datas
def ajustar_datas(data_ida, data_volta):
    nova_ida = datetime.strptime(data_ida, "%Y-%m-%d") - timedelta(days=1)
    nova_volta = datetime.strptime(data_volta, "%Y-%m-%d") + timedelta(days=1)
    return nova_ida.strftime("%Y-%m-%d"), nova_volta.strftime("%Y-%m-%d")


# Função para salvar no CSV (com companhias + preços)
def salvar_csv(voos, origem, destino):
    if not voos.get("data"):
        return

    carriers = voos.get("dictionaries", {}).get("carriers", {})

    registros = []
    for voo in voos["data"]:
        preco_total = voo["price"]["total"]
        moeda = voo["price"]["currency"]

        airline_codes = voo.get("validatingAirlineCodes", [])
        airline_names = [carriers.get(code, code) for code in airline_codes]

        dep = voo["itineraries"][0]["segments"][0]["departure"]["at"]
        ret = voo["itineraries"][-1]["segments"][-1]["arrival"]["at"]

        registros.append(
            {
                "origin": origem,
                "destination": destino,
                "departure_date": dep,
                "return_date": ret,
                "price_brl": preco_total,
                "currency": moeda,
                "airlines_codes": ",".join(airline_codes),
                "airlines_names": ",".join(airline_names),
                "query_time": datetime.now().isoformat(),
            }
        )

    df = pd.DataFrame(registros)

    # Salvar em CSV
    if not os.path.exists(CSV_FILE):
        df.to_csv(CSV_FILE, index=False, mode="w", encoding="utf-8")
    else:
        df.to_csv(CSV_FILE, index=False, mode="a", header=False, encoding="utf-8")

    print(f"✅ {len(df)} voos salvos no CSV.")


# Função principal
def verificar_voos():
    token = obter_token()
    origens = ["GRU", "CGH", "VCP"]
    destino = "NAT"
    data_ida = "2025-10-12"
    data_volta = "2025-10-18"

    for origem in origens:
        try:
            voos = buscar_voos(token, origem, destino, data_ida, data_volta)
            if voos.get("data"):
                print(f"\nVoos encontrados de {origem} para {destino}.")
                salvar_csv(voos, origem, destino)
            else:
                print(
                    f"\nNenhum voo encontrado de {origem} para {destino}. Tentando datas ajustadas..."
                )
                nova_ida, nova_volta = ajustar_datas(data_ida, data_volta)
                voos_ajustados = buscar_voos(
                    token, origem, destino, nova_ida, nova_volta
                )
                if voos_ajustados.get("data"):
                    print(
                        f"\nVoos encontrados com datas ajustadas de {origem} para {destino}."
                    )
                    salvar_csv(voos_ajustados, origem, destino)
                else:
                    print(
                        f"\nNenhum voo encontrado de {origem} para {destino} mesmo com datas ajustadas."
                    )
        except requests.exceptions.RequestException as e:
            print(f"\nErro ao buscar voos de {origem} para {destino}: {e}")


# Agendamento
schedule.every().day.at("18:34").do(verificar_voos)

print("Monitor de voos iniciado... (Ctrl+C para parar)")
while True:
    schedule.run_pending()
    time.sleep(60)
