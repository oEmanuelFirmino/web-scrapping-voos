import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime

# II2One j0Ppje zmMKJ LbIaRd - Classe de onde
# II2One j0Ppje zmMKJ LbIaRd - Classe para onde
# TP4Lpb eoY5cb j0Ppje - Classe Data partida
# https://www.google.com/travel/flights/search?tfs=CBwQAhouEgoyMDI1LTA5LTI4MgJBRDICRzNAC0gXUABYF2oHCAESA0dSVXIHCAESA0NORhomEgoyMDI1LTA5LTMwMgJBRDICRzNqBwgBEgNDTkZyBwgBEgNHUlVAAUgBcAGCAQsI____________AZgBAQ&hl=pt-BR&gl=BR

# --- CONFIGURAÇÕES DA BUSCA ---
# Use os códigos IATA dos aeroportos
ORIGENS = ["GRU", "CGH", "VCP"]  # Guarulhos, Congonhas, Campinas
DESTINO = "NAT"  # Natal
DATA_IDA = "2025-10-12"
DATAS_VOLTA = ["2025-10-18", "2025-10-19"]
COMPANHIAS_ALVO = ["GOL", "LATAM", "Azul"]

# --- FILTROS DE HORÁRIO ---
HORA_MINIMA_IDA = datetime.time(11, 0)
HORA_MINIMA_VOLTA_DIA_18 = datetime.time(18, 0)


def configurar_driver():
    """Configura e retorna o driver do Selenium para o Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # chrome_options.add_argument("--headless")  # Descomente para rodar sem abrir a janela do navegador
    chrome_options.add_argument(
        "--log-level=3"
    )  # Reduz a quantidade de logs no terminal

    # Instala e gerencia o driver do Chrome automaticamente
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def buscar_voos(driver, origem, destino, data_ida, data_volta):
    """Navega no Google Voos e extrai as informações dos voos."""
    resultados = []

    # Monta a URL do Google Voos com os parâmetros da busca
    url = f"https://www.google.com/flights?hl=pt-BR#flt={origem}.{destino}.{data_ida}*{destino}.{origem}.{data_volta}"
    print(f"Buscando em: {url}")
    driver.get(url)

    try:
        # Espera o carregamento dos resultados. O seletor pode mudar, este é um exemplo.
        # Espera até que a lista de voos esteja presente na página
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.JMc5Xc"))
        )
        time.sleep(5)  # Pausa extra para garantir que todo o conteúdo dinâmico carregue

        # Encontra todos os "cards" de voos
        lista_voos = driver.find_elements(By.CSS_SELECTOR, "div.JMc5Xc")

        print(
            f"Encontrados {len(lista_voos)} resultados para {origem} -> {destino} (Volta em {data_volta})"
        )

        for voo in lista_voos:
            try:
                # Extrai as informações de cada card
                # OBS: Estes seletores CSS são os pontos mais frágeis e podem precisar de ajuste se o Google mudar o site.
                companhias = voo.find_element(
                    By.CSS_SELECTOR, "div.sSHqwe.tPgKwe.ogfYpb"
                ).text

                # Pega todos os horários (Partida Ida, Chegada Ida, Partida Volta, Chegada Volta)
                horarios = voo.find_elements(By.CSS_SELECTOR, "span.IMTMDR")
                hora_partida_ida = horarios[0].text
                hora_chegada_ida = horarios[1].text
                hora_partida_volta = horarios[2].text
                hora_chegada_volta = horarios[3].text

                paradas = voo.find_element(
                    By.CSS_SELECTOR, "div.y0NSEb.V1iAHe.sSHqwe.ogfYpb"
                ).text
                duracao = voo.find_element(By.CSS_SELECTOR, "div.XWOp0b").text
                preco = voo.find_element(By.CSS_SELECTOR, "div.YMlIz.FpEdX.").text

                # Adiciona à lista de resultados apenas se for de uma das companhias alvo
                if any(cia.lower() in companhias.lower() for cia in COMPANHIAS_ALVO):
                    resultados.append(
                        {
                            "Companhia": companhias.replace("\n", " "),
                            "Origem": origem,
                            "Destino": destino,
                            "Data_Ida": data_ida,
                            "Hora_Partida_Ida": hora_partida_ida,
                            "Hora_Chegada_Ida": hora_chegada_ida,
                            "Data_Volta": data_volta,
                            "Hora_Partida_Volta": hora_partida_volta,
                            "Hora_Chegada_Volta": hora_chegada_volta,
                            "Duração": duracao,
                            "Paradas": paradas,
                            "Preço": preco,
                        }
                    )
            except Exception as e:
                # Se um card de voo não tiver todas as informações, pula para o próximo
                # print(f"  - Erro ao extrair um voo específico: {e}")
                continue
    except Exception as e:
        print(
            f"  - Não foi possível carregar os resultados para a rota {origem}-{destino}. Erro: {e}"
        )

    return resultados


def aplicar_filtros_horario(df):
    """Aplica os filtros de horário no DataFrame final."""
    # Converte colunas de hora para o formato de tempo para permitir comparações
    df["Hora_Partida_Ida_dt"] = pd.to_datetime(
        df["Hora_Partida_Ida"], format="%H:%M", errors="coerce"
    ).dt.time
    df["Hora_Partida_Volta_dt"] = pd.to_datetime(
        df["Hora_Partida_Volta"], format="%H:%M", errors="coerce"
    ).dt.time

    # Condição 1: Voo de ida a partir das 11h
    condicao_ida = df["Hora_Partida_Ida_dt"] >= HORA_MINIMA_IDA

    # Condição 2: Para a volta no dia 18, o voo deve ser a partir das 18h
    condicao_volta_18 = (df["Data_Volta"] != "2025-10-18") | (
        (df["Data_Volta"] == "2025-10-18")
        & (df["Hora_Partida_Volta_dt"] >= HORA_MINIMA_VOLTA_DIA_18)
    )

    df_filtrado = df[condicao_ida & condicao_volta_18].copy()

    # Remove colunas de tempo auxiliares
    df_filtrado.drop(
        columns=["Hora_Partida_Ida_dt", "Hora_Partida_Volta_dt"], inplace=True
    )

    return df_filtrado


# --- BLOCO PRINCIPAL DE EXECUÇÃO ---
if __name__ == "__main__":
    driver = configurar_driver()
    todos_os_voos = []

    # Loop para buscar todas as combinações de origens e datas de volta
    for origem in ORIGENS:
        for data_volta in DATAS_VOLTA:
            voos_encontrados = buscar_voos(
                driver, origem, DESTINO, DATA_IDA, data_volta
            )
            todos_os_voos.extend(voos_encontrados)
            time.sleep(2)  # Pausa de cortesia entre as buscas

    driver.quit()

    if not todos_os_voos:
        print(
            "\nNenhum voo foi encontrado. Verifique os seletores CSS no script ou a sua conexão."
        )
    else:
        # Cria o DataFrame com todos os voos
        df_bruto = pd.DataFrame(todos_os_voos)

        # Aplica os filtros de horário
        print("\nAplicando filtros de horário...")
        df_final = aplicar_filtros_horario(df_bruto)

        # Salva o resultado em um arquivo CSV
        nome_arquivo = "voos_encontrados_natal.csv"
        df_final.to_csv(nome_arquivo, index=False, encoding="utf-8-sig")

        print("-" * 50)
        print(
            f"Busca finalizada! {len(df_final)} voos que atendem aos critérios foram salvos em '{nome_arquivo}'"
        )
        print("-" * 50)
