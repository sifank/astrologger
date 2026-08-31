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
DEBUG = True

#--------------------------------------------------------
# --- set equipment options box contents
OTAItems = ['None', 'C14', 'C11', 'ES152', 'Dwarf 3']
ReducerItems = ['None', '.2', '.7']
MountItems = ['None', 'CGX-L', '10Micron', 'CGE', 'Tripod']
ControllerItems = ['None', 'kanto', 'kobs', 'fieldkobs', 'taft', 'depoe', 'Phone']
FocuserItems = ['None', 'Gemini EAF', 'ASI-EAF', 'Esatto', 'Pegasus']
RotatorItems = ['None', 'Falcon', 'Arco']
GuiderItems = ['None', 'ASI OAG + ASI174', 'Celestron OAG + ASI174', 'Orion 80mm + ASI174']
FilterItems = ['None', 'ASI EFW-S', 'ASI EFW-L', 'L-CCD', 'Semi-APO', 'CLS CCD', 'Solar', 'Moon', 'Planet', 'Polarizer', 'VIS', 'Astro', 'Dual']
CameraItems = ['None', 'ASI294mc Pro', 'ASI1600mm Pro', 'ASI2600mm Pro', 'Dwarf Tele', 'Dwarf Wide']
SearchType = ['Date', 'Location', 'OTA', 'Mount','Camera','Filter']

#--------------------------------------------------------
# Diag printout if DEBUG is true
def debug(msg):
    if DEBUG == True:
        print(f"DIAG {msg}")

    return

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
# --- calc ephem data from give datetime object, returns envInfo Structure
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
def refreshData(reqDate):  # reqDate is a datetime object
    sql = "select GPSfix, CTime, UTime, locLat, locLon, locAlt from gpsloc;"
    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        EnvData = cursor.fetchone()
        envInfo = list(EnvData)
        closeDB(conn, cursor)
    except mysql.connector.Error as err: 
        rtime = datetime.now().strftime("%Y%m%d")
        utime = datetime.now(timezone.utc).strftime("%Y%m%d %H:%M:%S")
        reqDate = utime
        envInfo = [f"No Fix", {rtime}, {utime}, 44.867813, -124.040438, 20.0]
    closeDB(conn, cursor)

    ko = ephem.Observer()
    ko.epoch = reqDate.strftime("%Y")
    ko.date = ephem.date(reqDate)
    ko.lon = math.radians(envInfo[4])
    ko.lat = math.radians(envInfo[3])
    ko.elevation = envInfo[5]
    ko.pressure = 0
    ko.horizon = '-12'
    moon = ephem.Moon(ko)
    sun = ephem.Sun(ko)
    
    envInfo.append(ephem.localtime(ko.next_setting(sun, use_center=True)).strftime("%H:%M:%S"))
    envInfo.append(ephem.localtime(ko.next_rising(sun, use_center=True)).strftime("%H:%M:%S"))
    envInfo.append(ephem.localtime(ko.next_rising(moon)).strftime("%H:%M:%S"))
    envInfo.append(ephem.localtime(ko.next_setting(moon)).strftime("%H:%M:%S"))
    envInfo.append(round(moon.phase,1)) 
    return  envInfo


#--------------------------------------------------------
# sql = select Date, locName from obsSession where YEAR(dtDate) = 2026;
@app.route('/')
def index():
    conn, cursor = openDB()
    if conn == "None":
        return render_template('SQLerror.html', err="Can not open Database")
    try:
        cursor.execute("SELECT * FROM obsSession ORDER BY Date DESC;")
        Session = cursor.fetchall()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)
    
    return render_template('sessionMain.html', Session = Session, SearchType = SearchType)

#--------------------------------------------------------
@app.route('/details', methods=['POST'])
def details():
    ID = request.form.get('ID')
    sql = f"SELECT * FROM obsSession WHERE ID={ID};"

    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        Session = cursor.fetchone()
        #return render_template('SQLerror.html', err=sql)
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
        
    if cursor.rowcount == 0:
        return render_template('DoesNotExist.html', ID = ID, Type = "Session")

    sql = f"SELECT * FROM obsTarget WHERE SessionID = {Session[1]};"
    try:
        cursor.execute(sql)
        print(f"Targets sql: {sql}")
        Targets = cursor.fetchall()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)
    closeDB(conn, cursor)

    dtDate = Session[2]
    #debug(f"dtDate before test: {dtDate}, Type: {type(dtDate)}")
    if dtDate is None:
        dtDate = datetime.strptime(Session[1],"%Y%m%d").astimezone(timezone.utc)

    #debug(f"dtDate @ render: {dtDate}, Type: {type(dtDate)}")
    envInfo = refreshData(dtDate)
    #debug(f"envinfo date: {dtDate}, {envInfo}")
    return render_template('/sessionDetails.html', ID = ID, Session = Session, Targets = Targets, envInfo = envInfo)

#--------------------------------------------------------
@app.route('/search', methods=['POST'])
def search():
    sType = request.form.get('stype')
    if sType == "Location": sType = "locName"
    sRegex = request.form.get('sregex')

    debug(f"You entered a search for {sType} looking for: {sRegex}")

    sql = f"SELECT * FROM obsSession WHERE {sType} RLIKE \'{sRegex}\';"
    debug(f"Search SQL: {sql}")

    conn, cursor = openDB()
    try:
        cursor.execute(sql)
        Session = cursor.fetchall()
    except mysql.connector.Error as err:
        return render_template('SQLerror.html', err=err)

    if cursor.rowcount == 0:
        return render_template('DoesNotExist.html', ID = ID, Type = "Session")
        # get the targets associated with this session

    return render_template('/sessionSearch.html', ID = ID, Session = Session)

#--------------------------------------------------------
@app.route('/add', methods=['POST'])  
def add():
    ctime = datetime.now().strftime("%Y%m%d")
    reqDate = datetime.now().astimezone(timezone.utc)
    envInfo = refreshData(reqDate)
    return render_template('sessionAdd.html', envInfo=envInfo, ctime=ctime, OTAItems = OTAItems, ReducerItems = ReducerItems, MountItems = MountItems, ControllerItems = ControllerItems, FocuserItems = FocuserItems, RotatorItems = RotatorItems, GuiderItems = GuiderItems,  FilterItems = FilterItems, CameraItems = CameraItems)
    
#--------------------------------------------------------
@app.route('/addok', methods=['POST'])
def addok():
    if request.form['action'] == 'Add Session':
        sql = f"INSERT INTO obsSession set \
        Date = \"{request.form.get('Date')}\", \
        dtDate = \"{request.form.get('dtDate')}\", \
        locName = \"{request.form.get('Name')}\", \
        locLong = \"{request.form.get('Longitude')}\", \
        locLat = \"{request.form.get('Latitude')}\", \
        locHeight = \"{request.form.get('Altitude')}\", \
        OTA = \"{request.form.get('OTA')}\", \
        Reducer = \"{request.form.get('Reducer')}\", \
        Mount = \"{request.form.get('Mount')}\", \
        Controller = \"{request.form.get('Controller')}\", \
        Focuser = \"{request.form.get('Focuser')}\", \
        Rotator = \"{request.form.get('Rotator')}\", \
        Guider = \"{request.form.get('Guider')}\", \
        Filter = \"{request.form.get('Filter')}\", \
        Camera = \"{request.form.get('Camera')}\", \
        Objective = \"{request.form.get('Objectives')}\", \
        Notes = \"{request.form.get('Notes')}\" \
        ;"
        conn, cursor = openDB()
        try:
            #debug(f"DIAG add sql stmt: {sql}")
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
    
    debug(f"\nModify for ID: {ID} OTA: {Session[9]} Notes: {Session[8]} Objective: {Session[7]}\n")
    return render_template('sessionModify.html', ID = ID, Session = Session, OTAItems = OTAItems, ReducerItems = ReducerItems, MountItems = MountItems, ControllerItems = ControllerItems, FocuserItems = FocuserItems, RotatorItems = RotatorItems, GuiderItems = GuiderItems,  FilterItems = FilterItems, CameraItems = CameraItems)

#--------------------------------------------------------
@app.route('/modifyok', methods=['POST'])
def modifyok():
    if request.form['action'] == 'Submit':
        ID = request.form.get('ID')
        sql = f"SELECT * FROM obsSession WHERE ID={ID};"
        conn, cursor = openDB()
        try:
            cursor.execute(sql)
            Session = cursor.fetchone()
        except mysql.connector.Error as err:
            return render_template('SQLerror.html', err=err)
        closeDB(conn, cursor)

        OTA = request.form.get('OTA')
        if OTA == None:
            OTA = Session[9]

        Reducer = request.form.get('Reducer')
        if Reducer == None:
            Reducer = Session[10]

        Mount = request.form.get('Mount')
        if Mount == None:
            Mount = Session[11]

        Focuser = request.form.get('Focuser')
        if Focuser == None:
            Focuser = Session[13]

        Controller = request.form.get('Controller')
        if Controller == None:
            Controller = Session[14]

        Rotator = request.form.get('Rotator')
        if Rotator == None:
            Rotator = Session[14]

        Guider = request.form.get('Guider')
        if Guider == None:
            Guider =Session[15]

        Filter = request.form.get('Filter')
        if Filter == None:
            Filter =Session[16]

        Camera = request.form.get('Camera')
        if Camera == None:
            Camera = Session[17]

        ID = request.form.get('ID')
        sql = f"UPDATE obsSession set \
        Date = \"{request.form.get('Date')}\", \
        dtDate = \"{request.form.get('dtDate')}\", \
        locName = \"{request.form.get('Name')}\", \
        locLong = \"{request.form.get('Longitude')}\", \
        locLat = \"{request.form.get('Latitude')}\", \
        locHeight = \"{request.form.get('Altitude')}\", \
        Objective = \"{request.form.get('Objectives')}\", \
        Notes = \"{request.form.get('Notes')}\", \
        OTA = \"{OTA}\", \
        Reducer = \"{Reducer}\", \
        Mount = \"{Mount}\", \
        Controller = \"{Controller}\", \
        Focuser = \"{Focuser}\", \
        Rotator = \"{Rotator}\", \
        Guider = \"{Guider}\", \
        Filter = \"{Filter}\", \
        Camera = \"{Camera}\" \
        WHERE ID=\"{ID}\";"
        debug(f"\nModifyOk form for ID: {ID} OTA: {request.form.get('OTA')} Notes: {request.form.get('Notes')} Objective: {request.form.get('Objectives')}\n\n")
        conn, cursor = openDB()
        try:
            cursor.execute(sql)
            conn.commit()
            #debug(f"\nsql statement: {sql}\n")
        except mysql.connector.Error as err:
            return render_template('SQLerror.html', err=err)
        closeDB(conn, cursor)
        
    else:
        pass
    
    return redirect('/')

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
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `Date` varchar(20) DEFAULT NULL,
  `locName` varchar(40) DEFAULT NULL,
  `locLong` double DEFAULT NULL,
  `locLat` double DEFAULT NULL,
  `locHeight` double DEFAULT NULL,
  `Objective` varchar(150) DEFAULT NULL,
  `Notes` varchar(100) DEFAULT NULL,
  `OTA` varchar(20) DEFAULT NULL,
  `Reducer` varchar(20) DEFAULT NULL,
  `Mount` varchar(20) DEFAULT NULL,
  `Controller` varchar(20) DEFAULT NULL,
  `Focuser` varchar(20) DEFAULT NULL,
  `Rotator` varchar(20) DEFAULT NULL,
  `Guider` varchar(25) DEFAULT NULL,
  `Filter` varchar(20) DEFAULT NULL,
  `Camera` varchar(25) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `Date` (`Date`)
) ENGINE=InnoDB
'''
