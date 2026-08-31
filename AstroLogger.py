#!/usr/bin/python3
# Program: AstroLogger
# Version: 20260306
# Author:  Sifan Kahale
# Desc:    form for entering equipment data to db

from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector

# Create the Flask app instance
app = Flask(__name__)
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

#------------------------------------------------------------------------------------------------
# Main Window
@app.route("/")
def index():
    return render_template('AstroLogger.html')

    #return f"Processed Text: {processed_text}"

#------------------------------------------------------------------------------------------------
# This part is for local testing only (not used by Apache/mod_wsgi)
if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5010, debug=True)

