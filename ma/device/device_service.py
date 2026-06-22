from gmqtt import Client as MQTTClient
import os, asyncio, json, logging
import dotenv
from datetime import datetime, timezone
import redis
from threading import Thread
from queue import Queue
import time
import psycopg2
from zoneinfo import ZoneInfo

class MqttToRedis:
    def __init__(self):
        dotenv.load_dotenv()

        self.redis_client = redis.Redis(host= os.environ["REDIS_HOST"], port=6379, decode_responses=True)

        self.db_conn = psycopg2.connect(host=os.environ["POSTGRES_HOST"],
                                         database=os.environ["POSTGRES_DB"],
                                           user=os.environ["POSTGRES_USER"],
                                             password=os.environ["POSTGRES_PASSWORD"],
                                             port=int(os.environ["POSTGRES_PORT"]))
        self.db_conn.autocommit = True

        self.client = MQTTClient(os.environ["DEVICE_CLIENT"])
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.mqtt_broker = os.environ["MQTT_BROKER"]
        self.mqtt_port = int(os.environ["MQTT_PORT"])   

        self.device_list = os.environ["DEVICE_LIST"].split(',')
        self.device_loop = int(os.environ["DEVICE_LOOP"])  

        self.queue = Queue(maxsize=500000)
        Thread(target=self.device_to_redis, daemon=True).start()
        Thread(target=self.check_device, daemon=True).start()

        logging.basicConfig(
            filename='log/device.log', level=logging.WARNING,
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
                self.redis_client.hset("devices_list", device_id, json.dumps(payload))

            except Exception as e:
                logging.error(f"Error Redis: {e}")
            finally:
                self.queue.task_done()
    
    def check_device(self):
        while True:
            try:
                all_devices = self.redis_client.hgetall("devices_list")
                now = datetime.now(timezone.utc)
                devices_status = {}
                
                for device_id in self.device_list:
                    payload = all_devices.get(device_id)

                    if payload:
                        payload_dict = json.loads(payload)
                        last_seen = datetime.fromisoformat(payload_dict['timestamp'])
                        time_diff = (now - last_seen).total_seconds()
                        status = "online" if time_diff <= self.device_loop else "offline"
                        broker = payload_dict.get("broker")
                        modbus = payload_dict.get("modbus")
                        mac_id = payload_dict.get("mac_id")
                    else:
                        status = "offline"
                        broker, modbus, mac_id = 0, 0, "-"

                    devices_status[device_id] = status
                    
                    shift = self.work_shift(time_current=now)
                    # record to postgres
                    self.insert_postgres(shift,device_id,broker,modbus,mac_id)

                self.redis_client.set("device_status", json.dumps(devices_status))

            except Exception as e:
                logging.error(f"Error check_device: {e}")
            time.sleep(self.device_loop)

    def insert_postgres(self,shift,device_id,broker,modbus,mac_id):
        cursor = self.db_conn.cursor()
        query = """INSERT INTO device_tb (shift,device_id, broker, modbus,mac_id) VALUES (%s,%s,%s, %s, %s)"""
        cursor.execute(query, (shift,device_id, broker, modbus,mac_id))
        cursor.close()

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