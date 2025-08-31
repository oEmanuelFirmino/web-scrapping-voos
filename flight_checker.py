import os
import requests
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()  # Carrega variáveis do .env

# =====================================
# Supabase SDK
# =====================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# =====================================
# Autenticar Amadeus
# =====================================
def autenticar_amadeus():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("AMADEUS_CLIENT_ID"),
        "client_secret": os.getenv("AMADEUS_CLIENT_SECRET"),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()
    return response.json()["access_token"]


# =====================================
# Buscar voos
# =====================================
def buscar_voos(access_token, origem, destino, data_ida, data_volta):
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origem,
        "destinationLocationCode": destino,
        "departureDate": data_ida,
        "returnDate": data_volta,
        "adults": 1,
        "currencyCode": "BRL",
        "max": 10,
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


# =====================================
# Processar resultados
# =====================================
def processar_resultados(dados, origem, destino, data_ida, data_volta):
    registros = []
    for oferta in dados.get("data", []):
        preco_total = oferta["price"]["total"]
        airline = oferta.get("validatingAirlineCodes", ["N/A"])[0]
        registros.append(
            {
                "origin": origem,
                "destination": destino,
                "departure": data_ida,
                "return": data_volta,
                "airline": airline,
                "price_brl": float(preco_total),
                "raw_data": oferta,
                "query_time": datetime.now().isoformat(),
            }
        )
    return registros


# =====================================
# Salvar no Supabase
# =====================================
def salvar_supabase(registros):
    if not registros:
        print("Nenhum registro para salvar.")
        return

    try:
        response = supabase.table("voos").insert(registros).execute()
        print(f"{len(response.data)} registros salvos no Supabase.")
    except Exception as e:
        print("Erro ao salvar no Supabase:", e)


# =====================================
# Função principal
# =====================================
def comparar_precos():
    token = autenticar_amadeus()
    origens = [o.strip().upper() for o in os.getenv("ORIGENS", "GRU,VCP").split(",")]
    destino = os.getenv("DESTINO", "NAT")
    data_ida = os.getenv("DATA_IDA", "2025-10-12")
    data_volta = os.getenv("DATA_VOLTA", "2025-10-18")

    todos_registros = []
    for origem in origens:
        dados = buscar_voos(token, origem, destino, data_ida, data_volta)
        registros = processar_resultados(dados, origem, destino, data_ida, data_volta)
        todos_registros.extend(registros)

    return todos_registros


# =====================================
# Executar
# =====================================
if __name__ == "__main__":
    resultados = comparar_precos()
    salvar_supabase(resultados)
