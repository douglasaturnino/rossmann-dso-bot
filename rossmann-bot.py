import os
import json
import pandas as pd
import requests
from flask import Flask, request, Response

#constants
token = os.environ.get('TOKEN')

def send_message(chat_id, text):
    url= 'https://api.telegram.org/bot{}/'.format(token)
    url = url + 'sendMessage?chat_id={}'.format(chat_id)  

    r = requests.post(url, json={'text':text})
    print('Status Code {}'.format(r.status_code))
    
    return None

def load_dataset(store_id):
    # loading tet dataset
    home_path =  os.path.dirname(os.path.abspath(__file__))
    df_test_raw = pd.read_csv(os.path.join(home_path, 'test.csv'))
    df_store_raw = pd.read_csv(os.path.join(home_path, 'store.csv'))

    # merge test dataset + store
    df_test = pd.merge(df_test_raw, df_store_raw, how='left', on='Store')

    # choose store for prediction
    df_test = df_test[df_test['Store'] == store_id]

    if not df_test.empty:
        # remove closed days
        df_test = df_test[df_test['Open'] != 0]
        df_test = df_test[~df_test['Open'].isnull()]

        df_test = df_test.drop('Id', axis=1)

        # convert DataFrame to json
        data = json.dumps(df_test.to_dict(orient='records'))

    else:
        data = 'error'

    return data

def predict(data):

    # API Call
    url = 'https://rossmann-model.onrender.com/rossmann/predict'
    header = {'Content-type': 'application/json'}
    data = data

    r = requests.post(url, data=data, headers=header)
    print('Status Code - bot {}'.format(r.status_code))

    d1 = pd.DataFrame(r.json(), columns=r.json()[0].keys())

    return d1

def parse_message(message):

    chat_id = message['message']['chat']['id']
    
    try:
        store_id = message['message']['text']

        store_id = store_id.replace('/', '')
    
        store_id = int(store_id)
    except (ValueError, KeyError):
        store_id = 'error'

    return chat_id, store_id

# API inicialize
app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        message = request.get_json()
        # retorna status 200 caso o bot seja bloqueado.
        print(message)
        if 'my_chat_member' in message:
            return Response('OK', status=200)

        chat_id, store_id = parse_message(message)
        
        if store_id != 'error':
            # loading data
            data = load_dataset(store_id)
            
            if data != 'error':
                # prediction
                d1 = predict(data)

                # calculation
                d2 = d1[['store', 'prediction']].groupby('store').sum().reset_index()
                
                # send message
                msg = 'Store Number {} will sell R${:,.2f} in the next 6 weeks'.format(
                d2['store'].values[0], 
                d2['prediction'].values[0])

                send_message(chat_id, msg)
                return Response('OK', status=200)

            else:
                send_message(chat_id, 'Store Not Available')
                return Response('OK', status=200)

        else:
            send_message(chat_id, 'Store ID is Wrong')
            return Response('OK', status=200)

    else:
        return '<h1> Rossmann Telegram BOT </h1>'

if __name__ == '__main__':
    port = os.environ.get('PORT', 5000)
    app.run(host='0.0.0.0', port=port)