# Protocolo do estudo — versão 1, 16/09/2026

[English](STUDY.md) · [Início](../README.pt-BR.md)

## Pergunta e uso

Estimar o preço anunciado por noite a partir de características do imóvel e localização, para anúncios de anfitriões ausentes do treino, no mesmo snapshot do Rio. Público: analistas do mercado de aluguel por temporada e avaliadores de um estudo aplicado de ML. As saídas descrevem associações e erros preditivos, sem demonstrar retorno de investimento, causalidade no mercado imobiliário ou recomendação de preço.

Unidade: um ID de anúncio em um snapshot. Alvo: `price`, preço por noite em moeda local (BRL no Rio), conforme o [dicionário da fonte](https://docs.google.com/spreadsheets/d/1iWCNJcSutYqpULSQHlNyGInUvHg2BoUGoNRIGa6Szc4/edit). O símbolo de dólar isolado não comprova USD. O valor anunciado não equivale à fatura final nem a uma transação realizada.

## Fonte e auditoria

Usar os anúncios detalhados completos e o GeoJSON dos bairros em [snapshot.json](snapshot.json). Fonte Inside Airbnb, snapshot identificado como 24/06/2026, obtido em 16/09/2026. Coletas efetivas: 25/06, 26/06 e 01/07. Conferir hashes antes da análise; não substituir por arquivos novos silenciosamente.

O código original referencia 22/09/2023; esse download histórico não foi recuperado nem utilizado. A página atual anuncia disponibilidade trimestral recente; esta revisão adquiriu somente um snapshot. Não existe painel temporal validado.

Auditoria: 48.713 IDs de anúncios distintos, 27.688 anfitriões e 90 colunas; 44.542 preços positivos e 4.171 ausentes. Não foram encontrados preços preenchidos malformados ou não positivos. Todos os nomes de bairros correspondem a uma das 160 feições do GeoJSON. As coordenadas passam apenas na verificação de limites mundiais: contenção em polígonos, validade geométrica, consistência do sistema de referência e ambiguidades de fronteira ficam para 3.2. Ausências: banheiros 7.424, quartos 7.099, camas 5.282 e noites mínimas 7.

A auditoria lê todas as linhas e verifica formato do CSV, colunas obrigatórias, validade dos IDs e unicidade dos anúncios. Relata outros problemas, sem certificar prontidão para modelagem. Não inspeciona distribuições de preços, ordena atributos ou consome teste de modelos.

## Contrato e atributos

| Campos | Papel e regra |
|---|---|
| `id`, `host_id` | Strings não vazias de dígitos; anúncio único. Preservar como texto. Anfitrião define partições, nunca entra como preditor. |
| `last_scraped` | Proveniência da data de observação, separada do nome do snapshot. |
| `price` | Interpretar formato da fonte; exigir alvo finito e positivo. Excluir ausentes/inválidos do aprendizado supervisionado, registrando contagens. Nunca imputar o alvo. |
| `room_type`, `property_type`, `accommodates`, `bedrooms`, `beds`, `bathrooms`, `minimum_nights` | Conjunto inicial de características do imóvel. Validar tipos/limites, tratar categorias desconhecidas e ajustar imputação apenas no treino de cada fold. |
| `latitude`, `longitude`, `neighbourhood_cleansed` | Extensão geográfica para comparação com o modelo sem geografia. Validar alinhamento espacial primeiro. |
| Demais campos | Excluídos por padrão; inclusão exige revisão documentada. |

Excluir IDs, nomes, URLs, textos livres, biografias, avaliações, preços de calendário, renda/ocupação inferidas e estatísticas do alvo calculadas fora dos folds de treino. Comodidades e notas de avaliações ficam fora do conjunto inicial. Importância ou coeficientes geográficos não demonstram causalidade.

Não reutilizar os cortes históricos por quantis: anúncios caros válidos integram a população. Regras de validade devem ser justificadas pela semântica da fonte antes de comparar modelos. Transformações ajustadas no treino podem tratar assimetria; avaliar também em BRL original.

Não usar `head(1000)` independente por tabela. O estudo inicial usa todos os anúncios. Se calendários/avaliações forem necessários, selecionar primeiro IDs de anúncios, filtrar tabelas relacionadas por esses IDs e datas compatíveis, verificar órfãos, unicidade `(listing_id, date)` no calendário e IDs de avaliações. Agregar tabelas filhas antes da junção para evitar multiplicação de linhas. Essas extensões não foram adquiridas ou implementadas.

## Avaliação — implementar antes da exploração

1. Após elegibilidade estrutural, calcular SHA256 de `rio-v1|` seguido do `host_id` original, em UTF-8. Interpretar os primeiros oito bytes como inteiro sem sinal em big-endian, dividido por 2**64. Abaixo de 0,70: treino; abaixo de 0,85: validação; demais: teste final. Todos os anúncios do anfitrião herdam a partição. Proporções aproximadas por anfitrião, não exatas por anúncio.
2. Salvar hash da fonte, versão do protocolo, contagens e manifesto privado de anúncio/partição. Assegurar ausência de sobreposição de anúncios/anfitriões e partições não vazias. Investigar falhas estruturais sem escolher semente a partir dos preços. Explorar somente treino; validação serve para seleção explícita. Não inspecionar alvos do teste final ou ajustar decisões a partir de seus resumos.
3. Comparar mediana de treino e mediana por tipo de acomodação (fallback global), um modelo regularizado e um candidato baseado em árvores. Pré-processamento aprendido dentro da validação cruzada agrupada por anfitrião, apenas no treino. Fixar a pequena lista de candidatos e a regra de seleção na etapa 3.3 antes de ajustar modelos.
4. Métrica principal: MAE em BRL, ponderado por anúncio. Complementos: mediana do erro absoluto, RMSE, erro em escala logarítmica, MAE com peso igual por anfitrião e intervalo via bootstrap por anfitrião. Informar cobertura e contagens elegíveis. Examinar erros de desenvolvimento por tipo de acomodação e bairro; publicar agregados somente com pelo menos 30 anúncios e 10 anfitriões.
5. Teste espacial secundário: apenas nos dados de desenvolvimento, cinco folds determinísticos por grupos de bairros, retirando do treino anfitriões presentes no fold de avaliação. Manter bairros inteiros, relatar cobertura e reconhecer dependência entre áreas vizinhas. Avalia transferência para bairros separados, sem afirmar previsão temporal. Especificar e congelar a atribuição de bairros aos folds antes do treinamento na etapa 3.3.
6. Congelar atributos, transformações, hiperparâmetros e regra de seleção antes de avaliar uma única vez o teste final separado por anfitrião. Esse teste sustenta apenas desempenho para anfitriões não vistos dentro do mesmo snapshot. Previsão futura exige novos snapshots ordenados no tempo e política de sobreposição de entidades.

Atualização 3.2: divisão criada e congelada nos [metadados](eda/partitions.json). A EDA somente do treino e a validação espacial estão em [EDA.pt-BR.md](EDA.pt-BR.md). A presença de alvo válido define elegibilidade; atributos ausentes não removem anúncios. Nenhum modelo foi treinado e o teste final está reservado.

## Condições e publicação

Os [downloads do Inside Airbnb](https://insideairbnb.com/get-the-data/) indicam CC BY 4.0. As [políticas da fonte](https://insideairbnb.com/data-policies/) pedem atribuição, aquisição mínima, download único e evitar republicação. Manter dados brutos e linhas derivadas individuais locais; publicar URLs, hashes, código e resultados agregados. O recorte não depende de pedidos pagos ao arquivo histórico.

As [premissas da fonte](https://insideairbnb.com/data-assumptions/) explicam que coordenadas são deslocadas e datas indisponíveis não distinguem reservas de bloqueios. Evitar interpretação de endereço exato, identificação de anfitriões e conclusões de ocupação/receita. Notebooks e relatórios acadêmicos permanecem históricos; esta revisão não certifica suas saídas como resultados atuais.

## Conclusão e próxima entrega

A etapa 3.1 entrega escopo, manifesto, auditoria estrutural e entrada bilíngue. A etapa 3.2 deve criar/verificar partições, validar dados espaciais, investigar ausências e viés de seleção no treino e produzir EDA e mapas agregados. A etapa 3.3 implementa a avaliação congelada; 3.4 organiza relatório e demonstração.