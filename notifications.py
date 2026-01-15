import traceback
import mysql.connector
from datetime import datetime, time, timedelta,date
import time as t  # <- renamed to avoid conflict
import requests
import smtplib
from email.mime.text import MIMEText
import pytz  # <- For timezone handling
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from twilio.rest import Client

# 🔥 Check if alarm already acknowledged by any user
def is_alarm_answered(cursor, alarm):
    cursor.execute("""
        SELECT COUNT(*)
        FROM iot_api_devicealarmcalllog
        WHERE DEVICE_ID=%s
          AND PARAMETER_ID=%s
          AND ALARM_DATE=%s
          AND CALL_STATUS='ANSWERED'
    """, (
        alarm["DEVICE_ID"],
        alarm["PARAMETER_ID"],
        alarm["ALARM_DATE"]
    ))
    row = cursor.fetchone()
    return list(row.values())[0] > 0


TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

twilio = Client(TWILIO_SID, TWILIO_TOKEN)

print("TWILIO_SID =", TWILIO_SID)
print("TWILIO_TOKEN =", TWILIO_TOKEN)
print("TWILIO_NUMBER =", TWILIO_NUMBER)



devid_for_sms = None
phone_numbers = ""
uni_phones =""
email_ids = ""
device_name =""
dev_reading =""
# ================== DATABASE CONFIG ==================#
db_config = {
    "host": "switchyard.proxy.rlwy.net",
    "user": "root",
    "port": 28085,
    "password": "NOtYUNawwodSrBfGubHhwKaFtWyGXQct",
    "database": "railway",
}

# ================== SMS CONFIG ==================
SMS_API_URL = "http://www.universalsmsadvertising.com/universalsmsapi.php"
SMS_USER = "8960853914"
SMS_PASS = "8960853914"
SENDER_ID = "FRTLLP"

# # ================== EMAIL CONFIG ==================
# SMTP_SERVER = "smtp.gmail.com"
# SMTP_PORT = 587
# EMAIL_USER = "testwebservice71@gmail.com"
# EMAIL_PASS = "akuu vulg ejlg ysbt"

# ================== TIMEZONE CONFIG ==================
TZ = pytz.timezone("Asia/Kolkata")  # Singapore timezone


def build_message(ntf_typ, devnm):
    messages = {
        1: f"WARNING!! The Temperature of {devnm} has dipped below the lower limit. Please take necessary action- Regards Fertisense LLP",
        2: f"WARNING!! The Temperature of {devnm} has crossed the higher limit. Please take necessary action- Regards Fertisense LLP",
        3: f"WARNING!! The {devnm} is offline. Please take necessary action- Regards Fertisense LLP",
        4: f"WARNING!! The level of liquid nitrogen in {devnm} is low. Please take necessary action- Regards Fertisense LLP",
        5: f"INFO!! The device {devnm} is back online. No action is required - Regards Fertisense LLP",
        6: f"INFO!! The level of Liquid Nitrogen is back to normal for {devnm}. No action is required - Regards Fertisense LLP",
        7: f"INFO!! The temperature levels are back to normal for {devnm}. No action is required - Regards Fertisense LLP",
        8: f"WARNING!! The room temperature reading in {devnm} has dipped below the lower limit. Please take necessary action- Regards Fertisense LLP",
        9: f"WARNING!! The room temperature reading in {devnm} has gone above the higher limit. Please take necessary action- Regards Fertisense LLP",
        10: f"INFO!! The room temperature levels are back to normal in {devnm}. No action is required - Regards Fertisense LLP",
        11: f"WARNING!! The humidity reading in {devnm} has dipped below the lower limit. Please take necessary action- Regards Fertisense LLP",
        12: f"WARNING!! The humidity reading in {devnm} has gone above the higher limit. Please take necessary action- Regards Fertisense LLP",
        13: f"INFO!! The humidity levels are back to normal in {devnm}. No action is required - Regards Fertisense LLP",
        14: f"WARNING!! The VOC reading in {devnm} has dipped below the lower limit. Please take necessary action- Regards Fertisense LLP",
        15: f"WARNING!! The VOC reading in {devnm} has gone above the higher limit. Please take necessary action- Regards Fertisense LLP",
        16: f"INFO!! The VOC levels are back to normal in {devnm}. No action is required - Regards Fertisense LLP",
        17: f"WARNING!! The CO2 reading in {devnm} has dipped below the lower limit. Please take necessary action - Regards Fertisense LLP",
        18: f"WARNING!! The CO2 reading in {devnm} has gone above the higher limit. Please take necessary action - Regards Fertisense LLP",
        19: f"INFO!! The CO2 levels are back to normal in {devnm}. No action is required - Regards Fertisense LLP",
        20: f"WARNING!! The O2 reading in {devnm} has dipped below the lower limit. Please take necessary action - Regards Fertisense LLP",
        21: f"WARNING!! The O2 reading in {devnm} has gone above the higher limit. Please take necessary action - Regards Fertisense LLP",
        22: f"INFO!! The O2 levels are back to normal in {devnm}. No action is required - Regards Fertisense LLP",
        23: f"WARNING!! The Incubator temperature of {devnm} has crossed the higher limit. Please take necessary action - Regards Fertisense LLP",
        24: f"WARNING!! The Incubator temperature of {devnm} has dipped below the lower limit. Please take necessary action - Regards Fertisense LLP",
        25: f"INFO!!  The Incubator temperature levels are back to normal for {devnm}. No action is required - Regards Fertisense LLP",
    }
    
    return messages.get(ntf_typ, f"Alert for {devnm} - Regards Fertisense LLP")
    

def send_sms(phone, message):
    print("🔹 Sending SMS...")
    try:
        params = {
            "user_name": SMS_USER,
            "user_password": SMS_PASS,
            "mobile": phone,
            "sender_id": SENDER_ID,
            "type": "F",
            "text": message
        }
        response = requests.get(SMS_API_URL, params=params)
        print("✅ SMS sent! Response:", response.text)
    except Exception as e:
        print("❌ SMS failed:", e)



def send_email_brevo(to_email, subject, html_content):
    print("📧 Sending Email via Brevo...")

    BREVO_API_KEY = os.getenv("BREVO_API_KEY")   # <--- NO HARD CODE
    if not BREVO_API_KEY:
        print("❌ ERROR: BREVO_API_KEY not found in environment variables!")
        return
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"email": "fertisenseiot@gmail.com", "name": "Fertisense"},
            subject=subject,
            html_content=html_content
        )

        response = api_instance.send_transac_email(email)
        print("✔ Email sent:", response)

    except ApiException as e:
        print("❌ Email failed:", e)

def make_robo_call(phone, message):
    print("📞 Robo calling", phone)

    try:
        call = twilio.calls.create(
            to=phone,
            from_=TWILIO_NUMBER,
            twiml=f"<Response><Say voice='alice' language='en-IN'>{message}</Say></Response>",
            timeout=60,
            status_callback="https://fertisense-iot-production.up.railway.app/twilio/call-status/",
            status_callback_event=["initiated", "ringing", "answered", "completed"]
        )

        print("✅ CALL CREATED:", call.sid)
        return True

    except Exception as e:
        print("❌ TWILIO CALL FAILED:", e)
        return False


def get_contact_info(device_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        today = date.today()

        # ---- Subscription Check ----
        cursor.execute("""
            SELECT sh.*, msi.Package_Name
            FROM Subcription_History sh
            JOIN Master_Subscription_Info msi 
              ON sh.Subscription_ID = msi.Subscription_ID
            WHERE sh.Device_ID = %s
              AND sh.Subscription_ID = 1
              AND sh.Subcription_End_date >= %s
            ORDER BY sh.ID DESC
            LIMIT 1
        """, (device_id, today))

        subscription = cursor.fetchone()
        print(f"DEBUG: Subscription for device {device_id} ->", subscription)

        if not subscription:
            return [], []

        # ---- Get device org & centre ----
        cursor.execute("""
            SELECT ORGANIZATION_ID, CENTRE_ID
            FROM iot_api_masterdevice
            WHERE DEVICE_ID = %s
        """, (device_id,))
        device = cursor.fetchone()

        if not device:
            return [], []

        org_id = device["ORGANIZATION_ID"]
        centre_id = device["CENTRE_ID"]

        # ---- Pick ONLY ONE operator for this centre ----
        cursor.execute("""
            SELECT 
    mu.USER_ID,
    mu.PHONE,
    mu.EMAIL,
    mu.SEND_SMS,
    mu.SEND_EMAIL
FROM userorganizationcentrelink u
JOIN master_user mu ON mu.USER_ID = u.USER_ID_id
WHERE u.ORGANIZATION_ID_id = %s
  AND u.CENTRE_ID_id = %s
  AND mu.ROLE_ID = 3
  AND mu.SEND_SMS = 1
ORDER BY mu.USER_ID

        """, (org_id, centre_id))

        # row = cursor.fetchone()

        # phone_numbers = [row["PHONE"]]
        # email_ids = [row["EMAIL"]] if row["SEND_EMAIL"] == 1 else []
        rows = cursor.fetchall()
        
        if not rows:
            print("❌ No operator found for this centre")
            return [], []
        
        phone_numbers = []
        email_ids = []

        for r in rows:
            for part in r["PHONE"].split(","):
                 phone_numbers.append(part.strip())
            if r["SEND_EMAIL"] == 1:
               email_ids.append(r["EMAIL"])


        print("🔥 FINAL OPERATOR:", phone_numbers)

        return phone_numbers, email_ids

    except Exception as e:
        print("❌ Error in get_contact_info:", e)
        return [], []

    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals() and conn.is_connected():
            conn.close()



second_notification_sent = {}


def safe_time(t_value):
    if isinstance(t_value, time):
        return t_value
    try:
        return (datetime.min + t_value).time()
    except:
        return time(0, 0, 0)

def normalize_phone(num):
    num = num.strip()
    if num.startswith("+"):
        return num
    return "+91" + num

    
def get_call_count(cursor, alarm, phone):
    cursor.execute("""
        SELECT COUNT(*)
        FROM iot_api_devicealarmcalllog
        WHERE DEVICE_ID=%s
        AND PARAMETER_ID=%s
        AND PHONE_NUM=%s
        AND ALARM_DATE=%s
    """, (
        alarm["DEVICE_ID"],
        alarm["PARAMETER_ID"],
        phone,
        alarm["ALARM_DATE"]
    ))
    row = cursor.fetchone()

    if not row:
        return 0

    # mysql returns dict like {'COUNT(*)': 2}
    return list(row.values())[0]

def log_call(cursor, alarm, phone, attempt):
    now = datetime.now(TZ)

    # 🔥 Device se Org & Centre nikaalo
    cursor.execute("""
        SELECT ORGANIZATION_ID, CENTRE_ID
        FROM iot_api_masterdevice
        WHERE DEVICE_ID = %s
    """, (alarm["DEVICE_ID"],))

    row = cursor.fetchone()
    org_id = row["ORGANIZATION_ID"] if row else None
    centre_id = row["CENTRE_ID"] if row else None

    cursor.execute("""
        INSERT INTO iot_api_devicealarmcalllog
        (
            DEVICE_ID,
            SENSOR_ID,
            PARAMETER_ID,
            ALARM_DATE,
            ALARM_TIME,
            PHONE_NUM,
            CALL_DATE,
            CALL_TIME,
            SMS_CALL_FLAG,
            ORGANIZATION_ID,
            CENTRE_ID
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        alarm["DEVICE_ID"],
        alarm["PARAMETER_ID"],   # SENSOR_ID (reuse)
        alarm["PARAMETER_ID"],
        alarm["ALARM_DATE"],
        alarm["ALARM_TIME"],
        phone,
        now.date(),
        now.time(),
        attempt,
        org_id,
        centre_id
    ))

# 👆👆 yahan khatam 👆👆

# 🔥🔥 YAHAN RAKHNA HAI 🔥🔥
def get_ntf_type_by_id(param_id, curr, low, up):

    # ---- Incubator CO2 (PARAMETER_ID = 8) ----
    if param_id == 8:
        return 17 if curr < low else 18 if curr > up else 19
    
    # ---- Incubator O2 (PARAMETER_ID = 9) ----
    if param_id == 9:
        return 20 if curr < low else 21 if curr > up else 22
    
    # ---- Incubator Temperature (PARAMETER_ID = 4) ----
    if param_id == 4:
        return 24 if curr < low else 23 if curr > up else 25
    
    # ---- Default (Fridge / Cryo / Others) ----
    return 1 if curr < low else 2 if curr > up else 7


def check_and_notify():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT ID, DEVICE_ID, PARAMETER_ID, ALARM_DATE, ALARM_TIME,
                   SMS_DATE, SMS_TIME, EMAIL_DATE, READING, IS_ACTIVE
            FROM devicealarmlog
            WHERE IS_ACTIVE = 1
        """)
        alarms = cursor.fetchall()

        if not alarms:
            print("✅ No alarms found.")
            return

        now = datetime.now(TZ)

        for alarm in alarms:
            alarm_id = alarm["ID"]
            devid = alarm["DEVICE_ID"]
        # 🔥 Fetch device name
            cursor.execute(
            "SELECT device_name FROM iot_api_masterdevice WHERE device_id=%s",
             (devid,)
)
            rows = cursor.fetchall()
            device_name = rows[0]["device_name"] if rows else f"Device-{devid}"

       # 🔥 Fetch parameter name
            cursor.execute(
            "SELECT PARAMETER_NAME FROM iot_api_masterparameter WHERE PARAMETER_ID=%s",
            (alarm["PARAMETER_ID"],)
)
            rows = cursor.fetchall()
            param_name = rows[0]["PARAMETER_NAME"] if rows else "parameter"


            alarm_date = alarm["ALARM_DATE"]
            alarm_time = safe_time(alarm["ALARM_TIME"])
            dev_reading = alarm["READING"]

            raised_time = TZ.localize(datetime.combine(alarm_date, alarm_time))
            diff_seconds = (now - raised_time).total_seconds()

            first_sms_done = alarm["SMS_DATE"] is not None
            second_sms_done = second_notification_sent.get(alarm_id, False)
            is_active = int(alarm["IS_ACTIVE"])

            # ================== FIRST NOTIFICATION ==================
            if not first_sms_done and diff_seconds > 60:

                cursor.execute(
                    "SELECT device_name FROM iot_api_masterdevice WHERE device_id=%s",
                    (devid,)
                )
                row = cursor.fetchone()
                devnm = row["device_name"] if row else f"Device-{devid}"
                device_name = devnm

                cursor.execute("""
    SELECT
        MP.PARAMETER_ID,
        MP.PARAMETER_NAME,
        MP.UPPER_THRESHOLD,
        MP.LOWER_THRESHOLD,
        DRL.READING AS CURRENT_READING
    FROM devicealarmlog DAL
    JOIN iot_api_masterparameter MP
        ON MP.PARAMETER_ID = DAL.PARAMETER_ID
    LEFT JOIN device_reading_log DRL
        ON DRL.DEVICE_ID = DAL.DEVICE_ID
       AND DRL.PARAMETER_ID = DAL.PARAMETER_ID
    WHERE DAL.DEVICE_ID = %s
      AND DAL.PARAMETER_ID = %s
    ORDER BY DRL.READING_DATE DESC, DRL.READING_TIME DESC
    LIMIT 1
""", (devid, alarm["PARAMETER_ID"]))



                reading_row = cursor.fetchone()
                if not reading_row:
                    print(f"⚠️ No reading found for device {devnm}")
                    continue

                currreading = reading_row["CURRENT_READING"]
                if currreading is None:
                    print(f"⚠️ Skipping device {devnm} as current reading is NULL.")
                    continue

                upth = reading_row["UPPER_THRESHOLD"]
                lowth = reading_row["LOWER_THRESHOLD"]
                param_id = reading_row["PARAMETER_ID"]
                param_name = reading_row["PARAMETER_NAME"]



                print(f"Device {devnm}: Lower={lowth}, Upper={upth}, Current={currreading}")

                ntf_typ = get_ntf_type_by_id(param_id, currreading, lowth, upth)

                message = build_message(ntf_typ, devnm)
                phones, emails = get_contact_info(devid)

                flat_phones = []
                for p in phones:
                    if p:
                        parts = p.split(",")
                        for part in parts:
                            num = part.strip()
                            if num:
                                flat_phones.append(num)

                # Deduplicate final list
                unique_phones = list(set(flat_phones))

                print("Unique phone numbers:", unique_phones)
                # ---- FIX END ----

                for phone in unique_phones:
                    send_sms(phone, message)

                for em in emails:
                    if currreading > upth:
                        email_subject = f"IoT Alarm Notification for {device_name} | {param_name} | Current reading is : {dev_reading} and it is HIGHER then normal"
                    elif currreading < lowth:    
                        email_subject = f"IoT Alarm Notification for {device_name} | {param_name} | Current reading is : {dev_reading} and it is LOWER then normal"
                    else:
                        # NORMAL CONDITION → No mail
                        continue  
                    
                    email_body = f"""
                    <h2>⚠ IoT Alert Triggered</h2>
                    <p><b>Device:</b> {device_name}</p>
                    <p><b>{param_name}</b></p>
                    <p><b>Current Reading:</b> {dev_reading}</p>
                    <p><b>Limits:</b> {lowth} - {upth}</p>
                    <p>Please check the device immediately.</p>
                    <p></p>
                    <p></p>
                    <p>Regards</p>
                    <p>Team Fertisense.</p>
                    """

                    send_email_brevo(em, email_subject, email_body)

                now_ts = datetime.now(TZ)
                cursor.execute("""
                    UPDATE devicealarmlog
                    SET SMS_DATE=%s, SMS_TIME=%s, EMAIL_DATE=%s, EMAIL_TIME=%s
                    WHERE ID=%s
                """, (now_ts.date(), now_ts.time(), now_ts.date(), now_ts.time(), alarm_id))

                conn.commit()
                print(f"✅ First notification sent for alarm {alarm_id}")

        # ================== ROBO CALL AFTER 7 MIN ==================
                if first_sms_done and is_active == 1:

                    first_sms_dt = datetime.combine(
                    alarm["SMS_DATE"],
                    safe_time(alarm["SMS_TIME"])
                 )
                    first_sms_dt = TZ.localize(first_sms_dt)

                    elapsed = (now - first_sms_dt).total_seconds()
                    print("⏳ Seconds since first SMS:", elapsed)

                if elapsed >= 60:

                  if is_alarm_answered(cursor, alarm):
                   print("☎ Alarm already acknowledged. No more calls.")
            continue

        phones, _ = get_contact_info(devid)

        flat = []
        for p in phones:
            if p:
                for part in p.split(","):
                    flat.append(part.strip())

        unique_phones = list(dict.fromkeys(flat))

        for raw in unique_phones:

            phone = normalize_phone(raw)

            if is_alarm_answered(cursor, alarm):
                break

            call_count = get_call_count(cursor, alarm, phone)

            if call_count >= 3:
                continue

            voice_msg = f"Critical alert. {device_name} has dangerous {param_name}. Please check immediately."

            print("📞 Calling", phone)

            if make_robo_call(phone, voice_msg):
                log_call(cursor, alarm, phone, call_count + 1)
                conn.commit()

                # print("⏳ Waiting 60 seconds...")
                # t.sleep(65)
                print("⏳ Waiting for answer (max 60 sec)...")

                for _ in range(12):   # 12 × 5 sec = 60 sec
                  t.sleep(5)

              # 🔥 check every 5 seconds if someone answered
                if is_alarm_answered(cursor, alarm):
                    print("☎ Someone answered. Stopping further calls.")
                    return   # EXIT entire notification run



            # ================== SECOND NOTIFICATION ==================
            elif first_sms_done and is_active == 1 and not second_sms_done:

                first_sms_dt = datetime.combine(
                    alarm["SMS_DATE"], safe_time(alarm["SMS_TIME"])
                )
                first_sms_dt = TZ.localize(first_sms_dt)
                diff_hours = (now - first_sms_dt).total_seconds() / 3600

                if diff_hours >= 6:

                    cursor.execute(
                        "SELECT device_name FROM iot_api_masterdevice WHERE device_id=%s",
                        (devid,)
                    )
                    row = cursor.fetchone()
                    devnm = row["device_name"] if row else f"Device-{devid}"
                    device_name = devnm

                    cursor.execute("""
    SELECT
        MP.PARAMETER_ID,
        MP.PARAMETER_NAME,
        MP.UPPER_THRESHOLD,
        MP.LOWER_THRESHOLD,
        DRL.READING AS CURRENT_READING
    FROM devicealarmlog DAL
    JOIN iot_api_masterparameter MP
        ON MP.PARAMETER_ID = DAL.PARAMETER_ID
    LEFT JOIN device_reading_log DRL
        ON DRL.DEVICE_ID = DAL.DEVICE_ID
       AND DRL.PARAMETER_ID = DAL.PARAMETER_ID
    WHERE DAL.DEVICE_ID = %s
      AND DAL.PARAMETER_ID = %s
    ORDER BY DRL.READING_DATE DESC, DRL.READING_TIME DESC
    LIMIT 1
""", (devid, alarm["PARAMETER_ID"]))



                    reading_row = cursor.fetchone()
                    if not reading_row:
                        continue

                    currreading = reading_row["CURRENT_READING"]
                    if currreading is None:
                        print(f"⚠️ Skipping device {devnm} as current reading is NULL.")
                        continue

                    upth = reading_row["UPPER_THRESHOLD"]
                    lowth = reading_row["LOWER_THRESHOLD"]
                    param_id = reading_row["PARAMETER_ID"]
                    param_name = reading_row["PARAMETER_NAME"]


                    ntf_typ = get_ntf_type_by_id(param_id, currreading, lowth, upth)

                    message = build_message(ntf_typ, devnm)
                    phones, emails = get_contact_info(devid)

                    flat_phones = []
                    for p in phones:
                        if p:
                            parts= p.split(",")
                            for part in parts:
                                num = part.strip()
                                if num:
                                    flat_phones.append(num)

                    unique_phones = list(set(flat_phones))
                    print("Unique phone numbers:", unique_phones)

                    for phone in unique_phones:
                        send_sms(phone, message)

                    for em in emails:
                        if currreading > upth:
                            email_subject = f"IoT Alarm Notification (2nd Notification) for {device_name} |{param_name} | Current reading is : {dev_reading} and it is HIGHER then normal"
                        elif currreading < lowth:    
                            email_subject = f"IoT Alarm Notification (2nd Notification) for {device_name} | {param_name} | Current reading is : {dev_reading} and it is LOWER then normal"
                        else:
                            # NORMAL CONDITION → No mail
                            continue  
                        email_body = f"""
                        <h2>⚠ IoT Alert Triggered</h2>
                        <p><b>Device:</b> {device_name}</p>
                        <p><b>{param_name}</b></p>
                        <p><b>Current Reading:</b> {dev_reading}</p>
                        <p><b>Limits:</b> {lowth} - {upth}</p>
                        <p>Please check the device immediately.</p>
                        <p></p>
                        <p></p>
                        <p>Regards</p>
                        <p>Team Fertisense.</p>
                        """

                    send_email_brevo(em, email_subject, email_body)

                    now_ts = datetime.now(TZ)
                    cursor.execute("""
                        UPDATE devicealarmlog
                        SET EMAIL_DATE=%s,EMAIL_TIME=%s
                        WHERE ID=%s
                    """, (now_ts.time(), now_ts.time(), alarm_id))

                    conn.commit()
                    print(f"✅ Second notification sent for alarm {alarm_id}")
                else:
                   print("Elasped time", diff_seconds)
        cursor.close()
        conn.close()

    except Exception as e:
        traceback.print_exc()
        print("❌ Error in check_and_notify:", e)



if __name__ == "__main__":
    print("🚀 Starting notification check...")
    check_and_notify()
    print("✅ Notification check complete. Exiting now.")


