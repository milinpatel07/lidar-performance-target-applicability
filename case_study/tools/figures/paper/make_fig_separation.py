"""Fig. 5: ROC curves (top) and FAP against the threshold (bottom), split 0, test part.
Input: fig_separation_curves.csv (columns panel,row,condition,x,y,tau,L,U)."""
import sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('pdf')
import matplotlib.pyplot as plt

d = pd.read_csv(sys.argv[1]); out = sys.argv[2]
plt.rcParams.update({'font.family': 'STIXGeneral', 'mathtext.fontset': 'stix', 'font.size': 8,
                     'axes.labelsize': 8, 'axes.titlesize': 8.5, 'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5,
                     'legend.fontsize': 7.5, 'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
                     'pdf.fonttype': 42})
BLUE = (0/255, 114/255, 178/255); BLACK = 'black'
panels = [('distance (KITTI, $u_{\\mathrm{s}}$)', 'near', 'far', '$u_{\\mathrm{s}}$', [0, 0.2, 0.4]),
          ('weather (nuScenes, $u_{\\mathrm{e}}$)', 'clear', 'rain', '$u_{\\mathrm{e}}$', [0, 0.25, 0.5, 0.75]),
          ('dataset and detector ($u_{\\mathrm{s}}$)', 'nuScenes', 'KITTI', '$u_{\\mathrm{s}}$', [0, 0.2, 0.4])]
fig, axs = plt.subplots(2, 3, figsize=(345.827/72, 221.102/72))
for j, (p, cs, cu, ulab, xt) in enumerate(panels):
    g = d[d.panel == p]
    # ---- ROC
    ax = axs[0, j]
    ax.plot([0, 1], [0, 1], ls=':', lw=0.6, color=(0.62, 0.62, 0.62))
    for c, col, ls in [(cs, BLACK, '-'), (cu, BLUE, '--')]:
        r = g[(g.row == 'ROC') & (g.condition == c)]
        x = r.x.values; y = r.y.values; o = np.argsort(x, kind='stable')
        trapz = getattr(np, "trapezoid", None) or np.trapz   # trapezoid since NumPy 2.0, trapz before
        auc = trapz(y[o], x[o])
        ax.plot(x, y, ls=ls, lw=1.1, color=col, label='%s %.3f' % (c, auc))
        op = g[(g.row == 'ROC operating point') & (g.condition == c)].sort_values('tau', ascending=False)
        # larger tau = threshold selected at 0.1 (square); smaller tau = threshold selected at 10^-2 (circle)
        ax.plot(op.x.values[0], op.y.values[0], 's', ms=5, mfc='white', mec=col, mew=1.0, zorder=5)
        ax.plot(op.x.values[1], op.y.values[1], 'o', ms=4.5, mfc=col, mec=col, zorder=5)
    leg = ax.legend(loc='lower right', frameon=False, handlelength=1.6, borderaxespad=0.2)
    for t, col in zip(leg.get_texts(), [BLACK, BLUE]): t.set_color(col)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.set_xticks([0, 0.5, 1]); ax.set_yticks([0, 0.5, 1])
    ax.set_xticklabels(['0.0', '0.5', '1.0']); ax.set_yticklabels(['0.0', '0.5', '1.0'])
    ax.set_xlabel('correct detections withheld', labelpad=1)
    if j == 0: ax.set_ylabel('wrong detections rejected', labelpad=2)
    ax.set_title(p, pad=4)
    # ---- FAP against threshold
    ax = axs[1, j]
    for c, col, ls in [(cs, BLACK, '-'), (cu, BLUE, '--')]:
        r = g[(g.row == 'A_c(tau)') & (g.condition == c)].sort_values('x')
        ax.plot(r.x, r.y, ls=ls, lw=1.1, color=col)
    hb = g[g.row == 'HB interval at tau(0.1)']
    t0 = hb.x.values[0]
    xmax = g[g.row == 'A_c(tau)'].x.max()
    for yy in (0.1, 0.01): ax.axhline(yy, ls=':', lw=0.6, color=(0.62, 0.62, 0.62))
    ax.axvline(t0, color=BLACK, lw=0.9)
    off = 0.022 * xmax
    for c, col, dx in [(cs, BLACK, -off), (cu, BLUE, off)]:
        h = hb[hb.condition == c]
        ax.plot([t0 + dx, t0 + dx], [h.L.values[0], h.U.values[0]], color=col, lw=2.6, solid_capstyle='butt')
    ax.set_yscale('log'); ax.set_ylim(1e-3, 1); ax.set_xlim(0, xmax)
    ax.set_xticks(xt); ax.set_xticklabels(['%.2f' % v if len(xt) == 4 else '%.1f' % v for v in xt])
    ax.set_xlabel('threshold $\\tau$ on ' + ulab, labelpad=1)
    if j == 0: ax.set_ylabel('FAP $A_c(\\tau)$', labelpad=2)
    else: ax.set_yticklabels([])
for ax in axs.flat:
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.tick_params(length=2.5, pad=1.5)
fig.subplots_adjust(left=0.09, right=0.985, top=0.93, bottom=0.085, wspace=0.28, hspace=0.42)
fig.savefig(out)
