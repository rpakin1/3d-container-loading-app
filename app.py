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

st.title("📦 3D Container Loading Interactive App")
st.markdown("ระบบวางแผนจัดวางกล่องสินค้าในตู้คอนเทนเนอร์ 3 มิติ (แสดงสีแยกตามชนิดกล่องและลูกค้า)")

# ------------------------------------------------------------------------------
# 2. READ DATA FROM GOOGLE SHEETS (PUBLISHED CSV URLS)
# ------------------------------------------------------------------------------
# ⚠️ เปลี่ยน URL ด้านล่างนี้เป็น URL Publish to Web CSV จาก Google Sheets ของคุณ
CONTAINER_CSV_URL = "https://docs.google.com/spreadsheets/d/e/YOUR_CONTAINER_PUBLISHED_ID/pub?gid=0&single=true&output=csv"
BOX_CSV_URL = "https://docs.google.com/spreadsheets/d/e/YOUR_BOX_PUBLISHED_ID/pub?gid=12345&single=true&output=csv"

@st.cache_data(ttl=60) # ดึงข้อมูลใหม่ทุกๆ 60 วินาที
def load_sheet_data():
    try:
        df_c = pd.read_csv(CONTAINER_CSV_URL)
        df_b = pd.read_csv(BOX_CSV_URL)
        return df_c, df_b
    except Exception:
        # ข้อมูล Mockup สำรองกรณีที่ยังไม่ได้ใส่ URL หรือเชื่อมต่อ URL ไม่ได้
        df_c = pd.DataFrame([
            {'Container_ID': 'CONT-20', 'Container_Name': '20ft Dry Box', 'Width_cm': 235, 'Length_cm': 590, 'Height_cm': 239},
            {'Container_ID': 'CONT-40', 'Container_Name': '40ft High Cube', 'Width_cm': 235, 'Length_cm': 1203, 'Height_cm': 269}
        ])
        df_b = pd.DataFrame([
            {'Box_ID': 'BOX-A', 'Box_Name': 'กล่อง A (อะไหล่)', 'Customer_Name': 'ลูกค้า สมชาย', 'Width_cm': 40, 'Length_cm': 50, 'Height_cm': 30, 'Color': '#FF5733'},
            {'Box_ID': 'BOX-B', 'Box_Name': 'กล่อง B (อุปกรณ์)', 'Customer_Name': 'ลูกค้า สมหญิง', 'Width_cm': 60, 'Length_cm': 80, 'Height_cm': 40, 'Color': '#33FF57'},
            {'Box_ID': 'BOX-C', 'Box_Name': 'กล่อง C (เครื่องใช้ไฟฟ้า)', 'Customer_Name': 'ลูกค้า วิชัย', 'Width_cm': 50, 'Length_cm': 50, 'Height_cm': 60, 'Color': '#3380FF'}
        ])
        return df_c, df_b

df_container, df_box = load_sheet_data()

# ------------------------------------------------------------------------------
# 3. SIDEBAR USER INTERFACE (SELECTION)
# ------------------------------------------------------------------------------
st.sidebar.header("📋 เมนูเลือกตู้และสินค้า")

# 1. เลือกตู้คอนเทนเนอร์
selected_container_name = st.sidebar.selectbox(
    "เลือกตู้คอนเทนเนอร์:",
    df_container['Container_Name'].unique()
)
container_info = df_container[df_container['Container_Name'] == selected_container_name].iloc[0]

st.sidebar.markdown("---")
st.sidebar.subheader("ระบุจำนวนกล่องแต่ละชนิด")

# 2. กรอกจำนวนกล่อง
user_box_orders = []
for _, box in df_box.iterrows():
    label = f"{box['Box_Name']} [{box['Customer_Name']}]"
    qty = st.sidebar.number_input(label, min_value=0, value=5, step=1)
    if qty > 0:
        user_box_orders.append({'info': box, 'qty': qty})

# ------------------------------------------------------------------------------
# 4. 3D PLOTLY ENGINE (BOX & CONTAINER DRAWING)
# ------------------------------------------------------------------------------
def create_3d_cube_mesh(x1, y1, z1, x2, y2, z2, color, name_tag):
    """สร้างทรงกล่อง 3D ใน Plotly"""
    x = [x1, x2, x2, x1, x1, x2, x2, x1]
    y = [y1, y1, y2, y2, y1, y1, y2, y2]
    z = [z1, z1, z1, z1, z2, z2, z2, z2]
    
    # ดรรชนีสร้างพื้นผิวทั้ง 6 ด้านของกล่องสี่เหลี่ยม
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 5, 3, 6, 7, 1, 1, 5, 5, 7, 6]
    
    return go.Mesh3d(
        x=x, y=y, z=z, i=i, j=j, k=k,
        color=color,
        opacity=0.85,
        name=name_tag,
        showscale=False,
        hoverinfo="name"
    )

def plot_interactive_container(container, placed_boxes):
    fig = go.Figure()

    cw, cl, ch = container['Width_cm'], container['Length_cm'], container['Height_cm']

    # 1. วาดเส้นขอบตู้คอนเทนเนอร์ (Wireframe Box)
    fig.add_trace(go.Scatter3d(
        x=[0, cw, cw, 0, 0, 0, cw, cw, 0, 0, cw, cw, cw, cw, 0, 0],
        y=[0, 0, cl, cl, 0, 0, 0, cl, cl, 0, 0, 0, cl, cl, cl, cl],
        z=[0, 0, 0, 0, 0, ch, ch, ch, ch, ch, ch, 0, 0, ch, ch, 0],
        mode='lines',
        line=dict(color='black', width=4),
        name=f"ตู้ {container['Container_Name']}"
    ))

    # 2. วาดกล่องแต่ละใบลงในตู้
    for b in placed_boxes:
        mesh = create_3d_cube_mesh(
            b['x1'], b['y1'], b['z1'], 
            b['x2'], b['y2'], b['z2'], 
            color=b['color'],
            name_tag=b['label']
        )
        fig.add_trace(mesh)

    # 3. ตั้งค่ามุมมอง 3D Interactive
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X: กว้าง (cm)', range=[0, cw]),
            yaxis=dict(title='Y: ยาว/ลึก (cm)', range=[0, cl]),
            zaxis=dict(title='Z: สูง (cm)', range=[0, ch]),
            aspectmode='data'
        ),
        margin=dict(r=0, l=0, b=0, t=30),
        height=700
    )
    return fig

# ------------------------------------------------------------------------------
# 5. DBL SIMULATION & VISUALIZATION DISPLAY
# ------------------------------------------------------------------------------
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("📌 สรุปข้อมูลการจัดวาง")
    st.write(f"**ชนิดตู้:** {container_info['Container_Name']}")
    st.write(f"**ขนาดตู้:** {container_info['Width_cm']} x {container_info['Length_cm']} x {container_info['Height_cm']} ซม.")
    
    total_requested = sum(item['qty'] for item in user_box_orders)
    st.write(f"**จำนวนกล่องที่ต้องการวาง:** {total_requested} ใบ")

    run_btn = st.button("🚀 คำนวณและแสดงผล 3D", type="primary")

with col2:
    if run_btn or 'placed_data' not in st.session_state:
        # [ส่วนจำลองตำแหน่งพิกัดการวางกล่องแบบ DBL]
        placed_boxes = []
        curr_x, curr_y, curr_z = 0, 0, 0
        max_y_in_row = 0
        
        for item in user_box_orders:
            box = item['info']
            bw, bl, bh = box['Width_cm'], box['Length_cm'], box['Height_cm']
            
            for _ in range(item['qty']):
                # เช็กขอบเขตความกว้าง (X)
                if curr_x + bw > container_info['Width_cm']:
                    curr_x = 0
                    curr_y += max_y_in_row
                    max_y_in_row = 0
                
                # เช็กขอบเขตความยาว (Y)
                if curr_y + bl > container_info['Length_cm']:
                    curr_x = 0
                    curr_y = 0
                    curr_z += bh
                
                # เช็กขอบเขตความสูง (Z)
                if curr_z + bh <= container_info['Height_cm']:
                    placed_boxes.append({
                        'x1': curr_x, 'y1': curr_y, 'z1': curr_z,
                        'x2': curr_x + bw, 'y2': curr_y + bl, 'z2': curr_z + bh,
                        'color': box.get('Color', '#FF5733'),
                        'label': f"{box['Box_Name']} ({box['Customer_Name']})"
                    })
                    curr_x += bw
                    if bl > max_y_in_row:
                        max_y_in_row = bl

        st.session_state['placed_data'] = placed_boxes

    # แสดงผลกราฟิก 3D Interactive
    fig = plot_interactive_container(container_info, st.session_state['placed_data'])
    st.plotly_chart(fig, use_container_width=True)
