## clone project
git clone https://github.com/navy77/ma_auto_packing.git

### api backend 
1. go to api directory
2. docker compose down -v
3. docker rmi mic/mms_api:1.0.0
4. docker build --no-cache -t mic/mms_api:1.0.0 . 
5. docker compose up -d

### frontend
1. go to frontend directory
2. docker compose down -v
3. docker rmi mic/mms_frontend:1.0.0
4. docker build --no-cache -t mic/mms_frontend:1.0.0 .
5. docker compose up -d




