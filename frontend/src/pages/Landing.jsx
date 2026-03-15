import { Link } from "react-router-dom";
import { useEffect, useState, useRef } from "react";
import electricityImg from "../assets/electricity.png";

export default function LandingPage(){

  const [count1,setCount1]=useState(0);
  const [count2,setCount2]=useState(0);
  const sectionsRef = useRef([]);

  useEffect(()=>{
    let c1=0;
    let c2=0;

    const i1=setInterval(()=>{
      c1+=500;
      if(c1>=50000){
        c1=50000;
        clearInterval(i1);
      }
      setCount1(c1);
    },20);

    const i2=setInterval(()=>{
      c2+=1;
      if(c2>=95){
        c2=95;
        clearInterval(i2);
      }
      setCount2(c2);
    },40);

    return ()=>{
      clearInterval(i1);
      clearInterval(i2);
    }
  },[]);

  useEffect(()=>{
    const observer = new IntersectionObserver(
      (entries)=>{
        entries.forEach(entry=>{
          if(entry.isIntersecting){
            entry.target.classList.add("show");
          }
        })
      },
      {threshold:0.2}
    );

    sectionsRef.current.forEach(sec=>{
      if(sec) observer.observe(sec);
    });

    return ()=>observer.disconnect();
  },[]);

  const addRef = (el)=>{
    if(el && !sectionsRef.current.includes(el)){
      sectionsRef.current.push(el);
    }
  }

  return (
    <div className="landing">

<style>{`

*{
margin:0;
padding:0;
box-sizing:border-box;
font-family:Arial, Helvetica, sans-serif;
scroll-behavior:smooth;
}

.landing{
color:white;
background:#020617;
}

/* GRID BACKGROUND */

.grid-bg{
position:fixed;
width:100%;
height:100%;
background-image:linear-gradient(#1e293b 1px, transparent 1px),
                 linear-gradient(90deg,#1e293b 1px, transparent 1px);
background-size:60px 60px;
opacity:0.15;
animation:gridMove 20s linear infinite;
z-index:-1;
}

@keyframes gridMove{
from{transform:translateY(0)}
to{transform:translateY(60px)}
}

/* NAVBAR */

.navbar{
position:sticky;
top:0;
display:flex;
justify-content:space-between;
align-items:center;
padding:22px 80px;

background:linear-gradient(
270deg,
#0ea5e9,
#22c55e,
#a855f7,
#f59e0b
);

background-size:600% 600%;
animation:navGradient 10s ease infinite;

backdrop-filter:blur(12px);
z-index:10;
}

@keyframes navGradient{
0%{background-position:0% 50%}
50%{background-position:100% 50%}
100%{background-position:0% 50%}
}

.logo{
font-size:30px;
font-weight:bold;
color:white;
}

.nav-links a{
text-decoration:none;
color:white;
margin-left:30px;
font-size:18px;
transition:0.3s;
}

.nav-links a:hover{
color:#020617;
}

/* HERO */

.hero{
min-height:90vh;
display:flex;
align-items:center;
justify-content:space-between;
padding:60px 120px;
gap:60px;

opacity:0;
transform:translateY(40px);
animation:heroFade 1.5s ease forwards;
}

@keyframes heroFade{
to{
opacity:1;
transform:translateY(0);
}
}

.hero-text{
max-width:650px;
}

.hero-text h1{
font-size:80px;
background:linear-gradient(90deg,#38bdf8,#22c55e);
-webkit-background-clip:text;
color:transparent;
margin-bottom:30px;
}

.hero-text p{
font-size:22px;
line-height:1.8;
color:#cbd5f5;
}

.hero-btn{
margin-top:40px;
padding:16px 36px;
border:none;
border-radius:10px;
background:#22c55e;
color:white;
cursor:pointer;
font-size:18px;
transition:0.35s;
}

.hero-btn:hover{
transform:scale(1.12);
box-shadow:0 0 20px #22c55e;
}

.hero-image{
width:420px;
animation:float 5s ease-in-out infinite;
}

@keyframes float{
0%{transform:translateY(0)}
50%{transform:translateY(-15px)}
100%{transform:translateY(0)}
}

/* SECTION BASE */

section{
padding:120px 100px;
}

h2{
text-align:center;
margin-bottom:70px;
font-size:46px;
}

/* FEATURES */

#features{
background:linear-gradient(135deg,#020617,#0f172a,#1e3a8a);
}

.feature-grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
gap:35px;
}

.card{
background:linear-gradient(145deg,#1e293b,#0f172a);
border-radius:16px;
padding:40px;
transition:0.35s;
}

.card:hover{
transform:translateY(-14px) scale(1.04);
background:#334155;
}

.card h3{
font-size:26px;
color:#38bdf8;
margin-bottom:15px;
}

.card p{
font-size:18px;
color:#cbd5f5;
}

/* ABOUT */

#about{
background:linear-gradient(135deg,#020617,#1e1b4b,#312e81);
}

/* STATS */

#stats{
background:linear-gradient(135deg,#020617,#022c22,#064e3b);
}

.stats-grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
gap:35px;
}

.stat-card{
background:linear-gradient(145deg,#1e293b,#0f172a);
padding:50px;
border-radius:16px;
text-align:center;
transition:0.3s;
}

.stat-card:hover{
transform:translateY(-12px);
background:#334155;
}

.stat-card h3{
font-size:42px;
color:#22c55e;
}

.stat-card p{
margin-top:10px;
font-size:18px;
color:#cbd5f5;
}

/* CTA */

.cta{
text-align:center;
padding:150px 40px;
background:linear-gradient(120deg,#0f172a,#134e4a,#064e3b);
}

.cta h2{
font-size:50px;
margin-bottom:25px;
}

.cta p{
font-size:20px;
color:#cbd5f5;
margin-bottom:35px;
}

/* FOOTER */

.footer{
text-align:center;
padding:30px;
font-size:18px;
background:#020617;
color:#94a3b8;
}

/* SCROLL REVEAL */

.reveal{
opacity:0;
transform:translateY(80px);
transition:all 0.9s ease;
}

.reveal.show{
opacity:1;
transform:translateY(0);
}

/* RESPONSIVE */

@media(max-width:900px){

.hero{
flex-direction:column;
text-align:center;
}

.hero-image{
width:320px;
}

}

`}</style>

<div className="grid-bg"></div>

{/* NAVBAR */}

<div className="navbar">
<div className="logo">⚡ SmartGrid AI</div>

<div className="nav-links">
<a href="#features">Features</a>
<a href="#about">About</a>
<a href="#stats">Stats</a>
</div>
</div>

{/* HERO */}

<div className="hero">

<div className="hero-text">

<h1>Smart Grid AI Monitoring</h1>

<p>
Monitor electricity grids in real time, detect anomalies, and predict
failures using advanced AI models. GridGuard AI helps maintain
reliable and efficient power infrastructure.
</p>

<Link to="/National">
<button className="hero-btn">National Grid Link</button>
</Link>

</div>

<img src={electricityImg} alt="Electric Grid" className="hero-image" />

</div>

{/* FEATURES */}

<section id="features" ref={addRef} className="reveal">

<h2>Powerful Features</h2>

<div className="feature-grid">

<div className="card">
<h3>⚡ Real-Time Monitoring</h3>
<p>Track voltage, current and load from the grid instantly.</p>
</div>

<div className="card">
<h3>🤖 AI Fault Detection</h3>
<p>Predict overloads and transformer faults before failure.</p>
</div>

<div className="card">
<h3>📊 Smart Analytics</h3>
<p>Interactive charts and insights for better grid decisions.</p>
</div>

<div className="card">
<h3>🌍 Renewable Integration</h3>
<p>Analyze solar and wind contributions in the grid.</p>
</div>

</div>

</section>

{/* ABOUT */}

<section id="about" ref={addRef} className="reveal">

<h2>About SmartGrid AI</h2>

<p style={{fontSize:"20px",maxWidth:"900px",margin:"auto",lineHeight:"1.8"}}>
SmartGrid AI is an intelligent monitoring platform designed to enhance the
reliability and efficiency of modern electrical grids. Using machine learning
and real-time data analysis, the system identifies anomalies and predicts
potential failures before they disrupt power distribution.
</p>

</section>

{/* STATS */}

<section id="stats" ref={addRef} className="reveal">

<h2>Platform Impact</h2>

<div className="stats-grid">

<div className="stat-card">
<h3>{count1.toLocaleString()}+</h3>
<p>Data Records Processed</p>
</div>

<div className="stat-card">
<h3>{count2}%</h3>
<p>Prediction Accuracy</p>
</div>

<div className="stat-card">
<h3>24/7</h3>
<p>Real-Time Monitoring</p>
</div>

<div className="stat-card">
<h3>AI</h3>
<p>Powered Intelligence</p>
</div>

</div>

</section>

{/* CTA */}

<section className="cta reveal" ref={addRef}>

<h2>Start Monitoring Your Grid</h2>

<p>Access the AI dashboard and explore real-time grid analytics.</p>

<Link to="/National">
<button className="hero-btn">Grid Link</button>
</Link>

</section>

{/* FOOTER */}

<div className="footer">
© 2026 GridGuard AI — Intelligent Power Grid Monitoring
</div>

</div>
  );
}