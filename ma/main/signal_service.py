from gmqtt import Client as MQTTClient
import os, asyncio, json, logging
import dotenv
from datetime import datetime, timezone
import redis
from threading import Thread
from queue import Queue
import time
from zoneinfo import ZoneInfo
import clickhouse_connect

class MqttToRedis:
    def __init__(self):
        dotenv.load_dotenv()
        self.clickhouse_client = clickhouse_connect.get_client(host=os.environ["CLICKHOUSE_HOST"], port=int(os.environ["CLICKHOUSE_PORT"]), username=os.environ["CLICKHOUSE_USER"], password=os.environ["CLICKHOUSE_PASSWORD"])
        self.redis_client = redis.Redis(host= os.environ["REDIS_HOST"], port=6379, decode_responses=True)

        self.client = MQTTClient(os.environ["DEVICE_CLIENT"])
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.mqtt_broker = os.environ["MQTT_BROKER"]
        self.mqtt_port = int(os.environ["MQTT_PORT"])   

        self.device_list = os.environ["DEVICE_LIST"].split(',')
        self.device_loop = int(os.environ["DEVICE_LOOP"])  

        self.queue = Queue(maxsize=500000)
        Thread(target=self.data_to_redis, daemon=True).start()
        Thread(target=self.check_device, daemon=True).start()

        logging.basicConfig(
            filename='log/signal.log', level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s', force=True)

    async def connect(self):
        await self.client.connect(self.mqtt_broker,self.mqtt_port)

    async def subscribe(self, topic):
        self.client.subscribe(topic)

    def on_connect(self, client, flags, rc, properties):
        if rc == 0:
            logging.warning("Connected to MQTT Broker")
        else:
            logging.error(f"Connection failed with code {rc}")
            print(f"Connection failed with code {rc}")

    def on_message(self, client, topic, payload, qos, properties):
        try:
            topic = topic
            data = payload
            self.queue.put_nowait((data,topic))
        except Exception as e:
            logging.error(f"Error on_message: {e}")

    def on_disconnect(self, client, packet, exc=None):
        logging.error('Disconnected from MQTT Broker')
        print('Disconnected from MQTT Broker')

    async def start(self):
        await self.connect()
        await self.subscribe('mqtt/#')
        await self.subscribe('status/#')
        await self.subscribe('alarm/#')
        # await self.subscribe('data/#')
        await asyncio.Event().wait()

    def device_to_redis(self):
        while True:
            data, topic = self.queue.get()
            data_dict = json.loads(data)
            broker = data_dict.get("broker")
            modbus = data_dict.get("modbus")
            mac_id = data_dict.get("mac_id")
            try:
                device_id = topic.split('/')[3]
                now = datetime.now(timezone.utc).isoformat()
                payload = {
                    "timestamp": now,
                    "device_id": device_id,
                    "broker": broker,
                    "modbus": modbus,
                    "mac_id": mac_id,
                }
                self.redis_client.hset("devices", device_id, json.dumps(payload))

            except Exception as e:
                logging.error(f"Error Redis: {e}")
            finally:
                self.queue.task_done()
                
    def data_to_redis(self):
        while True:
            data, topic = self.queue.get()
            device_id = topic.split('/')[3]
            topic = topic.split('/')[0] 

            if topic == "mqtt":
                self.device(device_id,data)
            elif topic == "status":
                self.status(device_id,data)
            elif topic == "alarm":
                self.alarm(device_id,data)
            else:
                pass
            self.queue.task_done()

    def device(self,device_id,data):
        data_dict = json.loads(data)
        broker = data_dict.get("broker")
        modbus = data_dict.get("modbus")
        mac_id = data_dict.get("mac_id")
        try:
            now = datetime.now(timezone.utc).isoformat()
            payload = {
                "timestamp": now,
                "device_id": device_id,
                "broker": str(broker),
                "modbus": str(modbus),
                "mac_id": mac_id,
            }
            self.redis_client.hset("devices", device_id, json.dumps(payload))

        except Exception as e:
            logging.error(f"Error Redis device: {e}")

    def status(self,device_id,data):
        data_dict = json.loads(data)
        status = data_dict.get("status")

        try:
            now = datetime.now(timezone.utc).isoformat()
            shift = self.work_shift(time_current=datetime.now(timezone.utc))
            payload = {
                "timestamp": now,
                "device_id": device_id,
                "status": status
            }
            self.redis_client.hset("status", device_id, json.dumps(payload))
            # record to clickhouse
            self.insert_clickhouse_status(shift,device_id,status)
        except Exception as e:
            logging.error(f"Error Redis status: {e}")

    def alarm(self,device_id,data):
        data_dict = json.loads(data)
        status = data_dict.get("status")
        try:
            now = datetime.now(timezone.utc).isoformat()
            shift = self.work_shift(time_current=datetime.now(timezone.utc))
            payload = {
                "timestamp": now,
                "device_id": device_id,
                "status": status
            }
            self.redis_client.hset("alarm", device_id, json.dumps(payload))
            # record to clickhouse
            self.insert_clickhouse_alarm(shift,device_id,status)
        except Exception as e:
            logging.error(f"Error Redis alarm: {e}")

    def check_device(self):
        while True:
            try:
                all_devices = self.redis_client.hgetall("devices")
                now = datetime.now(timezone.utc)
                devices_status = {}
                
                for device_id in self.device_list:
                    payload = all_devices.get(device_id)

                    if payload:
                        payload_dict = json.loads(payload)
                        last_seen = datetime.fromisoformat(payload_dict['timestamp'])
                        time_diff = (now - last_seen).total_seconds()
                        status = "online" if time_diff <= (self.device_loop+30) else "offline"
                        if status == "online":
                            broker = payload_dict.get("broker")
                            modbus = payload_dict.get("modbus")
                            mac_id = payload_dict.get("mac_id")
                        else:
                            broker, modbus, mac_id = "0", "0", "-"
                    else:
                        status = "offline"
                        broker, modbus, mac_id = "0", "0", "-"

                    devices_status[device_id] = status
                    
                    shift = self.work_shift(time_current=now)
                    # record to clickhouse
                    self.insert_clickhouse_device(status,shift,device_id,broker,modbus,mac_id)

                self.redis_client.set("device_all", json.dumps(devices_status))

            except Exception as e:
                logging.error(f"Error check_device: {e}")
            time.sleep(self.device_loop)

    def insert_clickhouse_device(self,status,shift,device_id,broker,modbus,mac_id):
        data = [[status,shift, device_id, broker, modbus, mac_id]]
        self.clickhouse_client.insert('device_tb', data, 
            column_names=['status','shift', 'device_id', 'broker', 'modbus', 'mac_id'])
        
    def insert_clickhouse_status(self,shift,device_id,status):
        data = [[shift, device_id, status]]
        self.clickhouse_client.insert('status_raw_tb', data, 
            column_names=['shift', 'device_id', 'status'])
        
    def insert_clickhouse_alarm(self,shift,device_id,status):
        data = [[shift, device_id, status]]
        self.clickhouse_client.insert('alarm_raw_tb', data, 
            column_names=['shift', 'device_id', 'status'])

    def work_shift(self,time_current):
        thai_now = time_current.astimezone(ZoneInfo("Asia/Bangkok"))
        hour = thai_now.hour
        if 7 <= hour < 19:
            shift = "M"
        else:
            shift = "N"
        return shift
    
async def main():
    mqtt_client = MqttToRedis()
    await mqtt_client.start()
        
if __name__ == "__main__":
    asyncio.run(main())