"""Plot saved final aggregates; never loads a model or individual test rows."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1]
    folder=root/'reports/generated/final'
    report=json.loads((folder/'metrics.json').read_text(encoding='utf-8'))
    fields=['mae_brl','median_absolute_error_brl','host_weighted_mae_brl']
    labels=['Mean absolute error','Median absolute error','Equal-host MAE']
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    x=np.arange(len(fields))
    for offset,key,label,color in [(-.18,'metrics','Frozen HistGB + geography','#246b8e'),(.18,'room_median_metrics','Room-type median','#8997a2')]:
        values=[report[key][f] for f in fields]
        ax.bar(x+offset,values,width=.34,label=label,color=color)
        for pos,value in zip(x+offset,values): ax.text(pos,value+8,f'{value:.2f}',ha='center',fontsize=9)
    ax.set_xticks(x,labels)
    ax.set_ylabel('BRL — lower is better')
    ax.set_title('Final held-out test | 6,515 listings / 3,827 hosts')
    ax.set_ylim(0,750)
    ax.spines[['top','right']].set_visible(False)
    ax.legend(loc='upper right')
    fig.savefig(folder/'comparison.png',dpi=180)
    plt.close(fig)


if __name__=='__main__': main()