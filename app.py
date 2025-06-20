from flask import Flask, render_template, request, redirect, url_for
import subprocess
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    # Collect form data
    subject = request.form['subject']
    pose = request.form['pose']
    setting = request.form['setting']
    other = request.form['other']
    realism = request.form['realism_lora']
    detail = request.form['detail_lora']
    workflow = request.form['workflow_type']  # 'smoke' or 'final'

    # Build command
    cmd = [
        'python',
        'main.py',
        '--subject', subject,
        '--pose', pose,
        '--setting', setting,
        '--other', other,
        '--realism_lora', realism,
        '--detail_lora', detail,
        '--workflow_type', workflow
    ]
    # Execute backend
    subprocess.run(cmd, check=True)

    # Redirect back to form or show success
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)