from flask import (
    Blueprint, redirect, render_template,  session,url_for
)


bp = Blueprint('home', __name__)

 
@bp.route('/')
def index():
    if 'user_id' in session: 
        return redirect(url_for('attendance.index'))  
    return render_template('index.html') 


 