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
      if(c1>=50000){c1=50000;clearInterval(i1);} 
      setCount1(c1);
    },20);

    const i2=setInterval(()=>{
      c2+=1;
      if(c2>=95){c2=95;clearInterval(i2);} 
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
          background:radial-gradient(circle at 20% 20%,#0f172a,#020617);
        }

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
          from{transform:translateY(0);} 
          to{transform:translateY(60px);} 
        }

        .navbar{
          position:sticky;
          top:0;
          display:flex;
          justify-content:space-between;
          align-items:center;
          padding:25px 80px;
          background:rgba(2,6,23,0.75);
          backdrop-filter:blur(10px);
          z-index:10;
        }

        .logo{
          font-size:30px;
          font-weight:bold;
          color:#38bdf8;
        }

        .nav-links a{
          text-decoration:none;
          color:white;
          margin-left:30px;
          font-size:18px;
          transition:0.3s;
        }

        .nav-links a:hover{
          color:#38bdf8;
        }

        .hero{
          min-height:90vh;
          display:flex;
          align-items:center;
          justify-content:space-between;
          padding:60px 120px;
          gap:60px;
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
          transition:0.4s;
        }

        .hero-image:hover{
          transform:scale(1.05);
        }

        @keyframes float{
          0%{transform:translateY(0px)}
          50%{transform:translateY(-15px)}
          100%{transform:translateY(0px)}
        }

        section{
          padding:120px 100px;
        }

        h2{
          text-align:center;
          margin-bottom:70px;
          font-size:46px;
        }

        .feature-grid{
          display:grid;
          grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
          gap:35px;
        }

        .card{
          background:#1e293b;
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

        .about{
          display:flex;
          flex-wrap:wrap;
          gap:70px;
          align-items:center;
          justify-content:center;
        }

        .about-text{
          flex:1;
          min-width:300px;
        }

        .about-text p{
          font-size:20px;
          line-height:1.8;
        }

        .about-box{
          flex:1;
          min-width:300px;
          background:#1e293b;
          padding:50px;
          border-radius:16px;
          font-size:20px;
          transition:0.3s;
        }

        .about-box:hover{
          transform:scale(1.05);
          background:#334155;
        }

        .stats-grid{
          display:grid;
          grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
          gap:35px;
        }

        .stat-card{
          background:#1e293b;
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

        .cta{
          text-align:center;
          padding:150px 40px;
          background:linear-gradient(90deg,#020617,#0f172a);
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

        .footer{
          text-align:center;
          padding:30px;
          font-size:18px;
          background:#020617;
          color:#94a3b8;
        }

        .reveal{
          opacity:0;
          transform:translateY(80px);
          transition:all 0.9s ease;
        }

        .reveal.show{
          opacity:1;
          transform:translateY(0);
        }

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

      <div className="navbar">
        <div className="logo">⚡ SmartGrid AI</div>

        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#about">About</a>
          <a href="#stats">Stats</a>
          {/* <Link to="/National">National Grid Link</Link> */}
        </div>
      </div>

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

<section
  id="about"
  ref={addRef}
  className="about reveal py-32 px-10 lg:px-24"
>

  <div className="grid md:grid-cols-2 gap-16 items-center">

    {/* LEFT TEXT */}

    <div className="space-y-6">

      <h2 className="text-5xl font-bold bg-gradient-to-r from-sky-400 via-cyan-300 to-green-400 bg-clip-text text-transparent">
        About SmartGrid AI
      </h2>

      <p className="text-lg text-slate-300 leading-relaxed">
        SmartGrid AI is an intelligent monitoring platform designed to
        enhance the reliability and efficiency of modern electrical grids.
        Using machine learning and real-time data analysis, the system
        identifies anomalies and predicts potential failures before they
        disrupt power distribution.
      </p>

      <p className="text-lg text-slate-400">
        The platform transforms raw grid data into actionable insights,
        helping operators maintain stable energy flow and improve grid
        resilience.
      </p>

    </div>


    {/* RIGHT FEATURE CARDS */}

    <div className="grid grid-cols-2 gap-6">

      {/* Card 1 */}

      <div className="bg-gradient-to-br from-sky-500/20 to-sky-400/10 backdrop-blur border border-sky-400/30 p-6 rounded-xl hover:scale-105 transition duration-300">

        <div className="text-3xl mb-2">📡</div>

        <h3 className="text-sky-400 font-semibold">
          Grid Monitoring
        </h3>

        <p className="text-sm text-slate-300 mt-1">
          Track voltage, current and load conditions across the network.
        </p>

      </div>


      {/* Card 2 */}

      <div className="bg-gradient-to-br from-purple-500/20 to-indigo-400/10 backdrop-blur border border-purple-400/30 p-6 rounded-xl hover:scale-105 transition duration-300">

        <div className="text-3xl mb-2">🧠</div>

        <h3 className="text-purple-400 font-semibold">
          Predictive Intelligence
        </h3>

        <p className="text-sm text-slate-300 mt-1">
          AI models forecast potential grid faults before outages occur.
        </p>

      </div>


      {/* Card 3 */}

      <div className="bg-gradient-to-br from-green-500/20 to-emerald-400/10 backdrop-blur border border-green-400/30 p-6 rounded-xl hover:scale-105 transition duration-300">

        <div className="text-3xl mb-2">📊</div>

        <h3 className="text-green-400 font-semibold">
          Energy Analytics
        </h3>

        <p className="text-sm text-slate-300 mt-1">
          Transform grid data into actionable insights and visual reports.
        </p>

      </div>


      {/* Card 4 */}

      <div className="bg-gradient-to-br from-yellow-500/20 to-orange-400/10 backdrop-blur border border-yellow-400/30 p-6 rounded-xl hover:scale-105 transition duration-300">

        <div className="text-3xl mb-2">🔌</div>

        <h3 className="text-yellow-400 font-semibold">
          Reliable Distribution
        </h3>

        <p className="text-sm text-slate-300 mt-1">
          Maintain stable electricity flow and reduce power disruptions.
        </p>

      </div>

    </div>

  </div>

</section>
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

      <section className="cta reveal" ref={addRef}>
        <h2>Start Monitoring Your Grid</h2>
        <p>Access the AI dashboard and explore real-time grid analytics.</p>

        <Link to="/National">
          <button className="hero-btn">Grid Link</button>
        </Link>
      </section>

      <div className="footer">
        © 2026 GridGuard AI — Intelligent Power Grid Monitoring
      </div>

    </div>
  );
}
