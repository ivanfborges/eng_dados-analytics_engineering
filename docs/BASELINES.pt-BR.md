# Baselines e protocolo congelado de comparação

[English](BASELINES.md) · [Estudo](STUDY.pt-BR.md) · [Início](../README.pt-BR.md)

**Etapa 3.3a concluída. Duas referências simples avaliadas em folds do treino. Validação e teste final continuam sem uso.**

Prever a mediana por tipo de acomodação reduz o MAE fora da amostra de treino em R$ 10,57 frente à mediana geral (cerca de 1,81%). Essa é uma referência para os próximos experimentos de ML, não um sistema de precificação ou resultado de teste final.

![Erros dos baselines; legendas em inglês](baselines/comparison.png)

As barras indicam intervalos de 95% por bootstrap de anfitriões, condicionais às previsões já calculadas. Não incluem incerteza de novo treinamento nem dependência espacial entre anfitriões. A diferença pareada é mais precisa que o erro absoluto de cada modelo porque ambos preveem os mesmos anúncios.

## Resultados

Cada anúncio elegível do treino (31.636 anúncios; 17.912 anfitriões) recebe exatamente uma previsão fora da amostra de ajuste em cada desenho. Cada mediana usa somente dados de ajuste daquele fold. Tipo de acomodação desconhecido recebe a mediana geral do fold. Todos os anúncios com preço válido foram mantidos, inclusive preços pedidos muito altos.

| Avaliação | Baseline | MAE R$ | Mediana do erro absoluto R$ | RMSE R$ | RMSLE | MAE por anfitrião R$ |
|---|---|---:|---:|---:|---:|---:|
| Por anfitrião | Mediana geral | 584,42 | 192,25 | 5.155,29 | 0,8402 | 539,39 |
| Por anfitrião | Mediana por tipo | 573,85 | 181,17 | 5.152,99 | 0,8060 | 532,54 |
| Espacial | Mediana geral | 600,94 | 194,00 | 5.161,41 | 0,8931 | 555,42 |
| Espacial | Mediana por tipo | 592,14 | 182,00 | 5.159,66 | 0,8636 | 549,62 |

Na avaliação por anfitrião, o intervalo de 95% do MAE é [498,21; 703,53] para a mediana geral e [487,77; 692,77] para a mediana por tipo. A diferença pareada (tipo menos geral) é -10,57, intervalo [-12,15; -8,84]. No desenho espacial: -8,79, intervalo [-10,18; -7,35]. Foram 1.000 reamostragens de anfitriões, semente 42. São descrições condicionais dessas previsões, não garantias para novas populações.

RMSE muito maior que MAE é consistente com a cauda de preços observada na EDA. A mediana do erro absoluto é muito menor que o MAE. Reportar apenas uma dessas métricas esconderia variação relevante. Não removemos preços por quantis nem casos retrospectivamente para melhorar os resultados.

## Dois desenhos de avaliação

**Por anfitrião:** cinco folds determinísticos, SHA256 de UTF-8 `rio-cv-v1|host_id`, primeiros oito bytes unsigned big-endian módulo cinco. Nenhum anfitrião aparece simultaneamente no ajuste e na avaliação de um fold. Os folds avaliados têm 6.292–6.374 anúncios. A divisão externa treino/validação/teste permanece intacta.

**Espacial:** os 160 nomes de bairros foram atribuídos pelo SHA256 de `rio-spatial-v1|nome`, mesma regra de bytes/módulo. O mapeamento está em [protocol.json](baselines/protocol.json), commit `b430075`, anterior a qualquer ajuste de baseline. Usamos apenas a partição externa de treino. Todos os anúncios de ajuste pertencentes a anfitriões presentes nos bairros avaliados são retirados, inclusive anúncios em outros bairros.

| Fold espacial | Linhas de ajuste após remoção | Linhas avaliadas | Linhas removidas do ajuste |
|---|---:|---:|---:|
| 0 | 10.218 | 19.320 | 2.098 |
| 1 | 28.210 | 1.420 | 2.006 |
| 2 | 25.378 | 3.189 | 3.069 |
| 3 | 21.012 | 6.808 | 3.816 |
| 4 | 29.805 | 899 | 932 |

Bairros têm números desiguais de anúncios; os folds são bastante desbalanceados. O MAE combinado pondera anúncios e recebe mais influência dos folds maiores; publicamos também métricas por fold. Nenhum bairro foi realocado após observar resultados. São grupos de bairros separados, não blocos geográficos contíguos ou extrapolação com faixa de distância. Áreas vizinhas podem continuar dependentes. Nenhum desenho comprova desempenho futuro no tempo.

## Próxima comparação congelada

Seis candidatos, nesta ordem: mediana geral, mediana por tipo, Ridge com atributos do imóvel, Ridge com geografia, HistGradientBoosting com atributos do imóvel e HistGradientBoosting com geografia. Os quatro últimos **ainda não foram ajustados**.

- Ridge: alpha 10, alvo log1p(preço), inversa expm1, previsão limitada inferiormente a zero.
- HistGradientBoosting: perda de erro absoluto, 200 iterações, 15 folhas, taxa 0,05, mínimo de 20 casos por folha, L2 1, sem parada antecipada, semente 42; alvo em BRL.
- Atributos: capacidade, quartos, camas, banheiros, noites mínimas, tipo de acomodação e propriedade. Extensão geográfica: latitude, longitude e bairro.
- Números semanticamente inválidos viram ausentes. Imputação/indicadores, escala para Ridge e codificação categórica são ajustados dentro dos folds de treino. One-hot ignora categorias desconhecidas; IDs e agregados geográficos derivados do alvo ficam fora dos modelos.

Escolher o menor **MAE combinado dos folds por anfitrião, em BRL**, entre os seis candidatos. Empates dentro de 1e-9 seguem a ordem declarada. A avaliação espacial é diagnóstico, não outra métrica de ajuste. Não ampliar a busca depois de observar resultados. Ajustar o escolhido somente no treino externo e relatar validação uma vez, sem reordenar candidatos. Se um redesenho for necessário, registrar novo protocolo de desenvolvimento mantendo teste final reservado. Congelar configuração, artefato e relatório de validação antes da avaliação final; esta versão não reajusta em treino+validação.

## Reprodução e auditoria

Usar ambiente e arquivos descritos em [EDA.pt-BR.md](EDA.pt-BR.md). Nenhuma dependência adicional foi introduzida.

```sh
python -m unittest discover -s tests -v
python -m rio.baselines
python -m rio.plot_baselines
```

O executor confere o hash do treino e grava métricas agregadas imutáveis e **previsões individuais privadas** em `reports/generated/baselines/`, ignorado no Git. Reexecução no mesmo ambiente/dados preserva conteúdo idêntico; alterações exigem revisão. O comando de gráficos renderiza as métricas localmente. A publicação copia somente agregados revisados e o gráfico para `docs/baselines/`.

As [métricas](baselines/metrics.json) incluem cobertura por fold, resultados combinados, incerteza, versões e hashes de protocolo, treino e previsões privadas. Os 22 testes sintéticos cobrem isolamento, remoção de anfitriões, fallback de categorias desconhecidas, ponderação por anúncio/anfitrião e as proteções da EDA. Dados brutos e previsões individuais não são publicados.

Fonte: Inside Airbnb, snapshot 24/06/2026, conforme [manifesto](snapshot.json). Os resultados descrevem preços anunciados de casos elegíveis, sem representar receita, ocupação ou preço ótimo. Próxima entrega: 3.3b, implementar os quatro candidatos de ML congelados e documentar a seleção.