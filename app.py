import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Health Resources in Lebanon", page_icon="🏥", layout="wide")

# ---------------------------------------------------------------
# Data loading and cleaning (same steps as the Plotly assignment)
# ---------------------------------------------------------------
RENAME = {
    "type and size of medical resources - pharmacies": "Pharmacies",
    "total number of care centers": "Care centers",
    "total number of first aid centers": "First aid centers",
    "type and size of medical resources - medical centers": "Medical centers",
    "type and size of medical resources - hospitals": "Hospitals",
    "type and size of medical resources - clinics": "Clinics",
    "type and size of medical resources - labs and radiology": "Labs & radiology",
    "town": "Town",
    "refarea": "refArea",
}

FACILITY_COLS = ["Pharmacies", "Clinics", "First aid centers", "Care centers",
                 "Labs & radiology", "Medical centers", "Hospitals"]

# The 7 facility types are grouped into 3 levels of care to reduce clutter.
# Advanced care gets the only strong color because it carries the main story.
TIERS = {
    "Basic care": ["Pharmacies", "Clinics", "First aid centers"],
    "Community centers": ["Care centers", "Medical centers"],
    "Advanced care": ["Hospitals", "Labs & radiology"],
}
TIER_COLORS = {"Basic care": "#BFD7EA", "Community centers": "#5B8DB8", "Advanced care": "#D1495B"}
TIER_ORDER = list(TIERS.keys())

# refArea mixes governorates and districts, so every value is mapped to a governorate
AREA_TO_GOV = {
    "Mount_Lebanon": "Mount Lebanon", "Baabda": "Mount Lebanon", "Matn": "Mount Lebanon",
    "Keserwan": "Mount Lebanon", "Aley": "Mount Lebanon", "Byblos": "Mount Lebanon", "Chouf": "Mount Lebanon",
    "South": "South", "Sidon": "South", "Tyre": "South", "Jezzine": "South",
    "Nabatieh": "Nabatieh", "Bint_Jbeil": "Nabatieh", "Marjeyoun": "Nabatieh", "Hasbaya": "Nabatieh",
    "Beqaa": "Beqaa", "Zahl": "Beqaa", "Rashaya": "Beqaa",
    "Baalbek": "Baalbek-Hermel", "Hermel": "Baalbek-Hermel",
    "North": "North", "Tripoli": "North", "Batroun": "North", "Bsharri": "North",
    "Zgharta": "North", "Miniyeh": "North", "Koura": "North",
    "Akkar": "Akkar",
}


def to_governorate(url):
    area = str(url).split("/")[-1]
    for key, gov in AREA_TO_GOV.items():
        if key in area:
            return gov
    return "Other"


@st.cache_data
def load_data(path="health_resources.csv"):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]
    df = df.rename(columns=RENAME)
    df[FACILITY_COLS] = df[FACILITY_COLS].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)
    df["Town"] = df["Town"].astype(str).str.strip()
    df["Governorate"] = df["refArea"].apply(to_governorate)
    df["Total facilities"] = df[FACILITY_COLS].sum(axis=1)
    df["Label"] = df["Town"] + " (" + df["Governorate"] + ")"
    for tier, cols in TIERS.items():
        df[tier] = df[cols].sum(axis=1)
    return df[["Town", "Governorate", "Label"] + FACILITY_COLS + TIER_ORDER + ["Total facilities"]]


df = load_data()
gov_totals = df.groupby("Governorate")[FACILITY_COLS + TIER_ORDER].sum()
gov_totals["Total"] = gov_totals[FACILITY_COLS].sum(axis=1)
gov_totals = gov_totals.sort_values("Total", ascending=False)
national_total = int(gov_totals["Total"].sum())

# ---------------------------------------------------------------
# 1. Context
# ---------------------------------------------------------------
st.title("🏥 Where can people in Lebanon get healthcare?")
st.markdown(
    f"""
This page uses the **Health Resources in Lebanon (2023)** dataset from Impact Open Data,
published through AUB's linked open data portal. It lists **{len(df):,} towns** and counts
the health facilities in each one: pharmacies, clinics, first aid centers, care centers,
labs and radiology, medical centers and hospitals.

The question behind the page: **is access to healthcare spread evenly across Lebanon, or
concentrated in a few places?**
"""
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Health facilities", f"{national_total:,}")
c2.metric("Hospitals", f"{int(df['Hospitals'].sum()):,}")
c3.metric("Towns covered", f"{len(df):,}")
zero_share = (df["Total facilities"] == 0).mean()
c4.metric("Towns with no facility", f"{zero_share:.0%}")

# ---------------------------------------------------------------
# 2. Key insights (computed from the data)
# ---------------------------------------------------------------
top_gov = gov_totals.index[0]
low_gov = gov_totals.index[-1]
top_share = gov_totals["Total"].iloc[0] / national_total
top15 = df.nlargest(15, "Total facilities")
top15_share = top15["Total facilities"].sum() / national_total
biggest = top15.iloc[0]

st.subheader("Key insights")
i1, i2 = st.columns(2)
i1.info(
    f"**1. One region dominates.** {top_gov} holds {top_share:.0%} of all facilities "
    f"({int(gov_totals['Total'].iloc[0]):,}). {low_gov} has only {int(gov_totals['Total'].iloc[-1]):,} "
    f"and just {int(gov_totals.loc[low_gov, 'Hospitals'])} hospitals, versus "
    f"{int(gov_totals.loc[top_gov, 'Hospitals'])} in {top_gov}."
)
i2.info(
    f"**2. A few cities carry the load.** The top 15 towns (about 1% of all towns) hold "
    f"{top15_share:.0%} of the country's facilities. {biggest['Town']} alone has "
    f"{int(biggest['Total facilities'])}, close to the total for {low_gov}."
)

st.divider()

# ---------------------------------------------------------------
# 3. Linked interaction: governorate -> towns
# ---------------------------------------------------------------
st.header("Explore: drill down from region to town")

w1, w2 = st.columns([1, 2])
with w1:
    gov_options = ["All of Lebanon"] + gov_totals.index.tolist()
    governorate = st.selectbox(
        "Step 1 – Choose a governorate",
        gov_options,
        help="This also changes which towns you can pick in Step 2.",
    )

# The town list depends on the governorate chosen above (this is what links the widgets)
if governorate == "All of Lebanon":
    scope = df
    label_col = "Label"  # town names repeat across regions, so show the region too
else:
    scope = df[df["Governorate"] == governorate]
    label_col = "Town"

scope_sorted = scope.sort_values("Total facilities", ascending=False)
town_options = scope_sorted[label_col].tolist()

with w2:
    towns = st.multiselect(
        f"Step 2 – Compare towns in {governorate} (sorted by number of facilities, up to 10)",
        town_options,
        default=town_options[:5],
        max_selections=10,
        key=f"towns_{governorate}",  # resets the selection when the governorate changes
        help="Starts with the 5 best-equipped towns. Add a small town to see the contrast.",
    )

# KPIs for the selected scope
scope_total = int(scope["Total facilities"].sum())
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Facilities in {governorate}", f"{scope_total:,}")
k2.metric("Share of national total", f"{scope_total / national_total:.0%}")
k3.metric("Hospitals & labs (advanced care)", f"{int(scope['Advanced care'].sum()):,}")
k4.metric("Towns with no facility", f"{(scope['Total facilities'] == 0).mean():.0%}")

# One shared legend for both charts (same colors mean the same thing everywhere)
legend = " &nbsp;&nbsp; ".join(
    f"<span style='display:inline-block;width:12px;height:12px;background:{TIER_COLORS[t]};"
    f"border-radius:2px;margin-right:6px;vertical-align:middle'></span>"
    f"<b>{t}</b> <span style='color:#6b7280'>({', '.join(TIERS[t]).lower()})</span>"
    for t in TIER_ORDER
)
st.markdown(legend, unsafe_allow_html=True)


def stacked_hbar(data, name_col, order_top_to_bottom, title, highlight=None, height=420):
    """Horizontal stacked bar by level of care, biggest on top, total labeled at the end."""
    long = data.melt(id_vars=[name_col], value_vars=TIER_ORDER,
                     var_name="Level of care", value_name="Facilities")
    fig = px.bar(
        long, x="Facilities", y=name_col, color="Level of care", orientation="h",
        category_orders={name_col: order_top_to_bottom, "Level of care": TIER_ORDER},
        color_discrete_map=TIER_COLORS, title=title,
    )
    fig.update_traces(hovertemplate="%{y}<br>%{fullData.name}: %{x}<extra></extra>")
    if highlight is not None:
        for trace in fig.data:
            trace.marker.opacity = [1.0 if n == highlight else 0.25 for n in trace.y]
    totals = data.set_index(name_col)[TIER_ORDER].sum(axis=1)
    for name, total in totals.items():
        faded = highlight is not None and name != highlight
        fig.add_annotation(x=total, y=name, text=f"{int(total):,}", showarrow=False,
                           xanchor="left", xshift=6,
                           font=dict(size=13, color="#9ca3af" if faded else "#111827"))
    fig.update_layout(
        showlegend=False, height=height, bargap=0.3,
        xaxis=dict(title="Number of facilities", showgrid=True, gridcolor="#eef0f3"),
        yaxis=dict(title=""), plot_bgcolor="white",
        margin=dict(l=10, r=40, t=70, b=40), title_font_size=17,
    )
    return fig


left, right = st.columns(2)

# Chart 1: all governorates, the selected one highlighted
with left:
    gov_df = gov_totals[TIER_ORDER].reset_index()
    order = gov_totals.index.tolist()  # already sorted largest first
    if governorate == "All of Lebanon":
        title1 = f"{top_gov} has {top_share:.0%} of Lebanon's health facilities"
    else:
        rank = order.index(governorate) + 1
        share = gov_totals.loc[governorate, "Total"] / national_total
        title1 = f"{governorate} ranks #{rank} of 7, with {share:.0%} of all facilities"
    fig1 = stacked_hbar(gov_df, "Governorate", order, title1,
                        highlight=None if governorate == "All of Lebanon" else governorate)
    st.plotly_chart(fig1, width="stretch")

# Chart 2: the selected towns
with right:
    if not towns:
        st.warning("Pick at least one town in Step 2 to see the comparison.")
    else:
        chosen = scope[scope[label_col].isin(towns)].sort_values("Total facilities", ascending=False)
        top_town, low_town = chosen.iloc[0], chosen.iloc[-1]
        if len(chosen) >= 2 and low_town["Total facilities"] > 0:
            ratio = top_town["Total facilities"] / low_town["Total facilities"]
            title2 = f"{top_town['Town']} has {ratio:.0f}× the facilities of {low_town['Town']}"
        elif len(chosen) >= 2:
            title2 = f"{top_town['Town']} has {int(top_town['Total facilities'])} facilities; {low_town['Town']} has none"
        else:
            title2 = f"{top_town['Town']}: {int(top_town['Total facilities'])} facilities"
        fig2 = stacked_hbar(chosen, label_col, chosen[label_col].tolist(), title2,
                            height=max(420, 55 * len(chosen) + 140))
        st.plotly_chart(fig2, width="stretch")

st.caption("Hover over any bar to see exact numbers. Faded bars keep the national picture visible for comparison.")

# ---------------------------------------------------------------
# 4. Design justifications
# ---------------------------------------------------------------
st.subheader("Design choices")
with st.expander("Why a governorate dropdown (Step 1)?"):
    st.markdown(
        """
**User question:** "How does my region compare to the rest of Lebanon, and how big is the gap?"

**Why this widget:** A dropdown fits because the user picks exactly one region from a short,
fixed list of seven. I considered a multiselect, but comparing all regions is already done by
the full bar chart, so picking one keeps the focus clear. Radio buttons would also work but take
more space on the page.

**Course concept – focusing attention while keeping context:** When a region is chosen, the other
bars fade instead of disappearing. The selected region stands out through contrast (a preattentive
attribute), while the faded bars keep the national context so the user still sees where it ranks.
The chart title also changes to state the answer directly (e.g. "Akkar ranks #7 of 7").
"""
    )
with st.expander("Why a linked town multiselect (Step 2)?"):
    st.markdown(
        """
**User question:** "Within this region, which towns have services and which are left out?"

**Why this widget:** A multiselect lets the user compare several towns side by side, which a
single dropdown cannot do. I considered a "top N" slider, but it only shows the biggest towns
and hides the small villages that make the access gap visible. The list is sorted by number of
facilities, so the best-equipped towns appear first, and it is capped at 10 towns.

**How it is linked:** The town list only contains towns from the governorate picked in Step 1,
and it resets to the 5 best-equipped towns of that region. This turns the page into a drill-down:
overview of all regions first, then zoom into one region, then details for specific towns.

**Course concept – reducing clutter and details on demand:** Showing all 1,137 towns at once would
be unreadable. Filtering to one region, starting with 5 towns and capping at 10 keeps the chart
clean, and the user adds detail only when they ask for it ("overview first, zoom and filter, then
details on demand").
"""
    )
with st.expander("Why the charts look the way they do"):
    st.markdown(
        """
- **3 levels of care instead of 7 facility types:** seven stacked colors made the small segments
  unreadable. Grouping them into basic care, community centers and advanced care reduces clutter
  and matches the story of the page.
- **Color is used on purpose:** basic and community care use muted blues, and only advanced care
  (hospitals and labs) gets a strong red, because that is where the gap between regions matters most.
- **Horizontal bars, sorted largest first:** region and town names stay readable without tilting,
  and the ranking can be read top to bottom.
- **Totals written at the end of each bar and one shared legend:** less back-and-forth between the
  chart, the axis and the legend.
- **Titles state the takeaway** rather than just naming the chart, and they update with the selection.
"""
    )

# ---------------------------------------------------------------
# 5. Data notes
# ---------------------------------------------------------------
with st.expander("Data notes and limitations"):
    st.markdown(
        """
- Source: Health Resources Lebanon 2023, Impact Open Data (impact.cib.gov.lb), via linked.aub.edu.lb.
- Beirut is not included in the dataset.
- Some large towns (e.g. Jounieh, Bourj Hammoud) show 0 facilities, which most likely reflects missing data.
- Values are raw counts, not adjusted for population, so populated areas naturally have more facilities.
- The source records location sometimes by governorate and sometimes by district; districts were mapped to their governorate.
"""
    )
