# Airbnb no Rio de Janeiro: preços anunciados e geografia

[English](README.md)

Estudo aplicado de Ciência de Dados: **quanto as características do imóvel e a localização ajudam a estimar o preço anunciado por noite para anúncios de anfitriões ausentes do treino, dentro de um snapshot do Rio?**

**Estado:** escopo e auditoria da fonte concluídos; análise exploratória e modelos são as próximas etapas. Ainda não há desempenho preditivo validado nem implantação em produção.

O snapshot identificado como 24/06/2026 contém 48.713 anúncios e 27.688 anfitriões. Há 44.542 preços presentes e positivos e 4.171 ausentes. O nome do snapshot não é a data de cada observação: a coleta efetiva varia de 25/06 a 01/07. São verificações estruturais, não resultados de modelos.

## Documentação

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
python -m unittest discover -s tests -v
```

Compare hashes e contagens com o manifesto. Uma alteração no arquivo da fonte exige revisão de versão. A data de obtenção registrada é a da aquisição original, não a da reexecução. Os dados brutos estão ignorados pelo Git. A auditoria não precisa de PostgreSQL nem das dependências antigas.

## Origem acadêmica e evolução

O projeto nasceu na pós-graduação em Engenharia de Dados, com PostgreSQL, Docker, dbt, Great Expectations e notebooks. Esses arquivos permanecem como material histórico; seus fluxos não foram reexecutados ou validados nesta revisão. O importador antigo lê as primeiras 1.000 linhas de cada tabela separadamente, sem garantir representatividade ou correspondência entre anúncios, avaliações e calendários. O novo estudo utiliza o snapshot completo de anúncios.

A análise irá separar anfitriões entre treino e avaliação, comparar baselines com ML e medir a contribuição da geografia. A transferência espacial terá avaliação própria. O desenho atual não prevê preços futuros nem demonstra relações causais.

## Fonte e limites

Dados: [Inside Airbnb](https://insideairbnb.com/get-the-data/), sob CC BY 4.0. Consulte as [políticas](https://insideairbnb.com/data-policies/), [premissas](https://insideairbnb.com/data-assumptions/) e o [dicionário](https://docs.google.com/spreadsheets/d/1iWCNJcSutYqpULSQHlNyGInUvHg2BoUGoNRIGa6Szc4/edit).

Preço anunciado não representa transação, receita ou recomendação de preço ótimo. Indisponibilidade no calendário não confirma reserva. Coordenadas são aproximadas. Novas saídas serão agregadas, sem identidades de anfitriões, textos de avaliações ou mapas individuais. A licença dos dados não define a licença do código deste repositório.