import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math

# ------------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="3D Container Loading System",
    page_icon="📦",
    layout="wide"
)

# ------------------------------------------------------------------------------
# 2. DYNAMIC COLOR GENERATOR
# ------------------------------------------------------------------------------
COLOR_PALETTE = [
    '#FF5733', '#33FF57', '#3380FF', '#FF33A8', '#33FFF3', 
    '#F3FF33', '#FF8333', '#9B59B6', '#1ABC9C', '#E67E22',
    '#8E44AD', '#2ECC71', '#D35400', '#C0392B', '#16A085'
]

def assign_box_colors(df_box):
    box_colors = {}
    if not df_box.empty and 'Box_ID' in df_box.columns:
        for idx, row in df_box.iterrows():
            box_id = row['Box_ID']
            color = COLOR_PALETTE[idx % len(COLOR_PALETTE)]
            box_colors[box_id] = color
    return box_colors

# ------------------------------------------------------------------------------
# 3. CORE DBL ALGORITHM (EXACT VB MODULE 3 LOGIC)
# ------------------------------------------------------------------------------
class EmptySpace:
    def __init__(self, x1, y1, z1, x2, y2, z2, lbs_z_limit=float('inf')):
        self.x1, self.y1, self.z1 = x1, y1, z1
        self.x2, self.y2, self.z2 = x2, y2, z2
        self.width = x2 - x1
        self.length = y2 - y1
        self.height = z2 - z1
        self.lbs_z = lbs_z_limit  # Maximum weight capacity supported on this space

def run_dbl_algorithm(container_info, user_box_orders, box_colors_map):
    cw = container_info['Width_cm']
    cl = container_info['Length_cm']
    ch = container_info['Height_cm']
    max_c_weight = container_info.get('Max_Weight_kg', 28000)

    # Initial space supports up to the max payload of the container
    space_list = [EmptySpace(0, 0, 0, cw, cl, ch, lbs_z_limit=max_c_weight)]
    placed_boxes = []

    boxes_in_stock = {item['info']['Box_ID']: item['qty'] for item in user_box_orders}
    box_info_dict = {item['info']['Box_ID']: item['info'] for item in user_box_orders}

    while space_list and any(qty > 0 for qty in boxes_in_stock.values()):
        # VB Logic: Seleccionar_Espacio (Min X1 -> Min Z1 -> Min Y1)
        space_list.sort(key=lambda s: (s.x1, s.z1, s.y1))
        space = space_list.pop(0)

        best_fit = float('inf')
        best_placement = None

        for box_id, qty_left in boxes_in_stock.items():
            if qty_left <= 0:
                continue
            
            box = box_info_dict[box_id]
            unit_weight = float(box.get('Weight_kg', 0))
            
            # Fetch LBS_z from Google Sheets dataframe
            raw_lbs = box.get('LBS_z', box.get('lbs_z', float('inf')))
            try:
                lbs_z_total = float(raw_lbs) if pd.notna(raw_lbs) and str(raw_lbs).strip() != '' else float('inf')
            except ValueError:
                lbs_z_total = float('inf')

            rotations = [
                (box['Width_cm'], box['Length_cm'], box['Height_cm'], 1),
                (box['Length_cm'], box['Width_cm'], box['Height_cm'], 2) if box.get('Allow_Z', 1) else None,
                (box['Width_cm'], box['Height_cm'], box['Length_cm'], 3) if box.get('Allow_X', 0) else None,
                (box['Height_cm'], box['Length_cm'], box['Width_cm'], 4) if box.get('Allow_Y', 0) else None,
                (box['Length_cm'], box['Height_cm'], box['Width_cm'], 5) if (box.get('Allow_Z', 1) and box.get('Allow_X', 0)) else None,
                (box['Height_cm'], box['Width_cm'], box['Length_cm'], 6) if (box.get('Allow_Z', 1) and box.get('Allow_Y', 0)) else None,
            ]

            for rot in filter(None, rotations):
                bw, bl, bh, rot_id = rot

                max_x_fit = int(space.width // bw)
                max_y_fit = int(space.length // bl)
                max_z_fit = int(space.height // bh)

                if max_x_fit == 0 or max_y_fit == 0 or max_z_fit == 0:
                    continue

                # --------------------------------------------------------------
                # WEIGHT VALIDATION (VB MODULE 3)
                # --------------------------------------------------------------
                # If box weight exceeds space weight capacity, skip this placement
                if unit_weight > 0 and unit_weight > space.lbs_z:
                    continue

                eje_x = min(max_x_fit, qty_left)
                if eje_x == 0: continue
                
                eje_y = min(max_y_fit, int(qty_left // eje_x))
                if eje_y == 0: continue

                # Calculate EjeZ using WorksheetFunction.Min from VB
                limit_by_height = max_z_fit
                limit_by_qty = int(qty_left // (eje_x * eje_y))
                
                if lbs_z_total > 0 and lbs_z_total < float('inf') and unit_weight > 0:
                    max_allowed_stack = math.floor(lbs_z_total / unit_weight)
                    limit_by_lbs = max(1, max_allowed_stack)
                else:
                    limit_by_lbs = float('inf')

                eje_z = min(limit_by_height, limit_by_qty, limit_by_lbs)
                if eje_z == 0: continue

                # Fit Total = Remaining waste space
                fit_x = space.width - (bw * eje_x)
                fit_y = space.length - (bl * eje_y)
                fit_z = space.height - (bh * eje_z)
                fit_total = fit_x + fit_y + fit_z

                if fit_total < best_fit:
                    best_fit = fit_total
                    best_placement = {
                        'box_id': box_id,
                        'box_info': box,
                        'bw': bw, 'bl': bl, 'bh': bh,
                        'eje_x': eje_x, 'eje_y': eje_y, 'eje_z': eje_z,
                        'total_items': eje_x * eje_y * eje_z,
                        'lbs_z_total': lbs_z_total,
                        'unit_weight': unit_weight
                    }

        if best_placement:
            bp = best_placement
            b_info = bp['box_info']
            block_w = bp['bw'] * bp['eje_x']
            block_l = bp['bl'] * bp['eje_y']
            block_h = bp['bh'] * bp['eje_z']

            box_color = box_colors_map.get(bp['box_id'], '#3380FF')

            for z_i in range(bp['eje_z']):
                for y_i in range(bp['eje_y']):
                    for x_i in range(bp['eje_x']):
                        x1 = space.x1 + (x_i * bp['bw'])
                        y1 = space.y1 + (y_i * bp['bl'])
                        z1 = space.z1 + (z_i * bp['bh'])
                        
                        placed_boxes.append({
                            'Box_ID': bp['box_id'],
                            'Box_Name': b_info['Box_Name'],
                            'Customer_Name': b_info['Customer_Name'],
                            'x1': x1, 'y1': y1, 'z1': z1,
                            'x2': x1 + bp['bw'], 'y2': y1 + bp['bl'], 'z2': z1 + bp['bh'],
                            'Width_cm': bp['bw'], 'Length_cm': bp['bl'], 'Height_cm': bp['bh'],
                            'weight_kg': b_info.get('Weight_kg', 0),
                            'color': box_color,
                            'label': f"{b_info['Box_Name']} | {b_info['Customer_Name']}"
                        })

            boxes_in_stock[bp['box_id']] -= bp['total_items']

            # ------------------------------------------------------------------
            # SPACE SPLITTING LOGIC (actualizar_espacios - VB Module 3)
            # ------------------------------------------------------------------
            # Space B: Right
            if space.x1 + block_w < space.x2:
                space_list.append(EmptySpace(space.x1 + block_w, space.y1, space.z1, space.x2, space.y2, space.z2, space.lbs_z))
            
            # Space D: Back
            if space.y1 + block_l < space.y2:
                space_list.append(EmptySpace(space.x1, space.y1 + block_l, space.z1, space.x1 + block_w, space.y2, space.z2, space.lbs_z))
            
            # Space C: Upper
            # VB Logic: c.LBSz = Min(espacio_disponible.LBSz - item.Peso, item.LBSz)
            if space.z1 + block_h < space.z2:
                upper_space_lbs = min(space.lbs_z - (bp['unit_weight'] * bp['eje_z']), bp['lbs_z_total'])
                if upper_space_lbs > 0:
                    space_list.append(EmptySpace(space.x1, space.y1, space.z1 + block_h, space.x1 + block_w, space.y1 + block_l, space.z2, upper_space_lbs))

    unfitted_boxes = []
    for item in user_box_orders:
        b_id = item['info']['Box_ID']
        leftover = boxes_in_stock[b_id]
        if leftover > 0:
            unfitted_boxes.append({
                'Box_ID': b_id,
                'Box_Name': item['info']['Box_Name'],
                'Customer_Name': item['info']['Customer_Name'],
                'Requested_Qty': item['qty'],
                'Unfitted_Qty': leftover,
                'Unit_Weight_kg': item['info'].get('Weight_kg', 0)
            })

    return placed_boxes, unfitted_boxes

# ------------------------------------------------------------------------------
# 4. LDD CALCULATION FUNCTION
# ------------------------------------------------------------------------------
def calculate_ldd(placed_boxes, container_info):
    if not placed_boxes:
        return 0, 0, 0, 0, 0, 0, 0, True

    total_weight = 0.0
    moment_x = 0.0
    moment_y = 0.0

    for b in placed_boxes:
        w = b['weight_kg']
        cx = (b['x1'] + b['x2']) / 2.0
        cy = (b['y1'] + b['y2']) / 2.0
        total_weight += w
        moment_x += (cx * w)
        moment_y += (cy * w)

    cg_x = moment_x / total_weight if total_weight > 0 else 0
    cg_y = moment_y / total_weight if total_weight > 0 else 0

    wheelbase = container_info.get('Kingpin_Distance_cm', container_info['Length_cm'] * 0.8)
    rear_axle_weight = total_weight * (cg_y / wheelbase) if wheelbase > 0 else 0
    front_axle_weight = total_weight - rear_axle_weight

    f_limit = container_info.get('Front_Axle_Limit_kg', 10000)
    r_limit = container_info.get('Rear_Axle_Limit_kg', 18000)

    pass_ldd = (front_axle_weight <= f_limit) and (rear_axle_weight <= r_limit)
    return total_weight, cg_x, cg_y, front_axle_weight, rear_axle_weight, f_limit, r_limit, pass_ldd

# ------------------------------------------------------------------------------
# 5. PLOTLY 3D RENDER ENGINE
# ------------------------------------------------------------------------------
def create_3d_cube_mesh(x1, y1, z1, x2, y2, z2, color, name_tag):
    x = [x1, x2, x2, x1, x1, x2, x2, x1]
    y = [y1, y1, y2, y2, y1, y1, y2, y2]
    z = [z1, z1, z1, z1, z2, z2, z2, z2]
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 5, 3, 6, 7, 1, 1, 5, 5, 7, 6]
    
    return go.Mesh3d(
        x=x, y=y, z=z, i=i, j=j, k=k,
        color=color, opacity=0.85, name=name_tag,
        showscale=False, hoverinfo="name"
    )

def plot_interactive_container(container, placed_boxes, cg_x, cg_y):
    fig = go.Figure()
    cw, cl, ch = container['Width_cm'], container['Length_cm'], container['Height_cm']

    fig.add_trace(go.Scatter3d(
        x=[0, cw, cw, 0, 0, 0, cw, cw, 0, 0, cw, cw, cw, cw, 0, 0],
        y=[0, 0, cl, cl, 0, 0, 0, cl, cl, 0, 0, 0, cl, cl, cl, cl],
        z=[0, 0, 0, 0, 0, ch, ch, ch, ch, ch, ch, 0, 0, ch, ch, 0],
        mode='lines', line=dict(color='black', width=4),
        name=f"Container {container['Container_Name']}"
    ))

    for b in placed_boxes:
        mesh = create_3d_cube_mesh(
            b['x1'], b['y1'], b['z1'], b['x2'], b['y2'], b['z2'],
            color=b['color'], name_tag=b['label']
        )
        fig.add_trace(mesh)

    if placed_boxes:
        fig.add_trace(go.Scatter3d(
            x=[cg_x], y=[cg_y], z=[ch / 2],
            mode='markers', marker=dict(size=10, color='red', symbol='diamond'),
            name='Accumulated CG Point'
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X: Width (cm)', range=[0, cw]),
            yaxis=dict(title='Y: Length (cm)', range=[0, cl]),
            zaxis=dict(title='Z: Height (cm)', range=[0, ch]),
            aspectmode='data'
        ),
        margin=dict(r=0, l=0, b=0, t=10), height=650
    )
    return fig

# ------------------------------------------------------------------------------
# 6. READ MASTER DATA FROM GOOGLE SHEETS
# ------------------------------------------------------------------------------
CONTAINER_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRFS2SNdgb2nBPQnwkyJRTGf2_9syexHsC3asjnkjhJOStVapomghBi9Ew9g5sYfohVoKVdghKajuCH/pub?gid=0&single=true&output=csv"
BOX_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRFS2SNdgb2nBPQnwkyJRTGf2_9syexHsC3asjnkjhJOStVapomghBi9Ew9g5sYfohVoKVdghKajuCH/pub?gid=1420125949&single=true&output=csv"

@st.cache_data(ttl=5)
def load_master_data():
    try:
        df_c = pd.read_csv(CONTAINER_CSV_URL)
        df_b = pd.read_csv(BOX_CSV_URL)
        return df_c, df_b
    except Exception:
        df_c = pd.DataFrame([
            {
                'Container_ID': 'CONT-20', 'Container_Name': '20ft Dry Box',
                'Width_cm': 235, 'Length_cm': 590, 'Height_cm': 239,
                'Max_Weight_kg': 28000, 'Front_Axle_Limit_kg': 10000, 'Rear_Axle_Limit_kg': 18000,
                'Kingpin_Distance_cm': 450
            },
            {
                'Container_ID': 'CONT-40', 'Container_Name': '40ft High Cube',
                'Width_cm': 235, 'Length_cm': 1203, 'Height_cm': 269,
                'Max_Weight_kg': 28600, 'Front_Axle_Limit_kg': 12000, 'Rear_Axle_Limit_kg': 16600,
                'Kingpin_Distance_cm': 950
            }
        ])
        df_b = pd.DataFrame([
            {'Box_ID': 'BOX-A', 'Box_Name': 'Box A (Parts)', 'Customer_Name': 'Somchai', 'Width_cm': 40, 'Length_cm': 50, 'Height_cm': 30, 'Weight_kg': 85.0, 'Allow_X': 0, 'Allow_Y': 0, 'Allow_Z': 1, 'LBS_z': 300},
            {'Box_ID': 'BOX-B', 'Box_Name': 'Box B (Equipment)', 'Customer_Name': 'Somying', 'Width_cm': 60, 'Length_cm': 80, 'Height_cm': 40, 'Weight_kg': 35.0, 'Allow_X': 1, 'Allow_Y': 1, 'Allow_Z': 1, 'LBS_z': 500},
            {'Box_ID': 'BOX-C', 'Box_Name': 'Pallet C (spare)', 'Customer_Name': 'BYD', 'Width_cm': 90, 'Length_cm': 115, 'Height_cm': 120, 'Weight_kg': 510.0, 'Allow_X': 0, 'Allow_Y': 0, 'Allow_Z': 1, 'LBS_z': 1500},
            {'Box_ID': 'BOX-D', 'Box_Name': 'Pallet C (spare)', 'Customer_Name': 'Toyota', 'Width_cm': 90, 'Length_cm': 115, 'Height_cm': 100, 'Weight_kg': 510.0, 'Allow_X': 0, 'Allow_Y': 0, 'Allow_Z': 1, 'LBS_z': 300}
        ])
        return df_c, df_b

df_container, df_box = load_master_data()
box_colors_map = assign_box_colors(df_box)

# ------------------------------------------------------------------------------
# 7. APP MAIN INTERFACE (3 TABS)
# ------------------------------------------------------------------------------
tab_user, tab_reports, tab_admin = st.tabs([
    "🚛 User View (3D Loading & LDD)", 
    "📊 Reports & Export CSV", 
    "⚙️ Admin (Master Data)"
])

# --- SIDEBAR INPUTS ---
st.sidebar.header("📋 Container & Cargo Selection")

if st.sidebar.button("🔄 Refresh Data from Google Sheet", use_container_width=True, type="primary"):
    load_master_data.clear()
    st.cache_data.clear()
    st.rerun()

selected_container_name = st.sidebar.selectbox("Select Container Type:", df_container['Container_Name'].unique())
container_info = df_container[df_container['Container_Name'] == selected_container_name].iloc[0]

st.sidebar.markdown("---")
st.sidebar.subheader("Specify Box Quantities")

user_box_orders = []
for _, box in df_box.iterrows():
    label = f"{box['Box_Name']} [{box['Customer_Name']}]"
    qty = st.sidebar.number_input(label, min_value=0, value=20, step=1)
    if qty > 0:
        user_box_orders.append({'info': box, 'qty': qty})

# Process DBL Algorithm & LDD
placed_boxes, unfitted_boxes = run_dbl_algorithm(container_info, user_box_orders, box_colors_map)
tot_w, cg_x, cg_y, f_axle, r_axle, f_limit, r_limit, ldd_pass = calculate_ldd(placed_boxes, container_info)

# --- TAB 1: 3D LOADING & LDD ---
with tab_user:
    st.title("📦 3D Container Loading & LDD Analysis")

    container_vol = container_info['Width_cm'] * container_info['Length_cm'] * container_info['Height_cm']
    used_vol = sum((b['x2']-b['x1'])*(b['y2']-b['y1'])*(b['z2']-b['z1']) for b in placed_boxes)
    vol_utilization = (used_vol / container_vol) * 100 if container_vol > 0 else 0
    weight_utilization = (tot_w / container_info['Max_Weight_kg']) * 100 if container_info['Max_Weight_kg'] > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 Volume Util.", f"{vol_utilization:.2f} %")
    m2.metric("⚖️ Total Weight", f"{tot_w:,.1f} kg", f"Limit {container_info['Max_Weight_kg']:,.0f} kg ({weight_utilization:.1f}%)")
    m3.metric("🎯 CG Point (X, Y)", f"{cg_x:.0f}, {cg_y:.0f} cm")
    m4.metric("🚛 LDD Status", "✅ Safe" if ldd_pass else "⚠️ Overload")

    st.markdown("### 🚛 Load Distribution Diagram (Axle Weights)")
    ldd_col1, ldd_col2 = st.columns(2)
    with ldd_col1:
        if f_axle <= f_limit:
            st.success(f"**Front Axle:** {f_axle:,.1f} kg / Limit {f_limit:,.0f} kg — Passed")
        else:
            st.error(f"**Front Axle:** {f_axle:,.1f} kg / Limit {f_limit:,.0f} kg — ⚠️ Overloaded!")
    with ldd_col2:
        if r_axle <= r_limit:
            st.success(f"**Rear Axle:** {r_axle:,.1f} kg / Limit {r_limit:,.0f} kg — Passed")
        else:
            st.error(f"**Rear Axle:** {r_axle:,.1f} kg / Limit {r_limit:,.0f} kg — ⚠️ Overloaded!")

    st.markdown("---")

    col_graph, col_legend = st.columns([4, 1])
    with col_graph:
        fig = plot_interactive_container(container_info, placed_boxes, cg_x, cg_y)
        st.plotly_chart(fig, use_container_width=True)

    with col_legend:
        st.subheader("🎨 Color Legend")
        for item in user_box_orders:
            box = item['info']
            color = box_colors_map.get(box['Box_ID'], '#FF5733')
            st.markdown(
                f'<div style="display: flex; align-items: center; margin-bottom: 8px;">'
                f'<div style="width: 20px; height: 20px; background-color: {color}; border-radius: 4px; margin-right: 10px;"></div>'
                f'<span><b>{box["Box_Name"]}</b><br><small>{box["Customer_Name"]}</small></span>'
                f'</div>', unsafe_allow_html=True
            )

# --- TAB 2: REPORTS & EXPORT CSV ---
with tab_reports:
    st.title("📊 Loading Summary & CSV Export")

    st.subheader("⚠️ 1. Unfitted Boxes Report")
    if unfitted_boxes:
        df_unfitted = pd.DataFrame(unfitted_boxes)
        st.warning(f"Found {sum(b['Unfitted_Qty'] for b in unfitted_boxes)} box(es) that could not fit into the container.")
        st.dataframe(df_unfitted, use_container_width=True)
        
        csv_unfitted = df_unfitted.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download Unfitted Boxes Report (CSV)",
            data=csv_unfitted,
            file_name="unfitted_boxes_report.csv",
            mime="text/csv"
        )
    else:
        st.success("🎉 All requested boxes have been placed successfully!")

    st.markdown("---")

    st.subheader("📍 2. Placed Boxes 3D Coordinates")
    if placed_boxes:
        df_placed = pd.DataFrame(placed_boxes)
        display_cols = ['Box_ID', 'Box_Name', 'Customer_Name', 'x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'Width_cm', 'Length_cm', 'Height_cm', 'weight_kg']
        df_placed_display = df_placed[display_cols]
        
        st.write(f"Total placed boxes: **{len(placed_boxes)}** units.")
        st.dataframe(df_placed_display, use_container_width=True)

        csv_placed = df_placed_display.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download 3D Placement Coordinates (CSV)",
            data=csv_placed,
            file_name="placed_boxes_positions.csv",
            mime="text/csv"
        )

# --- TAB 3: ADMIN MANAGEMENT ---
with tab_admin:
    st.title("⚙️ Master Data (Google Sheets Real-Time)")
    st.caption("This tab displays live data read directly from Google Sheets in real-time.")

    st.subheader("1. Container Master Table")
    st.dataframe(df_container, use_container_width=True)
    
    st.subheader("2. Box Master Table")
    st.dataframe(df_box, use_container_width=True)

    st.info("💡 If you update data in Google Sheets, click **'🔄 Refresh Data from Google Sheet'** in the left sidebar.")
