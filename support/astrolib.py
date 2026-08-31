#!/usr/bin/python3
# Program: kobsUtil.py
# Desc:    misc functions (from PanSTARRs ps1util)
# Usage:   no arguments
# Author:  Haydn & Sifan
# Version: 20200206

import sys, os, glob, math, pwd, re
import socket, subprocess, time, numpy, platform
import mysql.connector

#----------------------------------------------------------
# Configuration data 
secsPerHour = 60 * 60
secsPerDay  = 24 * secsPerHour
cachedShortHostName = None
ZERO_DATE_TIME = '0000-00-00 00:00:00'

host = "kiana"
user = "sifan"
password = "all4Sky"
database = "kahaleobs"

#----------------------------------------------------------
def runCmd(cmd, checkResultOk=True, debug=False):
    OK    = 0
    ERROR = 1
    if debug:
        sys.stderr.write("running: %s\n" % cmd)

    try:
    	aOutput = subprocess.run(cmd, shell=True, 
                  check=True, 
                  stderr = subprocess.PIPE, 
                  stdout=subprocess.PIPE, 
                  universal_newlines=True)
    except:
        if checkResultOk:
            sys.stderr.write("unable to run '%s'!\n" % cmd)
            if debug:
                sys.stderr.write("aResult=%s\n" % aResult)
                sys.stderr.write("aOutput=%s\n" % aOutput)
            sys.exit(ERROR)

    return aOutput.stdout

#------------------------------------------------
' mysqlQuery(sqlQuery) mysql query function - returns first line'
def mysqlQuery(sqlQuery):
        # Connect to db
        db = mysql.connector.connect(user=user,password=password,database=database, host=host)
        cursor=db.cursor()

        try:
                # Execute passed in query
                cursor.execute(sqlQuery)
                data = cursor.fetchone()
        except:
                print("Executing Sql Query failed")
                raise

        return data

#------------------------------------------------
' mysqlCmd(sqlCMD) execute mysql command - no data return'
def mysqlCmd(sqlCMD):
        # Connect to db
        db = mysql.connector.connect(user=user,password=password,database=database, host=host)
        cursor=db.cursor()

        try:
                # Execute passed in query
                cursor.execute(sqlCMD)
                db.commit()
        except:
                print(r"Executing Sql Command failed")
                db.rollback()
                raise

#----------------------------------------------------------
# Expects to return a single row selected by the given query via the given
# MySQL DB connection.
def selectOneRow(connection, query):
    selectCursor = connection.cursor()
    selectCursor.execute(query)
    if selectCursor.rowcount != 1:
        raise RuntimeError("selectOneRow(%s) resulted in %d rows!" %
                           (query, selectCursor.rowcount))
    return selectCursor.fetchone()

#----------------------------------------------------------
# Expects to return a single value from a single row selected by the given
# query via the given MySQL DB connection.
def selectOneValue(connection, query):
    return selectOneRow(connection, query)[0]


#----------------------------------------------------------
# Returns the first part of the hostname -- strips off anything beginning at
# the first period.
def getShortHostName():
    global cachedShortHostName
    if cachedShortHostName is not None:
        return cachedShortHostName
    cachedShortHostName = shortenHostName(socket.gethostname())
    return cachedShortHostName


#----------------------------------------------------------
# Given a short hostname or FQDN, returns the part before the first period.
def shortenHostName(aHostName):
    aHostName = aHostName.lower()
    dot = aHostName.find('.')
    if dot != -1:
        aHostName = aHostName[0:dot]
    # The dome controller thinks its name is "domecontroller".
    if aHostName == 'domecontroller':
        aHostName = 'Dome'
    # The TCC thinks its name is "panstarrs-tcc".
    if aHostName == 'panstarrs-tcc':
        aHostName = 'TCC'
    return aHostName


#----------------------------------------------------------
def deNullify(value):
    if value is None:
        return "NULL"
    return "%0.3f" % value

#----------------------------------------------------------
def pluralize(n):
    if int(n) == 1:
        return ''
    return 's'

def c2f(tempC):
    # Returns the Fahrenheit temperature.
    if tempC is None:
        return None
    return tempC * 9.0 / 5.0 + 32


#----------------------------------------------------------
def f2c(tempF):
    # Returns the Celsius temperature.
    if tempF is None:
        return None
    return (tempF - 32) * 5.0 / 9.0

#----------------------------------------------------------
def isAlive(ip):
    cmd = "ping -c1 -w1 %s" % ip
    aResult = subprocess.call(cmd,
                              shell=True,
                              stdout=open('/dev/null', 'w'),
                              stderr=subprocess.STDOUT)
    if aResult == 0:
        return True
    return False

#----------------------------------------------------------
# Converts backslash into backslash-backslash, and quotes into
# backslash quotes, for preparing things to go into the database.
def backslashify(aStr):
    return MySQLdb.escape_string(aStr) 


#----------------------------------------------------------
# Converts True/False into 1/0.
def boolToInt(b):
    assert(b in [True, False])
    if b:
        return 1
    return 0


#----------------------------------------------------------
# Returns the sine of an angle in degrees.
def degSine(deg):
    return math.sin(math.radians(deg))


#----------------------------------------------------------
# Returns the cosine of an angle in degrees.
def degCosine(deg):
    return math.cos(math.radians(deg))


#----------------------------------------------------------
# Returns the arc cosine of x in degrees.
def degArcCosine(x):
    return math.degrees(math.acos(x))


#----------------------------------------------------------
def calcSphericalDistance(alt0, az0, alt1, az1):
    # The formula for this comes from:
    #   http://en.wikipedia.org/wiki/Great-circle_distance
    # The altitudes and azimuths must be in degrees!
    deltaAlt     = alt0 - alt1
    deltaAzimuth = az0  - az1
    return degArcCosine(degCosine(deltaAlt) -
                        degCosine(alt0) *
                        degCosine(alt1) *
                        (1.0 - degCosine(deltaAzimuth)))


#----------------------------------------------------------
# Returns the Hardie Airmass from the altitude in degrees.
# From the code in:
# java/sources/eap/sky/earth/atmosphere/airmass/HardieAirmass.java
# which in turn references:
# The Hardie Airmass formula.
# Hardie, R. H. 1962. In Astronomical Techniques. Hiltner, W. A., ed. Chicago:
# University of Chicago Press, 184?. LCCN 62009113.
# Note the SLALIB software package also uses the same formula.
def calculateAirmass(altDeg):
    z = math.radians(90.0 - altDeg)
    s = 1.0 / (math.cos(min(1.52, z))) - 1.0
    return 1.0 + s*(0.9981833
               - s*(0.002875
               + s*(0.0008083)))


#----------------------------------------------------------
# Returns the altitude in degrees for the given Hardie Airmass.
# From the code in:
# java/sources/eap/sky/earth/atmosphere/airmass/HardieAirmass.java
# This code iterates until it finds the correct value to within 1 part in
# a million.
def calculateAltitudeFromAirmass(airmass):
    a = -0.002875
    b = 0.9981833
    s = 0
    while True:
        c = 1.0 - airmass - 0.0008083 * s * s * s
        q = -0.5 * (b + math.sqrt(b * b - 4.0 * a * c))
        next_s = c / q
        if abs(next_s - s) < 1e-6:
            return 90.0 - math.degrees(math.acos (1.0 / (next_s + 1.0)))
        s = next_s

#----------------------------------------------------------
def monthFmt (x, ignoredPos=None):
    # When graphing, show the day of the month, with the month below it.
    
    return time.strftime('%d\n%b', time.gmtime(x))


#----------------------------------------------------------
def mdyFmt (x, ignoredPos=None):
    # When graphing, show the month/day, with the year below it.
    
    return time.strftime('%b%d\n%Y', time.gmtime(x))


#----------------------------------------------------------
def calcAverage(vals):
    n = len(vals)
    aSum = 0.0
    for v in vals:
        aSum += v
    return aSum / n


#----------------------------------------------------------
def calcMinimum(vals):
    minVal = None
    for v in vals:
        if minVal is None or v < minVal:
            minVal = v
    return minVal


#----------------------------------------------------------
def calcRootMeanSquare(vals):
    n = len(vals)
    sumOfSquares = 0.0
    for v in vals:
        sumOfSquares += math.pow(v, 2)
    return math.sqrt(sumOfSquares / n)


#----------------------------------------------------------
def calcMedian(vals):
    sortedVals = list(vals)
    sortedVals.sort()
    n = len(sortedVals)
    if n % 2 == 0:
        mid = int((n - 1) / 2)
        return (sortedVals[mid] + sortedVals[mid+1]) / 2.0
    return sortedVals[int(n / 2)]
    

#----------------------------------------------------------
def calcMode(vals):
    # This should match the values for binrange on lines 17 and 28 of
    # ps/plot/seeing.py.
    rng = numpy.arange(0, 3.5, 0.02)
    
    histogram = numpy.histogram(vals, rng)[0]
    mode = None
    maxFrequency = max(histogram)
    
    for i in range(len(histogram)):
        if histogram[i] == maxFrequency:
            return rng[i]
    return mode


#----------------------------------------------------------
def calcMomentAboutMean(vals, r):
    aSum = 0.0
    mean = calcAverage(vals)
    n = len(vals)
    for v in vals:
        aSum += pow(v - mean, r) / n
    return aSum


#----------------------------------------------------------
def calcMomentCoefficientOfSkewness(vals):
    # Denoted by statisticians as g3.
    # skewness = (sqrt(n * (n - 1)) / (n - 2)) * m3 / (m2 ^ (3/2))
    # Mx = sum((val[i] - mean)^r) / n)
    n = len(vals)
    if (n <= 2):
        return None
    m3 = calcMomentAboutMean(vals, 3)
    m2 = calcMomentAboutMean(vals, 2)
    if m2 == 0:
        return None
    return (math.sqrt(n * (n - 1)) / (n - 2)) * m3 / pow(m2, 1.5)


#----------------------------------------------------------
def calcSum(vals):
    cnt = 0
    aSum = 0
    for v in vals:
        aSum += v
        cnt += 1
    if cnt == 0:
        return 0
    return aSum / cnt


#----------------------------------------------------------
def calcDewpoint(temperature, humidity):
    if temperature is None or humidity is None:
        return None
    if humidity < 0.5 or humidity > 100:
        return None
    # From: http://andrew.rsmas.miami.edu/bmcnoldy/Humidity.html
    return (243.04 * (math.log(humidity / 100.0) + 
                      ((17.625 * temperature) / (243.04 + temperature)))
            / (17.625 - math.log(humidity / 100.0) - 
               ((17.625 * temperature) / (243.04 + temperature))))


#----------------------------------------------------------
def commaize(n):
    # Handle negative numbers.
    if n < 0:
        return '-' + commaize(abs(n))
    # Handle floating point values.
    if isinstance(n, float):
        floatStr = str(n)
        decimalStr = floatStr[floatStr.index('.'):]
        commaizedStr = commaize(int(n))
        if decimalStr != '.0':
            commaizedStr += decimalStr
        return commaizedStr

    # It must be a string.
    digits = str(n)
    decimalPosition = digits.find('.')
    if decimalPosition >= 0:
        return commaize(digits[:decimalPosition]) + digits[decimalPosition:]
    result = ''
    x = len(digits)
    while x > 3:
        result = "," + digits[x-3:] + result
        digits = digits[:x-3]
        x -= 3
    result = digits + result
    return result

#----------------------------------------------------------
def trim(aStr):
    aStr = aStr.strip()
    return re.sub(r"\s+", " ", aStr)


#----------------------------------------------------------
def isPositiveInteger(aStr):
    if isinstance(aStr, int):
        return True
    return re.match(r"^(\d+)$", aStr)


#----------------------------------------------------------
def exitIfNotRunningAsRoot(msg):
    # Verify that we are running as root.
    euid = os.geteuid()
    user = pwd.getpwuid(euid)[0]
    if user != 'root':
        sys.stderr.write("%s\n" % msg)
    return

#----------------------------------------------------------
def secs2hours(secs):
    mm, ss = divmod(secs, 60)
    hh, mm = divmod(mm, 60)
    return "%d:%02d:%02d" % (hh, mm, ss)

