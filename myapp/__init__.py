import os
from flask import Flask,render_template
from dotenv import load_dotenv

from flask_mail import Mail


mail=Mail()


def create_app():
    load_dotenv()
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev'),
        DATABASE=os.path.join(app.instance_path, 'attendance.sqlite'),
    )

    app.config.from_pyfile('config.py', silent=True)
    try:
        os.makedirs(app.instance_path)
        # os.makedirs(app.static_folder)
        # os.makedirs(app.template_folder)
    except OSError:
        pass


    #print('CONFIG: ', app.config)
    # app.config.from_mapping(

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    mail.init_app(app)

    # Import the mail module (mail.py) with the blueprint inside it
    from . import mail_bp    # relative import!

    app.register_blueprint(mail_bp.bp)


    # a simple page that says hello
    # @app.route('/')
    # def home():
    #     return render_template('index.html')
    
    from . import home
    app.register_blueprint(home.bp, url_prefix='/')
    app.add_url_rule('/', endpoint='index')
    
    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)
 

    from . import employee
    app.register_blueprint(employee.bp, url_prefix='/employee')
    app.add_url_rule('/employee/', endpoint='index')

    from . import attendance
    app.register_blueprint(attendance.bp, url_prefix='/attendance')
    app.add_url_rule('/attendance/', endpoint='index')
    
    return app