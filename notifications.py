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


def get_contact_info(device_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        today = date.today()

        # ---- Subscription Check First ----
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
            return [], []   # Only 2 values

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

        cursor.execute("""
            SELECT USER_ID_id
            FROM userorganizationcentrelink
            WHERE ORGANIZATION_ID_id = %s
              AND CENTRE_ID_id = %s
        """, (org_id, centre_id))

        users_link = cursor.fetchall()
        user_ids = [u["USER_ID_id"] for u in users_link]

        if not user_ids:
            return [], []

        format_strings = ",".join(["%s"] * len(user_ids))
        query = f"""
            SELECT USER_ID, PHONE, EMAIL, SEND_SMS, SEND_EMAIL
            FROM master_user
            WHERE USER_ID IN ({format_strings})
              AND (SEND_SMS = 1 OR SEND_EMAIL = 1)
        """

        cursor.execute(query, tuple(user_ids))
        users = cursor.fetchall()

        phone_numbers = [u["PHONE"] for u in users if u["SEND_SMS"] == 1]
        print("Availablephone numbers",phone_numbers)
        #uni_phones = list(set(phone_numbers))
        email_ids = [u["EMAIL"] for u in users if u["SEND_EMAIL"] == 1]
       

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

# 🔥🔥 YAHAN RAKHNA HAI 🔥🔥
def get_ntf_type_by_name(param, curr, low, up):
    if param == "Inc_CO2":
        return 17 if curr < low else 18 if curr > up else 19
    if param == "Inc_O2":
        return 20 if curr < low else 21 if curr > up else 22
    if param == "Inc_Temp_T1":
        return 24 if curr < low else 23 if curr > up else 25
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
                    continue

                upth = reading_row["UPPER_THRESHOLD"]
                lowth = reading_row["LOWER_THRESHOLD"]
                param_name = reading_row["PARAMETER_NAME"]

                ntf_typ = get_ntf_type_by_name(param_name, currreading, lowth, upth)

                message = build_message(ntf_typ, devnm)
                phones, emails = get_contact_info(devid)

                flat_phones = []
                for p in phones:
                    if p:
                        for num in p.split(","):
                            flat_phones.append(num.strip())

                unique_phones = list(set(flat_phones))

                for phone in unique_phones:
                    send_sms(phone, message)

                for em in emails:
                    if currreading > upth:
                        email_subject = f"IoT Alarm Notification for {device_name} | HIGH"
                    elif currreading < lowth:
                        email_subject = f"IoT Alarm Notification for {device_name} | LOW"
                    else:
                        continue

                    send_email_brevo(em, email_subject, message)

                now_ts = datetime.now(TZ)
                cursor.execute("""
                    UPDATE devicealarmlog
                    SET SMS_DATE=%s, SMS_TIME=%s, EMAIL_DATE=%s, EMAIL_TIME=%s
                    WHERE ID=%s
                """, (now_ts.date(), now_ts.time(), now_ts.date(), now_ts.time(), alarm_id))

                conn.commit()
                print(f"✅ First notification sent for alarm {alarm_id}")

            # ================== SECOND NOTIFICATION ==================
            elif first_sms_done and is_active == 1 and not second_sms_done:

                first_sms_dt = TZ.localize(
                    datetime.combine(alarm["SMS_DATE"], safe_time(alarm["SMS_TIME"]))
                )
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
                        continue

                    upth = reading_row["UPPER_THRESHOLD"]
                    lowth = reading_row["LOWER_THRESHOLD"]
                    param_name = reading_row["PARAMETER_NAME"]

                    ntf_typ = get_ntf_type_by_name(param_name, currreading, lowth, upth)

                    message = build_message(ntf_typ, devnm)
                    phones, emails = get_contact_info(devid)

                    flat_phones = []
                    for p in phones:
                        if p:
                            for num in p.split(","):
                                flat_phones.append(num.strip())

                    unique_phones = list(set(flat_phones))

                    for phone in unique_phones:
                        send_sms(phone, message)

                    for em in emails:
                        send_email_brevo(
                            em,
                            f"IoT Alarm Notification (2nd) for {device_name}",
                            message
                        )

                    now_ts = datetime.now(TZ)
                    cursor.execute("""
                        UPDATE devicealarmlog
                        SET EMAIL_DATE=%s
                        WHERE ID=%s
                    """, (now_ts.time(), alarm_id))

                    conn.commit()
                    second_notification_sent[alarm_id] = True
                    print(f"✅ Second notification sent for alarm {alarm_id}")

        cursor.close()
        conn.close()

    except Exception as e:
        traceback.print_exc()



if __name__ == "__main__":
    print("🚀 Starting notification check...")
    check_and_notify()
    print("✅ Notification check complete. Exiting now.")


