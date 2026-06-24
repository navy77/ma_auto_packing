
import requests
from streamlit_echarts import st_echarts, JsCode
from streamlit_autorefresh import st_autorefresh
import dotenv
import streamlit as st
from streamlit_option_menu import option_menu
from datetime import datetime, timedelta

st_autorefresh(interval=60000, key="datarefresh")
chart_height = "300px"

def status_ratio_data():
    try:
        response = requests.get("http://127.0.0.1:8001/status/ratio-daily/mc1",timeout=5)
        if response.status_code == 200:
            raw_data = response.json()

            return [{"name": item["status"], "value": item["ratio"]} for item in raw_data]
        return []
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อ API ได้: {e}")
        return []

def status_ratio_monthly():
    try:
        response = requests.get("http://127.0.0.1:8001/status/ratio-monthly/mc1", timeout=5)
        if response.status_code == 200:
            json_response = response.json()

            raw_data = json_response.get("daily_data", [])

            dates = [item["date"] for item in raw_data]
            series_data = {"run": [], "stop": [], "offline": [], "alarm": []}

            for item in raw_data:
                details = item.get("details", [])
                day_details = {d["status"]: d["ratio"] for d in details}
                
                for status in series_data.keys():
                    series_data[status].append(day_details.get(status, 0))

            return dates, series_data
        
        return [], {"run": [], "stop": [], "offline": [], "alarm": []}
        
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อ API ได้: {e}")
        return [], {"run": [], "stop": [], "offline": [], "alarm": []}

def status_shift_monthly(shift_name):
    try:
        url = f"http://127.0.0.1:8001/status/ratio-monthly/mc1/{shift_name}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            raw_data = response.json().get("daily_data", [])
            
            # เก็บเฉพาะค่า ratio ของ status == "run"
            run_ratios = []
            dates = []
            for item in raw_data:
                dates.append(item["date"])
                # หาค่า ratio ของสถานะ run ถ้าไม่มีให้เป็น 0
                run_val = next((d["ratio"] for d in item.get("details", []) if d["status"] == "run"), 0)
                run_ratios.append(run_val)
            
            return dates, run_ratios
    except Exception as e:
        st.error(f"Error shift {shift_name}: {e}")
    return [], []

def status_timeline():
    try:
        response = requests.get("http://127.0.0.1:8001/status/timeline/mc1",timeout=5)
        if response.status_code == 200:
            raw_data = response.json()

            return response.json()
        return []
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อ API ได้: {e}")
        return []

def status_stacked_bar_chart():
    dates, series_data = status_ratio_monthly()

    order = ["run", "stop",  "alarm", "offline"]
    series = []
    color_map = {"run": "#22c55e", "stop": "#f59e0b", "offline": "#64748b", "alarm": "#ef4444"}
    
    for status in order:
        values = series_data.get(status, [])
        series.append({
            "name": status.capitalize(),
            "type": "bar",
            "stack": "total", 
            "data": values,
            "itemStyle": {"color": color_map.get(status)}
        })

    options = {
        "title": {
            "text": "Machine Operation Monthly",
            "left": "center",
            "top": "0%",
            "textStyle": {"fontSize": 20, "fontWeight": "bold"}
        },
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Run", "Stop", "Alarm","Offline"]},
        "xAxis": {"type": "category", "data": dates},
        "yAxis": {"type": "value","name": "Daily Ratio"},
        "series": series
    }
    
    st_echarts(options=options, height= chart_height)

def status_pie_chart():
    data = status_ratio_data()
    color_map = {"run": "#22c55e", "stop": "#ef4444","offline": "#64748b","alarm": "#f59e0b"     }

    for item in data:
        item["itemStyle"] = {"color": color_map.get(item["name"], "#3b82f6")}

    options = {
        "title": {
            "text": "Machine Operation Ratio",
            "left": "center",
            "top": "0%",
            "textStyle": {"fontSize": 20, "fontWeight": "bold"}
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{b}: {c}%" 
        },
        "legend": {"bottom": "1%", "left": "center"},
        "series": [
            {
                "name": "Status Ratio",
                "type": "pie",
                "radius": ["40%", "70%"],  
                "padAngle": 5,             
                "itemStyle": {
                    "borderRadius": 10  
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
    st_echarts(options=options, height=chart_height)

def status_shifts_chart():

    dates_n, data_n = status_shift_monthly("N")
    dates_m, data_m = status_shift_monthly("M")
    
    options = {
        "title": {"text": "Running Comparison Shift M vs N ", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Shift M", "Shift N"], "bottom": "5%"},
        "xAxis": {"type": "category", "data": dates_n}, 
        "yAxis": {"type": "value", "name": "Run Ratio (%)","min": 0,"max": 100,},

        "series": [
            {
                "name": "Shift M",
                "type": "line",
                "data": data_m,
                "smooth": True,
                "itemStyle": {"color": "#3b82f6"} # สีน้ำเงิน
            },
            {
                "name": "Shift N",
                "type": "line",
                "data": data_n,
                "smooth": True,
                "itemStyle": {"color": "#caef44"} # สีแดง
            }
        ]
    }
    st_echarts(options=options, height=chart_height)

def status_timeline_chart():

    rows = status_timeline()

    color_map = {
        "run": "#22c55e",
        "stop": "#ef4444",
        "alarm": "#f59e0b",
        "offline": "#64748b"
    }

    series_data = []

    for row in rows:

        start = datetime.fromisoformat(
            row["ts"]
        )

        end = start + timedelta(
            seconds=row["duration"]
        )

        series_data.append({
            "name": row["status"],
            "value": [
                start.strftime("%Y-%m-%d %H:%M:%S"),
                end.strftime("%Y-%m-%d %H:%M:%S"),
                row["status"]
            ],
            "itemStyle": {
                "color": color_map.get(
                    row["status"],
                    "#3b82f6"
                )
            }
        })

    options = {
        "title": {
            "text": "Machine Timeline",
            "left": "center"
        },
        "tooltip": {
            "trigger": "item"
        },
        "xAxis": {
            "type": "time"
        },
        "yAxis": {
            "type": "category",
            "data": ["MC1"]
        },
        "series": [
            {
                "type": "custom",
                "renderItem": """
                function(params, api) {

                    var start = api.coord([
                        api.value(0),
                        0
                    ]);

                    var end = api.coord([
                        api.value(1),
                        0
                    ]);

                    var height =
                        api.size([0,1])[1] * 0.6;

                    return {
                        type:'rect',
                        shape:{
                            x:start[0],
                            y:start[1]-height/2,
                            width:end[0]-start[0],
                            height:height
                        },
                        style:api.style()
                    };
                }
                """,
                "encode": {
                    "x": [0, 1],
                    "y": -1
                },
                "data": series_data
            }
        ]
    }

    st_echarts(
        options=options,
        height="250px"
    )


def status():
    col1,col2 = st.columns([1,1],border=True)
    with col1:
        with st.container():
            status_pie_chart()
    with col2:
        with st.container():
            status_timeline_chart()

    col1,col2 = st.columns([1,1],border=True)
    with col1:
        with st.container():
            status_stacked_bar_chart()

    with col2:
        with st.container():
            status_shifts_chart()


def main_layout():
    st.set_page_config(
        page_title="MMS System",
        page_icon="💻",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    with st.sidebar:
        selected = option_menu(
            "MMS", 
            ["Home", 'MC Status', 'MC Alarm'], 
            icons=['house', 'robot', 'exclamation-triangle'], 
            menu_icon="cast", 
            default_index=1
        )
        st.markdown("---")
        st.write("System Status: Operational")


    st.markdown("""<h1 style='text-align: center;'>MACHINE MONITORING DASHBOARD</h1>""", unsafe_allow_html=True)

    if selected == "Home":
        st.subheader("Production Result")


    elif selected == "MC Status":
        st.subheader("Machine Status")
        status()


    elif selected == "MC Alarm":
        st.subheader("Machine Alarm")


if __name__ == "__main__":
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file,override=True)
    main_layout()



-------------------------
def to_ms(dt_string):
    return int(
        datetime.fromisoformat(dt_string).timestamp() * 1000
    )

# -----------------------------
# Transform
# -----------------------------
devices = response["devices"]
colors = response["status_color"]

device_index = {
    device: idx
    for idx, device in enumerate(devices)
}

series_data = []

for row in response["timeline"]:

    series_data.append({
        "name": row["status"],
        "value": [
            device_index[row["device"]],
            to_ms(row["start"]),
            to_ms(row["end"]),
            row["status"]
        ],
        "itemStyle": {
            "color": colors.get(
                row["status"],
                "#999999"
            )
        }
    })

# -----------------------------
# Custom Render
# -----------------------------
render_item = JsCode("""
function(params, api) {

    var categoryIndex = api.value(0);

    var start = api.coord([
        api.value(1),
        categoryIndex
    ]);

    var end = api.coord([
        api.value(2),
        categoryIndex
    ]);

    var height =
        api.size([0, 1])[1] * 0.6;

    return {
        type: 'rect',
        shape: {
            x: start[0],
            y: start[1] - height / 2,
            width: end[0] - start[0],
            height: height
        },
        style: api.style()
    };
}
""")

tooltip_formatter = JsCode("""
function(params){

    return `
        Status : ${params.name}<br/>
        Start : ${new Date(params.value[1]).toLocaleString()}<br/>
        End : ${new Date(params.value[2]).toLocaleString()}
    `;
}
""")

# -----------------------------
# ECharts Option
# -----------------------------
option = {
    "title": {
        "text": "Machine State Timeline"
    },
    "tooltip": {
        "trigger": "item",
        "formatter": tooltip_formatter
    },
    "grid": {
        "left": 120,
        "right": 50,
        "top": 50,
        "bottom": 50
    },
    "xAxis": {
        "type": "time"
    },
    "yAxis": {
        "type": "category",
        "data": devices
    },
    "series": [
        {
            "type": "custom",
            "renderItem": render_item,
            "encode": {
                "x": [1, 2],
                "y": 0
            },
            "data": series_data
        }
    ]
}

# -----------------------------
# UI
# -----------------------------
st.title("Machine Timeline")

st_echarts(
    options=option,
    height="500px"
)

st.divider()

st.subheader("Mock JSON")

st.json(response)