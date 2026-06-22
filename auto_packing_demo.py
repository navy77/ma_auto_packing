from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import datetime, os, time

# Load .env from root
# ConfigManager.load()
load_dotenv("./.env")
# load_dotenv("/app/.env")
# load_dotenv("/app/app/.env")

time_prev_get=os.getenv("TIME_PREV_GET_DB")
host_p=os.getenv("POSTGRES_HOST")
port_p=os.getenv("POSTGRES_PORT")
database_p=os.getenv("POSTGRES_DB")
username_p=os.getenv("POSTGRES_USER")
password_p=os.getenv("POSTGRES_PASSWORD")
table_mcstatus_name=os.getenv("TABLE_2")
table_statusbox_name=os.getenv("TABLE_4")
mqtt_topic=os.getenv("MQTT_TOPIC_2")

class connect_database:
  
    def get_connection_pg():
        return psycopg2.connect(host=host_p,port=port_p,dbname=database_p,user=username_p,password=password_p)
    
class getdate_from_db:
    def fetch_status_from_db():
        client = connect_database.get_connection_pg()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # time_prev = datetime.datetime.strptime(time_prev_get, "%Y-%m-%d %H:%M:%S")
        table_name = table_mcstatus_name

        query = f"SELECT * FROM {table_name} WHERE occurred BETWEEN '{time_prev_get}' AND '{now}' ORDER BY occurred DESC"
        try:
            with client.cursor() as cursor:
                cursor.execute(query)
       
                result = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                df_status = pd.DataFrame(result, columns=columns)
        finally:
            client.close()  
        return df_status

    def fetch_device_status():
        client = connect_database.get_connection_pg()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # time_prev = datetime.datetime.strptime(time_prev_get, "%Y-%m-%d %H:%M:%S")
        table_name = table_statusbox_name
        
        query = f"SELECT * FROM {table_name} WHERE occurred BETWEEN '{time_prev_get}' AND '{now}' ORDER BY occurred DESC"
        try:
            with client.cursor() as cursor:
                cursor.execute(query)
       
                result = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                df_device = pd.DataFrame(result, columns=columns)
        finally:
            client.close()  
        return df_device
    
    def fetch_status_temp():
        conn = connect_database.get_connection_pg()
        table_name = "status_temp_tb"
        process="demo1"
        query = f"SELECT mc_no, status FROM {table_name} WHERE process = '{process}'"
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                df_status_temp = pd.DataFrame(result, columns=columns)
        finally:
            conn.close()  
        return df_status_temp
    
    def mc_no_list():
        mqtt_topic_value = list(str(mqtt_topic).split(","))
        mc_no_list = []
        for i in range(len(mqtt_topic_value)):
            mc_no_list.append(mqtt_topic_value[i].split("/")[3])
        return mc_no_list

    def state_device():
        df_device = getdate_from_db.fetch_device_status()
        df_status_temp = getdate_from_db.fetch_status_temp()
        def is_no_data_strict(df):
            return (
                df.empty or
                df.drop(columns=["mc_no"], errors="ignore").isna().all().all()
        )
        if is_no_data_strict(df_device):
            raise ValueError("⚠️ No data from source")

        time_prev = pd.to_datetime(time_prev_get, errors="coerce").tz_localize("Asia/Bangkok")
        time_now = pd.Timestamp.now(tz="Asia/Bangkok").floor("s")
        df_device["occurred"] = pd.to_datetime(df_device["occurred"], errors="coerce").dt.tz_localize("Asia/Bangkok")

        # -------------- Device state -------------- #
        df_device = df_device.sort_values(["mc_no", "occurred"])
        df_device["gap"] = df_device.groupby("mc_no")["occurred"].diff().dt.total_seconds().div(60)
        first_mask = df_device.groupby("mc_no").cumcount() == 0
        df_device.loc[first_mask, "gap"] = (
            df_device.loc[first_mask, "occurred"] - time_prev
        ).dt.total_seconds() / 60

        # -------------- Detect machine that no topic  -------------- #
        topic_empty_mc = df_device.groupby("mc_no")["topic"].apply(
            lambda x: x.isna().all() or (x.astype(str).str.strip() == "").all()
        )
        df_device["state_device"] = ((df_device["gap"] <= 6)).astype(int)

        # -------------- Add top row -------------- #
        last_ts = df_device.groupby("mc_no")["occurred"].max().reset_index()

        top_rows = pd.DataFrame({
            "mc_no": last_ts["mc_no"],
            "occurred": time_now,
        })

        top_rows["gap"] = (time_now - last_ts["occurred"]).dt.total_seconds() / 60
        top_rows["state_device"] = ((top_rows["gap"] <= 6)).astype(int)
        # ---------- Fill mc_no that only ot have ------------ #
        top_rows["topic"] = np.where(
            top_rows["mc_no"].isin(topic_empty_mc[topic_empty_mc].index),
            "",
            f"mqtt/{div}/{process}/" + top_rows["mc_no"]
        )
        df_device = pd.concat([df_device, top_rows], ignore_index=True)
 
        # # ---------- Force topic empty → state_device = 0 because not gateway or No data mqtt ----------- #
        # topic_empty = df_device["topic"].isna() | (df_device["topic"].astype(str).str.strip() == "")
        # df_device.loc[topic_empty, "state_device"] = 0

        # # # ------------- Planning state ------------- # 
        # # df_plan = get_data.get_plan_per_hr(time_now)
        # # df_plan = df_plan[["mc_no", "planning_stop_time"]].copy()
        # # df_device = df_device.merge(df_plan, on="mc_no", how="left")
        # # # ----- Find planning state: 1 = in planning stop time, 0 = not in planning stop time ----- #
        # # planning_valid = df_device["planning_stop_time"].fillna(0) > 0
        # # same_hour = df_device["ts"].dt.floor("h") == time_now.floor("h")
        # # df_device["planning_state"] = np.where(planning_valid & same_hour, 1, 0)

        # # ------ state_device machine level ------#
        # df_state_device_plan = (
        #     df_device.sort_values(["mc_no", "occurred"], ascending=[True, False])
        #     .groupby("mc_no", as_index=False)
        #     .agg({
        #         # "event_time": "first",
        #         "occurred": "first",
        #         "topic": "first",
        #         # "broker": "first",
        #         # "modbus": "first",
        #         # "mac_id": "first",
        #         # "planning_stop_time": "last",
        #         # "planning_state": "first",
        #         "state_device": "min"
        #     })
        # )     

        # df_status_device = df_state_device_plan.merge(
        #     df_status_temp.rename(columns={"status": "status_temp"}),
        #     on="mc_no",
        #     how="left"
        # )  
    
        # return df_status_device   # .drop(columns="gap")
   
class calculate_status:
    def calculate_status(df_status, df_device):
        df_calculate = pd.merge(df_status, df_device, on=['mc_no', 'process'], how='inner')
        df_calculate = df_calculate[['occurred_x', 'mc_no', 'process', 'mc_status', 'broker', 'modbus', 'mac_id']]
        df_calculate.rename(columns={'occurred_x': 'occurred'}, inplace=True)
        return df_calculate
    
if __name__ == "__main__":
    df_status = getdate_from_db.fetch_status_from_db()
    df_device = getdate_from_db.fetch_device_status()
    # df_status_temp = getdate_from_db.fetch_status_temp()
    df_device_state = getdate_from_db.state_device()
    df_device.to_csv('D:\Kanyalak_T\Training_1\MA\ma_auto_packing\df_device.csv', index=False, encoding="utf-8")
    df_device_state.to_csv('D:\Kanyalak_T\Training_1\MA\ma_auto_packing\df_device_state.csv', index=False, encoding="utf-8")
    print(df_device_state)   

