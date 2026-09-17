"""Render already saved aggregate model comparison; performs no fitting."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/'reports/generated/selection/comparison.json').read_text(encoding='utf-8'))
    names=list(report['evaluations']['host']['pooled_metrics'])
    fig,ax=plt.subplots(figsize=(10,5.5),layout='constrained')
    y=np.arange(len(names))
    for offset,mode,label,color in [(-.18,'host','Held-out hosts','#246b8e'),(.18,'spatial','Held-out neighbourhoods + host purge','#b96943')]:
        values=[report['evaluations'][mode]['pooled_metrics'][name]['mae_brl'] for name in names]
        ax.barh(y+offset,values,height=.34,label=label,color=color)
        for position,value in zip(y+offset,values): ax.text(value+3,position,f'{value:.1f}',va='center',fontsize=8)
    ax.set_yticks(y,names)
    ax.invert_yaxis()
    ax.set_xlabel('Training out-of-fold MAE (BRL; lower is better)')
    ax.set_title('Rio Airbnb | frozen candidate comparison')
    ax.spines[['top','right']].set_visible(False)
    ax.legend(loc='upper center', bbox_to_anchor=(.5,-.13), ncol=1)
    ax.set_xlim(0,1.2*max(report['evaluations'][mode]['pooled_metrics'][name]['mae_brl'] for mode in ['host','spatial'] for name in names))
    fig.savefig(root/'reports/generated/selection/comparison.png',dpi=180)
    plt.close(fig)


if __name__=='__main__': main()