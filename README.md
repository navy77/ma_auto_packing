version 1.0.0\
docker compose build --no-cache\
dd

for export image\
docker save --output ma_auto_packing.tar mic/mms_auto_packing:1.0.0

for import image\
docker load -i ma_auto_packing_100.tar