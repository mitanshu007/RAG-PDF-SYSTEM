"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import {supabaseBrowser} from "../lib/supabase";

type Doc={id:string;filename:string;status:string;created_at:string};
type Msg={role:"user"|"ai";text:string;sources?:{page:number|null;text:string;score:number}[]};

let extractorPromise:Promise<any>|null=null;
async function getExtractor(){
 if(!extractorPromise){extractorPromise=(async()=>{const {pipeline}=await import("@huggingface/transformers");return pipeline("feature-extraction","Xenova/all-MiniLM-L6-v2",{dtype:"fp32"});})();}
 return extractorPromise;
}
async function embed(text:string){const extractor=await getExtractor();const out=await extractor(text,{pooling:"mean",normalize:true});return Array.from(out.data) as number[];}
async function extractPdf(file:File){
 const pdfjs=await import("pdfjs-dist"); const buffer=await file.arrayBuffer(); const pdf=await pdfjs.getDocument({data:buffer}).promise;
 const pages:{page:number;text:string}[]=[];
 for(let i=1;i<=pdf.numPages;i++){const p=await pdf.getPage(i);const c=await p.getTextContent();pages.push({page:i,text:c.items.map((x:any)=>x.str||"").join(" ").replace(/\s+/g," ").trim()});}
 return pages;
}
function chunkText(text:string,size=1000,overlap=150){const out:string[]=[];for(let i=0;i<text.length;i+=size-overlap)out.push(text.slice(i,i+size));return out.filter(x=>x.trim());}

export default function Workspace(){
 const supabase=useMemo(()=>supabaseBrowser(),[]); const [session,setSession]=useState<any>(null); const [docs,setDocs]=useState<Doc[]>([]);
 const [selected,setSelected]=useState<string>(""); const [messages,setMessages]=useState<Msg[]>([]); const [question,setQuestion]=useState("");
 const [tab,setTab]=useState("Overview"); const [busy,setBusy]=useState(false); const [notice,setNotice]=useState("Ready");
 const fileRef=useRef<HTMLInputElement>(null);

 useEffect(()=>{supabase.auth.getSession().then(({data})=>setSession(data.session));const {data}=supabase.auth.onAuthStateChange((_e,s)=>setSession(s));return()=>data.subscription.unsubscribe();},[supabase]);
 useEffect(()=>{if(session)loadDocs();},[session]);
 async function auth(provider:"google"|"github"){await supabase.auth.signInWithOAuth({provider,options:{redirectTo:window.location.origin}});}
 async function loadDocs(){const s=await supabase.auth.getSession();if(!s.data.session)return;const r=await fetch("/api/documents",{headers:{Authorization:"Bearer "+s.data.session.access_token}});const j=await r.json();if(r.ok)setDocs(j.documents||[]);}
 async function upload(file:File){
  if(file.type!=="application/pdf"){setNotice("Only PDF files are supported.");return;} setBusy(true);setNotice("Reading PDF…");
  try{
   const pages=await extractPdf(file);const chunks:{id:string;page:number;text:string;vector:number[]}[]=[];
   for(const p of pages){for(const t of chunkText(p.text)){setNotice("Embedding PDF chunks…");chunks.push({id:crypto.randomUUID(),page:p.page,text:t,vector:await embed(t)});}}
   const documentId=crypto.randomUUID();const s=await supabase.auth.getSession();if(!s.data.session)throw new Error("Please sign in again.");
   const r=await fetch("/api/ingest",{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+s.data.session.access_token},body:JSON.stringify({documentId,filename:file.name,chunks})});
   const j=await r.json();if(!r.ok)throw new Error(j.error||"Upload failed");setNotice("PDF indexed successfully.");await loadDocs();setSelected(documentId);setTab("AI Chat");
  }catch(e){setNotice(e instanceof Error?e.message:"Upload failed");}finally{setBusy(false);}
 }
 async function ask(){
  if(!question.trim()||!selected||busy)return;const q=question.trim();setQuestion("");setMessages(m=>[...m,{role:"user",text:q}]);setBusy(true);setNotice("Searching selected PDF…");
  try{const vector=await embed(q);const s=await supabase.auth.getSession();if(!s.data.session)throw new Error("Please sign in again.");const r=await fetch("/api/query",{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+s.data.session.access_token},body:JSON.stringify({question:q,documentId:selected,vector,topK:5,responseStyle:"balanced"})});const j=await r.json();if(!r.ok)throw new Error(j.error||"Query failed");setMessages(m=>[...m,{role:"ai",text:j.answer,sources:j.sources}]);setNotice("Answer generated.");}catch(e){setMessages(m=>[...m,{role:"ai",text:e instanceof Error?e.message:"Query failed"}]);setNotice("Query failed.");}finally{setBusy(false);}
 }
 if(!session)return <main className="main" style={{maxWidth:650,margin:"80px auto"}}><div className="card"><div className="brand"><span>NEXA</span> — Knowledge Workspace</div><h1 style={{marginTop:28}}>Private PDF intelligence</h1><p className="muted">Sign in to upload PDFs and chat only with your selected document.</p><div className="row" style={{marginTop:24}}><button className="btn primary" onClick={()=>auth("google")}>Continue with Google</button><button className="btn" onClick={()=>auth("github")}>Continue with GitHub</button></div><p className="muted" style={{fontSize:12,marginTop:20}}>Your document queries are scoped by your account and selected PDF.</p></div></main>;
 return <div className="nexa-shell"><aside className="sidebar"><div className="brand"><span>NEXA</span></div><div className="nav">{["Overview","Documents","AI Chat","Settings"].map(x=><button key={x} className={tab===x?"active":""} onClick={()=>setTab(x)}>{x}</button>)}</div><div className="userbox">{session.user.email}<br/><button className="btn" style={{marginTop:10,width:"100%"}} onClick={()=>supabase.auth.signOut()}>Sign out</button></div></aside>
 <main className="main"><div className="topbar"><div><h1>{tab}</h1><div className="muted">NEXA — private PDF knowledge workspace</div></div><div className="muted">{notice}</div></div>
 {tab==="Overview"&&<><div className="grid"><div className="card stat">Documents<strong>{docs.length}</strong></div><div className="card stat">Selected<strong>{selected?"1":"0"}</strong></div><div className="card stat">Mode<strong>PDF-only</strong></div></div><div className="card" style={{marginTop:16}}><h2>Workspace</h2><p className="muted">Upload a PDF, select it, and ask questions grounded only in that PDF.</p><button className="btn primary" onClick={()=>fileRef.current?.click()} disabled={busy}>Upload PDF</button><input ref={fileRef} type="file" accept="application/pdf" hidden onChange={e=>{const f=e.target.files?.[0];if(f)upload(f);e.currentTarget.value="";}}/></div></>}
 {tab==="Documents"&&<div className="card"><div className="row"><h2 style={{marginRight:"auto"}}>Your PDFs</h2><button className="btn primary" onClick={()=>fileRef.current?.click()}>Upload PDF</button><input ref={fileRef} type="file" accept="application/pdf" hidden onChange={e=>{const f=e.target.files?.[0];if(f)upload(f);e.currentTarget.value="";}}/></div><div className="list">{docs.length?docs.map(d=><div className="doc" key={d.id}><div><strong>{d.filename}</strong><div className="muted">{d.status}</div></div><button className={"btn "+(selected===d.id?"primary":"")} onClick={()=>{setSelected(d.id);setMessages([]);setTab("AI Chat")}}>{selected===d.id?"Selected":"Chat"}</button></div>):<div className="empty">No PDFs uploaded yet.</div>}</div></div>}
 {tab==="AI Chat"&&<div className="card chat">{!selected?<div className="empty">Select a PDF from Documents first.</div>:<><div className="muted">Selected PDF: {docs.find(d=>d.id===selected)?.filename||selected}</div><div className="messages">{messages.map((m,i)=><div key={i}><div className={"msg "+m.role}>{m.text}</div>{m.sources?.map((s,j)=><div className="source" key={j}>Page {s.page??"?"} · score {Number(s.score).toFixed(3)}<br/>{s.text.slice(0,300)}{s.text.length>300?"…":""}</div>)}</div>)}</div><div className="composer"><input value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")ask()}} placeholder="Ask something about this PDF…" disabled={busy}/><button className="btn primary" onClick={ask} disabled={busy}>Ask</button></div></>}</div>}
 {tab==="Settings"&&<div className="card"><h2>Settings</h2><p className="muted">Authentication is handled by Supabase. Retrieval is restricted to your user ID and the selected document ID.</p><div className="source">Security boundary: the server verifies the Supabase access token, verifies document ownership, then applies both user_id and document_id filters in Qdrant.</div></div>}
 </main></div>;
}