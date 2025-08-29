import os
import requests
import psycopg2
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


# =====================================
# 1. Autenticação na Amadeus
# =====================================
def autenticar_amadeus():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("AMADEUS_CLIENT_ID"),
        "client_secret": os.getenv("AMADEUS_CLIENT_SECRET"),
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]


# =====================================
# 2. Buscar voos
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
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


# =====================================
# 3. Processar resultados
# =====================================
def processar_resultados(dados, origem, destino, data_ida, data_volta):
    registros = []
    if "data" not in dados:
        return registros

    for oferta in dados["data"]:
        preco_total = oferta["price"]["total"]
        airline = (
            oferta["validatingAirlineCodes"][0]
            if "validatingAirlineCodes" in oferta
            else "N/A"
        )

        registros.append(
            {
                "origin": origem,
                "destination": destino,
                "departure": data_ida,
                "return": data_volta,
                "airline": airline,
                "amadeus_price_brl": float(preco_total),
                "query_time": datetime.now().isoformat(),
                "raw_data": oferta,
            }
        )
    return registros


# =====================================
# 4. Salvar no Supabase (Postgres)
# =====================================
def salvar_supabase(registros):
    db_url = os.getenv("SUPABASE_DB_URL")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    for r in registros:
        cur.execute(
            """
            insert into voos (origin, destination, departure, return, airline, price_brl, raw_data, query_time)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                r.get("origin"),
                r.get("destination"),
                r.get("departure"),
                r.get("return"),
                r.get("airline"),
                r.get("amadeus_price_brl"),
                json.dumps(r.get("raw_data")),
                datetime.now(),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


# =====================================
# 5. Função principal
# =====================================
def comparar_precos():
    access_token = autenticar_amadeus()

    # Parâmetros fixos do problema
    origens = ["GRU", "CGH", "VCP"]  # São Paulo e Campinas
    destino = "NAT"  # Natal
    data_ida = "2025-10-12"
    data_volta = "2025-10-18"

    todos_registros = []
    for origem in origens:
        dados = buscar_voos(access_token, origem, destino, data_ida, data_volta)
        registros = processar_resultados(dados, origem, destino, data_ida, data_volta)
        todos_registros.extend(registros)

    return todos_registros


if __name__ == "__main__":
    resultados = comparar_precos()
    if resultados:
        salvar_supabase(resultados)
        print(f"{len(resultados)} registros salvos no Supabase.")
    else:
        print("Nenhum resultado encontrado.")
