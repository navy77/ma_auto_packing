from dotenv import load_dotenv, set_key
from influxdb import InfluxDBClient
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import os, time
from pathlib import Path

# Load .env from root
# ConfigManager.load()
# load_dotenv("./.env")
load_dotenv("/app/.env")
# load_dotenv("/app/app/.env")

time_prev_get=os.getenv("TIME_PREV_GET_STATUS")
# DB connection parameters
influx_server=os.getenv('INFLUX_SERVER')
influx_database=os.getenv('INFLUX_DATABASE')
influx_user_login=os.getenv('INFLUX_USER_LOGIN')
influx_password=os.getenv('INFLUX_PASSWORD')
influx_port=os.getenv('INFLUX_PORT')
influx_measurement=os.getenv('INFLUX_MEASUREMENT')
mqtt_topic=os.getenv("MQTT_TOPIC_2")

host_p=os.getenv("POSTGRES_HOST")
port_p=os.getenv("POSTGRES_PORT")
database_p=os.getenv("POSTGRES_DB")
username_p=os.getenv("POSTGRES_USER")
password_p=os.getenv("POSTGRES_PASSWORD")
table_mcstatus_name=os.getenv("TABLE_2")

class connect_database:
    def get_connection_influx():
        return InfluxDBClient(host=influx_server, port=influx_port, username=influx_user_login, password=influx_password, database=influx_database)
    
    def get_connection_pg():
        return psycopg2.connect(host=host_p,port=port_p,dbname=database_p,user=username_p,password=password_p)

class mc_status_store_db:
    def query_influx():
        df_influx = None
        time_now = pd.Timestamp.now(tz="Asia/Bangkok")
        # time_prev = pd.Timestamp(time_prev_get, tz="Asia/Bangkok")
        time_prev = pd.Timestamp(time_prev_get)
        # Convert time_prev and time_now to nanoseconds since epoch for InfluxDB query
        time_prev_ns = int(time_prev.timestamp() * 1e9) + (time_prev.microsecond)
        time_now_ns = int(time_now.timestamp() * 1e9)
        print(f"time_prev: {time_prev}, time_now: {time_now}")
        print(f"time_prev: {time_prev_ns}, time_now: {time_now_ns}")
        try:
            result_lists = []
            client = connect_database.get_connection_influx()
            mqtt_topic_value = list(str(mqtt_topic).split(","))
            for i in range(len(mqtt_topic_value)):
                # query = f"SELECT time,status,topic FROM {influx_measurement} WHERE topic ='{mqtt_topic_value[i]}' order by time desc limit 120"
                query = f"SELECT time,status,topic FROM {influx_measurement} WHERE time > {time_prev_ns} AND time < {time_now_ns} AND topic ='{mqtt_topic_value[i]}' order by time desc"
                result = client.query(query)
                result_df = pd.DataFrame(result.get_points())
                result_lists.append(result_df)
            query_influx = pd.concat(result_lists, ignore_index=True)

            last_event = (pd.to_datetime(time_prev_ns, unit='ns')).to_datetime64()
            if query_influx.empty:
                newest_time = last_event
                df_influx = None
                print("influxdb data is emply")
                # query_influx.__name__,"influxdb data is emply"  
            else:
                query_influx = query_influx.sort_values(by="time",ascending=False)
                query_influx["time"] = pd.to_datetime(query_influx["time"]).dt.tz_convert(None)
                query_influx["ts"] = query_influx["time"]  
                query_influx["time"] = query_influx["time"] + pd.DateOffset(hours=7) 
                query_influx["time"] = query_influx["time"].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
                if last_event !='':
                    new_query_influx = query_influx[query_influx.ts > last_event]
                    if not new_query_influx.empty:
                        df_influx = new_query_influx
                        newest_time = df_influx.head(1)['ts'].values[0]
                else:
                    df_influx = query_influx
                    newest_time = df_influx.head(1)['ts'].values[0]
            return df_influx, newest_time
        except Exception as e:
            print('cannot query influxdb : '+str(e))
            # (query_influx.__name__,"cannot query influxdb",e)

    def edit_col(df_influx):
            if df_influx is None:
                print("df_influx is empty and no new data to insert")
                return None
            else:
                try:
                    df = df_influx.copy()
                    df_split = df['topic'].str.split('/', expand=True)
                    df['mc_no'] = df_split[3].values
                    df['process'] = df_split[2].values
                    df.drop(columns=['topic','ts'],inplace=True)
                    df.rename(columns = {'time':'occurred'}, inplace = True)
                    df.rename(columns={'status': 'mc_status'}, inplace=True)
                    df_insert = df[['occurred','mc_status','mc_no','process']]
                    return df_insert
                except Exception as e:
                    print('cannot edit dataframe data : '+str(e))
                # (edit_col.__name__,"cannot edit dataframe data",e)

    def df_to_db(df_insert, newest_time):
                #connect to db
                mcstatus_list = ['occurred','mc_status','mc_no','process']
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
                                    INSERT INTO {table_mcstatus_name} (registered, occurred, mc_status, mc_no, process)
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
                            with open("/app/.env","r") as f:
                            # with open("./.env","r") as f:
                                lines = f.readlines()
                            with open("/app/.env","w") as f:
                            # with open("./.env","w") as f:
                                for line in lines:
                                    if line.startswith("TIME_PREV_GET_STATUS"):  # Update the line with the new time
                                        f.write(f"TIME_PREV_GET_STATUS='{new_time}'\n")
                                    else: # Keep the line unchanged
                                        f.write(line)
                            print(f"insert data: {df} ")
                    except Exception as e:
                        print('cannot insert df to sql: '+str(e))
                        # (df_to_db.__name__,"cannot insert df to sql",e)


if __name__ == "__main__":  
    try:
        print("Starting MMS Status StoreDB...📥")
        df_influx, newest_time = mc_status_store_db.query_influx()
        df_insert = mc_status_store_db.edit_col(df_influx)
        time.sleep(1)
        mc_status_store_db.df_to_db(df_insert, newest_time)
    except ValueError as e:
        print(f"Error: {e}")