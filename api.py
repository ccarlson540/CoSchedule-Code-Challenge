# -*- coding: utf-8 -*-
"""
Created on Wed Apr 28 16:27:42 2021

@author: Charlie Carlson
"""

from flask import Flask, abort, request
from uuid import uuid4
import requests
import requests.auth
import urllib
import pandas as pd
import flask
from flask_session import Session
import json

CLIENT_ID = 'CO_3bjGxqJkH0A'
CLIENT_SECRET = 'pHK5oLHVTIlRdxHEAM_ASarbtG3x8w'
REDIRECT_URI = 'http://localhost:65010/reddit_callback'
BASE_URL = 'http://localhost:65010/'

#TODO: Delete testing variables after finishing tests
responses = [] #empty list to append responses to for testing. 


def user_agent():
    return 'CoSchedule Code Challenge by /uWholeSet4125'

def base_headers():
    return {"User-Agent": user_agent()}


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route('/')
def homepage():
    #TODO hide behind my site's login
    #TODO create login html page (use index.html as base file)
    #TODO remove direct link and use as redirect after logging in/make page
    # explaining why second authentication to Reddit is required
    text = '<a href="%s">Authenticate with reddit</a>'
    return text % make_authorization_url()


def make_authorization_url():
    # Generate a random string for the state parameter
    # Save it for use later to verify user logging in with same state
    state = str(uuid4())
    save_created_state(state)
    params = {"client_id": CLIENT_ID,
              "response_type": "code",
              "state": state,
              "redirect_uri": REDIRECT_URI,
              "duration": "temporary",
              "scope": "identity"}
    url = ('https://www.reddit.com/api/v1/authorize?client_id=' + CLIENT_ID
    + '&response_type=code&state=' + state +'&redirect_uri=' + REDIRECT_URI
    + '&duration=temporary&scope=read' )
    return url

# Save results to csv as basic database
#TODO determine if username and time should be saved to database also
def save_created_state(state):
    logins = pd.read_csv('logins.csv')
    logins = logins.append({'state' : state}, ignore_index = True)
    logins.to_csv('logins.csv')
    
# check if state is contained in database
def is_valid_state(state):
    logins = pd.read_csv('logins.csv')
    if state in list(logins['state']):
        return True
    else:
        return False

@app.route('/reddit_callback')
def reddit_callback():
    error = request.args.get('error', '')
    if error:
        return "Error: " + error
    state = request.args.get('state', '')
    if not is_valid_state(state):
        # login is invalid: return HTTP 403 - Forbidden
        abort(403)
    code = request.args.get('code')
    access_token = get_token(code)
    flask.session['access_token'] = access_token
    # TODO: pass access token on redirect
    return flask.redirect(flask.url_for('search_page'))

def get_token(code):
    client_auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    post_data = {"grant_type": "authorization_code",
                 "code": code,
                 "redirect_uri": REDIRECT_URI}
    headers = base_headers()
    response = requests.post("https://ssl.reddit.com/api/v1/access_token",
                             auth=client_auth,
                             headers=headers,
                             data=post_data)
    token_json = response.json()
    return token_json["access_token"]

@app.route('/search_page/')
def search_page():
    return flask.render_template('search_page.html')

@app.route('/search/', methods=['POST', 'GET'])
def search():
    if request.method == 'POST':
        flask.session['query'] = request.form['searchBox']
        flask.session['subreddit'] = request.form['subreddit']
        results = search_reddit(flask.session['subreddit'], flask.session['query'])
        return  flask.render_template('search_page_result.html', data=results)
    
@app.route('/search/<post_id>/', methods=['POST', 'PATCH', 'GET'])
def post_comment(post_id): 
    if request.method == 'POST':
        #new comment
        username = 'asdf' #flask.session['username'] #TODO update username when login is created
        comments = pd.read_csv('comments.csv')
        new_comment = request.form['comment']
        comments = comments.append({"Post_ID" : post_id, "Username" : username}
                                   , ignore_index=True)
        comments.to_csv('comments.csv')
        reddit_data = search_reddit(flask.session['subreddit'], flask.session['query'])
        results = add_comments_to_reddit_data(reddit_data)
        # results = add_post_ratings_to_reddit_data(reddit_data)
        # results = format_data(reddit_data, live_comments, live_ratings)
        return flask.render_template('search_page_result.html', data=results)

def search_reddit(subreddit, q):
    headers = base_headers()
    headers.update({"Authorization": "bearer " + flask.session.get('access_token', None)})
    response = requests.get("https://oauth.reddit.com/r/" + subreddit 
                            + "/search?q=" + q, headers=headers)
    results = response.json()
    return results

def add_comments_to_reddit_data(reddit_data):
    # search comments.csv for comments on each post_id
    comments_db = pd.read_csv('comments.csv')
    reddit_data = json.loads(reddit_data)
    for post in reddit_data['data']['children']:
        post['data']['comments'] = list(comments_db[comments_db['Post_ID'] == post['data']['id']])
    return reddit_data
        

def add_post_ratings_to_reddit_data():
    #TODO search ratings.csv for ratings on each post_id
    pass

def format_data(reddit_data, comments, ratings):
    #TODO format data to make friendly JSON file that contains only the necessary info
    pass
    
def get_username(access_token):
    headers = base_headers()
    headers.update({"Authorization": "bearer " + access_token})
    response = requests.get("https://oauth.reddit.com/api/v1/me", headers=headers)
    me_json = response.json()
    return me_json['name']


if __name__ == '__main__':
    app.run(debug=False, port=65010)