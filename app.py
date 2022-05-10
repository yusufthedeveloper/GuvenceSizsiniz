
import os
from os import walk
import re
import shutil
import sys
import random
import argparse
import requests
from email import message
import json
import os
import glob
from re import T
from flask import Flask, flash, jsonify, make_response, render_template, url_for, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from cryptography.fernet import Fernet
from datetime import datetime
from zipfile import ZipFile
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
import zippyshare_downloader
from flask_ngrok import run_with_ngrok


s = requests.Session()

app = Flask(__name__)
run_with_ngrok(app) 
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///holdup.db"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class filetokens (db.Model):
    id = db.Column(db.Integer, primary_key = True)
    file_name = db.Column(db.String(200), nullable = False)
    file_url = db.Column(db.String(200), nullable = False)

class passtokens (db.Model):
    id = db.Column(db.Integer, primary_key = True)
    application_name = db.Column(db.String(200), nullable = False)
    passwkey = db.Column(db.String(200), nullable = False)

class logintokens (db.Model):
    id = db.Column(db.Integer, primary_key = True)
    token_name = db.Column(db.String(200), nullable = False)
    token = db.Column(db.String(200), nullable = False)

def __init__(self, token_name, token):
   self.token_name = token_name
   self.token = token
    
def check_size(abs):
	total = os.path.getsize(abs)
	if total > 524288000:
		raise Exception("File exceeds 500 MB limit.")
	return total


def upload(abs, fname):
	server = random.randint(1, 120)
	total = check_size(abs)
	url = "https://www{}.zippyshare.com/upload".format(server)
	files = {
		'file': open(abs, 'rb')
	}
	files['private'] = "true"
	r = s.post(url, files=files)
	return r.text
	
def extract(html):
	regex = (
		r'onclick=\"this.select\(\);" value="(https://www\d{1,3}'
		r'.zippyshare.com/v/[a-zA-Z\d]{8}/file.html)'
	)
	url = re.search(regex, html)
	if not url:
		raise Exception("Failed to extract URL.")
	return url.group(1)

def mainload(abs):
	fname = os.path.basename(abs)
	print(fname)
	html = upload(abs, fname)
	url = extract(html)
	return url

@app.route('/upload', methods=['POST'])
def ul():
   if request.method == 'POST':
        f = request.files['file']
        shutil.rmtree('cahce')
        os.makedirs('cahce')
        data = db.session.query(logintokens).all()
        f.save("cahce/" + secure_filename(f.filename))
        fernet = Fernet(bytes(data[1].token,"utf-8"))
        with open("cahce/" + secure_filename(f.filename), 'rb') as file:
            original = file.read()
            encrypted = fernet.encrypt(original)
        encrypted = fernet.encrypt(original)
        with open("cahce/" + secure_filename(f.filename) + ".lck", 'wb') as encrypted_file:
            encrypted_file.write(encrypted)
        os.remove("cahce/" + secure_filename(f.filename))
        url = mainload("cahce/" + secure_filename(f.filename) + ".lck")
        tasknew = filetokens(file_name = secure_filename(f.filename), file_url = url)
        db.session.add(tasknew)
        db.session.commit()
        return redirect('/files')



@app.route('/backupkey', methods=['GET'])
def dl():
    return send_file("passrecover.zip", as_attachment=True)

@app.route('/', methods=['GET'])
def index():
    return redirect('/setup')

@app.route('/settings/logpasschange', methods=['POST'])
def changepass():
    try:
        data = db.session.query(logintokens).all()
        if request.cookies.get('LoginToken') == data[0].token:
            data[0].token = request.form['password']
            db.session.commit()
            return redirect('/login')
        else:
            return redirect('/login')
    except:
        return redirect('/login')

@app.route('/settings', methods=['GET'])
def settings():
    data = db.session.query(logintokens).all()
    try:
        if request.cookies.get('LoginToken') == data[0].token:
            return render_template('settings.html')
        else:
            return redirect('/login')
    except:
        return redirect('/login')

@app.route('/files', methods=['GET'])
def myfiles(): 
    data = db.session.query(logintokens).all()
    if request.cookies.get('LoginToken') == data[0].token:
        try:
                passd = filetokens.query.all()
                return render_template('myfiles.html',passlist=passd)
        except:
            return redirect('/login')
    else:
        return redirect('/login')

@app.route("/passwords/take/<int:pa_id>")
def take(pa_id):
    data = db.session.query(logintokens).all()
    if request.cookies.get('LoginToken') == data[0].token:
        f = Fernet(bytes(data[1].token, "utf-8"))
        qemum = passtokens.query.filter_by(id=pa_id).first()
        qemu = f.decrypt(bytes(qemum.passwkey, "utf-8"))
        return render_template('take.html',passwkey = str(qemu).split("'")[1])

@app.route("/file/restore/<int:pa_id>")
def fr(pa_id):
    data = db.session.query(logintokens).all()
    if request.cookies.get('LoginToken') == data[0].token:
        shutil.rmtree('cahce')
        os.makedirs('cahce')
        todo = filetokens.query.filter_by(id=pa_id).first()
        zippyshare_downloader.download(todo.file_url, progress_bar=True, replace=False, folder="cahce", filename="cahce")
        # using the key
        fernet = Fernet(bytes(data[1].token, "utf-8"))
        spl = todo.file_name
        
        filenames = next(walk("cahce/"), (None, None, []))[2] 
        with open("cahce/"+filenames[0], 'rb') as enc_file:
            encrypted = enc_file.read()
        decrypted = fernet.decrypt(encrypted)
        with open("cahce/"+todo.file_name, 'wb') as dec_file:
            dec_file.write(decrypted)
        return send_file("cahce/"+todo.file_name, as_attachment=True)
        
@app.route("/file/delete/<int:pa_id>")
def deletef(pa_id):
    data = db.session.query(logintokens).all()
    if request.cookies.get('FileToken') == data[0].token:
        todo = passtokens.query.filter_by(id=pa_id).first()
        db.session.delete(todo)
        db.session.commit()
        return redirect("/files")
        
@app.route("/passwords/delete/<int:pa_id>")
def deletep(pa_id):
    data = db.session.query(logintokens).all()
    if request.cookies.get('LoginToken') == data[0].token:
        todo = passtokens.query.filter_by(id=pa_id).first()
        db.session.delete(todo)
        db.session.commit()
        return redirect("/passwords")

@app.route('/passwords/add', methods=['POST'])
def passadd():
    try: 
        data = db.session.query(logintokens).all()
        if request.cookies.get('LoginToken') == data[0].token:
            dkey = data[1].token
            reslove = bytes(dkey, encoding='utf8')
            f = Fernet(reslove)
            token = f.encrypt(bytes(request.form['password'], encoding='utf8'))
            tkey = str(token).split("'")[1]
            tasknew = passtokens(application_name = request.form['appname'], passwkey = tkey)
            db.session.add(tasknew)
            db.session.commit()
            return redirect('/passwords')
        else:
            return redirect('/login')
    except:
        return redirect('/login')

@app.route('/passwords', methods=['GET'])
def dash():
    data = db.session.query(logintokens).all()
    try:
        if request.cookies.get('LoginToken') == data[0].token:
            passd = passtokens.query.all()
            return render_template('index.html',passlist=passd)
        else:
            return redirect('/login')
    except:
        return redirect('/login')

@app.route('/logout', methods=['GET'])
def logout():
    resp = make_response(redirect('/login'))
    resp.delete_cookie('LoginToken')
    return resp

@app.route('/modalclose', methods=['POST', 'GET'])
def close():
    global messagebx
    try:
        os.remove("passrecover.zip")
    except:
        pass
    messagebx = "ok"
    return redirect('/login')

@app.route('/passreco', methods=['POST', 'GET'])
def reco():
    data = db.session.query(logintokens).all()
    dkey = data[1].token
    reslove = bytes(dkey, encoding='utf8')
    f = Fernet(reslove)
    token = f.encrypt(bytes(data[0].token, encoding='utf8'))
    global formatted
    formatted = str(token).split("'")[1]
    global messagebx
    messagebx = 'Bu kodu kayıt sürecinde parolakurtar.zip icindeki parolakurtar.exe yi pcnizde çalıştırıp giriş kodunu edinebilirsiniz'
    return redirect('/login')

@app.route('/api/login', methods=['GET'])
def aplogin():
    token = request.args.get('check', default = '*', type = str)
    if (db.session.query(db.exists().where(logintokens.token_name == 'LoginToken')).scalar()):
        data = db.session.query(logintokens).all()
        if token == data[0].token:
            return 'Passed!|'+data[1].token
        else:
            return 'Forbidden!'

@app.route('/login', methods=['POST', 'GET'])
def login():
    if (db.session.query(db.exists().where(logintokens.token_name == 'LoginToken')).scalar()):
        if request.method == 'POST':
            data = db.session.query(logintokens).all()
            if request.form['token'] == data[0].token:
                resp = make_response(redirect('/passwords'))
                resp.set_cookie('LoginToken',  request.form['token'])
                return resp
            else:
                return redirect('/passreco')
        else:
            try:
                if messagebx.startswith("ok"):
                    return render_template('login.html', show_predictions_modal = False)
                if messagebx.startswith("Bu kodu kayıt sürecinde parolakurtar.zip"):
                    return render_template('login.html', format=formatted , direct_dl = False, message=messagebx, show_predictions_modal = True)
                if messagebx.startswith("Aşagıdaki butona basıp"):
                    return render_template('login.html', format="" , direct_dl = True, message=messagebx, show_predictions_modal = True)
            except:
                return render_template('login.html', show_predictions_modal = False)
    else:
        return redirect('/setup')
            
@app.route('/setup', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
            try:
                tasknew = logintokens(token_name = str("LoginToken"), token = request.form['token'])
                key = Fernet.generate_key()
                encoding = 'utf-8'
                crpt = key.decode(encoding)
                keybase = logintokens(token_name = str("FernToken"), token = crpt)
                db.session.add(tasknew)
                db.session.add(keybase)
                db.session.commit()
                tkm = open("passrecover/token.key", "x")
                tkm.write(crpt)
                tkm.close()
                with ZipFile('passrecover.zip', 'w') as zip:
                    for root, directories, files in os.walk("passrecover", topdown=False):
                        for name in files:
                            zip.write(os.path.join(root, name))
                        for name in directories:
                            zip.write(os.path.join(root, name))
                global messagebx
                messagebx = 'Aşagıdaki butona basıp karşıdan inen dosyayı lütfen saklayınız şifreyi unutmanız halinde içindeki araç size lazım olucaktır'
                return redirect('/login')
            except:
                return 'There was an issue'

    else:
        if (db.session.query(db.exists().where(logintokens.token_name == 'LoginToken')).scalar()):
            return redirect('/login')
        else:
           return render_template('setup.html')

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=80)
