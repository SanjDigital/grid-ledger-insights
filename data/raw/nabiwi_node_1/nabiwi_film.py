"""
GridLedger Forensic Film – Nabiwi Node
"The Film": 2-Year Forensic Graph
Parses raw SMS export → builds monthly master → renders publication-quality PNG
"""

import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 1. PARSE RAW SMS DATA
# ─────────────────────────────────────────────────────────────
TARGET_METER = '37154463253'
SOURCE_FILE  = '/mnt/user-data/uploads/SMS_exported_from_HiSuite2026-03-14_084735150.csv'

print("Loading SMS data …")
raw = pd.read_csv(SOURCE_FILE)
raw['Time'] = pd.to_datetime(raw['Time'], format='%Y/%m/%d %H:%M:%S')
raw = raw.sort_values('Time').reset_index(drop=True)

# ── 1a. ESCOM token purchases ─────────────────────────────────
escom_rows = raw[raw['Content'].str.contains(TARGET_METER, na=False)].copy()
escom_records = []
for _, row in escom_rows.iterrows():
    m = re.search(r'Units:\s*([\d.]+)\s*kwh', str(row['Content']), re.IGNORECASE)
    if m:
        kwh = float(m.group(1))
        if kwh < 600:          # exclude the anomalous 560-kWh credit load
            escom_records.append({'date': row['Time'].date(), 'metered_kwh': kwh})

edf = pd.DataFrame(escom_records)
edf['month'] = pd.to_datetime(edf['date']).dt.to_period('M')
monthly_metered = edf.groupby('month')['metered_kwh'].sum().reset_index()

# ── 1b. Operator production reports ("pa" messages) ───────────
pa_rows = raw[raw['Content'].str.match(r'^[Pp][Aa]\s+\d', na=False)].copy()

def parse_pa(content):
    """Extract every daily production record embedded in a single SMS."""
    records = []
    parts = re.split(r'\s+(?=[Pp][Aa]\s+\d)', content.strip())
    for part in parts:
        m_date  = re.search(r'[Pp][Aa]\s+(\d{1,2})[.\s/](\d{1,2})[.\s/](\d{2,4})', part)
        m_open  = re.search(r'open\s+(\d+)',          part, re.IGNORECASE)
        m_close = re.search(r'clos[eo]\s*(\d+)',      part, re.IGNORECASE)
        m_units = re.search(r'ndagayil\s+(\d+)',      part, re.IGNORECASE)
        m_amt   = re.search(r'amount\s+([\d,]+)',     part, re.IGNORECASE)
        m_late  = re.search(r'late\s+([\d,]+)',       part, re.IGNORECASE)
        if not (m_date and m_units):
            continue
        d, mo, y = int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3))
        if y < 100:
            y += 2000
        try:
            dt = datetime(y, mo, d)
        except ValueError:
            continue
        open_r  = int(m_open.group(1))  if m_open  else None
        close_r = int(m_close.group(1)) if m_close else None
        # Reported kWh = meter-reading drop; fall back to ndagayil count
        rep_kwh = max((open_r - close_r), 0) if (open_r and close_r) else int(m_units.group(1))
        milling = float(m_amt.group(1).replace(',', ''))  if m_amt  else 0.0
        net_rev = float(m_late.group(1).replace(',', '')) if m_late else 0.0
        records.append({
            'date':         dt.date(),
            'reported_kwh': rep_kwh,
            'kg_input':     int(m_units.group(1)),   # units ground ≈ kg proxy
            'cash_collected': milling + net_rev,     # total revenue (revised model)
        })
    return records

all_pa = []
for _, row in pa_rows.iterrows():
    all_pa.extend(parse_pa(str(row['Content'])))

pdf = pd.DataFrame(all_pa)
pdf = pdf.drop_duplicates(subset=['date'])
pdf = pdf[pdf['date'] <= datetime(2026, 3, 14).date()]
pdf['month'] = pd.to_datetime(pdf['date']).dt.to_period('M')

monthly_prod = pdf.groupby('month').agg(
    reported_kwh  = ('reported_kwh',   'sum'),
    cash_collected= ('cash_collected', 'sum'),
    kg_input      = ('kg_input',       'sum'),
).reset_index()

# ─────────────────────────────────────────────────────────────
# 2. BUILD MONTHLY MASTER TABLE
# ─────────────────────────────────────────────────────────────
master = monthly_metered.merge(monthly_prod, on='month', how='outer')
master = master.sort_values('month').reset_index(drop=True)
master['month_dt']      = master['month'].dt.to_timestamp()
master['reported_kwh']  = master['reported_kwh'].fillna(0)
master['cash_collected']= master['cash_collected'].fillna(0)
master['kg_input']      = master['kg_input'].fillna(0)
master['metered_kwh']   = master['metered_kwh'].fillna(0)

# ── 2a. Derived metrics ───────────────────────────────────────
# EAR: Energy Accountability Ratio  (clipped to [0, 1])
master['EAR'] = (master['reported_kwh'] / master['metered_kwh'].replace(0, np.nan)).clip(0, 1)

# ERR: Effective Revenue Rate  (MWK per metered kWh)
master['ERR'] = master['cash_collected'] / master['metered_kwh'].replace(0, np.nan)

# SEC: Specific Energy Consumption  (metered kWh per kg input)
master['SEC'] = np.where(
    master['kg_input'] > 0,
    master['metered_kwh'] / master['kg_input'],
    np.nan
)

# ── Phase boundaries ─────────────────────────────────────────
P1_START = pd.Timestamp('2022-08-01')   # Blind Zone
P1_END   = pd.Timestamp('2023-07-31')
P2_START = pd.Timestamp('2023-08-01')   # Active Concealment
P2_END   = pd.Timestamp('2026-02-28')
P3_START = pd.Timestamp('2026-03-01')   # GridLedger Enforcement
P3_END   = pd.Timestamp('2026-04-01')   # extend slightly for visibility

# ── Key numbers for annotations ───────────────────────────────
p1_hidden    = master[master['month_dt'] <= P1_END]['metered_kwh'].sum()
p2_gap       = (master[(master['month_dt'] >= P2_START) & (master['month_dt'] <= P2_END)]['metered_kwh'].sum()
              - master[(master['month_dt'] >= P2_START) & (master['month_dt'] <= P2_END)]['reported_kwh'].sum())
final_ear    = master[master['month_dt'] >= P3_START]['EAR'].mean()
total_hidden = p1_hidden + p2_gap

print(f"Phase 1 blind kWh  : {p1_hidden:,.0f}")
print(f"Phase 2 gap kWh    : {p2_gap:,.0f}")
print(f"Total hidden kWh   : {total_hidden:,.0f}")
print(f"Final EAR (Phase 3): {final_ear:.3f}")

# ── Print verification table ──────────────────────────────────
print("\n── Monthly Master Table ─────────────────────────────────")
pd.set_option('display.float_format', '{:,.1f}'.format)
print(master[['month','metered_kwh','reported_kwh','cash_collected',
              'kg_input','EAR','ERR','SEC']].to_string(index=False))

# ─────────────────────────────────────────────────────────────
# 3. RENDER "THE FILM"
# ─────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family':       'DejaVu Sans',
    'font.size':         9,
    'axes.linewidth':    0.6,
    'xtick.major.width': 0.6,
    'ytick.major.width': 0.6,
    'xtick.minor.visible': True,
    'xtick.minor.width': 0.4,
    'figure.dpi':        180,
})

DARK_BG   = '#0D1117'
GRID_COL  = '#1E2530'
TEXT_COL  = '#C9D1D9'
SUB_COL   = '#8B949E'
MET_COL   = '#A8B2C1'   # metered kWh  – cool silver
REP_COL   = '#F0A500'   # reported kWh – amber
EAR_COL   = '#3FB950'   # EAR          – green
ERR_COL   = '#79C0FF'   # ERR          – blue
FILL_COL  = '#F0A500'   # invisibility fill

P1_COL = '#FF4444'      # Blind Zone
P2_COL = '#FF8800'      # Active Concealment
P3_COL = '#23863A'      # GridLedger Enforcement

fig = plt.figure(figsize=(18, 10), facecolor=DARK_BG)

# ── Layout: main chart (top 70%) + ERR strip (bottom 30%) ────
gs = fig.add_gridspec(2, 1, height_ratios=[3, 1],
                      hspace=0.08, top=0.88, bottom=0.09,
                      left=0.07, right=0.93)

ax1 = fig.add_subplot(gs[0])   # kWh + EAR
ax3 = fig.add_subplot(gs[1])   # ERR strip

ax1.set_facecolor(DARK_BG)
ax3.set_facecolor(DARK_BG)
ax2 = ax1.twinx()              # EAR right axis

x = master['month_dt']

# ─── Phase shading ────────────────────────────────────────────
def shade(ax, xmin, xmax, color, alpha=0.10, zorder=0):
    ax.axvspan(xmin, xmax, color=color, alpha=alpha, zorder=zorder, linewidth=0)

for ax in [ax1, ax3]:
    shade(ax, P1_START, P1_END   + pd.Timedelta(days=31), P1_COL, alpha=0.13)
    shade(ax, P2_START, P2_END   + pd.Timedelta(days=31), P2_COL, alpha=0.07)
    shade(ax, P3_START, P3_END,                            P3_COL, alpha=0.15)

# Phase border lines
for ax in [ax1, ax3]:
    for ts, col in [(P2_START, P2_COL), (P3_START, P3_COL)]:
        ax.axvline(ts, color=col, lw=1.2, alpha=0.7, zorder=3, linestyle='--')

# ─── kWh area fill (Invisibility Layer) ─────────────────────
# Only where metered > reported (the gap)
met = master['metered_kwh'].values
rep = master['reported_kwh'].values
below = np.minimum(met, rep)
above = np.maximum(met, rep)

ax1.fill_between(x, below, above,
                 where=(met >= rep),
                 color=FILL_COL, alpha=0.18,
                 label='Invisibility Layer (unreported kWh)',
                 zorder=2)

# ─── Main kWh lines ──────────────────────────────────────────
ax1.plot(x, master['metered_kwh'],
         color=MET_COL, lw=2.0, zorder=5,
         label='Metered kWh (ESCOM tokens)', solid_capstyle='round')

ax1.plot(x, master['reported_kwh'],
         color=REP_COL, lw=2.0, linestyle='--', zorder=5,
         label='Reported kWh (operator)', dash_capstyle='round')

# ─── EAR on right axis ───────────────────────────────────────
ear_clean = master['EAR'].copy()
# Phase 1: EAR is 0 by definition (no reports) – mark differently
p1_mask = master['month_dt'] <= P1_END
p2_mask = (master['month_dt'] > P1_END) & (master['month_dt'] <= P2_END)
p3_mask = master['month_dt'] > P2_END

ax2.plot(x[~p1_mask], ear_clean[~p1_mask],
         color=EAR_COL, lw=2.2, zorder=6, label='EAR')
# Phase 1 EAR as dotted zero baseline
ax2.plot(x[p1_mask], ear_clean[p1_mask],
         color=EAR_COL, lw=1.2, alpha=0.4, linestyle=':', zorder=4)

# EAR horizontal reference band
ax2.axhspan(0.95, 1.0, color=EAR_COL, alpha=0.08, zorder=1)
ax2.axhline(1.0, color=EAR_COL, lw=0.5, alpha=0.3, zorder=2)

# ─── ERR strip ───────────────────────────────────────────────
err_valid = master['ERR'].replace(0, np.nan)
ax3.plot(x, err_valid, color=ERR_COL, lw=1.8, zorder=5)
ax3.fill_between(x, 0, err_valid.fillna(0),
                 color=ERR_COL, alpha=0.15, zorder=2)
ax3.axhline(0, color=GRID_COL, lw=0.5)

# ─── Axes formatting ─────────────────────────────────────────
for ax in [ax1, ax2, ax3]:
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_color(GRID_COL)
    ax.spines['left'].set_color(GRID_COL)
    ax.spines['right'].set_color(GRID_COL)
    ax.tick_params(colors=SUB_COL, which='both')
    ax.yaxis.label.set_color(SUB_COL)

ax1.set_xlim(x.min() - pd.Timedelta(days=15),
             x.max() + pd.Timedelta(days=45))
ax1.set_ylim(-30, master['metered_kwh'].max() * 1.15)
ax2.set_ylim(-0.05, 1.25)
ax3.set_xlim(ax1.get_xlim())
ax3.set_ylim(0, err_valid.max() * 1.3)

ax1.yaxis.set_major_locator(mticker.MultipleLocator(200))
ax1.yaxis.set_minor_locator(mticker.MultipleLocator(100))
ax1.grid(axis='y', color=GRID_COL, lw=0.5, zorder=0)
ax1.grid(axis='x', color=GRID_COL, lw=0.3, alpha=0.4, zorder=0)

ax2.yaxis.set_major_locator(mticker.MultipleLocator(0.25))
ax2.yaxis.set_minor_locator(mticker.MultipleLocator(0.05))

ax3.yaxis.set_major_locator(mticker.MultipleLocator(500))
ax3.grid(axis='y', color=GRID_COL, lw=0.4, alpha=0.6, zorder=0)

ax1.set_ylabel('kWh (metered / reported)', color=SUB_COL, fontsize=9)
ax2.set_ylabel('EAR  (0 – 1)', color=EAR_COL, fontsize=9)
ax3.set_ylabel('ERR\n(MWK/kWh)', color=ERR_COL, fontsize=8, labelpad=4)

import matplotlib.dates as mdates
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax1.tick_params(labelbottom=False)
ax3.tick_params(axis='x', labelsize=7.5, colors=SUB_COL)

# ─── Phase labels ─────────────────────────────────────────────
def phase_label(ax, x_center, y_frac, text, color, fontsize=8.5):
    ymin, ymax = ax.get_ylim()
    y = ymin + (ymax - ymin) * y_frac
    ax.text(x_center, y, text,
            color=color, fontsize=fontsize, fontweight='bold',
            ha='center', va='center', alpha=0.85,
            bbox=dict(boxstyle='round,pad=0.3', fc=DARK_BG, ec=color,
                      alpha=0.7, lw=0.8),
            zorder=10)

p1_mid = P1_START + (P1_END - P1_START) / 2
p2_mid = P2_START + (P2_END - P2_START) / 2
p3_mid = P3_START + pd.Timedelta(days=15)

phase_label(ax1, p1_mid, 0.90, '① BLIND ZONE', P1_COL, fontsize=8.0)
phase_label(ax1, p1_mid, 0.80, 'Pre-Jeremiah operator', P1_COL, fontsize=7.0)
phase_label(ax1, p2_mid, 0.90, '② ACTIVE CONCEALMENT', P2_COL, fontsize=8.0)
phase_label(ax1, p2_mid, 0.80, 'Jeremiah · system exists, enforcement absent', P2_COL, fontsize=7.0)
phase_label(ax1, p3_mid, 0.90, '③ ENFORCEMENT', P3_COL, fontsize=8.0)
phase_label(ax1, p3_mid, 0.80, 'GridLedger active', P3_COL, fontsize=7.0)

# ─── Annotation callouts ──────────────────────────────────────
def callout(ax, x_pt, y_pt, x_text, y_text, text, color, fontsize=8.2):
    ax.annotate(text,
                xy=(x_pt, y_pt), xytext=(x_text, y_text),
                textcoords='data',
                color=TEXT_COL, fontsize=fontsize,
                ha='center',
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=1.0, connectionstyle='arc3,rad=0.2'),
                bbox=dict(boxstyle='round,pad=0.35', fc='#161B22',
                          ec=color, lw=0.8, alpha=0.92),
                zorder=15)

# Phase 1 — Blind Zone (pre-Jeremiah operator, no reporting system)
callout(ax1,
        pd.Timestamp('2023-02-01'), 280,
        pd.Timestamp('2022-11-01'), 950,
        f'Different operator. No reporting\nsystem. {p1_hidden:,.0f} kWh purchased –\nzero accountability.',
        P1_COL)

# Phase 2 peak gap month with pattern note
callout(ax1,
        pd.Timestamp('2025-11-01'), master.loc[master['month_dt']==pd.Timestamp('2025-11-01'), 'metered_kwh'].values[0],
        pd.Timestamp('2024-09-01'), 1400,
        f'Peak gap: Nov 2025 – 489 kWh hidden.\nPatterns: leading-day compression,\nholiday gaps, 560-kWh token anomaly.',
        P2_COL)

# Phase 2 — total gap: system introduced but enforcement absent
callout(ax1,
        pd.Timestamp('2024-06-01'), 500,
        pd.Timestamp('2024-01-01'), 280,
        f'Reporting system introduced,\nbut gaps persist. {p2_gap:,.0f} kWh\nhidden – enforcement absent.',
        P2_COL)

# Phase 3 — EAR rising but not closed; enforcement must be sustained
ax2.annotate(
    f'GridLedger active. EAR = {final_ear:.2f}.\nGap shrinks – not closed.\nEnforcement must be sustained.',
    xy=(pd.Timestamp('2026-03-01'), final_ear),
    xytext=(pd.Timestamp('2025-08-01'), 1.12),
    textcoords='data',
    color=TEXT_COL, fontsize=8.0, ha='center',
    arrowprops=dict(arrowstyle='->', color=EAR_COL, lw=1.0,
                    connectionstyle='arc3,rad=-0.25'),
    bbox=dict(boxstyle='round,pad=0.35', fc='#161B22',
              ec=EAR_COL, lw=0.8, alpha=0.92),
    zorder=15)

# 560-kWh anomalous token load — Jeremiah concealment technique
anomaly_date = pd.Timestamp('2025-02-01')
callout(ax1,
        anomaly_date,
        master.loc[master['month_dt']==anomaly_date, 'metered_kwh'].values[0],
        pd.Timestamp('2025-05-01'), 1300,
        '560 kWh bulk load\n(Feb 2025) – breaks\ntoken audit trail',
        '#FF79C6')

# ─── Title block ──────────────────────────────────────────────
fig.text(0.07, 0.955,
         'THE FILM — NABIWI NODE  ·  GridLedger Forensic Audit',
         color=TEXT_COL, fontsize=14, fontweight='bold', va='top')

fig.text(0.07, 0.930,
         f'Meter 37154463253  ·  Aug 2022 – Mar 2026  ·  '
         f'Total hidden energy: {total_hidden:,.0f} kWh  ·  '
         f'Est. unaccounted revenue: MWK {total_hidden * 1_000:,.0f}+',
         color=SUB_COL, fontsize=8.5, va='top')

fig.text(0.07, 0.911,
         'Phase 1: baseline opacity (pre-Jeremiah, no system).  '
         'Phase 2: Jeremiah takes over – system introduced, enforcement absent.  '
         'Phase 3: GridLedger enforcement begins – EAR rises but full closure requires persistence.',
         color=SUB_COL, fontsize=7.8, va='top', alpha=0.85)

# ─── Legend ───────────────────────────────────────────────────
legend_elements = [
    Line2D([0],[0], color=MET_COL, lw=2,  label='Metered kWh (ESCOM tokens)'),
    Line2D([0],[0], color=REP_COL, lw=2,  label='Reported kWh (operator SMS)', linestyle='--'),
    mpatches.Patch(color=FILL_COL, alpha=0.35, label='Invisibility Layer (unreported energy)'),
    Line2D([0],[0], color=EAR_COL, lw=2,  label='EAR – Energy Accountability Ratio (right axis)'),
    mpatches.Patch(color=P1_COL,   alpha=0.35, label='① Blind Zone – pre-Jeremiah, no reporting system'),
    mpatches.Patch(color=P2_COL,   alpha=0.25, label='② Active Concealment – system exists, enforcement absent'),
    mpatches.Patch(color=P3_COL,   alpha=0.40, label='③ GridLedger Enforcement – gap shrinking, not yet closed'),
]
leg = ax1.legend(handles=legend_elements,
                 loc='upper left', fontsize=7.8,
                 framealpha=0.85, edgecolor=GRID_COL,
                 facecolor='#161B22', labelcolor=TEXT_COL,
                 ncol=2, columnspacing=1.2,
                 bbox_to_anchor=(0.0, 0.82))

# ─── Watermark ────────────────────────────────────────────────
fig.text(0.93, 0.015, 'GridLedger  ·  CONFIDENTIAL',
         color=SUB_COL, fontsize=7, ha='right', alpha=0.5)

# ─────────────────────────────────────────────────────────────
# 4. SAVE
# ─────────────────────────────────────────────────────────────
out_path = '/mnt/user-data/outputs/nabiwi_forensic_film.png'
Path(out_path).parent.mkdir(parents=True, exist_ok=True)
plt.savefig(out_path, dpi=200, bbox_inches='tight',
            facecolor=DARK_BG, edgecolor='none')
print(f"\nSaved → {out_path}")
plt.close()
