from flask import Flask, request, redirect, session, render_template_string, jsonify
import os, datetime

app = Flask(__name__)
app.secret_key = "secret"

UPLOAD = "static"
os.makedirs(UPLOAD, exist_ok=True)

users = {}      # username -> dp filename
messages = {}   # (u1,u2) -> list of messages


# ================= LOGIN =================
LOGIN_HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{
 margin:0;height:100vh;display:flex;justify-content:center;align-items:center;
 font-family:system-ui;background:linear-gradient(135deg,#833ab4,#fd1d1d,#fcb045)
}
.card{
 background:white;padding:30px;width:90%;max-width:360px;
 border-radius:16px;box-shadow:0 20px 40px rgba(0,0,0,.25);text-align:center
}
input{width:100%;padding:14px;margin-top:15px;border-radius:10px;border:1px solid #ddd}
button{
 width:100%;padding:14px;margin-top:20px;border:none;border-radius:10px;
 background:linear-gradient(135deg,#833ab4,#fd1d1d);color:white;font-weight:bold
}
</style>
</head>
<body>
<form method="post" class="card">
<h2>Mini Insta Chat</h2>
<p style="color:#666">Chat beautifully</p>
<input name="u" placeholder="Username" required>
<button>Enter</button>
</form>
</body>
</html>
"""


# ================= SEARCH =================
SEARCH_HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{margin:0;font-family:system-ui;background:#f5f5f7}
nav{
 padding:15px;background:white;display:flex;justify-content:space-between;
 box-shadow:0 2px 6px rgba(0,0,0,.05)
}
input{
 width:calc(100% - 30px);margin:15px;padding:14px;border-radius:14px;
 border:1px solid #ddd;font-size:15px
}
.user{
 margin:10px 15px;padding:12px;background:white;border-radius:16px;
 display:flex;align-items:center;box-shadow:0 6px 14px rgba(0,0,0,.05);
 cursor:pointer;transition:.2s
}
.user:hover{transform:scale(1.02)}
.user img{width:50px;height:50px;border-radius:50%;margin-right:12px}
</style>
<script>
function search(q){
 q=q.toLowerCase();
 document.querySelectorAll('.user').forEach(u=>{
  u.style.display=u.innerText.toLowerCase().includes(q)?'flex':'none';
 });
}
</script>
</head>
<body>

<nav>
<b>Search</b>
<a href="/profile">Profile</a>
</nav>

<input placeholder="Search users" onkeyup="search(this.value)">

{% for u in users %}
 {% if u!=me %}
 <div class="user" onclick="location.href='/chat/{{u}}'">
  <img src="/static/{{users[u] or 'default.png'}}">
  <b>{{u}}</b>
 </div>
 {% endif %}
{% endfor %}

</body>
</html>
"""


# ================= CHAT =================
CHAT_HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:system-ui;background:#eceff1}

.chat{position:fixed;inset:0;display:flex;flex-direction:column}

.header{
 height:60px;background:linear-gradient(135deg,#833ab4,#fd1d1d);
 color:white;display:flex;align-items:center;padding:0 15px;
 box-shadow:0 4px 10px rgba(0,0,0,.2)
}
.header img{
 width:40px;height:40px;border-radius:50%;border:2px solid white;margin:0 10px
}
.back{font-size:22px;cursor:pointer}

.messages{
 flex:1;overflow-y:auto;padding:15px;padding-bottom:90px
}

.date{text-align:center;color:#777;font-size:12px;margin:15px}

.bubble{
 max-width:75%;padding:12px 16px;margin:6px 0;border-radius:18px;
 box-shadow:0 4px 8px rgba(0,0,0,.1);font-size:15px
}
.me{
 background:#dcf8c6;margin-left:auto;border-bottom-right-radius:4px
}
.other{
 background:white;border-bottom-left-radius:4px
}
.time{font-size:11px;color:#666;margin-top:4px}

.input-area{
 position:fixed;bottom:0;left:0;right:0;background:white;
 display:flex;padding:10px;box-shadow:0 -4px 10px rgba(0,0,0,.15)
}
.input-area input{
 flex:1;padding:12px;border-radius:20px;border:1px solid #ddd;font-size:15px
}
.input-area button{
 margin-left:10px;padding:12px 20px;border:none;border-radius:20px;
 background:linear-gradient(135deg,#833ab4,#fd1d1d);color:white;font-weight:bold
}
</style>

<script>
function load(){
 fetch("/data/{{chat}}")
 .then(r=>r.json())
 .then(d=>{
  let box=document.getElementById("messages");
  box.innerHTML="";
  let last="";
  d.forEach(m=>{
   if(m.date!=last){
    box.innerHTML+=`<div class="date">${m.date}</div>`;
    last=m.date;
   }
   box.innerHTML+=`
    <div class="bubble ${m.me?'me':'other'}">
      ${m.text}
      <div class="time">${m.time}</div>
    </div>`;
  });
  box.scrollTop=box.scrollHeight;
 });
}
setInterval(load,2000);
</script>
</head>

<body onload="load()">
<div class="chat">

 <div class="header">
  <span class="back" onclick="location.href='/home'">←</span>
  <img src="/static/{{users[chat] or 'default.png'}}">
  <b>{{chat}}</b>
 </div>

 <div id="messages" class="messages"></div>

 <form method="post" class="input-area">
  <input name="msg" placeholder="Type a message" autocomplete="off">
  <button>Send</button>
 </form>

</div>
</body>
</html>
"""

PROFILE_HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
body{
 margin:0;
 font-family:system-ui;
 background:#f2f3f7;
}

.header{
 height:160px;
 background:linear-gradient(135deg,#833ab4,#fd1d1d,#fcb045);
 border-bottom-left-radius:30px;
 border-bottom-right-radius:30px;
 display:flex;
 align-items:center;
 justify-content:center;
 color:white;
 font-size:22px;
 font-weight:bold;
}

.card{
 width:90%;
 max-width:360px;
 margin:-70px auto 0;
 background:white;
 border-radius:24px;
 box-shadow:0 20px 40px rgba(0,0,0,.15);
 padding:25px;
 text-align:center;
}

.dp-wrapper{
 position:relative;
 width:130px;
 height:130px;
 margin:-90px auto 10px;
 background:linear-gradient(135deg,#833ab4,#fd1d1d,#fcb045);
 border-radius:50%;
 padding:4px;
}

.dp-wrapper img{
 width:100%;
 height:100%;
 border-radius:50%;
 background:white;
 object-fit:cover;
}

.username{
 font-size:20px;
 font-weight:600;
 margin-top:10px;
}

.sub{
 font-size:13px;
 color:#777;
 margin-bottom:20px;
}

form{
 margin-top:10px;
}

input[type=file]{
 display:none;
}

.label-btn{
 display:block;
 padding:14px;
 border-radius:14px;
 background:#f1f1f1;
 cursor:pointer;
 font-size:14px;
 margin-bottom:15px;
}

button{
 width:100%;
 padding:14px;
 border:none;
 border-radius:18px;
 background:linear-gradient(135deg,#833ab4,#fd1d1d);
 color:white;
 font-size:16px;
 font-weight:bold;
 box-shadow:0 10px 20px rgba(0,0,0,.2);
}

.back{
 display:block;
 margin-top:20px;
 text-decoration:none;
 color:#833ab4;
 font-weight:600;
}
</style>
</head>

<body>

<div class="header">
 My Profile
</div>

<div class="card">

 <div class="dp-wrapper">
  <img src="/static/{{dp or 'default.png'}}">
 </div>

 <div class="username">{{session["u"]}}</div>
 <div class="sub">Mini Insta Chat User</div>

 <form method="post" enctype="multipart/form-data">
  <label class="label-btn">
   Choose new profile picture
   <input type="file" name="dp" required>
  </label>
  <button>Update Profile Picture</button>
 </form>

 <a class="back" href="/home">← Back to Search</a>

</div>

</body>
</html>
"""




# ================= ROUTES =================
@app.route("/", methods=["GET","POST"])
def login():
 if request.method=="POST":
  u=request.form["u"]
  session["u"]=u
  users.setdefault(u,None)
  return redirect("/home")
 return LOGIN_HTML

@app.route("/home")
def home():
 return render_template_string(SEARCH_HTML,users=users,me=session["u"])

@app.route("/chat/<u>", methods=["GET","POST"])
def chat(u):
 me=session["u"]
 k=tuple(sorted([me,u]))
 messages.setdefault(k,[])
 if request.method=="POST":
  now=datetime.datetime.now()
  messages[k].append({
   "s":me,
   "t":request.form["msg"],
   "time":now.strftime("%I:%M %p"),
   "date":now.strftime("%d %b %Y")
  })
 return render_template_string(CHAT_HTML,users=users,me=me,chat=u)

@app.route("/data/<u>")
def data(u):
 me=session["u"]
 k=tuple(sorted([me,u]))
 return jsonify([{
  "text":m["t"],
  "time":m["time"],
  "date":m["date"],
  "me":m["s"]==me
 } for m in messages.get(k,[])])

@app.route("/profile", methods=["GET","POST"])
def profile():
 if request.method=="POST":
  f=request.files["dp"]
  name=session["u"]+".png"
  f.save(os.path.join(UPLOAD,name))
  users[session["u"]]=name
 return render_template_string(PROFILE_HTML,dp=users[session["u"]])

app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 5000))
)