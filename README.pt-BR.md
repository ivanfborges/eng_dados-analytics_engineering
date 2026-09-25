# Airbnb no Rio de Janeiro: preços anunciados e geografia

[English](README.md)

Estudo aplicado de Ciência de Dados: **quanto as características do imóvel e a localização ajudam a estimar o preço anunciado por noite para anúncios de anfitriões ausentes do treino, dentro de um snapshot do Rio?**

**Estado:** avaliação final concluída. HistGradientBoosting com geografia: MAE R$ 482,67 versus R$ 620,57 do baseline por tipo (redução de 22,22%). Teste final consumido; não há implantação em produção.

O snapshot identificado como 24/06/2026 contém 48.713 anúncios e 27.688 anfitriões. Há 44.542 preços presentes e positivos e 4.171 ausentes. O nome do snapshot não é a data de cada observação: a coleta efetiva varia de 25/06 a 01/07. São verificações estruturais, não resultados de modelos.

## Experimente a interface

Valide entradas fictícias sem dados privados, consulte previsões ilustrativas ou execute inferência com o artefato local confiável e congelado. Veja o [guia de inferência](docs/INFERENCE.pt-BR.md). Não é necessário retreinar.

## Documentação

- [Avaliação final e limitações](docs/FINAL.pt-BR.md)
- [Seleção, validação e limitações do modelo](docs/SELECTION.pt-BR.md)
- [Baselines, incerteza e comparação congelada dos modelos](docs/BASELINES.pt-BR.md)
- [Exploração do treino: resultados, mapas e reprodução](docs/EDA.pt-BR.md)
- [Protocolo, contrato de dados e avaliação](docs/STUDY.pt-BR.md)
- [Manifesto da fonte e auditoria estrutural](docs/snapshot.json)
- [Descrição acadêmica original preservada](docs/ACADEMIC-ORIGINAL.pt-BR.md)

## Reproduzir a auditoria

Python 3.11 ou superior; apenas biblioteca padrão. Baixe cada arquivo **uma única vez**, pelas URLs exatas em `docs/snapshot.json`, e salve em:

```text
data/raw/2026-06-24/listings.csv.gz
data/raw/2026-06-24/neighbourhoods.geojson
```

```sh
python scripts/audit_snapshot.py
```

Compare hashes e contagens com o manifesto. Uma alteração no arquivo da fonte exige revisão de versão. A data de obtenção registrada é a da aquisição original, não a da reexecução. Os dados brutos estão ignorados pelo Git. A auditoria não precisa de PostgreSQL nem das dependências antigas.

## Resultados do treino

Mediana do preço anunciado: R$ 454,97; média: R$ 875,69. Preços ausentes afetam 8,45% dos anúncios de treino e coincidem com maior ausência de camas e banheiros. O mapa cobre 53 bairros com suporte suficiente. São resultados descritivos do treino, não desempenho de modelos.

![Medianas dos bairros no treino](docs/eda/neighbourhood_prices.png)

O [relatório de EDA](docs/EDA.pt-BR.md) detalha limites da população, correção geométrica, partições congeladas e ambiente isolado dos testes sintéticos.

## Origem acadêmica e evolução

O projeto nasceu na pós-graduação em Engenharia de Dados, com PostgreSQL, Docker, dbt, Great Expectations e notebooks. Esses arquivos permanecem como material histórico; seus fluxos não foram reexecutados ou validados nesta revisão. O importador antigo lê as primeiras 1.000 linhas de cada tabela separadamente, sem garantir representatividade ou correspondência entre anúncios, avaliações e calendários. O novo estudo utiliza o snapshot completo de anúncios.

O estudo concluído separa anfitriões entre treino e avaliação, compara dois baselines e quatro candidatos ML e avalia geografia em folds por anfitrião e bairro. O modelo final e sua interface de inferência usam o artefato congelado. O desenho atual não prevê preços futuros nem demonstra relações causais.

## Fonte e limites

Dados: [Inside Airbnb](https://insideairbnb.com/get-the-data/), sob CC BY 4.0. Consulte as [políticas](https://insideairbnb.com/data-policies/), [premissas](https://insideairbnb.com/data-assumptions/) e o [dicionário](https://docs.google.com/spreadsheets/d/1iWCNJcSutYqpULSQHlNyGInUvHg2BoUGoNRIGa6Szc4/edit).

Preço anunciado não representa transação, receita ou recomendação de preço ótimo. Indisponibilidade no calendário não confirma reserva. Coordenadas são aproximadas. Novas saídas serão agregadas, sem identidades de anfitriões, textos de avaliações ou mapas individuais. A licença dos dados não define a licença do código deste repositório.
