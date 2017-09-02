from flask import Flask, jsonify, request
from flask_restful import Api, Resource, reqparse

app = Flask(__name__)
api = Api(app)


class UserAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        # self.reqparse.add_argument('title', type=str, location='json')
        super(UserAPI, self).__init__()

    def get(self, id):
        return {"id": id}

    def post(self, id):
        print id
        data = request.form['uuu']
        task = {"uid": data}
        return task

api.add_resource(UserAPI, '/users/<int:id>', endpoint='user')

if __name__ == '__main__':
    app.run()
