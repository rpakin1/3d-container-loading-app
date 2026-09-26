import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ------------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="3D Container Loading & LDD Visualizer",
    page_icon="📦",
    layout="wide"
)

st.title("📦 3D Container Loading & LDD Analysis App")
st.markdown("ระบบจัดวางกล่อง 3 มิติ พร้อมวิเคราะห์ % การใช้ตู้ และระบบตรวจสอบน้ำหนักลงเพลารถ (LDD)")

# ------------------------------------------------------------------------------
# 2. READ DATA FROM GOOGLE SHEETS
# ------------------------------------------------------------------------------
CONTAINER_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRFS2SNdgb2nBPQnwkyJRTGf2_9syexHsC3asjnkjhJOStVapomghBi9Ew9g5sYfohVoKVdghKajuCH/pub?gid=0&single=true&output=csv"
BOX_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRFS2SNdgb2nBPQnwkyJRTGf2_9syexHsC3asjnkjhJOStVapomghBi9Ew9g5sYfohVoKVdghKajuCH/pub?gid=1420125949&single=true&output=csv"

@st.cache_data(ttl=60)
def load_sheet_data():
    try:
        df_c = pd.read_csv(CONTAINER_CSV_URL)
        df_b = pd.read_csv(BOX_CSV_URL)
        return df_c, df_b
    except Exception:
        # Mockup Data สำรองกรณีไม่ได้เชื่อม URL (พร้อมข้อมูลเพลา LDD)
        df_c = pd.DataFrame([
            {
                'Container_ID': 'CONT-20', 'Container_Name': '20ft Dry Box', 
                'Width_cm': 235, 'Length_cm': 590, 'Height_cm': 239, 
                'Max_Weight_kg': 28000, 'Front_Axle_Limit_kg': 10000, 'Rear_Axle_Limit_kg': 18000,
                'Kingpin_Distance_cm': 450 # ระยะห่างระหว่างเพลาหน้า-หลัง (cm)
            },
            {
                'Container_ID': 'CONT-40', 'Container_Name': '40ft High Cube', 
                'Width_cm': 235, 'Length_cm': 1203, 'Height_cm': 269, 
                'Max_Weight_kg': 28600, 'Front_Axle_Limit_kg': 12000, 'Rear_Axle_Limit_kg': 16600,
                'Kingpin_Distance_cm': 950
            }
        ])
        df_b = pd.DataFrame([
            {'Box_ID': 'BOX-A', 'Box_Name': 'กล่อง A (อะไหล่หนัก)', 'Customer_Name': 'สมชาย', 'Width_cm': 40, 'Length_cm': 50, 'Height_cm': 30, 'Weight_kg': 85.0, 'Color': '#FF5733'},
            {'Box_ID': 'BOX-B', 'Box_Name': 'กล่อง B (อุปกรณ์)', 'Customer_Name': 'สมหญิง', 'Width_cm': 60, 'Length_cm': 80, 'Height_cm': 40, 'Weight_kg': 35.0, 'Color': '#33FF57'},
            {'Box_ID': 'BOX-C', 'Box_Name': 'กล่อง C (เครื่องใช้ไฟฟ้า)', 'Customer_Name': 'วิชัย', 'Width_cm': 50, 'Length_cm': 50, 'Height_cm': 60, 'Weight_kg': 25.0, 'Color': '#3380FF'}
        ])
        return df_c, df_b

df_container, df_box = load_sheet_data()

# ------------------------------------------------------------------------------
# 3. SIDEBAR USER INTERFACE
# ------------------------------------------------------------------------------
st.sidebar.header("📋 เมนูเลือกตู้และสินค้า")

selected_container_name = st.sidebar.selectbox(
    "เลือกประเภทตู้คอนเทนเนอร์:",
    df_container['Container_Name'].unique()
)
container_info = df_container[df_container['Container_Name'] == selected_container_name].iloc[0]

st.sidebar.markdown("---")
st.sidebar.subheader("ระบุจำนวนกล่องแต่ละประเภท")

user_box_orders = []
for _, box in df_box.iterrows():
    label = f"{box['Box_Name']} [{box['Customer_Name']}]"
    qty = st.sidebar.number_input(label, min_value=0, value=15, step=1)
    if qty > 0:
        user_box_orders.append({'info': box, 'qty': qty})

# ------------------------------------------------------------------------------
# 4. LDD CALCULATION FUNCTION (LOAD DISTRIBUTION DIAGRAM)
# ------------------------------------------------------------------------------
def calculate_ldd(placed_boxes, container_info):
    """คำนวณจุดศูนย์ถ่วงสะสม (CG) และน้ำหนักลงเพลาหน้า-หลัง"""
    if not placed_boxes:
        return 0, 0, 0, 0, 0, 0, True, True

    total_weight = 0.0
    moment_y = 0.0 # โมเมนต์แนวยาว (ลึก)
    moment_x = 0.0 # โมเมนต์แนวกว้าง

    for b in placed_boxes:
        w = b['weight_kg']
        # จุดศูนย์ถ่วงของกล่องแต่ละใบ (Center point)
        center_x = (b['x1'] + b['x2']) / 2.0
        center_y = (b['y1'] + b['y2']) / 2.0
        
        total_weight += w
        moment_x += (center_x * w)
        moment_y += (center_y * w)

    # จุดศูนย์ถ่วงรวม (CG_X, CG_Y) หน่วยเป็น cm
    cg_x = moment_x / total_weight if total_weight > 0 else 0
    cg_y = moment_y / total_weight if total_weight > 0 else 0

    # คำนวณการกระจายน้ำหนักลงเพลา (Simple 2-Axle Model)
    # ใช้สัดส่วนระยะทาง CG_Y เทียบกับระยะห่างเพลา (Kingpin/Axle Distance)
    wheelbase = container_info.get('Kingpin_Distance_cm', container_info['Length_cm'] * 0.8)
    
    # คำนวณน้ำหนักลงเพลาหลัง และเพลาหน้า (kg)
    rear_axle_weight = total_weight * (cg_y / wheelbase)
    front_axle_weight = total_weight - rear_axle_weight

    # ตรวจสอบขีดจำกัดเพลา
    front_limit = container_info.get('Front_Axle_Limit_kg', 10000)
    rear_limit = container_info.get('Rear_Axle_Limit_kg', 18000)

    front_pass = front_axle_weight <= front_limit
    rear_pass = rear_axle_weight <= rear_limit

    return total_weight, cg_x, cg_y, front_axle_weight, rear_axle_weight, front_limit, rear_limit, front_pass and rear_pass

# ------------------------------------------------------------------------------
# 5. 3D PLOTLY ENGINE
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

    # 1. วาดโครงตู้
    fig.add_trace(go.Scatter3d(
        x=[0, cw, cw, 0, 0, 0, cw, cw, 0, 0, cw, cw, cw, cw, 0, 0],
        y=[0, 0, cl, cl, 0, 0, 0, cl, cl, 0, 0, 0, cl, cl, cl, cl],
        z=[0, 0, 0, 0, 0, ch, ch, ch, ch, ch, ch, 0, 0, ch, ch, 0],
        mode='lines',
        line=dict(color='black', width=4),
        name=f"ตู้ {container['Container_Name']}"
    ))

    # 2. วาดกล่องแต่ละใบ
    for b in placed_boxes:
        mesh = create_3d_cube_mesh(
            b['x1'], b['y1'], b['z1'], 
            b['x2'], b['y2'], b['z2'], 
            color=b['color'],
            name_tag=b['label']
        )
        fig.add_trace(mesh)

    # 3. วาดจุดศูนย์ถ่วง CG (Center of Gravity Point)
    if placed_boxes:
        fig.add_trace(go.Scatter3d(
            x=[cg_x], y=[cg_y], z=[ch / 2],
            mode='markers',
            marker=dict(size=10, color='red', symbol='diamond'),
            name='จุด CG สะสม'
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X: กว้าง (cm)', range=[0, cw]),
            yaxis=dict(title='Y: ยาว (cm)', range=[0, cl]),
            zaxis=dict(title='Z: สูง (cm)', range=[0, ch]),
            aspectmode='data'
        ),
        margin=dict(r=0, l=0, b=0, t=10),
        height=650
    )
    return fig

# ------------------------------------------------------------------------------
# 6. SIMULATION & DBL PACKING
# ------------------------------------------------------------------------------
container_vol = container_info['Width_cm'] * container_info['Length_cm'] * container_info['Height_cm']
max_weight_kg = container_info.get('Max_Weight_kg', 28000)

placed_boxes = []
curr_x, curr_y, curr_z = 0, 0, 0
max_y_in_row = 0
total_box_volume = 0
placed_count = 0

for item in user_box_orders:
    box = item['info']
    bw, bl, bh = box['Width_cm'], box['Length_cm'], box['Height_cm']
    weight = box.get('Weight_kg', 0)
    
    for _ in range(item['qty']):
        if curr_x + bw > container_info['Width_cm']:
            curr_x = 0
            curr_y += max_y_in_row
            max_y_in_row = 0
        
        if curr_y + bl > container_info['Length_cm']:
            curr_x = 0
            curr_y = 0
            curr_z += bh
        
        if curr_z + bh <= container_info['Height_cm']:
            placed_boxes.append({
                'x1': curr_x, 'y1': curr_y, 'z1': curr_z,
                'x2': curr_x + bw, 'y2': curr_y + bl, 'z2': curr_z + bh,
                'weight_kg': weight,
                'color': box.get('Color', '#FF5733'),
                'label': f"{box['Box_Name']} | ลูกค้า: {box['Customer_Name']} ({weight} kg)"
            })
            total_box_volume += (bw * bl * bh)
            placed_count += 1
            
            curr_x += bw
            if bl > max_y_in_row:
                max_y_in_row = bl

# คำนวณ LDD
tot_w, cg_x, cg_y, f_axle, r_axle, f_limit, r_limit, ldd_pass = calculate_ldd(placed_boxes, container_info)

# คำนวณ % Utilization
vol_utilization = (total_box_volume / container_vol) * 100
weight_utilization = (tot_w / max_weight_kg) * 100

# ------------------------------------------------------------------------------
# 7. DISPLAY DASHBOARD & LDD METRICS
# ------------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("📦 Volume Utilization", f"{vol_utilization:.2f} %")
m2.metric("⚖️ Total Weight", f"{tot_w:,.1f} / {max_weight_kg:,.0f} kg", f"{weight_utilization:.1f}%")
m3.metric("🎯 จุด CG (X, Y)", f"{cg_x:.0f}, {cg_y:.0f} cm")
m4.metric("🚛 สถานะ LDD เพลา", "✅ ปลอดภัย" if ldd_pass else "⚠️ น้ำหนักเกินเพลา")

# แสดงแถบแจ้งเตือน LDD แยกตามเพลา
st.markdown("### 🚛 วิเคราะห์น้ำหนักลงเพลารถ (Load Distribution Diagram)")
ldd_col1, ldd_col2 = st.columns(2)

with ldd_col1:
    f_ratio = (f_axle / f_limit) * 100 if f_limit > 0 else 0
    if f_axle <= f_limit:
        st.success(f"**เพลาหน้า (Front Axle):** {f_axle:,.1f} kg / พิกัด {f_limit:,.0f} kg ({f_ratio:.1f}%) — ผ่านมาตรฐาน")
    else:
        st.error(f"**เพลาหน้า (Front Axle):** {f_axle:,.1f} kg / พิกัด {f_limit:,.0f} kg ({f_ratio:.1f}%) — ⚠️ เกินพิกัด!")

with ldd_col2:
    r_ratio = (r_axle / r_limit) * 100 if r_limit > 0 else 0
    if r_axle <= r_limit:
        st.success(f"**เพลาหลัง (Rear Axle):** {r_axle:,.1f} kg / พิกัด {r_limit:,.0f} kg ({r_ratio:.1f}%) — ผ่านมาตรฐาน")
    else:
        st.error(f"**เพลาหลัง (Rear Axle):** {r_axle:,.1f} kg / พิกัด {r_limit:,.0f} kg ({r_ratio:.1f}%) — ⚠️ เกินพิกัด!")

st.markdown("---")

col_graph, col_legend = st.columns([4, 1])

with col_graph:
    fig = plot_interactive_container(container_info, placed_boxes, cg_x, cg_y)
    st.plotly_chart(fig, use_container_width=True)

with col_legend:
    st.subheader("🎨 สัญลักษณ์สีกล่อง")
    for item in user_box_orders:
        box = item['info']
        color = box.get('Color', '#FF5733')
        st.markdown(
            f'<div style="display: flex; align-items: center; margin-bottom: 8px;">'
            f'<div style="width: 20px; height: 20px; background-color: {color}; border-radius: 4px; margin-right: 10px;"></div>'
            f'<span><b>{box["Box_Name"]}</b><br><small>น้ำหนัก: {box.get("Weight_kg",0)} kg/ใบ</small></span>'
            f'</div>', 
            unsafe_allow_html=True
        )
