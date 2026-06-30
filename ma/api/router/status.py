from fastapi import APIRouter,HTTPException
from database import get_db_client
from datetime import datetime, timedelta, timezone
import pandas as pd 
import calendar

router = APIRouter()

# get current status 
@router.get("/current/{mc}")
def get_current_status_by_mc(mc:str):
    client = get_db_client()
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
    finally:
        client.close()
    
# get status ratio daily
@router.get("/ratio-daily/{mc}")
def get_status_ratio_daily_by_mc(mc:str):
    client = get_db_client()
    bangkok_tz = timezone(timedelta(hours=7))
    now = datetime.now(bangkok_tz)
    if now.hour < 7:
        start_date = (now - timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
    else:
        start_date = now.replace(hour=7, minute=0, second=0, microsecond=0)
    
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
                df1['shift'] = "M"
                df = df1
        else:
            if df1.empty:
                df1 = df2.head(1).copy()
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start
                df1['status'] = "NO DATA"
                df1['shift'] = "M"
            else:
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start
                df1['shift'] = "M"

            df = pd.concat([df1, df2], ignore_index=True)

        if df.empty:
            raise HTTPException(status_code=400, detail="Item not found")
        else:
            df = df.sort_values(['ts'])
            df['next_ts'] = df['ts'].shift(-1)
            df['next_ts'] = df['next_ts'].fillna(pd.to_datetime(end))

            df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds()).round(1)
            df = df.groupby(['status'])['duration'].sum().reset_index()
            
            # find ratio %
            df = df.groupby(['status'])['duration'].sum().reset_index()
            total_duration = df['duration'].sum()
            df['ratio'] = ((df['duration'] / total_duration) * 100).round(1)

            df['status'] = df['status'].str.upper()

            return df.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()

# get status ratio monthly
@router.get("/ratio-monthly/{mc}")
def get_status_ratio_monthly_by_mc(mc: str):
    client = get_db_client()
    result_data = []
    # find end month
    bangkok_tz = timezone(timedelta(hours=7))
    now = datetime.now(bangkok_tz)
    
    if now.hour < 7:
        shift_date = now - timedelta(days=1)
    else:
        shift_date = now
        
    year = shift_date.year
    month = shift_date.month
    last_day = calendar.monthrange(year,month )[1]
    
    today_shift_start = shift_date.replace(hour=7, minute=0, second=0, microsecond=0)

    query_1 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts < %(start)s ORDER BY ts DESC LIMIT 1"""

    query_2 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts BETWEEN %(start)s AND %(end)s ORDER BY ts ASC"""
    
    base = datetime(year, month, 1, 7, 0, 0, tzinfo=bangkok_tz)
    try:
        now_naive = now.replace(tzinfo=None)
        for i in range(0, last_day):
            start = (base + timedelta(days=i)).replace(tzinfo=None)
            if start.date() >= now_naive.date():
                break
            end_of_day = start + timedelta(days=1) - timedelta(seconds=1)
            end = min(end_of_day, now_naive)
            print(end)
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
                    df1['shift'] = "M"
                    df_raw = df1
            else:
                if df1.empty:
                    df1 = df2.head(1).copy()
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start
                    df1['status'] = "NO DATA"
                    df1['shift'] = "M"
                else:
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start
                    df1['shift'] = "M"

                df_raw = pd.concat([df1, df2], ignore_index=True)

            result_data.append(df_raw)
            
        if not result_data:
            df = pd.DataFrame(columns=['ts', 'shift', 'device_id', 'status'])
        else:
            df = pd.concat(result_data, ignore_index=True)

        all_days = pd.date_range(start=f"{year}-{month:02d}-01", end=f"{year}-{month:02d}-{last_day}")

        if df.empty:
            result_data = []
            for d in all_days:
                date_str = d.strftime('%Y-%m-%d')
                result_data.append({
                    "date": date_str,
                    "details": []
                })
            return {"daily_data": result_data}
        else:
            df = df.sort_values(['ts'])
            df['ts'] = pd.to_datetime(df['ts'])

            df['date_shift'] = (df['ts'] - timedelta(hours=7)).dt.strftime('%Y-%m-%d')
            df['next_ts'] = df['ts'].shift(-1).fillna(pd.to_datetime(end))
            df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds() / 60.).round(1)
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
                    day_data['ratio'] = (day_data['duration'] / total_d * 100).round(1)
                    details = day_data[['status', 'duration', 'ratio']].to_dict(orient='records')
                    
                result_data.append({
                    "date": date_str,
                    "details": details
                })
                
            return {"daily_data": result_data}

    except Exception as e:
        return {"error": str(e)}
    finally:
        client.close()
    
# get status ratio shift monthly
@router.get("/ratio-monthly/{mc}/{shift}/{status}")
def get_status_ratio_shift_monthly_by_mc(mc: str, shift: str,status: str):
    client = get_db_client()
    result_data = []
    # find end month
    bangkok_tz = timezone(timedelta(hours=7))
    now = datetime.now(bangkok_tz)
    
    if now.hour < 7:
        shift_date = now - timedelta(days=1)
    else:
        shift_date = now
        
    year = shift_date.year
    month = shift_date.month
    last_day = calendar.monthrange(year,month )[1]
    
    today_shift_start = shift_date.replace(hour=7, minute=0, second=0, microsecond=0)

    query_1 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts < %(start)s ORDER BY ts DESC LIMIT 1"""

    query_2 = """SELECT ts, shift, device_id, status FROM default.status_tb WHERE device_id = %(mc)s
        AND ts BETWEEN %(start)s AND %(end)s ORDER BY ts ASC"""
    
    base = datetime(year, month, 1, 7, 0, 0, tzinfo=bangkok_tz)
    try:
        now_naive = now.replace(tzinfo=None)
        for i in range(0, last_day):
            start = (base + timedelta(days=i)).replace(tzinfo=None)
            if start.date() >= now_naive.date():
                break
            end_of_day = start + timedelta(days=1) - timedelta(seconds=1)
            end = min(end_of_day, now_naive)
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
                    df1['shift'] = "M"
                    df_raw = df1
            else:
                if df1.empty:
                    df1 = df2.head(1).copy()
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start
                    df1['status'] = "NO DATA"
                    df1['shift'] = "M"
                else:
                    df1['ts'] = pd.to_datetime(df1['ts'])
                    start = pd.to_datetime(start)
                    df1['ts'] = start
                    df1['shift'] = "M"

                df_raw = pd.concat([df1, df2], ignore_index=True)

            result_data.append(df_raw)
            
        if not result_data:
            df = pd.DataFrame(columns=['ts', 'shift', 'device_id', 'status'])
        else:
            df = pd.concat(result_data, ignore_index=True)
        
        all_days = pd.date_range(start=f"{year}-{month:02d}-01", end=f"{year}-{month:02d}-{last_day}")
        
        if df.empty:
            result_data = []
            for d in all_days:
                date_str = d.strftime('%Y-%m-%d')
                result_data.append({
                    "date": date_str,
                    "details": []
                })
            return {"shift": shift, "daily_data": result_data}
        else:
            df = df.sort_values(['ts'])
            df['next_ts'] = df['ts'].shift(-1)
            df['next_ts'] = df['ts'].shift(-1).fillna(pd.to_datetime(end))
            df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds()).round(1)
            df = df[df['shift'] == shift].copy()
            
            df['date_shifted'] = (df['ts'] - timedelta(hours=7)).dt.strftime('%Y-%m-%d')
            df['status'] = df['status'].str.upper()
            
            daily_summary = df.groupby(['date_shifted', 'status'])['duration'].sum().reset_index()

            result_data = []
            for d in all_days:
                date_str = d.strftime('%Y-%m-%d')
                day_data = daily_summary[daily_summary['date_shifted'] == date_str]
                total_d = day_data['duration'].sum()

                details = []
                if total_d > 0:
                    day_data = day_data.copy()
                    day_data['ratio'] = (day_data['duration'] / total_d * 100).round(1)

                    day_data = day_data[day_data["status"] == status]
                    
                    details = day_data[['status', 'duration', 'ratio']].to_dict(orient='records')
                
                result_data.append({
                    "date": date_str,
                    "details": details
                })
                
            return {"shift": shift, "daily_data": result_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()
    
@router.get("/timeline/{mc}")
def get_timeline_data(mc: str):
    client = get_db_client()
    bangkok_tz = timezone(timedelta(hours=7))
    now = datetime.now(bangkok_tz)
    if now.hour < 7:
        start_date = (now - timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
    else:
        start_date = now.replace(hour=7, minute=0, second=0, microsecond=0)

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
                df1['shift'] = "M"
                df = df1
        else:
            if df1.empty:
                df1 = df2.head(1).copy()
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start
                df1['status'] = "NO DATA"
                df1['shift'] = "M"
            else:
                df1['ts'] = pd.to_datetime(df1['ts'])
                start = pd.to_datetime(start)
                df1['ts'] = start
                df1['shift'] = "M"

            df = pd.concat([df1, df2], ignore_index=True)

        if df.empty:
            raise HTTPException(status_code=400, detail="Item not found")
        else:
            df = df.sort_values(['ts'])
            df['next_ts'] = df['ts'].shift(-1)
            df['next_ts'] = df['next_ts'].fillna(pd.to_datetime(end))

            df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds()).round(1)
            df['status'] = df['status'].str.upper()
            df = df[['ts', 'status', 'duration']]

            return df.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    finally:
        client.close()