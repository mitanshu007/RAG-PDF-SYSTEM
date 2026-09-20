import {NextRequest,NextResponse} from "next/server";
import {adminSupabase,getUserFromRequest} from "../../../lib/server-auth";
export const dynamic="force-dynamic"; export const maxDuration=60;
export async function POST(request:NextRequest){
 try{
  const user=await getUserFromRequest(request); const {question,documentId,vector,topK=5,responseStyle="balanced"}=await request.json();
  if(!question||!documentId||!Array.isArray(vector))return NextResponse.json({error:"question, documentId and vector are required"},{status:400});
  const supabase=adminSupabase();
  const {data:document,error:docError}=await supabase.from("documents").select("id,filename").eq("id",documentId).eq("user_id",user.id).maybeSingle();
  if(docError)throw docError; if(!document)return NextResponse.json({error:"Document not found for this user"},{status:404});
  const qdrantUrl=(process.env.QDRANT_URL||"").replace(/\/$/,""); const collection=process.env.QDRANT_COLLECTION||"docs";
  if(!qdrantUrl)throw new Error("QDRANT_URL is not configured");
  const headers:Record<string,string>={"Content-Type":"application/json"}; if(process.env.QDRANT_API_KEY)headers["api-key"]=process.env.QDRANT_API_KEY;
  const search=await fetch(qdrantUrl+"/collections/"+encodeURIComponent(collection)+"/points/search",{method:"POST",headers,body:JSON.stringify({vector,limit:Math.min(Math.max(Number(topK)||5,1),10),with_payload:true,filter:{must:[{key:"user_id",match:{value:user.id}},{key:"document_id",match:{value:documentId}}]}}),cache:"no-store"});
  if(!search.ok)throw new Error("Qdrant search error: "+await search.text());
  const result=await search.json(); const hits=Array.isArray(result.result)?result.result:[];
  const context=hits.map((hit:any,i:number)=>"[Source "+(i+1)+" | Page "+(hit.payload?.page_number??"?")+"]\n"+(hit.payload?.text??"")).join("\n\n");
  if(!context)return NextResponse.json({answer:"I couldn't find relevant content in the selected PDF.",sources:[]});
  let answer="";
  if(process.env.GROQ_API_KEY){
   const groq=await fetch("https://api.groq.com/openai/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+process.env.GROQ_API_KEY},body:JSON.stringify({model:"llama-3.3-70b-versatile",temperature:.15,messages:[{role:"system",content:"You are NEXA, a PDF-grounded assistant. Answer ONLY from the supplied context from the selected PDF. If the answer is not supported by the context, say you cannot find it in the selected PDF. Never use outside knowledge. Response style: "+responseStyle},{role:"user",content:"Question: "+question+"\n\nContext from selected PDF ("+document.filename+"):\n"+context}]})});
   if(!groq.ok)throw new Error("Groq error: "+await groq.text()); const data=await groq.json(); answer=data.choices?.[0]?.message?.content||"No answer was generated.";
  }else answer="Groq is not configured. Retrieved PDF context:\n\n"+context;
  return NextResponse.json({answer,sources:hits.map((hit:any)=>({page:hit.payload?.page_number??null,text:hit.payload?.text??"",score:hit.score}))});
 }catch(error){return NextResponse.json({error:error instanceof Error?error.message:"Query failed"},{status:500});}
}