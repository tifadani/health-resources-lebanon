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

COLORS = {
    "Pharmacies": "#2E86AB", "Clinics": "#A23B72", "First aid centers": "#F18F01",
    "Care centers": "#C73E1D", "Labs & radiology": "#3B1F2B",
    "Medical centers": "#6A994E", "Hospitals": "#E63946",
}

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
    return df[["Town", "Governorate", "Label"] + FACILITY_COLS + ["Total facilities"]]


df = load_data()
gov_totals = df.groupby("Governorate")[FACILITY_COLS].sum()
gov_totals["Total"] = gov_totals.sum(axis=1)
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
default_towns = town_options[:5]

with w2:
    towns = st.multiselect(
        f"Step 2 – Compare towns in {governorate} (sorted by number of facilities)",
        town_options,
        default=default_towns,
        key=f"towns_{governorate}",  # resets the selection when the governorate changes
        help="Starts with the 5 best-equipped towns. Add a small town to see the contrast.",
    )

# KPIs for the selected scope
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Facilities in {governorate}", f"{int(scope['Total facilities'].sum()):,}")
k2.metric("Share of national total", f"{scope['Total facilities'].sum() / national_total:.0%}")
k3.metric("Hospitals", f"{int(scope['Hospitals'].sum()):,}")
k4.metric("Towns with no facility", f"{(scope['Total facilities'] == 0).mean():.0%}")

left, right = st.columns(2)

# Chart 1: governorates, with the selected one highlighted
with left:
    long = gov_totals[FACILITY_COLS].reset_index().melt(
        id_vars="Governorate", var_name="Facility type", value_name="Count")
    fig1 = px.bar(
        long, x="Governorate", y="Count", color="Facility type",
        category_orders={"Governorate": gov_totals.index.tolist(), "Facility type": FACILITY_COLS},
        color_discrete_map=COLORS,
        title="Health facilities by governorate and type",
    )
    if governorate != "All of Lebanon":
        for trace in fig1.data:
            trace.marker.opacity = [1.0 if g == governorate else 0.25 for g in trace.x]
    fig1.update_layout(legend_title_text="", xaxis_title="", yaxis_title="Number of facilities")
    st.plotly_chart(fig1, width="stretch")

# Chart 2: selected towns, broken down by facility type
with right:
    if not towns:
        st.warning("Pick at least one town in Step 2 to see the comparison.")
    else:
        chosen = scope[scope[label_col].isin(towns)].sort_values("Total facilities")
        town_long = chosen.melt(id_vars=[label_col], value_vars=FACILITY_COLS,
                                var_name="Facility type", value_name="Count")
        fig2 = px.bar(
            town_long, x="Count", y=label_col, color="Facility type", orientation="h",
            category_orders={label_col: chosen[label_col].tolist(), "Facility type": FACILITY_COLS},
            color_discrete_map=COLORS,
            title=f"What the selected towns have ({governorate})",
        )
        fig2.update_layout(legend_title_text="", yaxis_title="", xaxis_title="Number of facilities")
        st.plotly_chart(fig2, width="stretch")

# ---------------------------------------------------------------
# 4. Design justifications
# ---------------------------------------------------------------
st.subheader("Design choices")
with st.expander("Why a governorate dropdown (Step 1)?"):
    st.markdown(
        """
**User question:** "How does my region compare to the rest of Lebanon, and how big is the gap?"

**Why this widget:** A dropdown fits because the user picks exactly one region from a short,
fixed list of seven. I considered a multiselect, but comparing several regions at once is
already done by the full bar chart, so picking one region keeps the focus clear. Radio buttons
would also work but take up more space on the page.

**Course concept – focusing attention:** When a region is chosen, the other bars fade instead
of disappearing. The selected region stands out through a preattentive attribute (contrast),
while the faded bars keep the national context so the user still sees where the region ranks.
"""
    )
with st.expander("Why a linked town multiselect (Step 2)?"):
    st.markdown(
        """
**User question:** "Within this region, which towns have services and which are left out?"

**Why this widget:** A multiselect lets the user compare a few towns side by side, which a
single dropdown cannot do. I considered a "top N" slider, but it only shows the biggest towns
and hides the small villages that make the access gap visible. The list is sorted by number of
facilities so the best-equipped towns appear first.

**How it is linked:** The town list only contains towns from the governorate picked in Step 1,
and it resets with the 5 best-equipped towns of that region. This turns the page into a
drill-down: overview of all regions first, then zoom into one region, then details for specific
towns.

**Course concept – reducing clutter and details on demand:** Showing all 1,137 towns at once
would be unreadable. Filtering the list to one region and starting with 5 towns keeps the chart
clean, and the user adds detail only when they ask for it ("overview first, zoom and filter,
then details on demand").
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
