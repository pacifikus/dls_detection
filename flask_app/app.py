import pika
import uuid
import json
import graypy
from flask import Flask, render_template, request, redirect

app = Flask(__name__)


class RpcClient(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq'))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='rpc_queue')
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, data):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='rpc_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
                expiration='300000'
            ),
            body=data)
        while self.response is None:
            self.connection.process_data_events()
        return self.response


@app.route('/', methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if request.form['image'] != '':
            image = request.form['image']
            if 'data:image' in image:
                client = RpcClient()
                result = client.call(image)
                result_str = result.decode("utf-8")
                client.connection.close()
                return get_result_template(result_str)
            else:
                return render_template('error.html', error_message='Wrong file format')

    return render_template('main.html', Status=True)


def get_result_template(result_str):
    if result_str == 'Invalid image':
        return render_template('error.html', error_message='Unknown error', title='Error')
    else:
        return render_template('result.html', result_str=f'data:image/png;base64,{result_str}', title='Error')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
