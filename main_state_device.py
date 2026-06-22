from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import datetime, os, time
import numpy as np

# Load .env from root
# ConfigManager.load()
load_dotenv("./.env")
# load_dotenv("/app/.env")
# load_dotenv("/app/app/.env")

time_prev_get=os.getenv("TIME_PREV_GET_BOXSTATE")
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
    

class state_device_to_db:
    def state_device():
        df_device = getdate_from_db.fetch_device_status()
        time_prev = pd.to_datetime(time_prev_get, errors="coerce").tz_localize("Asia/Bangkok")
        time_now = pd.Timestamp.now(tz="Asia/Bangkok").floor("s")

        def is_no_data_strict(df):
            return (
                df.empty or
                df.drop(columns=["mc_no"], errors="ignore").isna().all().all(), time_prev
            )
    
        if is_no_data_strict(df_device):
            raise ValueError("⚠️ No data from source")

        df_device["occurred"] = pd.to_datetime(df_device["occurred"], errors="coerce").dt.tz_localize("Asia/Bangkok")

        # -------------- Device state -------------- #
        df_device = df_device.sort_values(["mc_no", "occurred"])
        df_device["gap"] = df_device.groupby("mc_no")["occurred"].diff().dt.total_seconds().div(60)
        first_mask = df_device.groupby("mc_no").cumcount() == 0
        df_device.loc[first_mask, "gap"] = (
            df_device.loc[first_mask, "occurred"] - time_prev
        ).dt.total_seconds() / 60

        # -------------- Detect machine that no topic  -------------- #
        topic_empty_mc = df_device.groupby("mc_no").apply(
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
        top_rows["mc_no"] = np.where(
            top_rows["mc_no"].isin(topic_empty_mc[topic_empty_mc].index),
            ""
        )
        df_device = pd.concat([df_device, top_rows], ignore_index=True)
 
        # ---------- Force topic empty → state_device = 0 because not gateway or No data mqtt ----------- #
        topic_empty = df_device["mc_no"].isna() | (df_device["mc_no"].astype(str).str.strip() == "")
        df_device.loc[topic_empty, "state_device"] = 0
        df_status_device = df_device
        return df_status_device, time_now  # .drop(columns="gap")
   

    def df_to_db(df_status_device, newest_time):
                #connect to db
                mcstatus_list = ['occurred','device_status','mc_no','process']
                conn = connect_database.get_connection_pg()
                if df_insert is None:
                    print("No new data to insert")
                    return None
                else:
                    try:
                        if not df_insert is None:
                            df = df_insert.copy()
                            for index, row in df.iterrows():
                                value = None
                                for i in range(len(mcstatus_list)):
                                    address = mcstatus_list[i]
                                    if value == None:
                                        value = ",'"+str(row[address])+"'"
                                    else:
                                        value = value+",'"+str(row[address])+"'"

                                insert_string = f"""
                                    INSERT INTO {table_mcstatus_name} (registered, occurred, device_status, mc_no, process)
                                    values(
                                        NOW() AT TIME ZONE 'Asia/Bangkok'
                                        {value}
                                        )
                                    """
                                with conn.cursor() as cursor:
                                    cursor.execute(insert_string)
                                    conn.commit()
                            conn.close()   
                            df_insert = None
                            # ------ Update TIME_PREV_GET to .env ------- # 
                            new_time = newest_time
                            # with open("/app/.env","r") as f:
                            with open("./.env","r") as f:
                                lines = f.readlines()
                            # with open("/app/.env","w") as f:
                            with open("./.env","w") as f:
                                for line in lines:
                                    if line.startswith("TIME_PREV_GET_BOXSTATE"):  # Update the line with the new time
                                        f.write(f"TIME_PREV_GET_BOXSTATE='{new_time}'\n")
                                    else: # Keep the line unchanged
                                        f.write(line) 
                            print(f"insert data: {df} ")
                    except Exception as e:
                        print('cannot insert df to sql: '+str(e))
                        # (df_to_db.__name__,"cannot insert df to sql",e)


if __name__ == "__main__":  
    try:
        print("Starting MMS StatusBox StoreDB...📥")
        df_status_device, newest_time = state_device_to_db.state_device()
        time.sleep(1)
        state_device_to_db.df_to_db(df_status_device, newest_time)
    except ValueError as e:
        print(f"Error: {e}")