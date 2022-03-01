from msilib.schema import Directory
import os
import requests
import json
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, send_file, session, Response
import matplotlib.pyplot as plt
from darts import TimeSeries
from darts.models import ARIMA
from requests_html import HTMLSession
import threading

app = Flask(__name__, instance_relative_config=True)
session = "null"
lastrebuiltcache = 0.0

#region API
def rebuildCache():
    #Rebuild featured cache

    try:
        os.mkdir("./cache")
    except:
        pass

    itemobjects = list(dict.fromkeys(getFeatured()))
    f = open("./cache/featured.json", "w", encoding="utf-8")
    js = json.dumps(itemobjects)
    f.write(js)
    f.close()

    #rebuild top played cache
    URL = "https://steamcharts.com"
    r = requests.get(URL)
    soup = BeautifulSoup(r.content, 'html5lib')

    gametrs = soup.select("#top-games tbody tr")
    topgames = []

    for i in range(len(gametrs)):
        gamename = gametrs[i].select(".game-name a")[0].text.replace("\n", "").replace("\t", "")
        gameplayers = int(gametrs[i].select(".num")[0].text.replace(",", ""))
        topgames.append([gamename, gameplayers])

    f = open("./cache/top.json", "w", encoding="utf-8")
    js = json.dumps(topgames)
    f.write(js)
    f.close()
    global lastrebuiltcache
    lastrebuiltcache = time.time()

def getFeatured():

    """
    URL = "https://store.steampowered.com"
    session = HTMLSession()
    r = session.get(URL)
    r.html.render(sleep=1, keep_page=True, scrolldown=1)
    

    headers = {
        'User-agent':
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }

    #r = requests.get(URL, headers=headers)

    #soup = BeautifulSoup(r.content, 'html5lib')
    items = r.html.find('.store_main_capsule')
    itemobjects = []

    for i in range(len(items)):
        appID = items[i].attrs["data-ds-appid"]
        itemobjects.append(appID)
    
    session.close()
    """

    headers = {
        'User-agent':
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }

    r = requests.get("https://store.steampowered.com/search/results/?query&start=0&count=10&dynamic_data=&sort_by=_ASC&os=win&filter=topsellers&infinite=1", headers=headers)

    html = json.loads(r.text)["results_html"]
    soup = BeautifulSoup(html, 'html5lib')

    games = soup.select("[data-ds-appid]")

    itemobjects = []

    for i in range(10):
        if (not "," in games[i].attrs["data-ds-appid"]):
            itemobjects.append(games[i].attrs["data-ds-appid"])

    r.close

    return itemobjects

def predict_ARIMA(series):
    model = ARIMA(p=32, d=1,q=12)
    model.fit(series)
    return model.predict(len(series))

def getProperUnit(num):
    if (num < 60):
        return str(num) + " Seconds"
    elif (num < 3600):
        return str(num / 60) + " Minutes"
    elif (num < 86400):
        return str(num / 3600) + " Hours"
    elif (num < 31536000):
        return str(num / 86400) + " Days"
    else:
        return str(num / 31536000) + " Years"

def plotGraph(jsonObj, seconds):
    
    x = []
    y = []
    data = []
    usedtimes = []

    #-1 means all time
    if (seconds == -1):
        #now - release date
        seconds = (jsonObj[-1][0] / 1000) - (jsonObj[0][0] / 1000)

    #If the game is not old enough
    #If now - 3 months is less that the release date
    if ((jsonObj[-1][0] / 1000) - 77760000 < (jsonObj[0][0] / 1000)):
        print("GAME IS TOO YOUNG")
        return "young"

    """
    if (seconds < 86400):
        fr = "H"
    elif (seconds < 604800):
        fr = "D"
    else:
        fr = "M"
    """

    fr = "M"

    for i in range(len(jsonObj)):
        unixtime = int(jsonObj[i][0]) / 1000

        if (unixtime > (jsonObj[-1][0] / 1000) - seconds):
            x.append(unixtime)
            y.append(jsonObj[i][1])
            rawtime = datetime.utcfromtimestamp(unixtime)

            if (fr == "M"):
                formattedtime = rawtime.strftime('%Y-%m')

            if (not formattedtime in usedtimes):
                data.append([formattedtime, int(jsonObj[i][1])])
                usedtimes.append(formattedtime)
                #print(formattedtime)

            #print("Players at " + str(formattedtime) + " UTC: " + str(jsonObj[i][1]))
        else:
            pass    

    df = pd.DataFrame(data, columns = ["Month", "y"])

    series = TimeSeries.from_dataframe(df, time_col='Month', value_cols='y', fill_missing_dates=True)

    if (fr == "M" and len(data) < 30):
        return "young"
    else:
        prediction = predict_ARIMA(series)

    return prediction.to_json()

@app.route("/playdata/<steamID>")
def getPlayData(steamID):

    if (os.path.exists("./cache/" + steamID + ".pr.json")):
        f = open("./cache/" + steamID + ".pr.json", "r", encoding="utf-8")
        c = f.read()
        f.close
        return c


    URL = "https://steamcharts.com/app/" + str(steamID) + "#7d"
    DATAURL = "https://steamcharts.com/app/" + str(steamID) + "/chart-data.json"
    r = requests.get(URL)
    chart = requests.get(DATAURL)
    
    if (r.status_code == 500):
        return "young"

    jsonObj = json.loads(chart.content)
    soup = BeautifulSoup(r.content, 'html5lib') 

    currentUsers = int(soup.select("#app-heading .app-stat:has(.timeago) .num")[0].get_text().replace(",", ""))
    coverImg = "https://steamcharts.com/assets/steam-images/" + str(steamID) + ".jpg"
    gameName = soup.select("title")[0].get_text().replace(" - Steam Charts", "")
    
    graph = plotGraph(jsonObj, -1)
    f = open("./cache/" + steamID + ".pr.json", "w", encoding="utf-8")
    c = f.write(graph)
    f.close

    return graph

    print("Game Name: " + str(gameName))
    print("CCU: " + str(currentUsers))
    print("Cover: " + coverImg)


def fallbackData(id):

    headers = {
        'User-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
    }
    URL = "https://store.steampowered.com/api/appdetails/?appids=" + id
    r = requests.get(URL, headers=headers)

    j = json.loads(r.text)


    return j[id]

@app.route("/req")
def req():
    URL = request.headers["requrl"]

    headers = dict(request.headers)
    headers["Host"] = request.headers["vhost"]
    headers["Referer"] = request.headers["vref"]
    del request.headers["vhost"]
    del request.headers["vref"]
    del request.headers["requrl"]

    r = requests.get(URL, headers=headers)

    return r.text
    
@app.route("/info/<id>")
def getGameData(id):

    if (os.path.exists("./cache/" + id + ".json")):
        f = open("./cache/" + id + ".json", "r", encoding="utf-8")
        c = f.read()
        f.close
        return c

    URL = "https://steamspy.com/app/" + id
    
    headers = {
        'User-agent':
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }

    r = requests.get(URL, headers=headers)

    soup = BeautifulSoup(r.content, 'html5lib')

    try:
        data = {
            "appID" : id,
            "gameName" : soup.select("title")[0].text.split(" - SteamSpy - All the data and stats about Steam games")[0],
            "shortDescription" : soup.select(".col-md-4 p")[0].text.split("Store\n                  | Hub\n                  | SteamDB")[0],
            "headerImage" : "https://steamcdn-a.akamaihd.net/steam/apps/" + id + "/header.jpg"
        }
    except:
        fallback = fallbackData(id)
        data = {
            "appID" : id,
            "gameName" : fallback["data"]["name"],
            "shortDescription" : fallback["data"]["short_description"],
            "headerImage" : "https://steamcdn-a.akamaihd.net/steam/apps/" + id + "/header.jpg"
        }

    if (data["shortDescription"] == ""):
        data["shortDescription"] = fallbackData(id)["data"]["short_description"]

    f = open("./cache/" + id + ".json", "w", encoding="utf-8")
    c = f.write(json.dumps(data))
    f.close

    r.close()

    return json.dumps(data)

@app.route("/featured")
def featured():
    f = open("./cache/featured.json", "r", encoding="utf-8")
    c = f.read()
    f.close
    return c

@app.route("/top")
def top():
    f = open("./cache/top.json", "r", encoding="utf-8")
    c = f.read()
    f.close
    return c

@app.route("/autocomplete/<query>")
def autocomplete(query):
    URL = "https://94he6yatei-dsn.algolia.net/1/indexes/steamdb/?x-algolia-agent=SteamDB+Autocompletion&x-algolia-application-id=94HE6YATEI&x-algolia-api-key=4e93170f248c58869d226a339bd6a52c&hitsPerPage=15&attributesToSnippet=null&attributesToHighlight=name&attributesToRetrieve=objectID,lastUpdated&query=" + query

    headers = {
        'User-agent':
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582",
        "Host" : "94he6yatei-dsn.algolia.net",
        "Referer" : "https://steamdb.info/",
        "Origin" : "https://steamdb.info/"
    }

    r=requests.get(URL, headers=headers)

    return r.text

@app.route("/searchapi/<query>")
def searchapi(query):
    URL = "https://steamcharts.com/search/?q=" + query
    
    headers = {
        'User-agent':
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }

    r = requests.get(URL, headers=headers)

    soup = BeautifulSoup(r.content, 'html5lib')
    results = soup.select(".common-table tbody tr")
    resultsCollected = []

    for i in range(len(results)):
        data = {
            "appID" : results[i].select(".left a")[0]["href"].replace("/app/", ""),
            "gameName" : results[i].select(".left a")[0].text,
            "shortDescription" : "Not Scraped",
            "playerCount" : results[i].select(".num")[0].text,
            "headerImage" : "https://steamcharts.com/assets/steam-images/" + results[i].select(".left a")[0]["href"].replace("/app/", "") + ".jpg"
        }
        resultsCollected.append(data)

    return json.dumps(resultsCollected)
#endregion

@app.route("/")
def index():

    #Log IP Addresses For Analytics
    ip_addr = request.remote_addr
    if(not os.path.exists("./analytics.json")):
        f = open("./analytics.json", "a")
        f.write("[]")
        f.close
    f = open("./analytics.json", "r")
    analytics = json.loads(f.read())
    f.close()
    analytics.append(ip_addr)
    analytics = list(dict.fromkeys(analytics))
    f = open("./analytics.json", "w")
    f.write(json.dumps(analytics))
    f.close

    return render_template("index.html")

@app.route("/app/<path:appid>")
def appPage(appid):

    if ("/" in appid):
        appid = appid.split("/")[0]

    renderedPage = render_template("app.html")
    renderedPage = renderedPage.replace(f"%%APPID%%", appid)
    appData = getGameData(appid)
    parsedAppData = json.loads(appData)
    renderedPage = renderedPage.replace(f"%%APPDATA%%", appData)
    renderedPage = renderedPage.replace(f"%%REQUESTURL%%", request.url)
    renderedPage = renderedPage.replace(f"%%APPNAME%%", parsedAppData["gameName"])
    try:
        renderedPage = renderedPage.replace(f"%%REFERER%%", request.headers["Referer"])
    except:
        renderedPage = renderedPage.replace(f"%%REFERER%%", "/")
    return renderedPage

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/favicon.png")
def favicon():
    return send_file("./static/favicon.png", mimetype='image/png')




@app.before_request 
def before_request_callback(): 
    pass

def runApp():
    app.run("0.0.0.0", port=25640, debug=True, use_reloader=False)

def mainThreadLoop():
    while (True):
        global lastrebuiltcache
        #If cache is older than 5 minutes
        if (time.time() - lastrebuiltcache > 300):
            rebuildCache()

        time.sleep(1)

t = threading.Thread(target=runApp, args=())
t.start()


rebuildCache()
mainThreadLoop()
