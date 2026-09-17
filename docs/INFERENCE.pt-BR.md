# Inferência com o modelo congelado

[English](INFERENCE.md) · [Estudo](../README.pt-BR.md) · [Avaliação final](FINAL.pt-BR.md)

A CLI estima preços anunciados por noite, em reais, usando o pipeline `histgb_geo` já ajustado. Não treina, seleciona ou avalia modelos. Validação e teste final já foram consumidos. O binário e os dados individuais da fonte não são distribuídos.

## Início rápido público: sem dados privados

Em um checkout limpo, use Python **3.11.14**, crie um ambiente e instale o lock do modelo. O `requirements.txt` da raiz pertence ao projeto acadêmico histórico.

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell:
.venv/Scripts/Activate.ps1
python -m pip install -r requirements-model-lock.txt
python -m unittest discover -s tests -v
python -m rio.predict --input examples/fictional_listings.csv --check-input
```

Resultado esperado: 46 testes aprovados e `valid_cases: 3`. Os testes usam dados sintéticos. A validação de entrada não carrega modelo, snapshot ou partições. Compare as [previsões ilustrativas](../examples/fictional_predictions.csv) com as [entradas fictícias](../examples/fictional_listings.csv). Os três casos foram inventados para esta interface, sem copiar anúncios reais. Não possuem preço observado e não demonstram acurácia.

## Inferência completa: exige artefato local confiável

O artefato local do mantenedor está em `reports/generated/selection/selected_pipeline.joblib`. Um clone público comum **não** contém esse arquivo. Não há download automático ou retreinamento como alternativa. Com acesso ao artefato confiável, informe seu caminho explicitamente e escolha um arquivo de saída novo:

```sh
python -m rio.predict --input examples/fictional_listings.csv --model /caminho/selected_pipeline.joblib --output predictions.csv
```

A saída preserva a ordem e o `case_id`, com `estimated_nightly_price_brl` arredondado para duas casas. Arquivos existentes não são sobrescritos; a pasta de destino deve existir. Mantenha previsões de anúncios reais privadas, por exemplo na pasta ignorada `reports/generated/`.

Antes da desserialização, a CLI verifica o SHA256 do modelo contra o [manifesto congelado](selection/selected_artifact.json), suas ligações aos registros de decisão e validação, comparação, implementação do modelo, protocolo, lock, versão do Python e versões dos pacotes instalados. SHA256 esperado: `a68512f4942bf396ccd0452496edd409334827043416927272d42512161d3a32`. Depois confere os parâmetros do estimador ajustado. Use somente arquivos joblib confiáveis: os hashes verificam consistência com registros confiáveis do repositório, não autenticidade independente. Nenhum arquivo de treino ou holdout é lido.

## Contrato de entrada

CSV UTF-8 separado por vírgulas, com cabeçalho e exatamente estas colunas únicas, em qualquer ordem:

| Campo | Valores aceitos |
|---|---|
| `case_id` | Texto único, não vazio; preservado na saída, excluído das features |
| `accommodates`, `minimum_nights` | Inteiros >= 1 ou vazio |
| `bedrooms`, `beds` | Inteiros >= 0 ou vazio |
| `bathrooms` | Número finito >= 0 ou vazio |
| `latitude`, `longitude` | Graus WGS84 finitos em [-90,90] / [-180,180] ou vazio |
| `room_type`, `property_type`, `neighbourhood_cleansed` | Texto sensível a maiúsculas ou vazio; categorias novas aceitas |

Use ponto decimal e célula vazia para ausências. `NaN`, infinito, números malformados, IDs duplicados, linhas com tamanho inconsistente, colunas extras (inclusive preço ou ID do anfitrião) e colunas faltantes são rejeitados. Espaços nas extremidades são removidos. Ausências numéricas usam medianas aprendidas no treino e indicadores de ausência; categorias vazias usam o token congelado e categorias desconhecidas produzem blocos one-hot zerados. A CLI rejeita números inválidos em vez de imputá-los silenciosamente; entradas válidas/ausentes usam o pré-processamento original.

Os dois primeiros exemplos ilustram características usuais; o terceiro exercita campos ausentes e categorias inventadas. Seu resultado numérico demonstra apenas o funcionamento do software. A validação não verifica consistência entre bairro e coordenadas, cobertura geográfica, plausibilidade de mercado ou confiabilidade preditiva. Limites mundiais de coordenadas verificam formato, não aplicabilidade fora do Rio.

## Interpretação e limites

As estimativas descrevem um snapshot do Rio, não preços futuros, transações, receita ou preço ótimo. No teste final, o MAE foi R$ 482,67 (intervalo de bootstrap por anfitrião de 95%: 366,38–632,28), contra R$ 620,57 do baseline por tipo. Esse é um erro agregado, **não** um intervalo de previsão para um imóvel novo. Os erros variam bastante entre segmentos e valores extremos continuam difíceis. Não há comprovação de adequação à produção ou garantia de incerteza individual. Consulte o [relatório final completo](FINAL.pt-BR.md).

Integridade do checkout: `.gitattributes` preserva os bytes CRLF originais do protocolo, pois o hash congelado foi registrado nesse formato. Nenhum conteúdo ou decisão experimental foi alterado. Um teste de regressão confere esse hash em novos checkouts.
