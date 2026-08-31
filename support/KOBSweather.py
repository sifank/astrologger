#!/usr/bin/python3
# File:         KOBSweather.py
# Version:      20210311
# Authur:       Sifan
# Desc:         retrieves weather data from mysql for the INDI KOBSweather driver

import sys, os
import mysql.connector

MYHost = "localhost"
MYUser = "sifan"
MYPwd = "all4Sky"
MYDb = "kahaleobs"
MYTbl = "sensordata"

#--------------------------------------------------------
# Main - initialize
#--------------------------------------------------------
# open up mysql connector
try:
    conn = mysql.connector.connect (host=MYHost, user=MYUser, passwd=MYPwd, db=MYDb)
    cursor = conn.cursor()
except mysql.connector.Error as e:
    print("DB Error opening db %d:  %s" % (e.args[0], e.args[1]))
    sys.exit(1)

#------------------------------------------------------
# Create data file and print html page
#------------------------------------------------------
# read in from db
try:
    cursor.execute ("SELECT * FROM %s ORDER BY time DESC LIMIT 1" % MYTbl)
except:
    print("DB Error reading servers table")
    sys.exit(1)

# read db and create csv records
for (time, 
  kobsTemp, 
  kobsHum, 
  kobsDp, 
  kobsPres,
  kobsLux, 
  kobsSkyTemp, 
  allskyTemp, 
  allskyHum, 
  allskyDp, 
  allskyPres, 
  allskyLux, 
  allskySkyTemp, 
  allskyWSpeed, 
  allskyWGust, 
  allskyWDir, 
  domeTemp, 
  domeHum, 
  domeDp, 
  domePres, 
  domeLux, 
  domeSkyTemp) in cursor:

    print("%s,%s,%s,%s,%s,%s,%s,%s\n" % (allskyTemp, allskyHum, allskyDp, allskyPres, allskyWSpeed, allskyWGust, allskySkyTemp, allskyLux))
    
cursor.close()

