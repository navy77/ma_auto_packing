import streamlit as st
import requests
from streamlit_echarts import st_echarts
from streamlit_autorefresh import st_autorefresh
import dotenv

st_autorefresh(interval=5000, key="datarefresh")
container_h = 300

def get_ratio_data():
    try:
        response = requests.get("http://127.0.0.1:8001/status/ratio-daily/mc3")
        if response.status_code == 200:
            raw_data = response.json()
            print(raw_data)
            return [{"name": item["status"], "value": item["ratio"]} for item in raw_data]
        return []
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อ API ได้: {e}")
        return []

def pie_chart():
    data = get_ratio_data()
    # 3. กำหนดค่า Option ของ ECharts
    options = {
        "tooltip": {"trigger": "item"},
        "legend": {"top": "5%", "left": "center"},
        "series": [
            {
                "name": "Status Ratio",
                "type": "pie",
                "radius": ["40%", "70%"],  # ทำให้เป็น Donut chart
                "padAngle": 5,             # กำหนดช่องว่างระหว่างชิ้น
                "itemStyle": {
                    "borderRadius": 10     # ทำให้ขอบมน
                },
                "data": data,
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)",
                    }
                },
            }
        ],
    }

    if data:
        st_echarts(options=options, height="200px")
    else:
        st.warning("ไม่มีข้อมูลที่จะแสดงผล")

def main_layout():
    st.set_page_config(
            page_title="MMS System",
            page_icon="💻",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    st.markdown("""<h1 style='text-align: center;'>MACHINE MONITORING DASHBOARD</h1>""", unsafe_allow_html=True)

    col1,col2 = st.columns([1,1],border=True)
    with col1:
        with st.container():
            st.markdown("piechart")
            pie_chart()
    with col2:
        with st.container():
            st.markdown("timeline")

    col1,col2 = st.columns([1,1],border=True)
    with col1:
        with st.container():
            st.markdown("stack")

    with col2:
        with st.container():
            st.markdown("line")



if __name__ == "__main__":
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file,override=True)
    main_layout()