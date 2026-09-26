import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ------------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="3D Container Loading Visualizer",
    page_icon="📦",
    layout="wide"
)

st.title("📦 3D Container Loading & Utilization App")
st.markdown("ระบบคำนวณและแสดงผลการจัดวางกล่อง 3 มิติ พร้อมวิเคราะห์ % การใช้พื้นที่และน้ำหนักตู้")

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
        # Mockup Data สำรองกรณีไม่ได้เชื่อม URL
        df_c = pd.DataFrame([
            {'Container_ID': 'CONT-20', 'Container_Name': '20ft Dry Box', 'Width_cm': 235, 'Length_cm': 590, 'Height_cm': 239, 'Max_Weight_kg': 28000},
            {'Container_ID': 'CONT-40', 'Container_Name': '40ft High Cube', 'Width_cm': 235, 'Length_cm': 1203, 'Height_cm': 269, 'Max_Weight_kg': 28600}
        ])
        df_b = pd.DataFrame([
            {'Box_ID': 'BOX-A', 'Box_Name': 'กล่อง A (อะไหล่)', 'Customer_Name': 'สมชาย', 'Width_cm': 40, 'Length_cm': 50, 'Height_cm': 30, 'Weight_kg': 15.0, 'Color': '#FF5733'},
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
    qty = st.sidebar.number_input(label, min_value=0, value=10, step=1)
    if qty > 0:
        user_box_orders.append({'info': box, 'qty': qty})

# ------------------------------------------------------------------------------
# 4. 3D PLOTLY ENGINE
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

def plot_interactive_container(container, placed_boxes):
    fig = go.Figure()
    cw, cl, ch = container['Width_cm'], container['Length_cm'], container['Height_cm']

    # วาดโครงตู้
    fig.add_trace(go.Scatter3d(
        x=[0, cw, cw, 0, 0, 0, cw, cw, 0, 0, cw, cw, cw, cw, 0, 0],
        y=[0, 0, cl, cl, 0, 0, 0, cl, cl, 0, 0, 0, cl, cl, cl, cl],
        z=[0, 0, 0, 0, 0, ch, ch, ch, ch, ch, ch, 0, 0, ch, ch, 0],
        mode='lines',
        line=dict(color='black', width=4),
        name=f"ตู้ {container['Container_Name']}"
    ))

    # วาดกล่องแต่ละใบ
    for b in placed_boxes:
        mesh = create_3d_cube_mesh(
            b['x1'], b['y1'], b['z1'], 
            b['x2'], b['y2'], b['z2'], 
            color=b['color'],
            name_tag=b['label']
        )
        fig.add_trace(mesh)

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
# 5. SIMULATION & METRICS CALCULATION
# ------------------------------------------------------------------------------
# ปริมาตรตู้รวม (cm³) และน้ำหนักตู้สูงสุด (kg)
container_vol = container_info['Width_cm'] * container_info['Length_cm'] * container_info['Height_cm']
max_weight_kg = container_info.get('Max_Weight_kg', 28000)

placed_boxes = []
curr_x, curr_y, curr_z = 0, 0, 0
max_y_in_row = 0

total_box_volume = 0
total_box_weight = 0
placed_count = 0

# อัลกอริทึมจัดวางเบื้องต้น (DBL)
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
                'color': box.get('Color', '#FF5733'),
                'label': f"{box['Box_Name']} | ลูกค้า: {box['Customer_Name']}"
            })
            total_box_volume += (bw * bl * bh)
            total_box_weight += weight
            placed_count += 1
            
            curr_x += bw
            if bl > max_y_in_row:
                max_y_in_row = bl

# คำนวณเปอร์เซ็นต์
vol_utilization = (total_box_volume / container_vol) * 100
weight_utilization = (total_box_weight / max_weight_kg) * 100

# ------------------------------------------------------------------------------
# 6. DISPLAY DASHBOARD METRICS & 3D GRAPH
# ------------------------------------------------------------------------------
# แสดงแถบ Dashboard ตัวเลขการใช้ตู้
m1, m2, m3, m4 = st.columns(4)
m1.metric("📦 ปริมาตรตู้ที่ใช้ (Volume)", f"{vol_utilization:.2f} %", help="คำนวณจากปริมาตรรวมของกล่อง / ปริมาตรตู้")
m2.metric("⚖️ น้ำหนักตู้ที่ใช้ (Weight)", f"{weight_utilization:.2f} %", f"{total_box_weight:,.1f} / {max_weight_kg:,.0f} kg")
m3.metric("📥 จำนวนกล่องที่บรรจุได้", f"{placed_count} ใบ")
m4.metric("🚛 ประเภทตู้คอนเทนเนอร์", container_info['Container_Name'])

st.markdown("---")

col_graph, col_legend = st.columns([4, 1])

with col_graph:
    fig = plot_interactive_container(container_info, placed_boxes)
    st.plotly_chart(fig, use_container_width=True)

with col_legend:
    st.subheader("🎨 สัญลักษณ์สีกล่อง")
    for item in user_box_orders:
        box = item['info']
        color = box.get('Color', '#FF5733')
        st.markdown(
            f'<div style="display: flex; align-items: center; margin-bottom: 8px;">'
            f'<div style="width: 20px; height: 20px; background-color: {color}; border-radius: 4px; margin-right: 10px;"></div>'
            f'<span><b>{box["Box_Name"]}</b><br><small>ลูกค้า: {box["Customer_Name"]}</small></span>'
            f'</div>', 
            unsafe_allow_html=True
        )
