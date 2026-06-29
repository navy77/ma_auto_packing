
import requests
from streamlit_echarts import st_echarts, JsCode
from streamlit_autorefresh import st_autorefresh
import dotenv
import streamlit as st
from streamlit_option_menu import option_menu
from datetime import datetime, timedelta
import os
import json

st_autorefresh(interval= 2000, key="datarefresh")
chart_height = "300px"

def config_pie():
    with open("config_pie.json", "r", encoding="utf-8") as f:
        options = json.load(f)
    return options

def config_stack():
    with open("config_stack.json", "r", encoding="utf-8") as f:
        options = json.load(f)
    return options

def config_line():
    with open("config_line.json", "r", encoding="utf-8") as f:
        options = json.load(f)
    return options


def status_ratio_data(device_id):
    try:
        response = requests.get(f"http://{api_host}:{api_port}/status/ratio-daily/{device_id}",timeout=5)
        if response.status_code == 200:
            raw_data = response.json()

            return [{"name": item["status"], "value": item["ratio"]} for item in raw_data]
        return []
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อ API ได้: {e}")
        return []

def status_ratio_monthly(device_id):
    try:
        response = requests.get(f"http://{api_host}:{api_port}/status/ratio-monthly/{device_id}", timeout=5)
        if response.status_code == 200:
            json_response = response.json()

            raw_data = json_response.get("daily_data", [])

            dates = [item["date"] for item in raw_data]
            series_data = {status: [] for status in status_mc}

            for item in raw_data:
                details = item.get("details", [])
                day_details = {d["status"]: d["ratio"] for d in details}
                
                for status in series_data.keys():
                    series_data[status].append(day_details.get(status, 0))

            return dates, series_data
        empty_data = {status: [] for status in status_mc}
        return [], empty_data
    
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อ API ได้: {e}")
        return [], {"run": [], "stop": [], "offline": [], "alarm": []}

def status_shift_monthly(shift_name,device_id,status):
    try:
        response = requests.get(f"http://{api_host}:{api_port}/status/ratio-monthly/{device_id}/{shift_name}", timeout=5)
        if response.status_code == 200:
            raw_data = response.json().get("daily_data", [])

            ratios = []
            dates = []
            for item in raw_data:
                dates.append(item["date"])
                run_val = next((d["ratio"] for d in item.get("details", []) if d["status"] == status), 0)
                ratios.append(run_val)
            return dates, ratios

    except Exception as e:
        st.error(f"Error shift {shift_name}: {e}")
    return [], []

def status_timeline(device_id):
    try:
        response = requests.get(f"http://{api_host}:{api_port}/status/timeline/{device_id}", timeout=5)
        if response.status_code == 200:

            return response.json()
        return []
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อ API ได้: {e}")
        return []

def status_stacked_bar_chart(device_id):
    dates, data = status_ratio_monthly(device_id)
    order = status_mc
    series = []
    stack_option = config_stack()
    stack_option["series"] = series
    stack_option["xAxis"]["data"] = dates

    for status in order:
        values = data.get(status, [])
        series.append({
            "name": status,
            "type": "bar",
            "stack": "total", 
            "data": values,
            "itemStyle": {"color": color_map.get(status, color_err)}
        })

    
    st_echarts(options=stack_option, height= chart_height)

def status_pie_chart(device_id):
    data = status_ratio_data(device_id)
    pie_option = config_pie()
    pie_option["series"][0]["data"] = data

    for status in data:
        status["itemStyle"] = {"color": color_map.get(status["name"], color_err)}
    
    st_echarts(options=pie_option, height=chart_height)

def status_line_chart(device_id):
    status = st.selectbox('Choose machine:', status_mc ,key='status_list')

    dates_n, data_n = status_shift_monthly("N",device_id,status)
    dates_m, data_m = status_shift_monthly("M",device_id,status)

    options = {
        "title": {"text": "Running Comparison Shift M vs N ", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Shift M", "Shift N"], "bottom": "5%"},
        "xAxis": {"type": "category", "data": dates_n}, 
        "yAxis": {"type": "value", "name": "Ratio (%)","min": 0,"max": 100,},

        "series": [
            {
                "name": "Shift M",
                "type": "line",
                "data": data_m,
                "smooth": True,
                "itemStyle": {"color": "#3b82f6"} 
            },
            {
                "name": "Shift N",
                "type": "line",
                "data": data_n,
                "smooth": True,
                "itemStyle": {"color": "#caef44"} 
            }
        ]
    }
    st_echarts(options=options, height=chart_height)

def status_timeline_chart(device):
    data = status_timeline("mc1")
 
    # color_map = {"MC_RUN": "#22c55e","stop": "#ef4444","alarm": "#f59e0b","unknown": "#ced6e1","offline": "#64748b"}
    shift_start = datetime.now().replace(hour=7,minute=0,second=0,microsecond=0
)

    shift_end = shift_start + timedelta(days=1)

    x_min = int(shift_start.timestamp() * 1000)
    x_max = int(shift_end.timestamp() * 1000)
 

    def to_ms(dt):
        return int(dt.timestamp() * 1000)
    
    series = []
    for row in data:
        start_dt = datetime.fromisoformat(row["ts"])
        end_dt = start_dt + timedelta(seconds=row["duration"] )

        series.append({
            "name": row["status"],
            "value": [0, to_ms(start_dt),to_ms(end_dt),row["status"]],
            "itemStyle": {"color": color_map.get(row["status"], color_err)}
        })


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
            <b>${params.name}</b><br/>
            Start : ${new Date(params.value[1]).toLocaleString()}<br/>
            End : ${new Date(params.value[2]).toLocaleString()}
        `;
    }
    """)

    option = {
        "title": {
            "text": "Machine Timeline",
            "left": "center",
            "top": "0%",
            "textStyle": {"fontSize": 20, "fontWeight": "bold"}
        },
        "tooltip": {
            "trigger": "item",
            "formatter": tooltip_formatter
        },
        
        "xAxis": {
            "type": "time",
            "min": x_min,
            "max": x_max,
            "splitNumber": 10,

            "axisLabel": {
                "formatter": "{HH}:{mm}"
            }
        },
        "yAxis": {
            "type": "category",
            "data": [device]
        },
        "series": [
            {
                "type": "custom",
                "renderItem": render_item,
                "encode": {
                    "x": [1, 2],
                    "y": 0
                },
                "data": series
            }
        ]
    }

    st_echarts(options=option,height="300px")


def status():
    col1,col2 = st.columns([1,5])
    with col1:
        choice = st.selectbox('Choose machine:', mc_list,key='mc_list')

    col1,col2 = st.columns([1,1],border=True)
    with col1:
        with st.container():
            status_pie_chart(choice)
    with col2:
        with st.container():
            status_timeline_chart("MC1")

    col1,col2 = st.columns([1,1],border=True)
    with col1:
        with st.container():
            status_stacked_bar_chart(choice)

    with col2:
        with st.container():
            status_line_chart("mc1")

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

    api_host = os.environ['API_HOST']
    api_port = int(os.environ['API_PORT'])

    mc_list = os.environ['MC_LIST']
    mc_list = [item.strip() for item in mc_list.split(',')]

    status_mc = os.environ['STATUS_LIST']
    status_mc = [item.strip() for item in status_mc.split(',')]

    color_err =  os.environ['COLOR_ERR']
    color_values = [
        os.environ["COLOR_1"],
        os.environ["COLOR_2"],
        os.environ["COLOR_3"],
        os.environ["COLOR_4"],
        os.environ["COLOR_UNKNOWN"]
    ]

    color_map = dict(zip(status_mc, color_values))
    pie_chart_options = config_pie()
    stack_chart_options = config_stack()
    # line_chart_options = config_line()

    main_layout()
