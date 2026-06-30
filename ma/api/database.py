import os
import dotenv
from clickhouse_connect import get_client

dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file, override=True)

def get_db_client():
    return get_client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ["CLICKHOUSE_PORT"]),
        username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
        database=os.environ["CLICKHOUSE_DB"]
    )

