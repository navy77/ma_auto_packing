from fastapi import APIRouter,HTTPException
from database import client
from datetime import datetime
from collections import defaultdict
from datetime import datetime
import pandas as pd 

router = APIRouter()

# get current status 
@router.get("/current/{div}/{process}/{mc}")
def get_current_status_by_mc(div:str,process:str,mc:str):
    query = """SELECT ts,shift,device_id,status FROM (SELECT *, row_number() 
    OVER (PARTITION BY device_id ORDER BY ts DESC)AS rn FROM default.status_tb) 
    WHERE rn = 1 AND device_id = %(mc)s """
    try:
        result = client.query(query, {'mc': mc})
        rows = result.result_rows
        
        if not rows:
            raise HTTPException(status_code=404, detail="Data not found")

        column_names = result.column_names
        data = dict(zip(column_names, rows[0]))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# get status ratio daily
@router.get("/ratio/{div}/{process}/{mc}")
def get_status_ratio_by_mc(div:str,process:str,mc:str):
    start = datetime.now().strftime("%Y-%m-%d 07:00:00")
    end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    query = """SELECT ts,shift,device_id,status FROM default.status_tb WHERE device_id = %(mc)s AND  ts BETWEEN %(start)s AND %(end)s ORDER BY ts DESC"""

    try:
        params = {'mc': mc, 'start': start, 'end': end}
        result = client.query(query, params)
        rows = result.result_rows
        column_names = result.column_names
        status = [dict(zip(column_names, row)) for row in rows]
        df_status = pd.DataFrame(status)

        if not df_status.empty:
            df_status = df_status.sort_values(by='ts', ascending=False)
            # call summary
            result = status_summary_duration(df_status)
            return result.to_dict(orient="records")
        else:
            raise HTTPException(status_code=400, detail="Item not found")
        # if not rows:
        #     raise HTTPException(status_code=404, detail="Data not found")
        # column_names = result.column_names
    
        # data = [dict(zip(column_names, row)) for row in x]
        # return data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def calculate_summary_without_pandas(rows):
    # 1. จัดกลุ่มข้อมูลตาม date และ mc_no
    # โครงสร้าง: grouped_data[date][mc_no] = list_of_rows
    grouped_data = defaultdict(lambda: defaultdict(list))
    
    for row in rows:
        # สมมติลำดับคือ: ts(0), shift(1), device_id(2), status(3)
        ts, _, mc, status = row
        
        # ปรับ logic วันที่ (ถ้าชั่วโมง < 7 ให้เป็นวันก่อนหน้า)
        date = (ts if ts.hour >= 7 else ts - datetime.timedelta(days=1)).date()
        grouped_data[date][mc].append({'ts': ts, 'status': status})

    summary_results = []

    # 2. คำนวณ duration และ ratio
    for date, mcs in grouped_data.items():
        for mc, data in mcs.items():
            # เรียงลำดับตามเวลา
            data.sort(key=lambda x: x['ts'])
            
            # คำนวณความต่างเวลา (Duration)
            status_durations = defaultdict(float)
            for i in range(len(data) - 1):
                duration = (data[i+1]['ts'] - data[i]['ts']).total_seconds()
                status = data[i]['status']
                status_durations[status] += duration
            
            # คำนวณยอดรวมเพื่อหา Ratio
            total_duration = sum(status_durations.values())
            
            # 3. จัดรูปผลลัพธ์
            for status, duration in status_durations.items():
                ratio = round((duration / total_duration) * 100, 2) if total_duration > 0 else 0
                summary_results.append({
                    "date": str(date),
                    "mc_no": mc,
                    "status": status,
                    "duration": duration,
                    "ratio": ratio
                })
                
    return summary_results

def status_summary_duration(df):

    df['ts'] = pd.to_datetime(df['ts'])
    df['date'] = df['ts'].dt.date
    df['date'] = df['ts'].apply(lambda x: (x - pd.Timedelta(days=1)).date() if x.hour < 7 else x.date())
    df = df.sort_values(by=['device_id','ts'], ascending=[True,True])
    df['end'] = df.groupby(['date', 'device_id'])['ts'].shift(-1)
    df['duration'] = (df['end'] - df['ts']).dt.total_seconds()
    df.to_csv("df.csv",index =False)
    df = df.groupby(['date', 'device_id', 'status'], as_index=False)['duration'].sum()
    df = df[['date','device_id','status','duration']]
    # find ratio %
    df['ratio'] = df.groupby(['date', 'device_id'])['duration'].transform(lambda x: (x / x.sum()) * 100)
    df['ratio'] = df['ratio'].round(2)
    df.to_csv("df2.csv",index =False)

    return df