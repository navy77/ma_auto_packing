from fastapi import APIRouter,HTTPException
from database import client
from datetime import datetime, timedelta
from collections import defaultdict
from datetime import datetime
import pandas as pd 
import calendar

router = APIRouter()

# get current status 
@router.get("/current/{mc}")
def get_current_status_by_mc(mc:str):
    query = """SELECT ts,shift,device_id,status FROM default.status_tb  
    WHERE device_id = %(mc)s ORDER BY ts DESC LIMIT 1"""
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
@router.get("/ratio-daily/{mc}")
def get_status_ratio_daily_by_mc(mc:str):
    now = datetime.now()
    if now.hour < 7:
        start_date = (now - timedelta(days=1)).replace(hour=7, minute=0, second=0)
    else:
        start_date = now.replace(hour=7, minute=0, second=0)
    
    start = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end = now.strftime("%Y-%m-%d %H:%M:%S")
    
    query_1 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts < %(start)s ORDER BY ts DESC LIMIT 1"""

    query_2 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts BETWEEN %(start)s AND %(end)s ORDER BY ts ASC"""
  
    try:
        params = {'mc': mc, 'start': start, 'end': end}
        result_1 = client.query(query_1, params)
        result_2 = client.query(query_2, params)

        df1 = pd.DataFrame(result_1.result_rows, columns=result_1.column_names)
        df2 = pd.DataFrame(result_2.result_rows, columns=result_2.column_names)
        if df2.empty:
            master_data = [{"ts":start,"shift":"M","device_id":mc,"status":"NO DATA"}]
            df2 = pd.DataFrame(master_data)
            if df1.empty: # no data before / after
                df = df2
            else: # has data before no data after
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start
                df = df1
        else:
            if df1.empty:
                df1 = df2.head(1)
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start
                df1['status'] = "NO DATA"
            else:
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start

            df = pd.concat([df1, df2], ignore_index=True)

        if df.empty:
            raise HTTPException(status_code=400, detail="Item not found")
        else:
            df = df.sort_values(['ts'])
            df['next_ts'] = df['ts'].shift(-1)
            df['next_ts'] = df['next_ts'].fillna(pd.to_datetime(end))

            df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds()).round(0)
            df = df.groupby(['status'])['duration'].sum().reset_index()
            
            # find ratio %
            df = df.groupby(['status'])['duration'].sum().reset_index()
            total_duration = df['duration'].sum()
            df['ratio'] = ((df['duration'] / total_duration) * 100).round(0)

            df['status'] = df['status'].str.upper()

            return df.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# get status ratio monthly
@router.get("/ratio-monthly/{mc}")
def get_status_ratio_monthly_by_mc(mc: str):
    result_data = []
    # find end month
    year = datetime.now().year
    month = datetime.now().month
    last_day = calendar.monthrange(year,month )[1]

    query_1 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts < %(start)s ORDER BY ts DESC LIMIT 1"""

    query_2 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts BETWEEN %(start)s AND %(end)s ORDER BY ts ASC"""
    
    base = datetime(year, month, 1, 7, 0, 0)
    try:
        for i in range(0,(last_day-1)):
            start = base + timedelta(days=i)
            end = start + timedelta(days=1) - timedelta(seconds=1)
            params = {'mc': mc, 'start': start, 'end': end}
            result_1 = client.query(query_1, params)
            result_2 = client.query(query_2, params)
            df1 = pd.DataFrame(result_1.result_rows, columns=result_1.column_names)
            df2 = pd.DataFrame(result_2.result_rows, columns=result_2.column_names)

            if df2.empty:
                master_data = [{"ts":start,"shift":"M","device_id":mc,"status":"NO DATA"}]
                df_raw = pd.DataFrame(master_data)
                if df1.empty: # no data before / after
                    df_raw = df_raw
                else: # has data before/ no data after
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start
                    df_raw = df1
            else:
                if df1.empty:
                    df1 = df2.head(1)
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start
                    df1['status'] = "NO DATA"
                else:
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start

                df_raw = pd.concat([df1, df2], ignore_index=True)

            result_data.append(df_raw)
        df = pd.concat(result_data, ignore_index=True)

        if df.empty:
            raise HTTPException(status_code=400, detail="Item not found")
        else:
            df = df.sort_values(['ts'])

            all_days = pd.date_range(start=f"{year}-{month:02d}-01", end=f"{year}-{month:02d}-{last_day}")
            df['ts'] = pd.to_datetime(df['ts'])

            df['date_shift'] = (df['ts'] - timedelta(hours=7)).dt.strftime('%Y-%m-%d')
            df['next_ts'] = df['ts'].shift(-1).fillna(pd.to_datetime(end))
            df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds() / 60.).round(0)
            df['status'] = df['status'].str.upper()

            daily_summary = df.groupby(['date_shift', 'status'])['duration'].sum().reset_index()

            result_data = []
            for d in all_days:
                date_str = d.strftime('%Y-%m-%d')
                day_data = daily_summary[daily_summary['date_shift'] == date_str]
                total_d = day_data['duration'].sum()
                total_nodata_duration = day_data.loc[day_data["status"] == "NO DATA","duration"].sum()

                details = []
                if total_nodata_duration < 1440 and total_d > 0:
                    day_data = day_data.copy()
                    day_data['ratio'] = (day_data['duration'] / total_d * 100).round(0)
                    details = day_data[['status', 'duration', 'ratio']].to_dict(orient='records')
                    
                result_data.append({
                    "date": date_str,
                    "details": details
                })
                
            return {"daily_data": result_data}

    except Exception as e:
        return {"error": str(e)}
    
# get status ratio shift monthly
@router.get("/ratio-monthly/{mc}/{shift}/{status}")
def get_status_ratio_shift_monthly_by_mc(mc: str, shift: str,status: str):
    result_data = []
  # find end month
    year = datetime.now().year
    month = datetime.now().month
    last_day = calendar.monthrange(year,month )[1]

    query_1 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts < %(start)s ORDER BY ts DESC LIMIT 1"""

    query_2 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts BETWEEN %(start)s AND %(end)s ORDER BY ts ASC"""
    
    base = datetime(year, month, 1, 7, 0, 0)
    try:
        for i in range(0,(last_day)):
            start = base + timedelta(days=i)
            end = start + timedelta(days=1) - timedelta(seconds=1)
            params = {'mc': mc, 'start': start, 'end': end}
            result_1 = client.query(query_1, params)
            result_2 = client.query(query_2, params)
            df1 = pd.DataFrame(result_1.result_rows, columns=result_1.column_names)
            df2 = pd.DataFrame(result_2.result_rows, columns=result_2.column_names)

            if df2.empty:
                master_data = [{"ts":start,"shift":"M","device_id":mc,"status":"NO DATA"}]
                df_raw = pd.DataFrame(master_data)
                if df1.empty: # no data before / after
                    df_raw = df_raw
                else: # has data before/ no data after
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start
                    df_raw = df1
            else:
                if df1.empty:
                    df1 = df2.head(1)
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start
                    df1['status'] = "NO DATA"
                else:
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start

                df_raw = pd.concat([df1, df2], ignore_index=True)

            result_data.append(df_raw)
        df = pd.concat(result_data, ignore_index=True)
        
        if df.empty:
            raise HTTPException(status_code=400, detail="Item not found")
        else:
            df = df.sort_values(['ts'])
            df['next_ts'] = df['ts'].shift(-1)
            df['next_ts'] = df['ts'].shift(-1).fillna(pd.to_datetime(end))
            df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds()).round(0)
            df = df[df['shift'] == shift].copy()
            
            df['date_shifted'] = (df['ts'] - timedelta(hours=7)).dt.strftime('%Y-%m-%d')
            df['status'] = df['status'].str.upper()
            
            daily_summary = df.groupby(['date_shifted', 'status'])['duration'].sum().reset_index()

            all_days = pd.date_range(start=f"{year}-{month:02d}-01", end=f"{year}-{month:02d}-{last_day}")
            result_data = []
            for d in all_days:
                date_str = d.strftime('%Y-%m-%d')
                day_data = daily_summary[daily_summary['date_shifted'] == date_str]
                total_d = day_data['duration'].sum()

                details = []
                if total_d > 0:
                    day_data = day_data.copy()
                    day_data['ratio'] = (day_data['duration'] / total_d * 100).round(0)

                    day_data = day_data[day_data["status"] == status]
                    
                    details = day_data[['status', 'duration', 'ratio']].to_dict(orient='records')
                
                result_data.append({
                    "date": date_str,
                    "details": details
                })
                
            return {"shift": shift, "daily_data": result_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/timeline/{mc}")
def get_timeline_data(mc: str):
    now = datetime.now()
    if now.hour < 7:
        start_date = (now - timedelta(days=1)).replace(hour=7, minute=0, second=0)
    else:
        start_date = now.replace(hour=7, minute=0, second=0)

    start = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end = now.strftime("%Y-%m-%d %H:%M:%S")

    query_1 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts < %(start)s ORDER BY ts DESC LIMIT 1"""

    query_2 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts BETWEEN %(start)s AND %(end)s ORDER BY ts ASC"""

    try:
        params = {'mc': mc, 'start': start, 'end': end}
        result_1 = client.query(query_1, params)
        result_2 = client.query(query_2, params)

        df1 = pd.DataFrame(result_1.result_rows, columns=result_1.column_names)
        df2 = pd.DataFrame(result_2.result_rows, columns=result_2.column_names)
        if df2.empty:
            master_data = [{"ts":start,"shift":"M","device_id":mc,"status":"NO DATA"}]
            df2 = pd.DataFrame(master_data)
            if df1.empty: # no data before / after
                df = df2
            else: # has data before no data after
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start
                df = df1
        else:
            if df1.empty:
                df1 = df2.head(1)
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start
                df1['status'] = "NO DATA"
            else:
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start

            df = pd.concat([df1, df2], ignore_index=True)

        if df.empty:
            raise HTTPException(status_code=400, detail="Item not found")
        else:
            df = df.sort_values(['ts'])
            df['next_ts'] = df['ts'].shift(-1)
            df['next_ts'] = df['next_ts'].fillna(pd.to_datetime(end))

            df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds()).round(0)
            df['status'] = df['status'].str.upper()
            df = df[['ts', 'status', 'duration']]

            return df.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )