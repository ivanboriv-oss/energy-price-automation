import requests
import xml.etree.ElementTree as ET
import re
import json
import time
from datetime import datetime, timedelta, timezone

# System config
ENTSOE_TOKEN = "YOUR_ENTSOE_TOKEN"
PRICE_THRESHOLD = 15  # Threshold in EUR. 

# Huawei FusionSolar config
HUAWEI_API_URL = "https://eu5.fusionsolar.huawei.com"
HUAWEI_USER = "YOUR_EMAIL@DOMAIN.COM"
HUAWEI_PASS = "YOUR_PASSWORD"
PLANT_CODE = "YOUR_PLANT_CODE"


def get_today_prices():
    """Fetch prices from ENTSO-E and return as dict { 'HH:MM': price }"""
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc.strftime('%Y%m%d0000')
    end_time = (now_utc + timedelta(days=1)).strftime('%Y%m%d0000')
    
    url = "https://web-api.tp.entsoe.eu/api"
    params = {
        'securityToken': ENTSOE_TOKEN,
        'documentType': 'A44',
        'in_Domain': '10YCA-BULGARIA-R',
        'out_Domain': '10YCA-BULGARIA-R',
        'periodStart': start_time,
        'periodEnd': end_time
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        prices_dict = {}
        
        if response.status_code == 200:
            xml_text = re.sub(r'\sxmlns="[^"]+"', '', response.text)
            root = ET.fromstring(xml_text)
            for point in root.findall('.//Point'):
                position = int(point.find('position').text)
                price = float(point.find('price.amount').text)
                
                total_minutes = (position - 1) * 15
                hour = total_minutes // 60
                minute = total_minutes % 60
                prices_dict[f"{hour:02d}:{minute:02d}"] = price
        return prices_dict
    except Exception as e:
        # TODO: maybe replace print statements with a proper logging module in the future
        print(f"Error connecting to ENTSO-E: {e}")
        return None

def set_huawei_power(limit_percentage):
    """Login to FusionSolar and send active power control command"""
    login_url = f"{HUAWEI_API_URL}/thirdData/login"
    control_url = f"{HUAWEI_API_URL}/thirdData/activePowerControl"
    
    # 1. Get token
    login_payload = {"userName": HUAWEI_USER, "systemCode": HUAWEI_PASS}
    headers = {"Content-Type": "application/json"}
    
    try:
        session = requests.Session()
        login_res = session.post(login_url, json=login_payload, headers=headers, timeout=10)
        
        if login_res.status_code == 200:
            token = login_res.headers.get('xsrf-token')
            if not token:
                print("ERROR: Login successful, but xsrf-token is missing.")
                return False
            
            # 2. Send command
            control_payload = {
                "stationCode": PLANT_CODE,
                "controlValue": int(limit_percentage * 10) # 100% = 1000
            }
            control_headers = {
                "Content-Type": "application/json",
                "xsrf-token": token
            }
            
            control_res = session.post(control_url, json=control_payload, headers=control_headers, timeout=10)
            
            if control_res.status_code == 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS: Command for {limit_percentage}% accepted by cloud.")
                return True
            else:
                print(f"Control error: {control_res.text}")
                return False
        else:
            print(f"Huawei login error: {login_res.text}")
            return False
            
    except Exception as e:
        print(f"Network error communicating with Huawei: {e}")
        return False


def run_automation():
    print("Starting automation loop...")
    
    while True:
        now_local = datetime.now()
        
        # Calculate seconds until next 15-min interval (XX:00, XX:15, XX:30, XX:45)
        minutes_to_next = 15 - (now_local.minute % 15)
        seconds_to_wait = (minutes_to_next * 60) - now_local.second
        
        # Add a 5-second buffer to ensure the exchange and servers have updated their data
        seconds_to_wait += 5 
        
        next_run_time = now_local + timedelta(seconds=seconds_to_wait)
        print(f"\nNext check at: {next_run_time.strftime('%H:%M:%S')}. Sleeping...")
        
        time.sleep(seconds_to_wait)
        
        print(f"\n--- CHECK [{datetime.now().strftime('%H:%M:%S')}] ---")
        now_utc = datetime.now(timezone.utc)
        current_minute = (now_utc.minute // 15) * 15
        current_time_key = f"{now_utc.hour:02d}:{current_minute:02d}"
        
        prices = get_today_prices()
        
        if prices and current_time_key in prices:
            current_price = prices[current_time_key]
            print(f"UTC Time: {current_time_key} | Current price: {current_price} EUR/MWh")
            
            if current_price <= PRICE_THRESHOLD:
                print(">> Price is below threshold! Sending command: 0% power.")
                set_huawei_power(0)
            else:
                print(">> Price is good. Sending command: 100% power.")
                set_huawei_power(100)
        else:
            print("Warning: Failed to read price for current interval. Plant stays in current state.")

if __name__ == "__main__":
    # Initial check before entering sleep loop
    prices_test = get_today_prices()
    if prices_test:
        print("Initial ENTSO-E connection successful.")
    else:
        print("Problem connecting to ENTSO-E on startup.")
        
    run_automation()