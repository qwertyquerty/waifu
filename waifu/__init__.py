from flask import Flask, render_template, send_from_directory, abort

from flask_marshmallow import Marshmallow

from flask_restful import Api

from flask_sqlalchemy import SQLAlchemy

from webargs.flaskparser import parser

from waifu.config import cfg

app = Flask(__name__)

app.config.update({
    "SQLALCHEMY_DATABASE_URI": f"mysql+mysqlconnector://{cfg.get('db.user')}:{cfg.get('db.pass')}@{cfg.get('db.host')}:{cfg.get('db.port')}/{cfg.get('db.name')}?charset=utf8mb4",
})

db_ext = SQLAlchemy(app)
ma_ext = Marshmallow(app)
rest_ext = Api(app)

@app.route("/")
def index_page():
    from waifu.db import Prompt
    total_waifu_count = Prompt.query.count()
    return render_template("index.html", cfg=cfg, total_waifu_count=total_waifu_count)

@app.route("/static/<path:path>")
def send_static_content(path):
    return send_from_directory("static", path)

@app.route("/ads.txt")
def ads_txt():
    return send_from_directory("static", "ads.txt")


parser.location = "query"

@parser.error_handler
def handle_request_parsing_error(err, req, schema, *, error_status_code, error_headers):
    abort(400, err.messages)


app.config['TEMPLATES_AUTO_RELOAD'] = True

from waifu.resources import *
rest_ext.add_resource(RequestResource, "/generate")
rest_ext.add_resource(ImageResource, "/image/<string:id>")
rest_ext.add_resource(QueueResource, "/queue/<string:id>")
