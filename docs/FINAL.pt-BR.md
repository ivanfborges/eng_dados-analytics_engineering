# Avaliação final no teste reservado

[English](FINAL.md) · [Seleção](SELECTION.pt-BR.md) · [Início](../README.pt-BR.md)

**Etapa 3.3c concluída. O teste final foi consumido uma vez. O modelo permanece inalterado e não deve ser ajustado com esses resultados.**

Em **6.515 anúncios elegíveis de 3.827 anfitriões não vistos**, o HistGradientBoosting congelado com geografia teve **MAE de R$ 482,67**, contra **R$ 620,57** da mediana por tipo calculada no treino: redução de aproximadamente **22,22%**. É uma estimativa dentro do mesmo snapshot e para anúncios com preços positivos observados, não previsão temporal ou resultado em produção.

![Erros no teste final](final/comparison.png)

A tabela usa ponto decimal, conforme os arquivos estruturados.

| Métrica | Modelo congelado | Mediana por tipo |
|---|---:|---:|
| MAE BRL | 482.67 | 620.57 |
| Median absolute error BRL | 126.24 | 190.04 |
| RMSE BRL | 3036.63 | 3292.67 |
| RMSLE | 0.61 | 0.84 |
| Equal-host MAE BRL | 455.15 | 564.60 |

RMSLE com maior precisão: 0,611815 frente a 0,839881. A mediana do erro (R$ 126,24) é muito menor que a média; RMSE de R$ 3.036,63 evidencia erros grandes ainda relevantes. Não houve corte de preços altos ou exclusão retrospectiva.

## Incerteza e comparação

Intervalo de 95% do MAE por bootstrap de anfitriões: **[366,38; 632,28]**. Diferença pareada modelo menos baseline: **-137,90**, intervalo **[-190,99; -97,01]**. São 1.000 reamostragens, semente 42 e previsões fixas. Consideram múltiplos anúncios por anfitrião, sem incluir incerteza de novo treinamento ou dependência entre anfitriões, inclusive espacial.

MAE na validação foi R$ 434,08; no teste final, R$ 482,67. São amostras reservadas diferentes, não tendência cronológica. Não houve mudança de candidato, parâmetros, pré-processamento ou piso zero a partir do teste. O artefato continua ajustado somente nos 31.636 anúncios originais de treino.

## Elegibilidade e variação dos erros

Dos 7.094 anúncios atribuídos ao teste, 6.515 têm preços finitos positivos; **579 não têm alvo elegível**. Foram excluídos pela regra predefinida, sem imputar preço. Cobertura supervisionada de aproximadamente 91,84% dos anúncios atribuídos; a avaliação não representa anúncios sem preço observado. Atributos ausentes são tratados pelo pipeline congelado.

A tabela usa ponto decimal.

| Acomodação | Anúncios | Anfitriões | MAE BRL | RMSLE |
|---|---:|---:|---:|---:|
| Entire home/apt | 5341 | 3244 | 501.22 | 0.587 |
| Private room | 1117 | 735 | 413.42 | 0.715 |
| Shared room | 57 | 32 | 101.80 | 0.717 |

Os três tipos observados atendem ao suporte mínimo. **85 grupos de bairros observados** foram suprimidos por terem menos de 30 anúncios elegíveis ou 10 anfitriões. Agregados completos dos grupos com suporte em [metrics.json](final/metrics.json).

Itanhangá tem MAE de R$ 6.430,31 em 32 anúncios/22 anfitriões, mas mediana do erro de R$ 238,99: a média é fortemente influenciada pela cauda. São Conrado tem MAE de R$ 1.726,00 em 87 anúncios/72 anfitriões. Esses grupos exigem cautela, misturam características de imóveis e não demonstram efeitos causais do bairro. Não motivarão ajustes após o teste. O relatório não identifica imóveis ou anfitriões individuais.

## Integridade e execução única

O [protocolo final](final/PROTOCOL.md) e o avaliador foram registrados no commit `000022a` antes de acessar o teste. A checagem prévia conferiu hashes de fontes, atribuições, treino, modelo, código, dependências e decisão; versões instaladas e Python; classe, parâmetros, atributos e número de iterações do estimador. SHA256 do modelo preservado: `a68512f4942bf396ccd0452496edd409334827043416927272d42512161d3a32`.

Um marcador exclusivo foi criado antes da leitura dos preços do teste. O carregador filtra anfitriões antes de interpretar alvos e verifica membros exatos e ausência de sobreposição com treino/validação. O avaliador chama predict, nunca fit no modelo selecionado. A referência usa medianas somente do treino, com fallback global. Previsões individuais foram salvas privadamente antes dos resumos.

Teste **CONSUMIDO**. Não apagar marcador nem repetir seleção/treinamento para melhorar esses resultados. CSV final ignorado no Git, SHA256 `d0da23892b7dbd71c46a8b4c29f440342bba2f7c1cacb06124fccbadf0051f81`. O JSON público contém somente métricas agregadas e proveniência.

## Verificação e limites de reprodução

Usar Python 3.11.14 e `requirements-model-lock.txt`. Trinta e seis testes sintéticos passaram, cobrindo hashes divergentes, parâmetros alterados, sobreposição, filtro anterior ao acesso ao alvo e bloqueio de repetição.

```sh
python -m unittest discover -s tests -v
python -m rio.final_evaluation --check-only
# Reconstruir resumos/gráfico das previsões privadas salvas, sem nova previsão:
python -m rio.final_evaluation --summarize-saved
python -m rio.plot_final
```

O comando padrão `python -m rio.final_evaluation` é de uso único e agora recusa execução neste workspace. Reconstrução de resumos confere hashes e preserva saída imutável. Reprodução em outra pasta com os mesmos dados não cria teste independente. Modelo binário e dados individuais não são distribuídos; proveniência em [seleção](SELECTION.pt-BR.md).

Limitações: snapshot único, coordenadas aproximadas, atributos incompletos, diferenças de completude associadas à ausência de preço, representação desigual de anfitriões e preços anunciados em vez de transações. Não há evidência de receita, ocupação, preço ótimo ou recomendação de implantação. Próximo passo: exemplos de inferência e demonstração em checkout limpo com o mesmo artefato, sem nova seleção.
