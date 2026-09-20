import {NextRequest,NextResponse} from "next/server";
import {adminSupabase,getUserFromRequest} from "../../../lib/server-auth";
export const dynamic="force-dynamic";
export async function GET(request:NextRequest){
 try{
  const user=await getUserFromRequest(request); const supabase=adminSupabase();
  const {data,error}=await supabase.from("documents").select("id,filename,status,created_at").eq("user_id",user.id).order("created_at",{ascending:false});
  if(error)throw error; return NextResponse.json({documents:data??[]});
 }catch(error){return NextResponse.json({error:error instanceof Error?error.message:"Unauthorized"},{status:401});}
}