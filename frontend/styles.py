import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
        :root { --obsidian:#070911; --panel:#0d1120; --line:#202943; --muted:#8993aa; --blue:#54a8ff; --violet:#9d78ff; }
        [data-testid="stAppViewContainer"] { background: var(--obsidian); color:#f5f7fb; }
        [data-testid="stAppViewContainer"] > .main { background-image: linear-gradient(rgba(110,139,195,.045) 1px, transparent 1px), linear-gradient(90deg, rgba(110,139,195,.045) 1px, transparent 1px); background-size: 42px 42px; }
        [data-testid="stHeader"] { background: rgba(7,9,17,.75); }
        html, body, [class*="css"] { font-family: Manrope, sans-serif; }
        h1,h2,h3 { letter-spacing:-.04em; }
        .block-container { max-width: 1440px; padding: 2.2rem 3rem 4rem; }
        .brand { display:flex; align-items:center; gap:.75rem; margin-bottom:2.3rem; }
        .brand-mark { width:34px; height:34px; position:relative; border:1px solid #4d83c7; border-radius:10px; background:linear-gradient(135deg,#172b52,#17122f); box-shadow:0 0 28px #365aa044; }
        .brand-mark:before,.brand-mark:after { content:""; position:absolute; width:8px; height:8px; border:2px solid var(--blue); border-radius:50%; }
        .brand-mark:before { left:7px; top:7px; box-shadow:13px 13px 0 -1px var(--violet); }
        .brand-mark:after { right:6px; bottom:7px; border-color:var(--violet); }
        .brand-name { font-weight:800; font-size:1.15rem; letter-spacing:.1em; }
        .brand-sub { color:#6f7c9a; font-family:'DM Mono'; font-size:.6rem; letter-spacing:.12em; text-transform:uppercase; }
        .eyebrow { color:var(--blue); font:500 .68rem 'DM Mono'; letter-spacing:.14em; text-transform:uppercase; }
        .hero-title { font-size:clamp(2.4rem,5vw,5.4rem); line-height:.98; max-width:820px; margin:.45rem 0 1.1rem; }
        .hero-title span { color:transparent; background:linear-gradient(105deg,#fff 20%,#a8cfff 55%,#a483ff 90%); background-clip:text; }
        .hero-copy { color:#a6b0c6; font-size:1.05rem; max-width:670px; line-height:1.7; }
        .card { background:rgba(13,17,32,.78); border:1px solid var(--line); border-radius:18px; padding:1.25rem; box-shadow:0 18px 50px #00000022; }
        .metric { font-size:2rem; font-weight:800; margin-top:.3rem; }
        .metric-label { color:var(--muted); font:500 .68rem 'DM Mono'; text-transform:uppercase; letter-spacing:.1em; }
        .dropzone { border:1px dashed #3c5e99; border-radius:18px; padding:2rem; text-align:center; background:radial-gradient(circle at 50% 0%, #22458133, transparent 55%), rgba(10,16,33,.85); }
        .dropzone-title { font-weight:700; font-size:1.1rem; margin:.7rem 0 .25rem; }
        .dropzone-copy { color:var(--muted); font-size:.85rem; }
        .stage-row { display:flex; align-items:center; gap:.35rem; overflow:auto; padding:.4rem 0; }
        .stage { min-width:82px; text-align:center; color:#697591; font:500 .6rem 'DM Mono'; letter-spacing:.05em; text-transform:uppercase; }
        .stage-dot { width:24px; height:24px; margin:0 auto .35rem; border:1px solid #36405a; border-radius:50%; }
        .stage.active { color:#a7cfff; } .stage.active .stage-dot { background:#4e9cff; border-color:#9ecbff; box-shadow:0 0 18px #4e9cff88; }
        .connector { height:1px; flex:1; min-width:14px; background:#29334d; }
        .source { border-left:2px solid #7f6cff; padding:.65rem .8rem; margin-top:.7rem; background:#15152b; border-radius:0 10px 10px 0; }
        .source-title { font-weight:700; font-size:.82rem; } .source-meta { color:#8e9ab2; font: .68rem 'DM Mono'; margin-top:.25rem; }
        .source-text { color:#b4bed0; font-size:.78rem; margin-top:.5rem; line-height:1.5; }
        .chat-user { margin:1rem 0 1rem auto; max-width:78%; background:#15284c; border:1px solid #2d5592; padding:.9rem 1rem; border-radius:14px 14px 4px 14px; }
        .chat-assistant { max-width:88%; background:#101629; border:1px solid #273351; padding:1.15rem 1.25rem; border-radius:4px 14px 14px 14px; line-height:1.7; }
        .graph { display:flex; flex-direction:column; align-items:center; gap:.25rem; padding:1.2rem; }
        .node { border:1px solid #334c7e; border-radius:999px; padding:.38rem .85rem; color:#bdd8ff; font:500 .68rem 'DM Mono'; background:#111a30; }
        .arrow { color:#737c9d; font:1rem 'DM Mono'; }
        [data-testid="stSidebar"] { background:#080b14; border-right:1px solid #1b2338; }
        [data-testid="stSidebar"] .block-container { padding:1.5rem 1rem; }
        [data-testid="stFileUploader"] { background:transparent; }
        button[kind="primary"] { background:linear-gradient(110deg,#2f83ef,#7658dd)!important; border:0!important; }
        .stButton button { border-radius:10px; border-color:#2b3857; }
        @media(max-width:760px){ .block-container{padding:1.25rem 1rem 3rem;} .hero-title{font-size:2.8rem;} .chat-user,.chat-assistant{max-width:100%;} }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.html(
        """
        <script>
        (() => {
          const install = () => {
            if (window.__nexaPaletteInstalled) return;
            window.__nexaPaletteInstalled = true;
            const host = window.parent.document;
            const palette = host.createElement("div");
            palette.id = "nexa-command-palette";
            palette.innerHTML = `
              <div class="nexa-palette-backdrop"></div>
              <div class="nexa-palette">
                <div class="nexa-palette-kicker">COMMAND DECK <span>ESC</span></div>
                <input autofocus placeholder="Search workspace..." />
                <button data-action="chat">✦ <b>New chat</b><small>Start a clean thread</small></button>
                <button data-action="docs">▣ <b>Search documents</b><small>Jump to your library</small></button>
                <button data-action="upload">↥ <b>Upload PDF</b><small>Add a knowledge source</small></button>
              </div>`;
            const style = host.createElement("style");
            style.textContent = `
              #nexa-command-palette{display:none;position:fixed;inset:0;z-index:99999;font-family:Manrope, sans-serif}
              #nexa-command-palette.open{display:block}.nexa-palette-backdrop{position:absolute;inset:0;background:#02040bcc;backdrop-filter:blur(8px)}
              .nexa-palette{position:relative;width:min(520px,calc(100vw - 32px));margin:14vh auto;background:#0d1120;border:1px solid #33466d;border-radius:16px;padding:14px;box-shadow:0 30px 90px #000}
              .nexa-palette-kicker{padding:4px 8px 10px;color:#7f8eac;font:11px 'DM Mono',monospace;letter-spacing:.12em}.nexa-palette-kicker span{float:right}
              .nexa-palette input{width:100%;box-sizing:border-box;background:#080b14;border:1px solid #263453;color:#fff;border-radius:9px;padding:12px;margin-bottom:8px;outline:none}
              .nexa-palette button{display:grid;grid-template-columns:25px 1fr;gap:0;text-align:left;width:100%;background:transparent;border:0;border-radius:9px;color:#dce8ff;padding:11px;cursor:pointer}
              .nexa-palette button:hover{background:#17233d}.nexa-palette small{grid-column:2;color:#75839e;margin-top:3px}`;
            host.head.appendChild(style); host.body.appendChild(palette);
            const close=()=>palette.classList.remove("open");
            const clickText=(text)=>{[...host.querySelectorAll("label,button")].find(x=>x.innerText.includes(text))?.click();};
            host.addEventListener("keydown", e => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase()==="k"){e.preventDefault();palette.classList.add("open");palette.querySelector("input").focus()} if(e.key==="Escape") close();});
            palette.querySelector(".nexa-palette-backdrop").onclick=close;
            palette.querySelectorAll("button").forEach(button=>button.onclick=()=>{const action=button.dataset.action;close(); if(action==="chat")clickText("New chat"); if(action==="docs")clickText("Documents"); if(action==="upload")clickText("Upload PDF")});
          };
          if (window.parent.document.readyState === "loading") window.parent.document.addEventListener("DOMContentLoaded", install); else install();
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )
