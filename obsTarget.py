#!/usr/bin/python3
# Program: obsTarget
# Version: 20260227
# Author:  Sifan Kahale
# Desc:    Form for entering target data into db

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm, CSRFProtect
import mysql.connector, os
import ephem, math
from datetime import datetime, timezone

#--------------------------------------------------------
app = Flask(__name__)

DEBUG = True
ID = 0
binningItems = ['1x1', '2x2', '3x3', '4x4']
ExpType = ['Light', 'Dark', 'Bias', 'Flat']
SearchType = ['Target', 'CommonName', 'ImageType', 'Date']

#--------------------------------------------------------
# Database Configuration
db_config = {
    'host': 'depoe',
    'user': 'sifan',
    'password': 'all4Sky',
    'database': 'kahaleobs'
}

#--------------------------------------------------------
# Diag printout if DEBUG is true
def debug(msg):
    if DEBUG == True:
        print(f"DIAG {msg}")

    return

#--------------------------------------------------------
# Open Database
def openDB():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        #print(f"Database error: {err}")
        conn = cursor = "None"
    
    return conn, cursor

#--------------------------------------------------------
# Close Database
def closeDB(conn, cursor):
    conn.close()
    cursor.close()
    return

#--------------------------------------------------------
def refreshData():
    '''
    envInfo structure:
    0 - Date/time
    1 - Temp
    2 - Hum
    3 - Dp
    4 - Gust
    5 - Sky Temp
    6 - Sky Lux
    '''
    ctime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "select time, fallskyTemp, fallskyHum, fallskyDp, fallskyWGust, fallskySkyTemp, fallskyLux from sensordata order by time desc limit 1;"
    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        EnvData = cursor.fetchone()
        envInfo = list(EnvData)
        closeDB(conn, cursor)
    except mysql.connector.Error as err: 
        envInfo = [f"ctime, 70.1, 60.5, 60, 6.3, 53, 1000.00"]
    closeDB(conn, cursor)
    
    DpDep = envInfo[1] - envInfo[2]
    weather = f"[FieldAllSky] Temp: {envInfo[1]:.1f}, Hum: {envInfo[2]:.1f}, DpDep: {DpDep:.1f}, Gust: {envInfo[4]:.1f}, SkyTemp: {envInfo[5]:.1f}, SkyLux: {envInfo[6]}"
    
    return  weather, ctime

#--------------------------------------------------------
@app.route('/')
def index():
    conn, cursor = openDB()
    if conn == "None":
        return render_template('SQLerror.html', err="Can not open Database")
    try:
        cursor.execute("SELECT * FROM obsTarget ORDER BY Date DESC;")
        Target = cursor.fetchall()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)
    
    return render_template('targetMain.html', Target = Target, SearchType = SearchType)

#--------------------------------------------------------
@app.route("/details", methods=['POST'])
def details():
    ID = request.form.get('ID')
    sql = f"SELECT * FROM obsTarget WHERE ID={ID};"
    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        Target = cursor.fetchone()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)
        
    if cursor.rowcount == 0:
        return render_template('DoesNotExist.html', ID = ID, Type = "Target")
    
    return render_template('/targetDetails.html', ID = ID, Target = Target)

#--------------------------------------------------------
@app.route('/search', methods=['POST'])
def search():
    sType = request.form.get('stype')
    if sType == "Location": sType = "locName"
    sRegex = request.form.get('sregex')

    debug(f"You entered a search for {sType} looking for: {sRegex}")

    sql = f"SELECT * FROM obsTarget WHERE {sType} RLIKE \'{sRegex}\';"
    debug(f"Search SQL: {sql}")

    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        Target = cursor.fetchall()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)

    if cursor.rowcount == 0:
        return render_template('DoesNotExist.html', ID = ID, Type = "Target")

    return render_template('/targetSearch.html', ID = ID, Target = Target)

#--------------------------------------------------------
@app.route('/add', methods=['POST']) # TODO set session default to last created
def add():
    SesID =  datetime.now().strftime("%Y%m%d")
    weather, ctime = refreshData()
    return render_template('targetAdd.html', SesID = SesID, weather = weather, ctime = ctime, binningItems = binningItems, ExpType = ExpType)
    
#--------------------------------------------------------
@app.route('/addok', methods=['POST'])
def addok():
    #Name, EqID, Objectives, Notes
    if request.form['action'] == 'Add Target':
        # make sure equipment id is real
        SesID = request.form.get('SessionID')
        sql = f"SELECT * FROM obsSession WHERE Date = '{SesID}';"
        conn, cursor = openDB()
        try:
            cursor.execute(sql)
            Profile = cursor.fetchone()
        except mysql.connector.Error as err:
            return render_template('SQLerror.html', err=err)
        closeDB(conn, cursor)
        if cursor.rowcount == 0:
            return render_template('DoesNotExist.html', ID = SesID, Type = "Session")
    
        #print(f"DIAG SessionID  {request.form.get('SessionID')}")

        envInfo = refreshData()  # ya, I know, did it again, but want it fresh for sql
        sql = f"INSERT INTO obsTarget set \
        Target = \"{request.form.get('Target')}\", \
        CommonName = \"{request.form.get('CommonName')}\", \
        ImageType = \"{request.form.get('ImageType')}\", \
        SessionID = \"{request.form.get('SessionID')}\", \
        Date = \"{request.form.get('Date')}\", \
        Weather = \"{request.form.get('Weather')}\", \
        NumImages = {request.form.get('NumImages')}, \
        Duration = {request.form.get('Duration')}, \
        Gain = {request.form.get('Gain')}, \
        CamOffset = {request.form.get('Offset')}, \
        Binning = \"{request.form.get('Binning')}\", \
        CamTemp = {request.form.get('CamTemp')}, \
        Notes = \"{request.form.get('Notes')}\", \
        PostProc = \"{request.form.get('PostProc')}\" \
        ;"
        conn, cursor = openDB()
        print(f"DIAG add sql stmt: {sql}")
        try:
            cursor.execute(sql)
            conn.commit()
        except mysql.connector.Error as err:
            return render_template('SQLerror.html', err=err)
        closeDB(conn, cursor)

    else:
        pass
    
    return redirect('/')

#--------------------------------------------------------
@app.route('/modify', methods=['POST'])
def modify():
    ID = request.form.get('ID')
    #print(f"DIAG ID from modify request: {ID}")
    sql = f"SELECT * FROM obsTarget WHERE ID={ID};"
    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        Target = cursor.fetchone()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)
        
    if cursor.rowcount == 0:
        return render_template('DoesNotExist.html', ID = ID, Type = "Target")
    
    return render_template('targetModify.html', ID = ID, Target = Target, binningItems = binningItems, ExpType = ExpType)

#--------------------------------------------------------
@app.route('/modifyok', methods=['POST'])
def modifyok():
    if request.form['action'] == 'Modify Target':
        # make sure session ID is valid
        ID = request.form.get('SessionID')
        sql = f"SELECT * FROM obsSession WHERE Date={ID};"
        conn, cursor = openDB()
        try:
            cursor.execute(sql)
            Session = cursor.fetchone()
        except mysql.connector.Error as err:
            return render_template('SQLerror.html', err=err)
        closeDB(conn, cursor)
        if cursor.rowcount == 0:
            return render_template('DoesNotExist.html', ID = ID, Type = "Session")

        # bring back in the Profile so we can set values for selection boxes back to original
        ID = request.form.get('ID')
        sql = f"SELECT * FROM obsTarget WHERE ID={ID};"
        conn, cursor = openDB()
        try:
            cursor.execute(sql)
            Profile = cursor.fetchone()
        except mysql.connector.Error as err:
            return render_template('SQLerror.html', err=err)
        closeDB(conn, cursor)
        if cursor.rowcount == 0:
            return render_template('DoesNotExist.html', ID = ID, Type = "Target")
        
        # ImageType and Binning return None if not selected, so we have to set to orig values if so
        ImageType = request.form.get('ImageType')
        if ImageType == None:
            ImageType = Profile[3]

        Binning = request.form.get('Binning')
        if Binning == None:
            Binning = Profile[11]

        ID = request.form.get('ID')
        sql = f"UPDATE obsTarget set \
        Target = \"{request.form.get('Target')}\", \
        CommonName = \"{request.form.get('CommonName')}\", \
        SessionID = \"{request.form.get('SessionID')}\", \
        ImageType = \"{ImageType}\", \
        Date = \"{request.form.get('Date')}\", \
        Weather = \"{request.form.get('Weather')}\", \
        NumImages = \"{request.form.get('NumImages')}\", \
        Duration = {request.form.get('Duration')}, \
        Gain = \"{request.form.get('Gain')}\", \
        CamOffset = \"{request.form.get('CamOffset')}\", \
        Binning = \"{Binning}\", \
        CamTemp = \"{request.form.get('CamTemp')}\", \
        Notes = \"{request.form.get('Notes')}\", \
        PostProc = \"{request.form.get('PostProc')}\" \
        WHERE ID=\"{ID}\";"
        conn, cursor = openDB()
        try:
            #print(f"DIAG: sql statement: {sql}")
            cursor.execute(sql)
            conn.commit()
        except mysql.connector.Error as err:
            return render_template('SQLerror.html', err=err)
        closeDB(conn, cursor)
        
    else:
        pass
    
    return redirect('/')

#--------------------------------------------------------
@app.route('/removeok', methods=['POST'])
def removeok():
    ID = request.form.get('ID')
    sql = f"DELETE FROM obsTarget WHERE ID={ID};"
    conn, cursor = openDB()
    try:
        #print(f"DIAG: Delete sql: {sql}")
        cursor.execute(sql)
        conn.commit()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)

    return redirect('/')

#--------------------------------------------------------
@app.route('/doesNotExist', methods=['POST']) 
def doesNotExit(message):
    return redirect('/displayMsg', message=message)

#--------------------------------------------------------
@app.route('/refresh', methods=['POST'])
def refresh():
    return redirect('/')

#--------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5010, debug=True)

'''
CREATE TABLE `obsTarget` (
  `id` int NOT NULL AUTO_INCREMENT,
  `Target` varchar(20) DEFAULT NULL,
  `CommonName` varchar(50) DEFAULT NULL,
  `SessionID` int DEFAULT NULL,
  `Date` datetime DEFAULT NULL,
  `Weather` varchar(160) DEFAULT NULL,
  `NumImages` int DEFAULT NULL,
  `Gain` float DEFAULT NULL,
  `Offset` float DEFAULT NULL,
  `Binning` varchar(4) DEFAULT NULL,
  `CamTemp` float DEFAULT NULL,
  `Notes` varchar(200) DEFAULT NULL,
  `PostProc` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=latin1
'''
