import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1]
report=json.loads((root/'reports/generated/baselines/metrics.json').read_text(encoding='utf-8'))

fig, axes=plt.subplots(1,2,figsize=(10,4),layout='constrained',sharey=True)
for ax, mode, title in zip(axes,['host','spatial'],['Unseen hosts','Held-out neighbourhoods + host purge']):
    rows=report['evaluations'][mode]['pooled_metrics']
    vals=[rows[k]['mae_brl'] for k in ['global_median','room_median']]
    bounds=[rows[k]['mae_host_bootstrap_95ci'] for k in ['global_median','room_median']]
    ax.bar(['Global median','Room-type median'],vals,color=['#788995','#246b8e'],width=.55)
    ax.errorbar([0,1],vals,yerr=[[v-b[0] for v,b in zip(vals,bounds)],[b[1]-v for v,b in zip(vals,bounds)]],fmt='none',color='#182d3a',capsize=5)
    ax.set(title=title,ylim=(0,820))
    for i,v in enumerate(vals): ax.text(i,v+8,f'{v:.2f}',ha='center')
    ax.spines[['top','right']].set_visible(False)
axes[0].set_ylabel('Out-of-fold MAE (BRL; lower is better)')
fig.suptitle('Rio Airbnb | training-only baselines',fontsize=15)
fig.savefig(root/'reports/generated/baselines/comparison.png',dpi=180)
plt.close(fig)
