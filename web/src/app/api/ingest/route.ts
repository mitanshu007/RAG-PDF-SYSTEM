import {NextRequest,NextResponse} from "next/server";
import {adminSupabase,getUserFromRequest} from "../../../lib/server-auth";
export const dynamic="force-dynamic"; export const maxDuration=60;
export async function POST(request:NextRequest){
 try{
  const user=await getUserFromRequest(request); const body=await request.json();
  const {documentId,filename,chunks}=body;
  if(!documentId||!filename||!Array.isArray(chunks)||!chunks.length)return NextResponse.json({error:"documentId, filename and chunks are required"},{status:400});
  if(chunks.length>1000)return NextResponse.json({error:"Too many chunks in one request"},{status:400});
  const supabase=adminSupabase();
  const {error:docError}=await supabase.from("documents").upsert({id:documentId,user_id:user.id,filename,status:"processing"});
  if(docError)throw docError;
  const qdrantUrl=(process.env.QDRANT_URL||"").replace(/\/$/,""); const collection=process.env.QDRANT_COLLECTION||"docs";
  if(!qdrantUrl)throw new Error("QDRANT_URL is not configured");
  const points=chunks.map((c:{id:string;vector:number[];page:number;text:string},i:number)=>({id:c.id||documentId+"-"+i,vector:c.vector,payload:{source:filename,filename,document_id:documentId,user_id:user.id,page_number:c.page,chunk_id:c.id||documentId+"-"+i,text:c.text}}));
  const headers:Record<string,string>={"Content-Type":"application/json"}; if(process.env.QDRANT_API_KEY)headers["api-key"]=process.env.QDRANT_API_KEY;
  const response=await fetch(qdrantUrl+"/collections/"+encodeURIComponent(collection)+"/points?wait=true",{method:"PUT",headers,body:JSON.stringify({points}),cache:"no-store"});
  if(!response.ok)throw new Error("Qdrant error: "+await response.text());
  await supabase.from("documents").update({status:"ready"}).eq("id",documentId).eq("user_id",user.id);
  return NextResponse.json({ok:true,documentId,chunks:points.length});
 }catch(error){return NextResponse.json({error:error instanceof Error?error.message:"Ingestion failed"},{status:500});}
}