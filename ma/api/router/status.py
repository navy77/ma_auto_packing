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

    query = """SELECT ts,shift,device_id,status FROM default.status_tb WHERE device_id = %(mc)s 
    AND  ts BETWEEN %(start)s AND %(end)s ORDER BY ts ASC"""

    try:
        params = {'mc': mc, 'start': start, 'end': end}
        result = client.query(query, params)
        df_status = pd.DataFrame(result.result_rows, columns=result.column_names)

        df_status = df_status.sort_values(['ts'])
        df_status['next_ts'] = df_status['ts'].shift(-1)
        df_status['next_ts'] = df_status['next_ts'].fillna(pd.to_datetime(end))

        df_status['duration'] = ((df_status['next_ts'] - df_status['ts']).dt.total_seconds()).round(0)
        df = df_status.groupby(['status'])['duration'].sum().reset_index()
        # find ratio %
        df = df.groupby(['status'])['duration'].sum().reset_index()
        total_duration = df['duration'].sum()
        df['ratio'] = ((df['duration'] / total_duration) * 100).round(0)

        if not df.empty:
            return df.to_dict(orient="records")
        else:
            raise HTTPException(status_code=400, detail="Item not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# get status ratio monthly
@router.get("/ratio-monthly/{mc}")
def get_status_ratio_monthly_by_mc(mc: str):
    
    # find end month
    year = datetime.now().year
    month = datetime.now().month
    last_day = calendar.monthrange(year,month )[1]

    start = datetime.now().strftime("%Y-%m-01 07:00:00")
    end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    query = """SELECT ts, status FROM default.status_tb 
               WHERE device_id = %(mc)s AND  ts BETWEEN %(start)s AND %(end)s
               ORDER BY ts ASC"""
    
    try:
        params = {'mc': mc, 'start': start, 'end': end}
        result = client.query(query, params)
        df = pd.DataFrame(result.result_rows, columns=result.column_names)

        all_days = pd.date_range(start=f"{year}-{month:02d}-01", end=f"{year}-{month:02d}-{last_day}")

        df['ts'] = pd.to_datetime(df['ts'])
        df['date_shift'] = (df['ts'] - timedelta(hours=7)).dt.strftime('%Y-%m-%d')
        df['next_ts'] = df['ts'].shift(-1).fillna(pd.to_datetime(end))
        df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds() / 60.).round(0)

        # df['date'] = df['ts'].dt.strftime('%Y-%m-%d')
        
        # daily_summary = df.groupby(['date', 'status'])['duration'].sum().reset_index()
        daily_summary = df.groupby(['date_shift', 'status'])['duration'].sum().reset_index()

        result_data = []
        for d in all_days:
            date_str = d.strftime('%Y-%m-%d')
            day_data = daily_summary[daily_summary['date_shift'] == date_str]
            # day_data = daily_summary[daily_summary['date'] == date_str]
            
            total_d = day_data['duration'].sum()
    
            details = []
            if total_d > 0:
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
    
# get status count daily
@router.get("/count-daily/{mc}")
def get_status_count_daily_by_mc(mc:str):
    now = datetime.now()
    if now.hour < 7:
        start_date = (now - timedelta(days=1)).replace(hour=7, minute=0, second=0)
    else:
        start_date = now.replace(hour=7, minute=0, second=0)
    
    start = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end = now.strftime("%Y-%m-%d %H:%M:%S")

    query = """SELECT ts,shift,device_id,status FROM default.status_tb WHERE device_id = %(mc)s AND  
    ts BETWEEN %(start)s AND %(end)s ORDER BY ts ASC"""

    try:
        params = {'mc': mc, 'start': start, 'end': end}
        result = client.query(query, params)
        df_status = pd.DataFrame(result.result_rows, columns=result.column_names)
        if df_status.empty:
            raise HTTPException(status_code=400, detail="Item not found")
        
        df = df_status.groupby('status').size().reset_index(name='count')

        # find ratio %
        total_count = df['count'].sum()
        df['ratio'] = ((df['count'] / total_count) * 100).round(0)

        if not df.empty:
            return df.to_dict(orient="records")
        else:
            raise HTTPException(status_code=400, detail="Item not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# get status count monthly
@router.get("/count-monthly/{mc}")
def get_status_count_monthly_by_mc(mc: str):
    
    # find end month
    year = datetime.now().year
    month = datetime.now().month
    last_day = calendar.monthrange(year,month )[1]

    start = datetime.now().strftime("%Y-%m-01 07:00:00")
    end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    query = """SELECT ts, status FROM default.status_tb 
               WHERE device_id = %(mc)s AND  ts BETWEEN %(start)s AND %(end)s
               ORDER BY ts ASC"""
    
    try:
        params = {'mc': mc, 'start': start, 'end': end}
        result = client.query(query, params)
        df_status = pd.DataFrame(result.result_rows, columns=result.column_names)
        if df_status.empty:
            raise HTTPException(status_code=400, detail="Item not found")
        
        df_status['ts'] = pd.to_datetime(df_status['ts'])
        df_status['date_shift'] = (df_status['ts'] - timedelta(hours=7)).dt.strftime('%Y-%m-%d')

        # df_status['date'] = df_status['ts'].dt.strftime('%Y-%m-%d')

        daily_counts = df_status.groupby(['date_shift', 'status']).size().reset_index(name='count')

        all_days = pd.date_range(start=f"{year}-{month:02d}-01", end=f"{year}-{month:02d}-{last_day}")
        
        result_data = []
        for d in all_days:
            date_str = d.strftime('%Y-%m-%d')
            day_data = daily_counts[daily_counts['date_shift'] == date_str]
            
            total_count_day = day_data['count'].sum()
    
            details = []
            if total_count_day > 0:
                day_data = day_data.copy()
                day_data['ratio'] = (day_data['count'] / total_count_day * 100).round(0)
                details = day_data[['status', 'count', 'ratio']].to_dict(orient='records')
            
            result_data.append({
                "date": date_str,
                "details": details
            })
            
        return {"daily_data": result_data}
    except Exception as e:
        return {"error": str(e)}

# get status ratio shift monthly
@router.get("/ratio-monthly/{mc}/{shift}")
def get_status_ratio_shift_monthly_by_mc(mc: str, shift: str):

    now = datetime.now()
    year = now.year
    month = now.month
    last_day = calendar.monthrange(year, month)[1]

    start = datetime(year, month, 1, 7, 0, 0).strftime("%Y-%m-%d %H:%M:%S")
    end = now.strftime("%Y-%m-%d %H:%M:%S")

    query = """
        SELECT ts, status, shift 
        FROM default.status_tb 
        WHERE device_id = %(mc)s 
        AND ts BETWEEN %(start)s AND %(end)s 
        ORDER BY ts ASC
    """
    
    try:
        params = {'mc': mc, 'start': start, 'end': end}
        result = client.query(query, params)
        df = pd.DataFrame(result.result_rows, columns=result.column_names)
        
        if df.empty:
            raise HTTPException(status_code=400, detail="Item not found")
        

        df['ts'] = pd.to_datetime(df['ts'])
        df['next_ts'] = df['ts'].shift(-1).fillna(pd.to_datetime(end))
        df['duration'] = ((df['next_ts'] - df['ts']).dt.total_seconds() / 60.).round(0)
    
        df = df[df['shift'] == shift].copy()
        
        df['date_shifted'] = (df['ts'] - timedelta(hours=7)).dt.strftime('%Y-%m-%d')
        

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

    query = """SELECT ts,shift,device_id,status FROM default.status_tb WHERE device_id = %(mc)s 
    AND  ts BETWEEN %(start)s AND %(end)s ORDER BY ts ASC"""

    try:
        params = {'mc': mc, 'start': start, 'end': end}
        result = client.query(query, params)
        df_status = pd.DataFrame(result.result_rows, columns=result.column_names)

        df_status = df_status.sort_values(['ts'])
        df_status['next_ts'] = df_status['ts'].shift(-1)
        df_status['next_ts'] = df_status['next_ts'].fillna(pd.to_datetime(end))

        df_status['duration'] = ((df_status['next_ts'] - df_status['ts']).dt.total_seconds()).round(0)
        df_status = df_status[['ts', 'status', 'duration']]
    
        if not df_status.empty:
            return df_status.to_dict(orient="records")
        else:
            raise HTTPException(status_code=400, detail="Item not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
