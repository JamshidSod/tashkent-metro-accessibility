"""
Generate static isochrone maps for Tashkent Metro accessibility.
Produces 6 images: walk/bike × 5/10/15 min, each with basemap,
isochrone polygons, station dots + labels, and a summary table.
"""

import json
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.colors as mcolors
from matplotlib.gridspec import GridSpec
import contextily as ctx
from pathlib import Path

warnings.filterwarnings("ignore")
matplotlib.rcParams["font.family"] = "DejaVu Sans"

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
OUT  = ROOT / "Output"
OUT.mkdir(exist_ok=True)

# ── Colours ───────────────────────────────────────────────────────────────────
LINE_COLORS = {
    "Chilonzor Line":     "#1565C0",
    "O'zbekiston Line":   "#C62828",
    "Yunusobod Line":     "#2E7D32",
    "Ring Line (Yellow)": "#F9A825",
    "Other":              "#757575",
}

ISO_COLORS = {
    "walk": {5: "#D0E9FF", 10: "#5BA4CF", 15: "#1A5276"},
    "bike": {5: "#D5F5E3", 10: "#58D68D", 15: "#1E8449"},
}
ISO_ALPHA  = {5: 0.55, 10: 0.50, 15: 0.45}

# ── Load data ─────────────────────────────────────────────────────────────────
metrics  = pd.read_csv(DATA / "metrics.csv")
stations = gpd.read_file(DATA / "stations.geojson").to_crs(epsg=3857)
iso_walk = gpd.read_file(DATA / "isochrones_walk.geojson").to_crs(epsg=3857)
iso_bike = gpd.read_file(DATA / "isochrones_bike.geojson").to_crs(epsg=3857)

# stations.geojson already has 'line'; attach colour and metric columns
stations["color"] = stations["line"].map(LINE_COLORS).fillna("#757575")

metric_cols = ["station_id",
               "walk_area_5","walk_pop_5","walk_area_10","walk_pop_10","walk_area_15","walk_pop_15",
               "bike_area_5","bike_pop_5","bike_area_10","bike_pop_10","bike_area_15","bike_pop_15"]
stations = stations.merge(metrics[metric_cols], on="station_id", how="left")

# ── Helper: order stations along a line using nearest-neighbour path ──────────
def order_line_stations(sub_gdf):
    """Return integer index list ordering stations continuously along the line.
    Starts from the station most distant from the centroid (a natural endpoint)
    and greedily picks the closest unvisited station at each step."""
    pts = np.column_stack([sub_gdf.geometry.x.values,
                           sub_gdf.geometry.y.values])
    n = len(pts)
    if n <= 2:
        return list(range(n))

    # Start from the station furthest from the centroid
    cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
    start  = int(((pts[:, 0] - cx)**2 + (pts[:, 1] - cy)**2).argmax())

    visited   = [start]
    remaining = list(range(n))
    remaining.remove(start)

    while remaining:
        last = visited[-1]
        rem  = np.array(remaining)
        d    = (pts[rem, 0] - pts[last, 0])**2 + (pts[rem, 1] - pts[last, 1])**2
        nearest = remaining[int(d.argmin())]
        visited.append(nearest)
        remaining.remove(nearest)

    return visited


# ── Helper: build summary table for one mode/minute ───────────────────────────
def build_table(mode, minutes):
    area_col = f"{mode}_area_{minutes}"
    pop_col  = f"{mode}_pop_{minutes}"
    df = metrics[["name_uz", "line", area_col, pop_col]].copy()
    df.columns = ["Station", "Line", "Area (km²)", "Population"]
    df = df.sort_values("Area (km²)", ascending=False)
    # Aggregate by line
    agg = (df.groupby("Line", sort=False)
             .agg(Stations=("Station","count"),
                  **{"Avg Area (km²)": ("Area (km²)", "mean"),
                     "Total Pop":      ("Population", "sum")})
             .reset_index())
    agg["Avg Area (km²)"] = agg["Avg Area (km²)"].round(2)
    agg["Total Pop"] = agg["Total Pop"].apply(lambda x: f"{x:,.0f}")
    agg = agg.sort_values("Avg Area (km²)", ascending=False).reset_index(drop=True)
    return df, agg


# ── Main drawing function ──────────────────────────────────────────────────────
def make_map(mode, minutes):
    iso_all = iso_walk if mode == "walk" else iso_bike
    iso = iso_all[iso_all["minutes"] == minutes].copy()

    colors = ISO_COLORS[mode]
    alpha  = ISO_ALPHA[minutes]
    mode_label = "Walking" if mode == "walk" else "Cycling"
    area_col   = f"{mode}_area_{minutes}"
    pop_col    = f"{mode}_pop_{minutes}"

    # ── Figure layout ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(20, 14), dpi=150, facecolor="white")
    # Left: map (wider); Right: table panel
    gs = GridSpec(1, 2, figure=fig, width_ratios=[3, 1.2], wspace=0.03)
    ax_map   = fig.add_subplot(gs[0])
    ax_table = fig.add_subplot(gs[1])
    ax_table.axis("off")

    # ── Draw isochrones ────────────────────────────────────────────────────────
    iso.plot(
        ax=ax_map,
        color=colors[minutes],
        edgecolor="white",
        linewidth=0.4,
        alpha=alpha,
        zorder=2,
    )

    # ── Basemap ────────────────────────────────────────────────────────────────
    try:
        ctx.add_basemap(
            ax_map,
            crs=iso.crs,
            source=ctx.providers.CartoDB.Positron,
            zoom=12,
            attribution="© OpenStreetMap contributors © CARTO",
            attribution_size=7,
        )
    except Exception:
        try:
            ctx.add_basemap(ax_map, crs=iso.crs,
                            source=ctx.providers.Stamen.TonerLite, zoom=12)
        except Exception:
            ax_map.set_facecolor("#f5f5f5")

    # ── Metro lines — draw as ordered continuous paths ─────────────────────────
    line_order = ["Chilonzor Line", "O'zbekiston Line", "Yunusobod Line",
                  "Ring Line (Yellow)", "Other"]
    for line in line_order:
        sub = stations[stations["line"] == line]
        if len(sub) > 1:
            idx  = order_line_stations(sub)
            sub_ord = sub.iloc[idx]
            xs = sub_ord.geometry.x.values
            ys = sub_ord.geometry.y.values
            ax_map.plot(xs, ys, "-",
                        color=LINE_COLORS.get(line, "#999"),
                        linewidth=3.0, alpha=0.90, zorder=3,
                        solid_capstyle="round", solid_joinstyle="round")

    # ── Station dots ───────────────────────────────────────────────────────────
    for _, row in stations.iterrows():
        ax_map.plot(row.geometry.x, row.geometry.y, "o",
                    color=row["color"], markersize=6,
                    markeredgecolor="white", markeredgewidth=0.8,
                    zorder=5)

    # ── Station labels (only for larger isochrones to reduce clutter) ─────────
    # Use the station data that has metric values
    labeled = stations.copy()
    # Filter to top/bottom stations by area for 5-min to reduce clutter
    if minutes == 5:
        threshold = labeled[area_col].quantile(0.5)
        labeled = labeled[labeled[area_col] >= threshold]

    for _, row in labeled.iterrows():
        name = row.get("name_uz", "")
        ax_map.annotate(
            name,
            xy=(row.geometry.x, row.geometry.y),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=6.5,
            color="#1a1a1a",
            fontweight="bold",
            path_effects=[
                pe.Stroke(linewidth=2.5, foreground="white"),
                pe.Normal(),
            ],
            zorder=6,
            clip_on=True,
        )

    # ── Map extent: use isochrone bounds with padding ─────────────────────────
    xmin, ymin, xmax, ymax = iso.total_bounds
    pad_x = (xmax - xmin) * 0.05
    pad_y = (ymax - ymin) * 0.05
    ax_map.set_xlim(xmin - pad_x, xmax + pad_x)
    ax_map.set_ylim(ymin - pad_y, ymax + pad_y)
    ax_map.set_axis_off()

    # ── Legend ─────────────────────────────────────────────────────────────────
    iso_patch = mpatches.Patch(color=colors[minutes], alpha=0.7,
                               label=f"{minutes}-min {mode_label} zone")
    line_patches = [
        mpatches.Patch(color=c, label=l)
        for l, c in LINE_COLORS.items() if l != "Other"
    ]
    legend = ax_map.legend(
        handles=[iso_patch] + line_patches,
        loc="lower left",
        fontsize=8,
        framealpha=0.9,
        edgecolor="#cccccc",
        title="Legend",
        title_fontsize=9,
    )
    legend.get_frame().set_linewidth(0.5)

    # ── Title ──────────────────────────────────────────────────────────────────
    fig.text(
        0.38, 0.97,
        f"Tashkent Metro — {minutes}-Minute {mode_label} Accessibility",
        ha="center", va="top",
        fontsize=16, fontweight="bold", color="#1a1a1a",
    )
    fig.text(
        0.38, 0.935,
        "Isochrone coverage zones around 49 metro stations",
        ha="center", va="top",
        fontsize=10, color="#555555",
    )

    # ── Summary table ─────────────────────────────────────────────────────────
    station_df, agg_df = build_table(mode, minutes)

    # Top panel: per-line summary
    ax_table.text(0.5, 0.98, "Summary by Line",
                  ha="center", va="top", fontsize=11, fontweight="bold",
                  transform=ax_table.transAxes)

    col_labels = ["Metro Line", "Stations", "Avg Area\n(km²)", "Total Pop."]
    table_data = []
    row_colors = []
    for _, r in agg_df.iterrows():
        table_data.append([r["Line"], str(r["Stations"]),
                           f"{r['Avg Area (km²)']:.2f}", r["Total Pop"]])
        lc = LINE_COLORS.get(r["Line"], "#757575")
        # pale version of the line colour for row bg
        rgba = mcolors.to_rgba(lc, alpha=0.15)
        row_colors.append([rgba, rgba, rgba, rgba])

    tbl = ax_table.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc="center",
        loc="upper center",
        bbox=[0.0, 0.62, 1.0, 0.34],
        cellColours=row_colors,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#cccccc")
        cell.set_linewidth(0.5)
        if r == 0:
            cell.set_facecolor("#e8e8e8")
            cell.set_text_props(fontweight="bold")

    # Middle panel: overall stats
    total_pop   = metrics[pop_col].sum()
    avg_area    = metrics[area_col].mean()
    median_pop  = metrics[pop_col].median()
    max_station = metrics.loc[metrics[area_col].idxmax(), "name_uz"]
    max_area    = metrics[area_col].max()

    stats_lines = [
        ("Total population reached",  f"{total_pop:,.0f}"),
        ("Average area per station",  f"{avg_area:.2f} km²"),
        ("Median population reached", f"{median_pop:,.0f}"),
        ("Largest zone (station)",    f"{max_station}"),
        ("Largest zone (area)",       f"{max_area:.2f} km²"),
    ]

    ax_table.text(0.5, 0.60, "Overall Statistics",
                  ha="center", va="top", fontsize=11, fontweight="bold",
                  transform=ax_table.transAxes)
    y0 = 0.56
    for label, val in stats_lines:
        ax_table.text(0.03, y0, label + ":", ha="left", va="top",
                      fontsize=8.5, color="#555", transform=ax_table.transAxes)
        ax_table.text(0.97, y0, val, ha="right", va="top",
                      fontsize=8.5, fontweight="bold", transform=ax_table.transAxes)
        y0 -= 0.055
        ax_table.plot([0.01, 0.99], [y0 + 0.022, y0 + 0.022],
                      linewidth=0.4, color="#dddddd",
                      transform=ax_table.transAxes, clip_on=False)

    # Bottom panel: per-station table (top 15 by area)
    ax_table.text(0.5, 0.27, f"Top Stations by {minutes}-min {mode_label} Area",
                  ha="center", va="top", fontsize=10, fontweight="bold",
                  transform=ax_table.transAxes)

    top15 = station_df.head(15)
    st_data = [[r["Station"][:20], f"{r['Area (km²)']:.2f}",
                f"{r['Population']:,.0f}"]
               for _, r in top15.iterrows()]

    st_colors = []
    for _, r in top15.iterrows():
        lc = LINE_COLORS.get(r["Line"], "#757575")
        rgba = mcolors.to_rgba(lc, alpha=0.12)
        st_colors.append([rgba, rgba, rgba])

    tbl2 = ax_table.table(
        cellText=st_data,
        colLabels=["Station", "Area\n(km²)", "Pop."],
        cellLoc="center",
        loc="upper center",
        bbox=[0.0, 0.0, 1.0, 0.25],
        cellColours=st_colors,
    )
    tbl2.auto_set_font_size(False)
    tbl2.set_fontsize(7.5)
    for (r, c), cell in tbl2.get_celld().items():
        cell.set_edgecolor("#cccccc")
        cell.set_linewidth(0.4)
        if r == 0:
            cell.set_facecolor("#e8e8e8")
            cell.set_text_props(fontweight="bold")

    # Source note
    fig.text(0.5, 0.01,
             "Data: OpenStreetMap · WorldPop · Valhalla routing · Tashkent Metro (2024–2025)",
             ha="center", va="bottom", fontsize=7, color="#888888")

    # ── Save ──────────────────────────────────────────────────────────────────
    fname = OUT / f"isochrone_{mode}_{minutes}min.png"
    fig.savefig(fname, dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  Saved → {fname}")


# ── Run all 6 combinations ────────────────────────────────────────────────────
if __name__ == "__main__":
    combos = [
        ("walk", 5), ("walk", 10), ("walk", 15),
        ("bike", 5), ("bike", 10), ("bike", 15),
    ]
    for mode, mins in combos:
        print(f"Generating {mode} {mins}-min map …")
        make_map(mode, mins)
    print("\nDone. All maps saved to:", OUT)
