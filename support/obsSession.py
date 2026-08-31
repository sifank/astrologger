#!/usr/bin/python3
# Program: obsSession
# Version: 20260219
# Author:  Sifan Kahale
# Desc:    Form for entering session data into db

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm, CSRFProtect
import mysql.connector, os
import ephem, math
from datetime import datetime, timezone

#--------------------------------------------------------
app = Flask(__name__)

ID = 0

#--------------------------------------------------------
# Database Configuration
db_config = {
    'host': 'depoe',
    'user': 'sifan',
    'password': 'all4Sky',
    'database': 'kahaleobs'
}

#--------------------------------------------------------
# Open Database
def openDB():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
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
    0 - GPSfix
    1 - Local time
    2 - UTC time
    3 - Latitude
    4 - Longitude
    5 - Altitude
    6 - Evening Twilight
    7 - Morning Twilight
    8 - Moon rise
    9 - Moon set
    10 - Moon percent
    '''
    ctime = datetime.now().strftime("%Y%m%d")
    utime = datetime.now(timezone.utc).strftime("%Y%m%d %H:%M:%S")
    sql = "select GPSfix, CTime, UTime, locLat, locLon, locAlt from gpsloc;"
    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        EnvData = cursor.fetchone()
        envInfo = list(EnvData)
        closeDB(conn, cursor)
    except mysql.connector.Error as err: 
        envInfo = [f"No Fix", {ctime}, {utime}, 44.867813, -124.040438, 20.0]
    closeDB(conn, cursor)

    ko = ephem.Observer()
    ko.lon = math.radians(envInfo[4])
    ko.lat = math.radians(envInfo[3])
    ko.elevation = envInfo[5]
    ko.epoch = datetime.now().strftime("%Y")
    ko.pressure = 0
    ko.horizon = '-12'
    ko.date = ephem.now()
    moon = ephem.Moon(ko)
    sun = ephem.Sun(ko)
    
    envInfo.append(ephem.localtime(ko.next_setting(sun, use_center=True)).strftime("%Y-%m-%d %H:%M:%S"))
    envInfo.append(ephem.localtime(ko.next_rising(sun, use_center=True)).strftime("%Y-%m-%d %H:%M:%S"))
    envInfo.append(ephem.localtime(ko.next_rising(moon)).strftime("%Y-%-m-%d %H:%M:%S"))
    envInfo.append(ephem.localtime(ko.next_setting(moon)).strftime("%Y-%m-%d %H:%M:%S"))
    envInfo.append(round(moon.phase,1)) 
    return  ctime, envInfo

#--------------------------------------------------------
@app.route('/')
def index():
    conn, cursor = openDB()
    if conn == "None":
        return render_template('SQLerror.html', err="Can not open Database")
    try:
        cursor.execute("SELECT * FROM obsSession")
        Session = cursor.fetchall()
        cursor.execute("SELECT * FROM obsEquipment")
        Profiles = cursor.fetchall()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)
    
    return render_template('sessionMain.html', Session = Session, Profiles = Profiles)

#--------------------------------------------------------
@app.route('/details', methods=['POST'])
def details():
    ID = request.form.get('ID')
    sql = f"SELECT * FROM obsSession WHERE ID={ID};"
    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        Session = cursor.fetchone()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)
        
    if cursor.rowcount == 0:
        return render_template('DoesNotExist.html', ID = ID, Type = "Session")
    
    return render_template('/sessionDetails.html', ID = ID, Session = Session)

#--------------------------------------------------------
@app.route('/add', methods=['POST'])  # TODO reduce equip table length
def add():
    ctime, envInfo = refreshData()
    #print(f"Ctime in add: {ctime}")
    return render_template('sessionAdd.html', envInfo=envInfo, ctime=ctime)
    
#--------------------------------------------------------
@app.route('/addok', methods=['POST'])
def addok():
    #Name, EqID, Objectives, Notes
    if request.form['action'] == 'Add Session':    
        ctime, envInfo = refreshData()  # ya, I know, did it again, but want it fresh for sql

        # make sure equipment id is real
        EqID = request.form.get('EQname')
        sql = f"SELECT * FROM obsEquipment WHERE name={EqID};"
        print(f"DIAG: testing equip id {EqID} - sql: {sql}")
        conn, cursor = openDB()
        try:
            cursor.execute(sql)
            Profile = cursor.fetchone()
        except mysql.connector.Error as err:
            return render_template('DoesNotExist.html', ID = EqID, Type = "Equipment Profile")
        closeDB(conn, cursor)
    
        sql = f"INSERT INTO obsSession set \
        Date = \"{request.form.get('Date')}\", \
        locName = \"{request.form.get('Name')}\", \
        EquipProfile = \"{request.form.get('EQname')}\", \
        locLong = \"{request.form.get('Longitude')}\", \
        locLat = \"{request.form.get('Latitude')}\", \
        locHeight = \"{request.form.get('Altitude')}\", \
        EveningTwilight = \"{envInfo[6]}\", \
        MorningTwilight = \"{envInfo[7]}\", \
        moonRise = \"{envInfo[8]}\", \
        moonSet = \"{envInfo[9]}\", \
        moonPercent = \"{envInfo[10]}\", \
        Objective = \"{request.form.get('Objectives')}\", \
        Notes = \"{request.form.get('Notes')}\" \
        ;"
        conn, cursor = openDB()
        try:
            print(f"DIAG add sql stmt: {sql}")
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
    sql = f"SELECT * FROM obsSession WHERE ID={ID};"
    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        Session = cursor.fetchone()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)
        
    if cursor.rowcount == 0:
        return render_template('DoesNotExist.html', ID = ID, Type = "Session")
    
    return render_template('sessionModify.html', ID = ID, Session = Session)

#--------------------------------------------------------
@app.route('/modifyok', methods=['POST'])
def modifyok():
    if request.form['action'] == 'Modify Session':
        ID = request.form.get('ID')
        sql = f"UPDATE obsSession set \
        Date = \"{request.form.get('Date')}\", \
        locName = \"{request.form.get('locName')}\", \
        EquipProfile = \"{request.form.get('EquipProfile')}\", \
        locLong = \"{request.form.get('locLat')}\", \
        locLat = \"{request.form.get('locLat')}\", \
        locHeight = \"{request.form.get('locHeight')}\", \
        EveningTwilight = \"{request.form.get('EveningTwilight')}\", \
        MorningTwilight = \"{request.form.get('MorningTwilight')}\", \
        moonRise = \"{request.form.get('moonRise')}\", \
        moonset = \"{request.form.get('moonset')}\", \
        moonPercent = \"{request.form.get('moonPercent')}\", \
        Objective = \"{request.form.get('Objective')}\", \
        Notes = \"{request.form.get('Notes')}\" \
        WHERE ID=\"{ID}\";"
        conn, cursor = openDB()
        try:
            cursor.execute(sql)
            conn.commit()
            #print(f"DIAG: sql statement: {sql}")
        except mysql.connector.Error as err:
            return render_template('SQLerror.html', err=err)
        closeDB(conn, cursor)
        
    else:
        pass
    
    return redirect('/')

'''
#--------------------------------------------------------
@app.route('/remove', methods=['POST'])
def remove():
    ID = request.form.get('ID')
    sql = f"SELECT * FROM obsSession WHERE ID={ID};"
    conn, cursor = openDB()
    #print(f"DIAG: Delete sql: {sql}")
    try:
        cursor.execute(sql)
        Session = cursor.fetchone()
        print(f"DIAG: remove returned Session: {Session}")
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)
        
    if cursor.rowcount == 0:
        return render_template('DoesNotExist.html', ID = ID, Type = "Session")
    
    return render_template('sessionRemove.html', ID = ID, Session = Session)
'''

#--------------------------------------------------------
@app.route('/removeok', methods=['POST'])
def removeok():
    ID = request.form.get('ID')
    sql = f"DELETE FROM obsSession WHERE ID={ID};"
    conn, cursor = openDB()
    try:
        print(f"DIAG: Delete sql: {sql}")
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
@app.route('/rtnmain', methods=['POST'])
def rtnmain():
    #print(f"DIAG got to rtnmain")
    return redirect('<a href="http://depoe:5000"> </a>')
    #return redirect('/')

#--------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5010, debug=True)

'''
CREATE TABLE `obsSession` (
  `id` int NOT NULL AUTO_INCREMENT,
  `Date` datetime NOT NULL,
  `locName` varchar(20) NOT NULL,
  `EquipProfile` int DEFAULT NULL,
  `locLong` double DEFAULT NULL,
  `locLat` double DEFAULT NULL,
  `locHeight` double DEFAULT NULL,
  `EveningTwilight` datetime DEFAULT NULL,
  `MorningTwilight` datetime DEFAULT NULL,
  `moonRise` datetime DEFAULT NULL,
  `moonset` datetime DEFAULT NULL,
  `moonPercent` int DEFAULT NULL,
  `Objective` varchar(50) DEFAULT NULL,
  `Notes` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=latin1
'''
