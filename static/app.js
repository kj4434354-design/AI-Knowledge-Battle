let ws, roomCode="", isHost=false, timerInterval=null, seconds=15, answered=false;
const $=id=>document.getElementById(id);
function show(id){["setup","lobby","game","result"].forEach(x=>$(x).classList.toggle("hidden",x!==id))}
function connect(){return new Promise((resolve,reject)=>{
 const scheme=location.protocol==="https:"?"wss":"ws"; ws=new WebSocket(`${scheme}://${location.host}/ws`);
 ws.onopen=resolve;ws.onerror=reject;ws.onmessage=e=>handle(JSON.parse(e.data));
})}
async function send(data){if(!ws||ws.readyState!==1)await connect();ws.send(JSON.stringify(data))}
function playerName(){return $("name").value.trim()||"Player"}
$("create").onclick=async()=>{try{await send({action:"create",name:playerName(),category:$("category").value,difficulty:$("difficulty").value})}catch(e){$("notice").textContent="Could not connect. Please refresh and try again."}};
$("join").onclick=async()=>{let code=$("roomcode").value.trim().toUpperCase();if(code.length!==6){$("notice").textContent="Enter the 6-character room code.";return}try{await send({action:"join",name:playerName(),code})}catch(e){$("notice").textContent="Could not connect. Please refresh and try again."}};
$("start").onclick=()=>send({action:"start",code:roomCode});
$("copy").onclick=()=>navigator.clipboard.writeText(roomCode).then(()=>$("copy").textContent="Copied!");
function handle(m){
 if(m.type==="error"){$("notice").textContent=m.message;$("lobbyhint").textContent=m.message;return}
 if(m.type==="joined"){roomCode=m.code;isHost=m.host;$("code").textContent=roomCode;show("lobby");$("start").classList.toggle("hidden",!isHost);return}
 if(m.type==="state"){if(m.code){roomCode=m.code;$("code").textContent=roomCode;show("lobby")}$("players").innerHTML=m.players.map((p,i)=>`<div class="player"><span>${i===0?"✦ ":""}${escapeHtml(p.name)}</span><b>${p.score} pts</b></div>`).join("");$("lobbyhint").textContent=`${m.players.length}/8 players • ${m.category} • ${m.difficulty}`;return}
 if(m.type==="question"){show("game");answered=false;seconds=m.seconds;$("round").textContent=`QUESTION ${m.number} / ${m.total}`;$("question").textContent=m.question;$("feedback").textContent="";$("progress").textContent="Choose your answer before time runs out.";let opts=$("options");opts.innerHTML="";m.options.forEach((o,i)=>{let b=document.createElement("button");b.className="option";b.textContent=`${String.fromCharCode(65+i)}. ${o}`;b.onclick=()=>choose(i,b);opts.appendChild(b)});startTimer();return}
 if(m.type==="answer_received"){$("feedback").textContent="Answer submitted! Waiting for the other players…";return}
 if(m.type==="progress"){$("progress").textContent=`${m.answered} of ${m.total} players answered`;return}
 if(m.type==="reveal"){clearInterval(timerInterval);[...$("options").children].forEach((b,i)=>{b.disabled=true;if(i===m.correct)b.classList.add("correct")});return}
 if(m.type==="finished"){$("leaderboard").innerHTML=m.leaderboard.map((p,i)=>`<div class="player"><span>${["🥇","🥈","🥉"][i]||"🏅"} ${escapeHtml(p.name)}</span><b>${p.score} pts</b></div>`).join("");show("result")}
}
function choose(i,b){if(answered)return;answered=true;[...$("options").children].forEach(x=>x.disabled=true);b.classList.add("selected");send({action:"answer",choice:i})}
function startTimer(){clearInterval(timerInterval);$("timer").textContent=seconds;$("timerfill").style.width="100%";timerInterval=setInterval(()=>{seconds--;$("timer").textContent=seconds;$("timerfill").style.width=`${Math.max(0,seconds)/15*100}%`;if(seconds<=0)clearInterval(timerInterval)},1000)}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
