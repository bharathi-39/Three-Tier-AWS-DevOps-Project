import logging
from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics
from .config import Config
from .extensions import db,migrate,cors
from .routes import api

def create_app(config=Config):
    app=Flask(__name__); app.config.from_object(config); db.init_app(app); migrate.init_app(app,db); cors.init_app(app,origins=app.config['CORS_ORIGINS']); app.register_blueprint(api); PrometheusMetrics(app)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s')
    @app.errorhandler(404)
    def not_found(e): return {'success':False,'error':{'code':'NOT_FOUND','message':'Resource not found'}},404
    @app.errorhandler(Exception)
    def unexpected(e): app.logger.exception('Unhandled error'); return {'success':False,'error':{'code':'INTERNAL_ERROR','message':'Unexpected server error'}},500
    return app
