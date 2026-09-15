# ---------------------------------------------------------------------------
# 1. PREPARAÇÃO E LEITURA DOS DADOS
# # ---------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt


st.set_page_config(
    page_title="Menor Rota entre Aeroportos",
    layout="wide"
)

st.title("Rotas Aeroporto")


# ---------------------------------------------------------------------------
# 2. Leitura dos Dados da Planilha e Pré-Visualização
# ---------------------------------------------------------------------------

arquivo = "aerportos_brasil.xlsx"

xls = pd.ExcelFile(arquivo)

df = pd.read_excel(
    xls,
    sheet_name="Planilha2"
)

st.write("Pré-visualização dos dados:")

df_visualizacao = df.drop(
    columns=[
        "tipo_distancia",
        "grafo"
    ]
).rename(
    columns={
        "origem_iata": "IATA Origem",
        "origem_aeroporto": "Aeroporto de Origem",
        "origem_cidade": "Cidade de Origem",
        "origem_uf": "UF Origem",
        "destino_iata": "IATA Destino",
        "destino_aeroporto": "Aeroporto de Destino",
        "destino_cidade": "Cidade de Destino",
        "destino_uf": "UF Destino",
        "distancia_km": "Distância (km)"
    }
)

st.dataframe(
    df_visualizacao,
    use_container_width=True,
    height=500,
    hide_index=True
)


# ---------------------------------------------------------------------------
# 3. CONSTRUÇÃO DO GRAFO DE ROTAS AÉREAS
# ---------------------------------------------------------------------------

col_origem = "origem_iata"
col_destino = "destino_iata"

col_cidade_origem = "origem_cidade"
col_cidade_destino = "destino_cidade"

col_peso = "distancia_km"

grafo_dirigido = True


# Seleciona apenas as colunas necessárias

df_validos = df[
    [
        col_origem,
        col_destino,
        col_cidade_origem,
        col_cidade_destino,
        col_peso
    ]
].dropna(
    subset=[
        col_origem,
        col_destino,
        col_cidade_origem,
        col_cidade_destino,
        col_peso
    ]
)


# Verifica se a distância é numérica

df_validos = df_validos[
    pd.to_numeric(
        df_validos[col_peso],
        errors="coerce"
    ).notna()
]


# Converte a distância para float

df_validos[col_peso] = df_validos[col_peso].astype(float)


# Cria o grafo direcionado

G = nx.DiGraph()


# Adiciona os aeroportos e as conexões ao grafo

for _, row in df_validos.iterrows():

    origem = str(row[col_origem]).strip()
    destino = str(row[col_destino]).strip()
    peso = float(row[col_peso])

    G.add_edge(
        origem,
        destino,
        weight=peso
    )


# ---------------------------------------------------------------------------
# 4. Relaciona aeroportos às cidades
# ---------------------------------------------------------------------------

aeroporto_cidade = {}


for _, row in df_validos.iterrows():

    aeroporto_origem = str(row[col_origem]).strip()
    cidade_origem = str(row[col_cidade_origem]).strip()

    aeroporto_destino = str(row[col_destino]).strip()
    cidade_destino = str(row[col_cidade_destino]).strip()

    aeroporto_cidade[aeroporto_origem] = cidade_origem
    aeroporto_cidade[aeroporto_destino] = cidade_destino


# Lista de cidades disponíveis

cidades = sorted(
    set(aeroporto_cidade.values())
)


# ---------------------------------------------------------------------------
# MENSAGEM NA INTERFACE COM QUANTIDADE DE AEROPORTOS E CONEXÕES
# ---------------------------------------------------------------------------

st.success(
    f"Grafo construído com "
    f"{G.number_of_nodes()} aeroportos e "
    f"{G.number_of_edges()} conexões."
)


# ---------------------------------------------------------------------------
# 5. Escolha de origem e destino
# ---------------------------------------------------------------------------

st.header("Escolha Origem e Destino")


col_a, col_b = st.columns(2)


with col_a:

    partida = st.selectbox(
        "Cidade de Origem",
        cidades,
        key="partida"
    )


with col_b:

    destino_default = 1 if len(cidades) > 1 else 0

    chegada = st.selectbox(
        "Cidade de Destino",
        cidades,
        index=destino_default,
        key="chegada"
    )


calcular = st.button(
    "Calcular melhores escolhas",
    type="primary"
)


# ---------------------------------------------------------------------------
# 6. Execução do Dijkstra
# ---------------------------------------------------------------------------

if calcular:

    if partida == chegada:

        st.warning(
            "Selecione cidades de origem e destino diferentes."
        )

        st.stop()


    # -----------------------------------------------------------------------
    # Encontra todos os aeroportos das cidades escolhidas
    # -----------------------------------------------------------------------

    aeroportos_origem = [
        aeroporto
        for aeroporto, cidade in aeroporto_cidade.items()
        if cidade == partida
    ]


    aeroportos_destino = [
        aeroporto
        for aeroporto, cidade in aeroporto_cidade.items()
        if cidade == chegada
    ]


    # -----------------------------------------------------------------------
    # 1. ROTA COM MENOR DISTÂNCIA
    # -----------------------------------------------------------------------

    melhor_caminho_distancia = None
    menor_distancia = float("inf")


    for aeroporto_origem in aeroportos_origem:

        for aeroporto_destino in aeroportos_destino:

            try:

                caminho = nx.dijkstra_path(
                    G,
                    aeroporto_origem,
                    aeroporto_destino,
                    weight="weight"
                )


                distancia = nx.dijkstra_path_length(
                    G,
                    aeroporto_origem,
                    aeroporto_destino,
                    weight="weight"
                )


                if distancia < menor_distancia:

                    menor_distancia = distancia
                    melhor_caminho_distancia = caminho


            except nx.NetworkXNoPath:

                continue


    # -----------------------------------------------------------------------
    # 2. ROTA COM MENOR NÚMERO DE CONEXÕES
    # -----------------------------------------------------------------------

    melhor_caminho_conexoes = None
    menor_numero_conexoes = float("inf")
    menor_distancia_conexoes = float("inf")


    for aeroporto_origem in aeroportos_origem:

        for aeroporto_destino in aeroportos_destino:

            try:

                # Cada conexão recebe peso 1.
                # Assim, o Dijkstra procura primeiro
                # o caminho com a menor quantidade de conexões.

                caminho = nx.dijkstra_path(
                    G,
                    aeroporto_origem,
                    aeroporto_destino,
                    weight=lambda u, v, d: 1
                )


                numero_conexoes = len(caminho) - 1


                # Calcula a distância real da rota encontrada

                distancia_rota = 0


                for i in range(
                    len(caminho) - 1
                ):

                    distancia_rota += G[
                        caminho[i]
                    ][
                        caminho[i + 1]
                    ]["weight"]


                # Critério principal:
                # menor número de conexões.
                #
                # Critério de desempate:
                # menor distância entre as rotas
                # que possuem o mesmo número de conexões.

                if (
                    numero_conexoes < menor_numero_conexoes
                    or (
                        numero_conexoes == menor_numero_conexoes
                        and distancia_rota < menor_distancia_conexoes
                    )
                ):

                    menor_numero_conexoes = numero_conexoes
                    menor_distancia_conexoes = distancia_rota
                    melhor_caminho_conexoes = caminho


            except nx.NetworkXNoPath:

                continue


    # -----------------------------------------------------------------------
    # Verifica se existe alguma rota
    # -----------------------------------------------------------------------

    if (
        melhor_caminho_distancia is None
        and melhor_caminho_conexoes is None
    ):

        st.error(
            f"Não existe rota conectando "
            f"{partida} a {chegada} no grafo."
        )

        st.stop()


    # =======================================================================
    # ROTA COM MENOR DISTÂNCIA
    # =======================================================================

    if melhor_caminho_distancia is not None:

        st.markdown(
            "### Rota com menor distância"
        )


        # ---------------------------------------------------------------
        # Mostra cidade + aeroporto
        # ---------------------------------------------------------------

        rota_detalhada_distancia = []


        for aeroporto in melhor_caminho_distancia:

            cidade = aeroporto_cidade[aeroporto]

            rota_detalhada_distancia.append(
                f"{cidade} ({aeroporto})"
            )


        st.markdown(
            f"{' → '.join(rota_detalhada_distancia)}"
        )


        st.markdown(
            f"**Distância total:** "
            f"{menor_distancia:.2f} km"
        )


        st.markdown(
            f"**Número de conexões:** "
            f"{len(melhor_caminho_distancia) - 1}"
        )


        st.markdown(
            f"**Aeroportos utilizados:** "
            f"{' → '.join(melhor_caminho_distancia)}"
        )


        # ---------------------------------------------------------------
        # Detalhamento dos trechos
        # ---------------------------------------------------------------

        trechos_distancia = []


        for i in range(
            len(melhor_caminho_distancia) - 1
        ):

            aeroporto_origem = melhor_caminho_distancia[i]
            aeroporto_destino = melhor_caminho_distancia[i + 1]

            cidade_origem = aeroporto_cidade[
                aeroporto_origem
            ]

            cidade_destino = aeroporto_cidade[
                aeroporto_destino
            ]


            peso_trecho = G[
                aeroporto_origem
            ][
                aeroporto_destino
            ]["weight"]


            trechos_distancia.append({

                "De":
                    f"{cidade_origem} ({aeroporto_origem})",

                "Para":
                    f"{cidade_destino} ({aeroporto_destino})",

                "Distância (km)":
                    f"{peso_trecho:.2f}"

            })


        st.table(
            pd.DataFrame(trechos_distancia)
        )


    # =======================================================================
    # ROTA COM MENOR NÚMERO DE CONEXÕES
    # =======================================================================

    if melhor_caminho_conexoes is not None:

        st.markdown(
            "### Rota com menor número de conexões"
        )


        # ---------------------------------------------------------------
        # Mostra cidade + aeroporto
        # ---------------------------------------------------------------

        rota_detalhada_conexoes = []


        for aeroporto in melhor_caminho_conexoes:

            cidade = aeroporto_cidade[aeroporto]

            rota_detalhada_conexoes.append(
                f"{cidade} ({aeroporto})"
            )


        st.markdown(
            f"{' → '.join(rota_detalhada_conexoes)}"
        )


        st.markdown(
            f"**Número de conexões:** "
            f"{menor_numero_conexoes}"
        )


        # ---------------------------------------------------------------
        # Calcula a distância dessa rota
        # ---------------------------------------------------------------

        distancia_rota_conexoes = 0


        for i in range(
            len(melhor_caminho_conexoes) - 1
        ):

            aeroporto_origem = melhor_caminho_conexoes[i]
            aeroporto_destino = melhor_caminho_conexoes[i + 1]

            distancia_rota_conexoes += G[
                aeroporto_origem
            ][
                aeroporto_destino
            ]["weight"]


        st.markdown(
            f"**Distância total:** "
            f"{distancia_rota_conexoes:.2f} km"
        )


        # ---------------------------------------------------------------
        # Detalhamento dos trechos
        # ---------------------------------------------------------------

        st.markdown(
            f"**Aeroportos utilizados:** "
            f"{' → '.join(melhor_caminho_conexoes)}"
        )

        trechos_conexoes = []


        for i in range(
            len(melhor_caminho_conexoes) - 1
        ):

            aeroporto_origem = melhor_caminho_conexoes[i]
            aeroporto_destino = melhor_caminho_conexoes[i + 1]

            cidade_origem = aeroporto_cidade[
                aeroporto_origem
            ]

            cidade_destino = aeroporto_cidade[
                aeroporto_destino
            ]


            peso_trecho = G[
                aeroporto_origem
            ][
                aeroporto_destino
            ]["weight"]


            trechos_conexoes.append({

                "De":
                    f"{cidade_origem} ({aeroporto_origem})",

                "Para":
                    f"{cidade_destino} ({aeroporto_destino})",

                "Distância (km)":
                    f"{peso_trecho:.2f}"

            })


        st.table(
            pd.DataFrame(trechos_conexoes)
        )


    # -----------------------------------------------------------------------
    # 7. Visualização da rota com menor distância
    # -----------------------------------------------------------------------
    with st.expander(
        "Ver grafo de menor distância (rota mais barata)"
    ):
        if melhor_caminho_distancia is not None:

            st.subheader(
                "Visualização do grafo de caminho mais barato"
            )


            fig, ax = plt.subplots(
                figsize=(10, 7)
            )


            # Cria a posição dos nós

            pos = nx.spring_layout(
                G,
                seed=42,
                k=0.7
            )


            # Arestas da menor rota

            arestas_caminho = list(
                zip(
                    melhor_caminho_distancia[:-1],
                    melhor_caminho_distancia[1:]
                )
            )


            arestas_caminho_set = set(
                arestas_caminho
            )


            # Outras arestas

            outras_arestas = [
                e
                for e in G.edges()
                if e not in arestas_caminho_set
            ]


            # -------------------------------------------------------------------
            # Nós do grafo
            # -------------------------------------------------------------------

            nx.draw_networkx_nodes(
                G,
                pos,
                ax=ax,
                node_size=550,
                node_color="#cfe2f3",
                edgecolors="#333333"
            )


            # Destaca os aeroportos utilizados

            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=melhor_caminho_distancia,
                ax=ax,
                node_size=650,
                node_color="#ff9999",
                edgecolors="#990000"
            )


            # Nomes dos aeroportos

            nx.draw_networkx_labels(
                G,
                pos,
                ax=ax,
                font_size=8,
                font_weight="bold"
            )


            # -------------------------------------------------------------------
            # Arestas que não fazem parte da rota
            # -------------------------------------------------------------------

            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=outras_arestas,
                ax=ax,
                edge_color="#cccccc",
                width=0.8,
                arrows=grafo_dirigido,
                arrowsize=8
            )


            # -------------------------------------------------------------------
            # Arestas da melhor rota
            # -------------------------------------------------------------------

            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=arestas_caminho,
                ax=ax,
                edge_color="#cc0000",
                width=3,
                arrows=grafo_dirigido,
                arrowsize=15
            )


            # -------------------------------------------------------------------
            # Pesos das arestas
            # -------------------------------------------------------------------

            pesos_caminho = {
                e: G[e[0]][e[1]]["weight"]
                for e in arestas_caminho
            }


            nx.draw_networkx_edge_labels(
                G,
                pos,
                edge_labels=pesos_caminho,
                ax=ax,
                font_size=8,
                font_color="#990000"
            )


            # -------------------------------------------------------------------
            # Título
            # -------------------------------------------------------------------

            ax.set_title(
                f"Rota mais barata: "
                f"{partida} → {chegada} "
                f"(distância total: "
                f"{menor_distancia:.2f} km)"
            )


            ax.axis("off")


            st.pyplot(fig)

            plt.close(fig)

    # -----------------------------------------------------------------------
    # 8. Visualização da rota com menor número de conexões
    # -----------------------------------------------------------------------

    with st.expander(
        "Ver grafo de menor número de conexões"
    ):

        if melhor_caminho_conexoes is not None:

            st.subheader(
                "Visualização do grafo com menor número de conexões"
            )


            fig3, ax3 = plt.subplots(
                figsize=(10, 7)
            )


            # Cria a posição dos nós

            pos3 = nx.spring_layout(
                G,
                seed=42,
                k=0.7
            )


            # Arestas da rota com menor número de conexões

            arestas_conexoes = list(
                zip(
                    melhor_caminho_conexoes[:-1],
                    melhor_caminho_conexoes[1:]
                )
            )


            arestas_conexoes_set = set(
                arestas_conexoes
            )


            # Outras arestas

            outras_arestas_conexoes = [
                e
                for e in G.edges()
                if e not in arestas_conexoes_set
            ]


            # -------------------------------------------------------------------
            # Nós do grafo
            # -------------------------------------------------------------------

            nx.draw_networkx_nodes(
                G,
                pos3,
                ax=ax3,
                node_size=550,
                node_color="#cfe2f3",
                edgecolors="#333333"
            )


            # Destaca os aeroportos utilizados

            nx.draw_networkx_nodes(
                G,
                pos3,
                nodelist=melhor_caminho_conexoes,
                ax=ax3,
                node_size=650,
                node_color="#ff9999",
                edgecolors="#990000"
            )


            # Nomes dos aeroportos

            nx.draw_networkx_labels(
                G,
                pos3,
                ax=ax3,
                font_size=8,
                font_weight="bold"
            )
            

            # -------------------------------------------------------------------
            # Arestas que não fazem parte da rota
            # -------------------------------------------------------------------

            nx.draw_networkx_edges(
                G,
                pos3,
                edgelist=outras_arestas_conexoes,
                ax=ax3,
                edge_color="#cccccc",
                width=0.8,
                arrows=grafo_dirigido,
                arrowsize=8
            )


            # -------------------------------------------------------------------
            # Arestas da melhor rota
            # -------------------------------------------------------------------

            nx.draw_networkx_edges(
                G,
                pos3,
                edgelist=arestas_conexoes,
                ax=ax3,
                edge_color="#cc0000",
                width=3,
                arrows=grafo_dirigido,
                arrowsize=15
            )


            # -------------------------------------------------------------------
            # Pesos das arestas
            # -------------------------------------------------------------------

            pesos_conexoes = {
                e: G[e[0]][e[1]]["weight"]
                for e in arestas_conexoes
            }


            nx.draw_networkx_edge_labels(
                G,
                pos3,
                edge_labels=pesos_conexoes,
                ax=ax3,
                font_size=8,
                font_color="#990000"
            )


            # -------------------------------------------------------------------
            # Título
            # -------------------------------------------------------------------

            ax3.set_title(
                f"Rota com menor número de conexões: "
                f"{partida} → {chegada} "
                f"({menor_numero_conexoes} conexões)"
            )


            ax3.axis("off")


            st.pyplot(fig3)

            plt.close(fig3)

    # -----------------------------------------------------------------------
    # 9. Grafo completo
    # -----------------------------------------------------------------------

    with st.expander(
        "Ver grafo completo (todos os aeroportos e conexões)"
    ):

        fig2, ax2 = plt.subplots(
            figsize=(10, 7)
        )


        # Posição dos nós

        pos2 = nx.spring_layout(
            G,
            seed=42,
            k=0.7
        )


        # Nós

        nx.draw_networkx_nodes(
            G,
            pos2,
            ax=ax2,
            node_size=450,
            node_color="#cfe2f3",
            edgecolors="#333333"
        )


        # Nomes

        nx.draw_networkx_labels(
            G,
            pos2,
            ax=ax2,
            font_size=7
        )


        # Arestas

        nx.draw_networkx_edges(
            G,
            pos2,
            ax=ax2,
            edge_color="#999999",
            width=0.8,
            arrows=grafo_dirigido,
            arrowsize=6
        )


        # Pesos de todas as arestas

        edge_labels_all = nx.get_edge_attributes(
            G,
            "weight"
        )


        nx.draw_networkx_edge_labels(
            G,
            pos2,
            edge_labels=edge_labels_all,
            ax=ax2,
            font_size=6
        )


        ax2.axis("off")


        st.pyplot(fig2)

        plt.close(fig2)