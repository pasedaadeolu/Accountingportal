function updateClock(){

const now=new Date();

document.getElementById("clock").innerHTML=
now.toLocaleString();

}

setInterval(updateClock,1000);

updateClock();
