from datetime import timedelta
from flask import Flask, request, render_template, make_response, current_app, json, Response
import status
import os
from functools import update_wrapper
import sys
import hashlib
import master_data


# for a quick intro into Flask web-servers I recommend:
# raspberrypi.org/learning/python-web-server-with-flask/worksheet

# crossdomain function has been pasted from "flask.pocoo.org/snippets/56"
# enable communication between pi's
def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

app = Flask(__name__)

#master server functions ------------------------------------------------------------
PROFILE_ARRAY = []  
@app.route('/register', methods=['GET','POST'])
#@crossdomain(origin='*')
def register(): #14/07/17 this needs to be modified...
    if request.method == 'POST':
        #can't see print()? make sure you execute through terminal
        received_data = request.data
        print ("This is the data: " + received_data)
        #below removes the unwanted speech marks
        received_data = received_data[1:-1]
        master_data.add_new_data(received_data, request.remote_addr)
        return "Added your data to the master database!"

def populateProfileArray():
    PROFILE_ARRAY = []
    file = open(status.ip_file, 'r+')
    string = file.read()
    #PROFILE_ARRAY = string.split(":")
    array = string.splitlines()
    return array

#record statuses
@app.route('/getStatuses', methods=['GET','OPTIONS'])
#crossdomain(origin='*')
def getIP_List():
    #status.change_status("available")
    iplist = populateProfileArray()
    print("HERE!")
    print(PROFILE_ARRAY)
    return Response(json.dumps({'PROFILE' : iplist}))

#end master functions -------------------------------------------------------------------

#path to set username
@app.route('/set_user/<username>')
def set_user(username):
        try:
            return ("Your new name is, " + username)
        finally:
            print ("username : " + username)
            status.set_name(username)
            print ("new username set!")
            return ("Your new name is, " + username)
        
@app.route('/set_status/<new_status>')
def set_status(new_status):
        try:
            return ("Your new status is, " + new_status)
        finally:
            print ("status : " + new_status)
            status.change_status(new_status)
            print ("new status set!")
            return ("Your new status is, " + new_status)



#path to get current status, and name 
@app.route('/profiles', methods=['GET','OPTIONS'])
#crossdomain(origin='*')
def send_profiles():
    #current_status = status.get_status()
    #current_name = status.get_name()
    #totalString = current_status + "," + current_name
    #return Response(json.dumps({"status" : current_status, "name" : current_name}), mimetype="application/json")
    ip_list = []
    status_list = []
    name_list = []
        
    if os.path.exists(status.PROFILE_FILE):
        file = open(status.PROFILE_FILE, 'r')
        profiles_str = file.readline()
        profiles_arry = profiles_str.split(":")
        for profile in profiles_arry:
            profile_array = profile.split(",")
            ip_list.append(profile_array[0])
            status_list.append(profile_array[1])
            name_list.append(profile_array[2])
    
    return Response(json.dumps({'IPS' : ip_list, 'STATUSES' : status_list, 'NAMES' : name_list}), mimetype="application/json")

@app.route('/old',methods = ['POST','GET'])
def home():
    #when a button is pushed on the webpage, the status file changes
    #after status changes, the form is changed by render() then returned
    statuses = status.STATUSES
    if request.method =='POST':
        if request.form['status'] in statuses:
            status.change_status(request.form['status'])
    #if it's the first time opening accessing form results causes a crash
    #so this is checks if it's post and if not it doesn't load form results
    #if it is the first time, the form is loaded and results aren't accessed
    
    #return render_template('index.html')
    
    return render()


@app.route('/', methods=['GET', 'POST'])
def send():
    if request.method == 'POST':
      password = request.form['pwd']
      encoded_password = password.encode("utf-8")

      if check_password(encoded_password) == "Correct": #if they entered the correct password...
          if (request.form['which_form']) == "status_form": #if they are updating their status...
              the_new_status = request.form['new_status']
              status.change_status(the_new_status)
              return render_template('homepage.html', outcome = "Your new status is: " + the_new_status, the_color = "green", my_name = status.get_name())

          elif (request.form['which_form']) == "name_form": #if they are updating their name...
              the_new_name = request.form['new_name']
              status.set_name(the_new_name)
              return render_template('homepage.html', outcome = "Your new name is: " + the_new_name, the_color = "green", my_name = status.get_name())

      else: #display this if they got the password wrong
           return render_template('homepage.html', outcome = "You've entered the wrong password!", the_color = "red", my_name = status.get_name())
                    
    return render_template('homepage.html', my_name = status.get_name())

def check_password(encoded_password):
    if status.get_hash() == "": #if there is no password ---> make one
        set_password(encoded_password)
        return "Correct"

    elif hashlib.sha512(encoded_password+status.get_salt()).hexdigest() == status.get_hash(): #if the password was correct...
        return "Correct"
    
    return "Incorrect"

def set_password(the_new_password):
    salt = os.urandom(16) #generate a salt
    hash_result = hashlib.sha512(the_new_password+salt).hexdigest() #create the hash  
    status.set_salt(salt) #save the data
    status.set_hash(hash_result)


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        old_password = request.form['pwd']
        new_password_1 = request.form['new_pwd_1']
        new_password_2 = request.form['new_pwd_2']
        encoded_old_password = old_password.encode("utf-8")

        if check_password(encoded_old_password) == "Correct": #if they entered the correct password...
            if new_password_1 == new_password_2:
                set_password(new_password_1.encode("utf-8")) # must be encoded to be passed on to the hash
                return render_template('change_password.html', the_result ="Your new password has been set!") # new password set!
            return render_template('change_password.html', the_result ="Your new passwords do not match!") # passwords don't match
        return render_template('change_password.html', the_result ="Incorrect Original Password!") # your original password was wrong
    return render_template('change_password.html') # render the form


#14/07/17 - render() not in use...
#this returns the html file
#with appropiate information to display the correct page
def render():
    print ("HERE")
    address = ["static/assets/images/Available.png", "static/assets/images/Busy.png", "static/assets/images/Disturbable.png" ,"static/assets/images/Finding.png" , "static/assets/images/Party.png", "static/assets/images/Alert.png", "static/assets/images/Offline.png"]
    colors = ["#00FF7F","#DC143C","#FFA500","#1E90FF","#BA55D3", "#7E0308", "#000000"]
    #status.change_status("available")
    #current_status = status.get_status()
    #profiles = send_profiles()
    return render_template('index.html'
                           '''
                           ,
                           
                           title = current_status,
                           current_status = current_status,
                           statuses = status.STATUSES,
                           colors_statuses = dict(zip(status.STATUSES, colors)),
                           images_statuses = dict(zip(status.STATUSES, address)),
                           ip_list = profiles['IPS'],
                           name_list = profiles['NAMES'],
                           status_list = profiles['STATUSES'],
                           current_name = status.get_name()
                           '''
                           )

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", threaded=True)
    #"threaded=True" fixes timeout issues (somehow...)
