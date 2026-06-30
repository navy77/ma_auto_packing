import clickhouse_connect
import os, json, logging
import dotenv
import redis
from datetime import datetime
import pandas as pd

class ScheduleData:
    def __init__(self):
        dotenv.load_dotenv()
        self.redis_client = redis.Redis(host= os.environ["REDIS_HOST"], port=6379, decode_responses=True)
        self.device_list = os.environ["DEVICE_LIST"].split(',')

        logging.basicConfig(
            filename='log/schedule.log', level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s', force=True)

    def main(self):
        self.check_status() 
        self.check_alarm()

    def clickhouse_connect(self):
        try:
            clickhouse_client = clickhouse_connect.get_client(host=os.environ["CLICKHOUSE_HOST"],
                                                                    port=int(os.environ["CLICKHOUSE_PORT"]),
                                                                    username=os.environ["CLICKHOUSE_USER"],
                                                                        password=os.environ["CLICKHOUSE_PASSWORD"],
                                                                        )
            return clickhouse_client
        except Exception as e:
            logging.error(f"Error clickhouse_connect: {e}")

    def check_status(self):
        try:
            # get device status
            device_status = json.loads(self.redis_client.get("device_all"))
            
            df_device = pd.DataFrame.from_dict(device_status, orient='index', columns=['status'])
            df_device = df_device.reset_index().rename(columns={'index': 'device_id'})

            # get status 
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # read last_checked
            with open("time.json","r") as f:
                data = json.load(f)
            last_checked = data["time_status"]

            if last_checked =="":
                query = 'SELECT * FROM default.status_raw_tb WHERE created_at < %(end)s'
                parameters = {'end': now}
            else:
                query = 'SELECT * FROM default.status_raw_tb WHERE created_at > %(start)s AND created_at < %(end)s'
                parameters = {'start': last_checked, 'end': now}

            clickhouse_conn = self.clickhouse_connect()
            result = clickhouse_conn.query(query, parameters=parameters)
            df_status = pd.DataFrame(result.result_rows, columns=result.column_names)

            if not df_status.empty:
                df = pd.merge(df_device,df_status,on='device_id',how='left')
                df['created_at'] = df['created_at'].fillna(now)
                mask = (df['shift'].isna())
                df.loc[mask, 'shift'] = df.loc[mask, 'created_at'].apply(self.work_shift)

                df['status'] = df.apply(lambda row: row['status_y'] if row['status_x'] == "online" else 'offline', axis=1)
               
                df = df.fillna(0)
                df.rename(columns={'created_at': 'ts'}, inplace=True)
                df = df[['ts','device_id','shift', 'status']]
                df['ts'] = pd.to_datetime(df['ts'], utc=True)
                df['ts'] = df['ts'].dt.tz_convert('Asia/Bangkok')
                df['ts'] = df['ts'].dt.tz_localize(None)
                df = df[df['status'] != 0]

                clickhouse_conn = self.clickhouse_connect()
                clickhouse_conn.insert_df(table='status_tb',df=df)

                # write 
                data["time_status"] = now
                with open("time.json", "w") as f:
                    json.dump(data, f)

                print(f"{now}|check_status success")
                logging.warning("check_status success")

        except Exception as e:
            print(f"Error check_status: {e}")
            logging.error(f"Error check_status: {e}")

    def check_alarm(self):
        try:
            # get device status
            device_status = json.loads(self.redis_client.get("device_all"))
            
            df_device = pd.DataFrame.from_dict(device_status, orient='index', columns=['status'])
            df_device = df_device.reset_index().rename(columns={'index': 'device_id'})

            # get alarm 
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # read last_checked
            with open("time.json","r") as f:
                data = json.load(f)
            last_checked = data["time_alarm"]

            if last_checked =="":
                query = 'SELECT * FROM default.alarm_raw_tb WHERE created_at < %(end)s'
                parameters = {'end': now}
            else:
                query = 'SELECT * FROM default.alarm_raw_tb WHERE created_at > %(start)s AND created_at < %(end)s'
                parameters = {'start': last_checked, 'end': now}

            clickhouse_conn = self.clickhouse_connect()
            result = clickhouse_conn.query(query, parameters=parameters)
            df_status = pd.DataFrame(result.result_rows, columns=result.column_names)

            if not df_status.empty:
                df = pd.merge(df_device,df_status,on='device_id',how='left')
                df['created_at'] = df['created_at'].fillna(now)
                mask = (df['shift'].isna())
                df.loc[mask, 'shift'] = df.loc[mask, 'created_at'].apply(self.work_shift)

                df['status'] = df.apply(lambda row: row['status_y'] if row['status_x'] == "online" else 'offline', axis=1)
                df = df.fillna(0)

                df.rename(columns={'created_at': 'ts'}, inplace=True)
                df = df[['ts','device_id','shift', 'status']]
                df['ts'] = pd.to_datetime(df['ts'], utc=True)
                df['ts'] = df['ts'].dt.tz_convert('Asia/Bangkok')
                df['ts'] = df['ts'].dt.tz_localize(None)
                df = df[df['status'] != 0]

                clickhouse_conn = self.clickhouse_connect()
                clickhouse_conn.insert_df(table='alarm_tb',df=df)

                # write 
                data["time_alarm"] = now
                with open("time.json", "w") as f:
                    json.dump(data, f)

                print(f"{now}|check_alarm success")
                logging.warning("check_alarm success")
        
        except Exception as e:
            print(f"Error check_alarm: {e}")
            logging.error(f"Error check_alarm: {e}")

    def work_shift(self,ts):
        hour = ts.hour
        if 7 <= hour < 19:
            shift = "M"
        else:
            shift = "N"
        return shift
    
if __name__ == "__main__":
    scheduler = ScheduleData()
    scheduler.main()